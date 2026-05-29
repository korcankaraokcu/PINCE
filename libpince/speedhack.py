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

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable
import os
import struct
import time

from . import debugcore, typedefs, utils
from .utils import logger

ALLOC_NAME = "PINCE_speedhack"
CAVE_SIZE = 0x400

# The spinbox in MainWindow.ui owns the allowed range (0.2-10.0).
STEP = 0.1
DEFAULT_SPEED = 1.0

# Only the four wall/uptime clocks are scaled.
# CPU clocks (2, 3) and coarse clocks (5, 6) are passed through.
SCALED_CLOCK_IDS = (
    time.CLOCK_REALTIME,  # 0
    time.CLOCK_MONOTONIC,  # 1
    time.CLOCK_MONOTONIC_RAW,  # 4
    time.CLOCK_BOOTTIME,  # 7
)
NUM_OFFSET = 8 * 16
DEN_OFFSET = NUM_OFFSET + 8
STATE_SIZE = DEN_OFFSET + 8

# Absolute jump: movabs rax, imm64; jmp rax (12 bytes).
JUMP_SIZE = 12

# Syscall number because nanosleep has no vDSO entry, so it always goes through syscall.
SYS_NANOSLEEP = 35


@dataclass
class HookPatch:
    symbol: str
    address: int
    original_aob: str


@dataclass
class Session:
    enabled: bool = False
    speed: float = 1.0
    num: int = 1
    den: int = 1
    state_address: int = 0
    hooks: list[HookPatch] = field(default_factory=list)


session = Session()


def is_installed() -> bool:
    return session.enabled


@debugcore.execute_with_temporary_interruption
def _install(speed: float = 1.0) -> bool:
    # Patch libc time functions in the inferior to scale its perceived time.
    # Internal: callers use set_speed(), which installs on first use.
    global session
    if session.enabled:
        logger.error("Speedhack is already installed")
        return False
    if debugcore.currentpid == -1:
        logger.error("Speedhack requires an attached process")
        return False
    if debugcore.inferior_arch != typedefs.INFERIOR_ARCH.ARCH_64:
        logger.error("Speedhack currently supports only x86_64 inferiors")
        return False
    if ALLOC_NAME in debugcore.allocated_memory_chunks:
        logger.error("Speedhack memory is already allocated")
        return False

    ratio = _speed_to_ratio(speed)
    if ratio is None:
        return False

    vdso_clock_gettime = _resolve_vdso_function(debugcore.currentpid, "__vdso_clock_gettime")
    vdso_gettimeofday = _resolve_vdso_function(debugcore.currentpid, "__vdso_gettimeofday")

    builders: tuple[tuple[str, Callable[[int], bytes]], ...] = (
        ("clock_gettime", lambda cave: _build_clock_gettime_hook(cave, vdso_clock_gettime)),
        ("gettimeofday", lambda cave: _build_gettimeofday_hook(cave, vdso_gettimeofday)),
        ("nanosleep", _build_nanosleep_hook),
    )
    targets = []
    for symbol, build in builders:
        hex_addr = utils.extract_hex_address(debugcore.get_symbol_info(symbol))
        address = utils.safe_str_to_int(hex_addr, 16) if hex_addr else 0
        if not address:
            continue
        original_aob, patch_size = _read_patch_bytes(symbol, address)
        if original_aob is None:
            continue
        targets.append((symbol, address, build, original_aob, patch_size))

    if not targets:
        logger.error("Speedhack couldn't locate any time functions to hook")
        return False

    cave = debugcore.allocate_memory(CAVE_SIZE, ALLOC_NAME)
    if not cave:
        logger.error("Failed to allocate speedhack memory")
        return False

    installed: list[HookPatch] = []
    try:
        _mprotect_cave(cave)
        _initialize_state(cave, ratio.numerator, ratio.denominator)

        # Lay hooks out after the state block, 16-byte aligned.
        cursor = (cave + STATE_SIZE + 15) & ~15
        for symbol, address, build, original_aob, patch_size in targets:
            code = build(cave)
            if cursor + len(code) > cave + CAVE_SIZE:
                raise RuntimeError(f"Speedhack code cave is too small for {symbol}")
            debugcore.write_memory(cursor, typedefs.VALUE_INDEX.AOB, list(code))
            # movabs rax, cursor; jmp rax (12 bytes), NOP-padded out to whole instructions.
            patch = b"\x48\xb8" + struct.pack("<Q", cursor) + b"\xff\xe0" + b"\x90" * (patch_size - JUMP_SIZE)
            debugcore.modify_instruction(address, _bytes_to_aob(patch))
            installed.append(HookPatch(symbol, address, original_aob))
            cursor = (cursor + len(code) + 15) & ~15
    except Exception:
        logger.exception("Failed to install speedhack")
        for hook in reversed(installed):
            _restore_hook(hook)
        debugcore.free_memory(ALLOC_NAME)
        return False

    session = Session(
        enabled=True,
        speed=float(speed),
        num=ratio.numerator,
        den=ratio.denominator,
        state_address=cave,
        hooks=installed,
    )
    return True


@debugcore.execute_with_temporary_interruption
def set_speed(speed: float) -> bool:
    """Change the speed multiplier without re-patching anything."""
    if not session.enabled:
        return _install(speed)
    ratio = _speed_to_ratio(speed)
    if ratio is None:
        return False
    _rebase_state(ratio.numerator, ratio.denominator)
    session.speed = float(speed)
    session.num = ratio.numerator
    session.den = ratio.denominator
    return True


# Kept separate from uninstall() on purpose: if interrupting the inferior fails, the error surfaces to uninstall(),
# which still resets the session state.
# _restore_hook already swallows and logs its own failures, so only free_memory needs a guard here.
@debugcore.execute_with_temporary_interruption
def _do_uninstall() -> bool:
    success = True
    for hook in reversed(session.hooks):
        if not _restore_hook(hook):
            success = False
    if ALLOC_NAME in debugcore.allocated_memory_chunks:
        try:
            if not debugcore.free_memory(ALLOC_NAME):
                success = False
        except Exception:
            logger.exception("Failed to free speedhack memory")
            success = False
    return success


def uninstall() -> bool:
    """Restore the patched functions, free the code cave, and reset module state."""
    global session
    if not session.enabled:
        return True
    success = False
    try:
        success = _do_uninstall()
    except Exception:
        logger.exception("Speedhack uninstall failed")
    session = Session()
    return success


def reset() -> None:
    """Drop module state without touching the inferior.
    Used when the inferior is already gone as the hooks die with the process,
    so there's nothing to restore or free()."""
    global session
    session = Session()
    debugcore.allocated_memory_chunks.pop(ALLOC_NAME, None)


def _speed_to_ratio(speed: float) -> Fraction | None:
    try:
        ratio = Fraction(str(speed)).limit_denominator(1_000_000)
    except Exception:
        logger.exception("Invalid speedhack speed: %s", speed)
        return None
    if ratio <= 0:
        logger.error("Speedhack speed must be greater than zero: %s", speed)
        return None
    return ratio


def _resolve_vdso_function(pid: int, symbol: str) -> int | None:
    # Locate "[vdso]" in the inferior, parse its ELF, and return the absolute address of "symbol".
    # Returns None if the lookup fails. The hook builder then falls back to issuing the syscall itself.
    if pid <= 0:
        return None
    vdso_range = None
    try:
        with open(f"/proc/{pid}/maps") as maps:
            for line in maps:
                if "[vdso]" not in line:
                    continue
                addr_range = line.split(maxsplit=1)[0]
                start_s, end_s = addr_range.split("-")
                vdso_range = (int(start_s, 16), int(end_s, 16))
                break
    except OSError:
        return None
    if vdso_range is None:
        return None
    base, end = vdso_range
    try:
        with debugcore.memory_handle() as mem:
            mem.seek(base)
            blob = mem.read(end - base)
    except OSError:
        return None
    if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4] != 2:
        return None
    # The vDSO is linked at vaddr 0, so dynamic-segment offsets are direct blob indices.
    e_phoff = struct.unpack_from("<Q", blob, 32)[0]
    e_phentsize = struct.unpack_from("<H", blob, 54)[0]
    e_phnum = struct.unpack_from("<H", blob, 56)[0]
    dyn_off = dyn_size = None
    for i in range(e_phnum):
        ph = e_phoff + i * e_phentsize
        if struct.unpack_from("<I", blob, ph)[0] == 2:  # PT_DYNAMIC
            dyn_off = struct.unpack_from("<Q", blob, ph + 16)[0]
            dyn_size = struct.unpack_from("<Q", blob, ph + 32)[0]
            break
    if dyn_off is None:
        return None
    DT_NULL, DT_HASH, DT_STRTAB, DT_SYMTAB = 0, 4, 5, 6
    strtab = symtab = hashtab = None
    for i in range(0, dyn_size, 16):
        tag, val = struct.unpack_from("<qQ", blob, dyn_off + i)
        if tag == DT_NULL:
            break
        if tag == DT_HASH:
            hashtab = val
        elif tag == DT_STRTAB:
            strtab = val
        elif tag == DT_SYMTAB:
            symtab = val
    if None in (strtab, symtab, hashtab):
        return None
    nchain = struct.unpack_from("<I", blob, hashtab + 4)[0]
    target = symbol.encode() + b"\x00"
    for i in range(nchain):
        sym = symtab + i * 24
        if sym + 24 > len(blob):
            break
        st_name = struct.unpack_from("<I", blob, sym)[0]
        if st_name == 0:
            continue
        name_start = strtab + st_name
        name_end = blob.find(b"\x00", name_start)
        if name_end < 0:
            continue
        if blob[name_start : name_end + 1] == target:
            return base + struct.unpack_from("<Q", blob, sym + 8)[0]
    return None


def _read_patch_bytes(symbol: str, address: int) -> tuple[str | None, int]:
    # Disassemble enough instructions at "address" to host a 12 bytes jump.
    dump = debugcore.hex_dump(address, 32)
    if not dump or "??" in dump:
        logger.error("Failed to read %s instructions at 0x%x", symbol, address)
        return None, 0
    code = bytes(int(b, 16) for b in dump)
    utils.cs_64.skipdata = False
    consumed = 0
    for _, size, _, _ in utils.cs_64.disasm_lite(code, address):
        consumed += size
        if consumed >= JUMP_SIZE:
            return _bytes_to_aob(code[:consumed]), consumed
    logger.error("Failed to find enough whole instructions to patch %s", symbol)
    return None, 0


def _initialize_state(state_addr: int, num: int, den: int) -> None:
    # Zero the state block then seed real/fake bases for each scaled clock.
    blob = bytearray(STATE_SIZE)
    struct.pack_into("<Q", blob, NUM_OFFSET, num)
    struct.pack_into("<Q", blob, DEN_OFFSET, den)
    for clk in SCALED_CLOCK_IDS:
        now = time.clock_gettime_ns(clk)
        offset = clk * 16
        struct.pack_into("<Q", blob, offset, now)
        struct.pack_into("<Q", blob, offset + 8, now)
    debugcore.write_memory(state_addr, typedefs.VALUE_INDEX.AOB, list(blob))


def _rebase_state(new_num: int, new_den: int) -> None:
    # Re-anchor each clock so fake time stays continuous across speed changes.
    state_addr = session.state_address
    for clk in SCALED_CLOCK_IDS:
        slot = state_addr + clk * 16
        real_base = _read_u64(slot)
        fake_base = _read_u64(slot + 8)
        now = time.clock_gettime_ns(clk)
        new_fake = fake_base + (now - real_base) * session.num // session.den
        debugcore.write_memory(slot, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", now & 0xFFFFFFFFFFFFFFFF)))
        debugcore.write_memory(
            slot + 8, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", new_fake & 0xFFFFFFFFFFFFFFFF))
        )
    debugcore.write_memory(
        state_addr + NUM_OFFSET, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", new_num & 0xFFFFFFFFFFFFFFFF))
    )
    debugcore.write_memory(
        state_addr + DEN_OFFSET, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", new_den & 0xFFFFFFFFFFFFFFFF))
    )


def _vdso_call_or_syscall(vdso_addr: int | None, syscall_nr: int, saves: tuple[str, ...]) -> str:
    # Emit asm that invokes the underlying time function.
    # If "vdso_addr" is set, we call it as a normal C function where the caller-saved regs in "saves" (rdi/rsi) are
    # pushed across the call.
    # SysV ABI needs rsp % 16 == 0 before "call" so we pad with 8 only when an even number of regs are saved.
    # Otherwise we issue the raw syscall, which preserves rdi/rsi for free.
    if vdso_addr is not None:
        saves_push = "\n".join(f"push {r}" for r in saves)
        saves_pop = "\n".join(f"pop {r}" for r in reversed(saves))
        align_pad = 8 if len(saves) % 2 == 0 else 0
        return f"""
            {saves_push}
            sub rsp, {align_pad}
            mov r11, {hex(vdso_addr)}
            call r11
            add rsp, {align_pad}
            {saves_pop}
        """
    return f"""
        mov rax, {syscall_nr}
        syscall
    """


def _build_clock_gettime_hook(state_addr: int, vdso_addr: int | None) -> bytes:
    # rdi = clockid_t, rsi = struct timespec*.
    # endbr64 is there because libc's entry may be reached via an indirect branch on CET-enabled processes.
    invoke = _vdso_call_or_syscall(vdso_addr, 228, ("rdi", "rsi"))
    # For some stupid reason, keystone can't assemble "endbr64" so we just write the bytes directly:
    # 0xF3 0x0F 0x1E 0xFA
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfa
        {invoke}
        test eax, eax
        jne done
        cmp edi, 7
        ja done
        cmp edi, 2
        je done
        cmp edi, 3
        je done
        cmp edi, 5
        je done
        cmp edi, 6
        je done
        mov r11, {hex(state_addr)}
        mov r10d, edi
        shl r10, 4
        add r10, r11
        mov r8, qword ptr [rsi]
        imul r8, r8, 1000000000
        add r8, qword ptr [rsi + 8]
        sub r8, qword ptr [r10]
        mov rax, r8
        mov rcx, qword ptr [r11 + {NUM_OFFSET}]
        mul rcx
        mov rcx, qword ptr [r11 + {DEN_OFFSET}]
        div rcx
        add rax, qword ptr [r10 + 8]
        mov rcx, 1000000000
        xor rdx, rdx
        div rcx
        mov qword ptr [rsi], rax
        mov qword ptr [rsi + 8], rdx
        xor eax, eax
    done:
        ret
    """
    return _assemble_hook(asm)


def _build_gettimeofday_hook(state_addr: int, vdso_addr: int | None) -> bytes:
    # rdi = struct timeval*, rsi = struct timezone* (unused).
    invoke = _vdso_call_or_syscall(vdso_addr, 96, ("rdi",))
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfa
        {invoke}
        test eax, eax
        jne done
        test rdi, rdi
        jz done
        mov r11, {hex(state_addr)}
        mov r8, qword ptr [rdi]
        imul r8, r8, 1000000000
        mov rax, qword ptr [rdi + 8]
        imul rax, rax, 1000
        add r8, rax
        sub r8, qword ptr [r11]
        mov rax, r8
        mov rcx, qword ptr [r11 + {NUM_OFFSET}]
        mul rcx
        mov rcx, qword ptr [r11 + {DEN_OFFSET}]
        div rcx
        add rax, qword ptr [r11 + 8]
        mov rcx, 1000000000
        xor rdx, rdx
        div rcx
        mov qword ptr [rdi], rax
        mov rax, rdx
        mov rcx, 1000
        xor rdx, rdx
        div rcx
        mov qword ptr [rdi + 8], rax
        xor eax, eax
    done:
        ret
    """
    return _assemble_hook(asm)


def _build_nanosleep_hook(state_addr: int) -> bytes:
    # rdi = const struct timespec* req, rsi = struct timespec* rem.
    # Scales req by den/num, retries on EINTR until the full real duration elapses,
    # then zeros the caller's rem (the game perceives a complete sleep).
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfa
        push rsi
        sub rsp, 16
        mov r11, {hex(state_addr)}
        mov r8, qword ptr [rdi]
        imul r8, r8, 1000000000
        add r8, qword ptr [rdi + 8]
        mov rax, r8
        mov rcx, qword ptr [r11 + {DEN_OFFSET}]
        mul rcx
        mov rcx, qword ptr [r11 + {NUM_OFFSET}]
        test rcx, rcx
        jz cleanup
        div rcx
        mov rcx, 1000000000
        xor rdx, rdx
        div rcx
        mov qword ptr [rsp], rax
        mov qword ptr [rsp + 8], rdx
    retry:
        mov rdi, rsp
        mov rsi, rsp
        mov rax, {SYS_NANOSLEEP}
        syscall
        test rax, rax
        jz cleanup
        cmp rax, -4
        je retry
    cleanup:
        add rsp, 16
        pop rsi
        test rsi, rsi
        jz done
        mov qword ptr [rsi], 0
        mov qword ptr [rsi + 8], 0
    done:
        xor eax, eax
        ret
    """
    return _assemble_hook(asm)


def _restore_hook(hook: HookPatch) -> bool:
    try:
        if hook.address in debugcore.modified_instructions_dict:
            debugcore.restore_instruction(hook.address)
        else:
            debugcore.write_memory(hook.address, typedefs.VALUE_INDEX.AOB, hook.original_aob)
        return True
    except Exception:
        logger.exception("Failed to restore %s", hook.symbol)
        return False


def _assemble_hook(asm: str) -> bytes:
    encoded = utils.assemble(asm, 0, typedefs.INFERIOR_ARCH.ARCH_64)
    if encoded is None:
        raise RuntimeError("Failed to assemble speedhack hook")
    return bytes(encoded[0])


def _bytes_to_aob(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def _read_u64(address: int) -> int:
    result = debugcore.read_memory(address, typedefs.VALUE_INDEX.INT64)
    return int(result) if result is not None else 0


def _mprotect_cave(address: int) -> None:
    # malloc only guarantees 16-byte alignment, so the cave can start anywhere within a page and straddle into the next.
    # We mprotect both pages unconditionally, which is cheaper than checking and harmless if only one is used.
    page = os.sysconf("SC_PAGE_SIZE")
    start = address & ~(page - 1)
    debugcore.send_command(f"p (int)mprotect({start}, {2 * page}, 7)")
