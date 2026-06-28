# -*- coding: utf-8 -*-
"""
Copyright (C) 2026 brkzlr <brksys@icloud.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# linux_speedhack.py scales the Linux clocks a process reads. Wine games don't read those directly,
# they go through Wine's ntdll, so we scale there instead.
#
# We only touch QueryPerformanceCounter: the hook calls the original through a trampoline and
# scales the value it returns, so the clock stays continuous no matter how Wine computes QPC
# (mainline uses CLOCK_BOOTTIME, Proton a TSC counter).

# Why only QueryPerformanceCounter:
# A clock gets used two ways: the value a game reads to pace itself and the deadlines the kernel waits on for it.
# We can only safely scale a clock the kernel never turns into a wait deadline.
# QPC qualifies, none of Wine's wait backends (ntsync/fsync/esync/the wineserver) build a deadline from it,
# so a fast QPC can't make the kernel wait against a drifted clock. Worst case a game just doesn't speed up.
#
# System time is the opposite: a game can "wait until system time T" and Wine turns that into a real-clock deadline.
# Scale the read but not the deadline and the kernel sits waiting for real time to crawl up to a fake-future value,
# so the game hangs.
# Scaling anything but QPC therefore means also rewriting every wait timeout, much bigger and riskier.
#
# Cost of QPC-only: games pacing off Sleep/GetTickCount/system time won't respond, real-time waits
# (frame pacing, vsync, audio) don't scale so slow-mo and high multipliers can be uneven, and QPC
# drifts from system time while active.
#
# TODO BRK later if necessary: hook the wait entries (NtDelayExecution, NtWaitForSingleObject/Multiple,
# NtSignalAndWaitForSingleObject) and rewrite the Windows timeout before Wine converts it,
# plus scale NtQuerySystemTime to match.

from __future__ import annotations

from dataclasses import dataclass, field
import io
import os
import re
import struct

import capstone
from capstone import x86 as cs_x86

from . import debugcore, linux_speedhack, typedefs, utils
from .utils import logger

ALLOC_NAME = "PINCE_wine_speedhack"
CAVE_SIZE = 0x1000

# Mirror linux_speedhack so PINCE can drive either module through one interface (the speedhack property).
STEP = linux_speedhack.STEP
DEFAULT_SPEED = linux_speedhack.DEFAULT_SPEED
JUMP_SIZE = linux_speedhack.JUMP_SIZE  # x86_64 detour: movabs rax, imm64; jmp rax (12 bytes)
JUMP_SIZE_32 = linux_speedhack.JUMP_SIZE_32  # i386 detour: mov eax, imm32; jmp eax (7 bytes)

# State block layout, all 8-byte little-endian. real/fake are in QPC's own units (whatever Wine returns),
# so the Python side never needs to know that unit.
NUM_OFFSET = 0
DEN_OFFSET = 8
INIT_OFFSET = 16  # 0 until the first hook call captures the base
REAL_BASE_OFFSET = 24  # original QPC value at install / last speed change
FAKE_BASE_OFFSET = 32  # fake QPC value at that same instant
LAST_REAL_OFFSET = 40  # most recent original QPC value, so a rebase stays continuous
LAST_FAKE_OFFSET = 48  # most recent fake QPC value
STATE_SIZE = 56

_cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_cs.detail = True
_cs_32 = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_cs_32.detail = True


@dataclass
class Session:
    # Speed/ratio aren't tracked here (unlike linux_speedhack.Session): the live ratio lives in the cave
    # and the rebase reads it back from there, so the Python side only needs these three.
    enabled: bool = False
    state_address: int = 0
    hooks: list[linux_speedhack.HookPatch] = field(default_factory=list)


session = Session()


def is_installed() -> bool:
    return session.enabled


@debugcore.execute_with_temporary_interruption
def _install(speed: float = 1.0) -> bool:
    # Hook RtlQueryPerformanceCounter in the inferior to scale its perceived time.
    # Callers use set_speed(), which installs on first use.
    # We hook only Rtl (not Nt): games reach QPC through it, and it scales right on both Proton
    # (Rtl computes QPC inline) and mainline (Rtl calls Nt) without double counting.
    global session
    if session.enabled:
        logger.error("Wine speedhack is already installed")
        return False
    if debugcore.currentpid == -1:
        logger.error("Wine speedhack requires an attached process")
        return False
    if ALLOC_NAME in debugcore.allocated_memory_chunks:
        logger.error("Wine speedhack memory is already allocated")
        return False

    ratio = linux_speedhack._speed_to_ratio(speed)
    if ratio is None:
        return False

    arch64 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64
    symbol = "RtlQueryPerformanceCounter"
    address = _resolve_ntdll_export(debugcore.currentpid, symbol, arch64)
    if not address:
        logger.error("Wine speedhack couldn't resolve %s", symbol)
        return False
    if arch64:
        original_aob, patch_size = linux_speedhack._read_patch_bytes(symbol, address)
    else:
        original_aob, patch_size = linux_speedhack._read_patch_bytes(symbol, address, utils.cs_32, JUMP_SIZE_32)
    if original_aob is None:
        return False
    raw = bytes.fromhex(original_aob.replace(" ", ""))

    cave = debugcore.allocate_memory(CAVE_SIZE, ALLOC_NAME)
    if not cave:
        logger.error("Failed to allocate Wine speedhack memory")
        return False

    installed: list[linux_speedhack.HookPatch] = []
    try:
        linux_speedhack._mprotect_cave(cave)
        _initialize_state(cave, ratio.numerator, ratio.denominator)
        # Wine maps ntdll read-execute, so make the page writable before patching it.
        linux_speedhack._ensure_writable(address)
        # Step every thread off the patch site first.
        # A thread stopped mid-prologue would resume on a torn instruction stream once we continue,
        # corrupting it for good (QPC is hot enough for that to actually happen, unlike linux native version).
        if not _step_threads_out_of_range(address, address + patch_size):
            raise RuntimeError("Couldn't step all threads out of the patch site")

        # Cave layout: state block, then the trampoline (relocated prologue + jump back into the
        # original), then the wrapper that calls it. 16-byte aligned throughout.
        tramp_addr = (cave + STATE_SIZE + 15) & ~15
        trampoline = _build_trampoline(address, raw, patch_size, arch64, tramp_addr)
        if trampoline is None:
            raise RuntimeError(f"Wine speedhack can't safely relocate the {symbol} prologue")
        wrapper_addr = _write_cave(cave, tramp_addr, trampoline, symbol)
        wrapper = (_build_qpc_wrapper if arch64 else _build_qpc_wrapper_32)(cave, tramp_addr)
        _write_cave(cave, wrapper_addr, wrapper, symbol)

        # Overwrite the entry with an absolute jump into the wrapper, NOP-padded to whole
        # instructions: movabs rax, wrapper; jmp rax (x64) or mov eax, wrapper; jmp eax (i386).
        if arch64:
            jump = b"\x48\xb8" + struct.pack("<Q", wrapper_addr) + b"\xff\xe0"
        else:
            jump = b"\xb8" + struct.pack("<I", wrapper_addr) + b"\xff\xe0"
        patch = jump + b"\x90" * (patch_size - (JUMP_SIZE if arch64 else JUMP_SIZE_32))
        linux_speedhack._write_verified(address, linux_speedhack._bytes_to_aob(patch))
        installed.append(linux_speedhack.HookPatch(symbol, address, original_aob))
    except Exception:
        logger.exception("Failed to install Wine speedhack")
        for hook in installed:
            linux_speedhack._restore_hook(hook)
        debugcore.free_memory(ALLOC_NAME)
        return False

    session = Session(True, cave, installed)
    return True


@debugcore.execute_with_temporary_interruption
def set_speed(speed: float) -> bool:
    """Change the speed multiplier without re-patching anything."""
    if not session.enabled:
        return _install(speed)
    ratio = linux_speedhack._speed_to_ratio(speed)
    if ratio is None:
        return False
    _rebase_state(ratio.numerator, ratio.denominator)
    return True


# Separate from uninstall() on purpose: if interrupting the inferior fails, the error surfaces to
# uninstall(), which still resets the session state.
@debugcore.execute_with_temporary_interruption
def _do_uninstall() -> bool:
    success = True
    for hook in reversed(session.hooks):
        if not linux_speedhack._restore_hook(hook):
            success = False
    # Restoring the entry stops new threads from jumping into the cave. Before freeing it, step any
    # thread still inside the cave back out so free() can't pull the rug out. Best effort: a thread
    # in the original with a pending return into the wrapper isn't caught, but free() of a chunk
    # this small returns it to the heap instead of unmapping, so the bytes stay valid until reused.
    cave = session.state_address
    if cave and not _step_threads_out_of_range(cave, cave + CAVE_SIZE):
        logger.error("Wine speedhack left a thread in the code cave; leaking it instead of freeing")
        debugcore.allocated_memory_chunks.pop(ALLOC_NAME, None)
        return False
    if success and ALLOC_NAME in debugcore.allocated_memory_chunks:
        try:
            if not debugcore.free_memory(ALLOC_NAME):
                success = False
        except Exception:
            logger.exception("Failed to free Wine speedhack memory")
            success = False
    return success


def uninstall() -> bool:
    """Restore the patched function, free the cave, and reset module state.

    Note: Fully removing the hook snaps QPC from the scaled timeline back to the real one.
    If the game was fast-forwarded that's a backward jump, so it briefly stalls while real time
    catches up to the deadlines it latched ahead of itself.
    That's inherent to removing a clock scaler (the fast-forwarded time has to be paid back)
    and dropping to 1.0 first doesn't help since the accumulated skew stays."""
    global session
    if not session.enabled:
        return True
    success = False
    try:
        success = _do_uninstall()
    except Exception:
        logger.exception("Wine speedhack uninstall failed")
    session = Session()
    debugcore.allocated_memory_chunks.pop(ALLOC_NAME, None)
    return success


def reset() -> None:
    """Drop module state without touching the inferior.
    Used when the inferior is already gone as the hooks die with the process,
    so there's nothing to restore or free()."""
    global session
    session = Session()
    debugcore.allocated_memory_chunks.pop(ALLOC_NAME, None)


def _initialize_state(state_addr: int, num: int, den: int) -> None:
    # Zero the block and seed num/den.
    # The base is captured lazily on the first hook call (INIT flag) since we can't read QPC from Python.
    blob = bytearray(STATE_SIZE)
    struct.pack_into("<Q", blob, NUM_OFFSET, num)
    struct.pack_into("<Q", blob, DEN_OFFSET, den)
    debugcore.write_memory(state_addr, typedefs.VALUE_INDEX.AOB, list(blob))


def _rebase_state(new_num: int, new_den: int) -> None:
    # Re-anchor on the latest (original, fake) pair the hook recorded so fake time stays continuous
    # across speed changes.
    # Runs while the inferior is stopped, so no race with the hook updating LAST_*.
    state_addr = session.state_address
    if linux_speedhack._read_u64(state_addr + INIT_OFFSET):
        _write_u64(state_addr + REAL_BASE_OFFSET, linux_speedhack._read_u64(state_addr + LAST_REAL_OFFSET))
        _write_u64(state_addr + FAKE_BASE_OFFSET, linux_speedhack._read_u64(state_addr + LAST_FAKE_OFFSET))
    _write_u64(state_addr + NUM_OFFSET, new_num)
    _write_u64(state_addr + DEN_OFFSET, new_den)


def _build_qpc_wrapper(state_addr: int, tramp_addr: int) -> bytes:
    # RtlQueryPerformanceCounter(LARGE_INTEGER *counter) -> BOOLEAN,
    # Microsoft x64 ABI: rcx = counter, returns TRUE.
    # Call the original (it fills *counter with the real value V),
    # then overwrite *counter with fake = fake_base + (V - real_base) * num / den.
    # Base is captured on the first call (INIT).
    # rsp is 16-byte aligned before the call (entry+8, push rbp, push rcx, sub 40).
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfa
        push rbp
        mov rbp, rsp
        push rcx
        sub rsp, 40
        mov r11, {hex(tramp_addr)}
        call r11
        add rsp, 40
        pop rcx
        mov rax, qword ptr [rcx]
        mov r11, {hex(state_addr)}
        mov r8, qword ptr [r11 + {INIT_OFFSET}]
        test r8, r8
        jnz scale
        mov qword ptr [r11 + {REAL_BASE_OFFSET}], rax
        mov qword ptr [r11 + {FAKE_BASE_OFFSET}], rax
        mov qword ptr [r11 + {INIT_OFFSET}], 1
    scale:
        mov r9, rax
        sub rax, qword ptr [r11 + {REAL_BASE_OFFSET}]
        mov r10, qword ptr [r11 + {NUM_OFFSET}]
        mul r10
        mov r10, qword ptr [r11 + {DEN_OFFSET}]
        div r10
        add rax, qword ptr [r11 + {FAKE_BASE_OFFSET}]
        mov qword ptr [r11 + {LAST_REAL_OFFSET}], r9
        mov qword ptr [r11 + {LAST_FAKE_OFFSET}], rax
        mov qword ptr [rcx], rax
        mov eax, 1
        pop rbp
        ret
    """
    return linux_speedhack._assemble_hook(asm)


def _build_qpc_wrapper_32(state_addr: int, tramp_addr: int) -> bytes:
    # Same idea as the x64 wrapper for i386 __stdcall:
    # the counter pointer is the one stack arg and the callee pops it (ret 4).
    # The 64-bit math (fake = fake_base + (V - real_base) * num / den) runs on 32-bit ops:
    # a 96-bit product (delta_lo*num and delta_hi*num combined) divided word by word by den.
    # num/den fit 32 bits (speeds 0.2-10.0) and the result fits 64 bits for any real session,
    # so the top division word is dropped.
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfb
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        push dword ptr [ebp + 8]
        mov eax, {hex(tramp_addr)}
        call eax
        sub esp, 48
        mov edi, dword ptr [ebp + 8]
        mov eax, dword ptr [edi]
        mov dword ptr [ebp - 40], eax
        mov eax, dword ptr [edi + 4]
        mov dword ptr [ebp - 44], eax
        mov esi, {hex(state_addr)}
        mov eax, dword ptr [esi + {INIT_OFFSET}]
        or eax, dword ptr [esi + {INIT_OFFSET + 4}]
        jnz do_scale
        mov eax, dword ptr [ebp - 40]
        mov dword ptr [esi + {REAL_BASE_OFFSET}], eax
        mov dword ptr [esi + {FAKE_BASE_OFFSET}], eax
        mov eax, dword ptr [ebp - 44]
        mov dword ptr [esi + {REAL_BASE_OFFSET + 4}], eax
        mov dword ptr [esi + {FAKE_BASE_OFFSET + 4}], eax
        mov dword ptr [esi + {INIT_OFFSET}], 1
        mov dword ptr [esi + {INIT_OFFSET + 4}], 0
    do_scale:
        mov eax, dword ptr [ebp - 40]
        sub eax, dword ptr [esi + {REAL_BASE_OFFSET}]
        mov dword ptr [ebp - 16], eax
        mov eax, dword ptr [ebp - 44]
        sbb eax, dword ptr [esi + {REAL_BASE_OFFSET + 4}]
        mov dword ptr [ebp - 20], eax
        mov eax, dword ptr [ebp - 16]
        mov ebx, dword ptr [esi + {NUM_OFFSET}]
        mul ebx
        mov dword ptr [ebp - 24], eax
        mov ecx, edx
        mov eax, dword ptr [ebp - 20]
        mul ebx
        add eax, ecx
        mov dword ptr [ebp - 28], eax
        adc edx, 0
        mov dword ptr [ebp - 32], edx
        mov ebx, dword ptr [esi + {DEN_OFFSET}]
        xor edx, edx
        mov eax, dword ptr [ebp - 32]
        div ebx
        mov eax, dword ptr [ebp - 28]
        div ebx
        mov dword ptr [ebp - 28], eax
        mov eax, dword ptr [ebp - 24]
        div ebx
        mov dword ptr [ebp - 24], eax
        mov eax, dword ptr [ebp - 24]
        add eax, dword ptr [esi + {FAKE_BASE_OFFSET}]
        mov ecx, eax
        mov eax, dword ptr [ebp - 28]
        adc eax, dword ptr [esi + {FAKE_BASE_OFFSET + 4}]
        mov dword ptr [edi], ecx
        mov dword ptr [edi + 4], eax
        mov edx, dword ptr [ebp - 40]
        mov dword ptr [esi + {LAST_REAL_OFFSET}], edx
        mov edx, dword ptr [ebp - 44]
        mov dword ptr [esi + {LAST_REAL_OFFSET + 4}], edx
        mov dword ptr [esi + {LAST_FAKE_OFFSET}], ecx
        mov dword ptr [esi + {LAST_FAKE_OFFSET + 4}], eax
        mov eax, 1
        add esp, 48
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret 4
    """
    return linux_speedhack._assemble_hook(asm, typedefs.INFERIOR_ARCH.ARCH_32)


def _build_trampoline(address: int, raw: bytes, patch_size: int, arch64: bool, tramp_addr: int) -> bytes | None:
    # The trampoline is the overwritten prologue plus a jump back into the rest of the original,
    # so calling it runs the function as if it was never patched.
    # The prologue is copied as is, so bail (None) if it holds anything position dependent we can't move:
    # a relative branch, or on x64 a rip-relative operand (i386 has neither rip-relative nor a 64-bit absolute jump).
    prologue = raw[:patch_size]
    for insn in (_cs if arch64 else _cs_32).disasm(prologue, address):
        if insn.group(capstone.CS_GRP_JUMP) or insn.group(capstone.CS_GRP_CALL) or insn.group(capstone.CS_GRP_RET):
            return None
        if arch64:
            for op in insn.operands:
                if op.type == cs_x86.X86_OP_MEM and op.mem.base == cs_x86.X86_REG_RIP:
                    return None
    target = address + patch_size
    if arch64:
        # jmp qword ptr [rip+0]; <8-byte target>. Position independent, clobbers nothing.
        return prologue + b"\xff\x25\x00\x00\x00\x00" + struct.pack("<Q", target)
    # jmp dword ptr [slot]; <4-byte target> right after it.
    # No rip-relative on i386, and no ret so it can't trip CET shadow-stack checks.
    slot = tramp_addr + len(prologue) + 6
    return prologue + b"\xff\x25" + struct.pack("<I", slot) + struct.pack("<I", target)


def _write_cave(cave: int, address: int, blob: bytes, symbol: str) -> int:
    # Write blob into the cave at address, returning the next 16-byte aligned cursor.
    if address + len(blob) > cave + CAVE_SIZE:
        raise RuntimeError(f"Wine speedhack code cave is too small for {symbol}")
    debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, list(blob))
    return (address + len(blob) + 15) & ~15


def _step_threads_out_of_range(low: int, high: int, max_steps: int = 64) -> bool:
    # Single-step any thread whose program counter sits in [low, high) until it's clear.
    # Runs while the inferior is stopped, so other threads stay frozen while we step one.
    # TODO BRK: Maybe move this to utils in case it might be useful for other stuff?
    info = debugcore.send_command("-thread-info")
    if not info:
        logger.error("Wine speedhack couldn't query thread info")
        return False
    current_match = re.search(r'current-thread-id="(\d+)"', info)
    current_thread = current_match.group(1) if current_match else None

    offenders = [tid for tid, addr in re.findall(r'id="(\d+)",[^}]*?frame=\{[^}]*?addr="(0x[0-9a-fA-F]+)"', info) if low <= int(addr, 16) < high]

    success = True
    for tid in offenders:
        debugcore.send_command(f"thread {tid}")
        stepped_out = False
        for _ in range(max_steps):
            pc = _current_pc()
            if pc is None or not (low <= pc < high):
                stepped_out = True
                break
            debugcore.step_instruction()
            debugcore.wait_for_stop(2)
            if debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                break  # step never settled; bail out and report failure below
        if not stepped_out:
            logger.error("Wine speedhack couldn't step thread %s out of the patch site", tid)
            success = False
            break

    if current_thread is not None:
        debugcore.send_command(f"thread {current_thread}")
    return success


def _current_pc() -> int | None:
    registers = debugcore.read_registers()
    if not registers:
        return None
    raw = registers.get("rip") or registers.get("eip")
    pc = utils.extract_hex_address(str(raw)) if raw is not None else None
    return int(pc, 16) if pc else None


def _write_u64(address: int, value: int) -> None:
    debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)))


def _resolve_ntdll_export(pid: int, symbol: str, arch64: bool = True) -> int | None:
    # Resolve a named ntdll.dll export to its runtime address.
    # gdb doesn't know PE exports, so we parse the export directory out of inferior memory.
    # A loaded PE spans several mappings, the one at file offset 0 holds the headers and its start is the image base.
    # A WoW64 prefix can map both a 32 and 64-bits ntdll,
    # so try each and let _parse_pe_export drop the one whose bitness doesn't match.
    if pid <= 0:
        return None
    try:
        bases = [
            int(start, 16)
            for start, _, _, map_offset, _, _, path in utils.get_regions(pid)
            if path and os.path.basename(path).lower() == "ntdll.dll" and int(map_offset, 16) == 0
        ]
        with debugcore.memory_handle() as mem:
            for base in bases:
                address = _parse_pe_export(mem, base, symbol, arch64)
                if address:
                    return address
    except OSError:
        return None
    return None


def _parse_pe_export(mem: io.BufferedReader, base: int, symbol: str, arch64: bool = True) -> int | None:
    # Walk a loaded PE's export directory.
    # In a loaded image an RVA is just an offset from the base.
    # The data directory sits at optional-header offset 112 on PE32+ (x86_64) but 96 on PE32 (i386),
    # since PE32's ImageBase/pointers are 4 bytes instead of 8.
    def read(addr: int, size: int) -> bytes:
        mem.seek(addr)
        return mem.read(size)

    header = read(base, 0x400)
    if len(header) < 0x40 or header[:2] != b"MZ":
        return None
    e_lfanew = struct.unpack_from("<I", header, 0x3C)[0]
    if e_lfanew + 4 + 20 + 2 > len(header) or header[e_lfanew : e_lfanew + 4] != b"PE\x00\x00":
        return None
    opt = e_lfanew + 24  # PE signature (4) + COFF file header (20)
    if struct.unpack_from("<H", header, opt)[0] != (0x20B if arch64 else 0x10B):  # match the inferior's bitness
        return None
    dir_off = 112 if arch64 else 96
    if opt + dir_off + 8 > len(header):
        return None
    export_rva = struct.unpack_from("<I", header, opt + dir_off)[0]
    export_size = struct.unpack_from("<I", header, opt + dir_off + 4)[0]
    if not export_rva:
        return None

    export_dir = read(base + export_rva, 40)
    if len(export_dir) < 40:
        return None
    num_funcs = struct.unpack_from("<I", export_dir, 20)[0]
    num_names = struct.unpack_from("<I", export_dir, 24)[0]
    funcs_rva = struct.unpack_from("<I", export_dir, 28)[0]
    names_rva = struct.unpack_from("<I", export_dir, 32)[0]
    ordinals_rva = struct.unpack_from("<I", export_dir, 36)[0]
    if not (num_names and funcs_rva and names_rva and ordinals_rva):
        return None

    names = read(base + names_rva, num_names * 4)
    ordinals = read(base + ordinals_rva, num_names * 2)
    funcs = read(base + funcs_rva, num_funcs * 4)
    if len(names) < num_names * 4 or len(ordinals) < num_names * 2 or len(funcs) < num_funcs * 4:
        return None

    target = symbol.encode()
    for i in range(num_names):
        name_rva = struct.unpack_from("<I", names, i * 4)[0]
        name_bytes = read(base + name_rva, len(target) + 1)
        if name_bytes[: len(target)] != target or name_bytes[len(target) : len(target) + 1] != b"\x00":
            continue
        ordinal = struct.unpack_from("<H", ordinals, i * 2)[0]
        if ordinal >= num_funcs:
            return None
        func_rva = struct.unpack_from("<I", funcs, ordinal * 4)[0]
        if not func_rva:
            return None
        if export_rva <= func_rva < export_rva + export_size:  # an RVA inside the dir is a forwarder string, not code
            logger.error("Wine speedhack: %s is a forwarder, can't hook", symbol)
            return None
        return base + func_rva
    return None
