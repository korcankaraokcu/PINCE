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

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable
import capstone
from capstone import Cs
from capstone import x86 as cs_x86
import io
import os
import re
import struct
import time

from . import debugcore, typedefs, utils
from .utils import logger

CAVE_SIZE = 0x1000
CAVE_MARKER = b"PINCE_SPEEDHACK\0"
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
CLOCK_SLOT_SIZE = 16
NUM_OFFSET = (max(SCALED_CLOCK_IDS) + 1) * CLOCK_SLOT_SIZE
DEN_OFFSET = NUM_OFFSET + 8
BUFFER_SIZE = DEN_OFFSET + 8
ACTIVE_OFFSET = BUFFER_SIZE * 2
STATE_SIZE = ACTIVE_OFFSET + 8

WINE_NUM_OFFSET = 0
WINE_DEN_OFFSET = 8
WINE_INIT_OFFSET = 16
WINE_REAL_BASE_OFFSET = 24
WINE_FAKE_BASE_OFFSET = 32
WINE_LAST_REAL_OFFSET = 40
WINE_LAST_FAKE_OFFSET = 48
WINE_STATE_SIZE = 56

# Absolute jump: movabs rax, imm64; jmp rax (12 bytes).
JUMP_SIZE = 12

# x86_64 syscall numbers. clock_gettime/gettimeofday use the syscall only as a vDSO fallback.
# nanosleep has no vDSO entry so it always goes through the syscall.
SYS_CLOCK_GETTIME = 228
SYS_GETTIMEOFDAY = 96
SYS_NANOSLEEP = 35

# i386 detour: mov eax, imm32 (5 bytes); jmp eax (2 bytes).
JUMP_SIZE_32 = 7

# i386 syscall numbers (differ from x86_64). nanosleep has no vDSO entry on either arch.
SYS_CLOCK_GETTIME_32 = 265
SYS_GETTIMEOFDAY_32 = 78
SYS_NANOSLEEP_32 = 162

_cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
_cs.detail = True
_cs_32 = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_cs_32.detail = True


@dataclass
class _LinuxSession:
    enabled: bool = False
    num: int = 1
    den: int = 1
    state_address: int = 0


@dataclass
class _WineSession:
    enabled: bool = False
    state_address: int = 0


def _run_stopped(callback: Callable[[], bool]) -> bool:
    was_running = debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
    if was_running and not debugcore.interrupt_inferior(typedefs.STOP_REASON.PAUSE):
        logger.error("Speedhack requires stopping the inferior, but interrupt timed out")
        return False
    if debugcore.inferior_status != typedefs.INFERIOR_STATUS.STOPPED:
        logger.error("Speedhack requires a stopped inferior")
        return False
    try:
        return callback()
    finally:
        if was_running:
            debugcore.continue_inferior()
            resumed = False
            for _ in range(10_000):
                if debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING or debugcore.currentpid == -1:
                    resumed = True
                    break
                time.sleep(0.0001)
            if not resumed:
                logger.error("Speedhack continue did not report RUNNING within 1s")


class _Speedhack:
    def __init__(self) -> None:
        self._session = self._session_type()

    def is_installed(self) -> bool:
        return self._session.enabled

    def _install(self, speed: float) -> bool:
        return _run_stopped(lambda: self._install_stopped(speed))

    def _install_ratio(self, speed: float) -> Fraction | None:
        if self._session.enabled:
            logger.error("%s speedhack is already installed", self._name)
            return None
        if debugcore.currentpid == -1:
            logger.error("%s speedhack requires an attached process", self._name)
            return None
        if self._alloc_name in debugcore.allocated_cave_chunks:
            logger.error("%s speedhack memory is already allocated", self._name)
            return None
        return _speed_to_ratio(speed)

    def reset(self) -> None:
        self._session = self._session_type()
        debugcore.allocated_cave_chunks.pop(self._alloc_name, None)


class LinuxSpeedhack(_Speedhack):
    _name = "Linux"
    _alloc_name = "PINCE_linux_speedhack"
    _session_type = _LinuxSession

    def _install_stopped(self, speed: float) -> bool:
        ratio = self._install_ratio(speed)
        if ratio is None:
            return False

        arch64 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64
        vdso_clock_gettime = _resolve_vdso_function(debugcore.currentpid, "__vdso_clock_gettime", arch64)
        vdso_gettimeofday = _resolve_vdso_function(debugcore.currentpid, "__vdso_gettimeofday", arch64)

        if arch64:
            builders = (
                ("clock_gettime", _build_clock_gettime_hook, vdso_clock_gettime),
                ("gettimeofday", _build_gettimeofday_hook, vdso_gettimeofday),
                ("nanosleep", lambda cave, _: _build_nanosleep_hook(cave), None),
            )
        else:
            builders = (
                ("clock_gettime", _build_clock_gettime_hook_32, vdso_clock_gettime),
                ("gettimeofday", _build_gettimeofday_hook_32, vdso_gettimeofday),
                ("nanosleep", lambda cave, _: _build_nanosleep_hook_32(cave), None),
            )
        disassembler = utils.cs_64 if arch64 else utils.cs_32
        jump_size = JUMP_SIZE if arch64 else JUMP_SIZE_32
        targets = []
        caves = set()
        for symbol, build, call_target in builders:
            hex_addr = utils.extract_hex_address(debugcore.get_symbol_info(symbol))
            entry_address = utils.safe_str_to_int(hex_addr, 16) if hex_addr else debugcore.resolve_libc_symbol(symbol)
            if not entry_address:
                continue
            needs_trampoline = call_target == entry_address
            patch_address = _get_patch_address(entry_address, arch64)
            if (target := _detour_target(patch_address, arch64)) is not None:
                if not _has_marker(target):
                    logger.error("%s is already hooked", symbol)
                    return False
                caves.add(target & -CAVE_SIZE)
                continue
            original_aob, patch_size = _read_patch_bytes(symbol, patch_address, disassembler, jump_size)
            if original_aob is None:
                continue
            targets.append((symbol, patch_address, build, call_target, needs_trampoline, original_aob, patch_size))

        if caves:
            if len(caves) != 1 or targets:
                logger.error("Linux speedhack hooks don't match")
                return False
            cave = caves.pop()
            state = cave + (_read_u64(cave + ACTIVE_OFFSET) & 1) * BUFFER_SIZE
            num, den = _read_u64(state + NUM_OFFSET), _read_u64(state + DEN_OFFSET)
            if not num or not den:
                logger.error("Linux speedhack state is invalid")
                return False
            self._session = _LinuxSession(True, num, den, cave)
            self._rebase_state(ratio.numerator, ratio.denominator)
            return True

        if not targets:
            logger.error("Linux speedhack couldn't locate any time functions to hook")
            return False

        cave = debugcore.allocate_cave(CAVE_SIZE, self._alloc_name)
        if not cave:
            logger.error("Failed to allocate Linux speedhack memory")
            return False

        installed = []
        try:
            self._initialize_state(cave, ratio.numerator, ratio.denominator)
            cursor = (cave + STATE_SIZE + 15) & ~15
            for symbol, address, build, call_target, needs_trampoline, original_aob, patch_size in targets:
                if needs_trampoline:
                    call_target = cursor
                    trampoline = _build_trampoline(address, bytes.fromhex(original_aob), arch64, call_target)
                    if trampoline is None:
                        raise RuntimeError(f"Linux speedhack can't safely relocate the {symbol} prologue")
                    cursor = _write_cave(cave, cursor, trampoline, symbol)
                hook_address = cursor + len(CAVE_MARKER)
                cursor = _write_cave(cave, cursor, CAVE_MARKER + build(cave, call_target), symbol)
                if arch64:
                    patch = b"\x48\xb8" + struct.pack("<Q", hook_address) + b"\xff\xe0" + b"\x90" * (patch_size - JUMP_SIZE)
                else:
                    patch = b"\xb8" + struct.pack("<I", hook_address) + b"\xff\xe0" + b"\x90" * (patch_size - JUMP_SIZE_32)
                _ensure_writable(address)
                if not _step_threads_out_of_range(address, address + patch_size):
                    raise RuntimeError(f"Couldn't step all threads out of {symbol}")
                installed.append((symbol, address, original_aob))
                _write_verified(address, _bytes_to_aob(patch))
        except Exception:
            logger.exception("Failed to install Linux speedhack")
            for hook in reversed(installed):
                _restore_hook(*hook)
            debugcore.free_cave(self._alloc_name)
            return False

        self._session = _LinuxSession(
            enabled=True,
            num=ratio.numerator,
            den=ratio.denominator,
            state_address=cave,
        )
        return True

    def set_speed(self, speed: float) -> bool:
        """Change the speed multiplier without re-patching anything."""
        if not self._session.enabled:
            return self._install(speed)
        ratio = _speed_to_ratio(speed)
        if ratio is None:
            return False
        self._rebase_state(ratio.numerator, ratio.denominator)
        return True

    def _initialize_state(self, state_addr: int, num: int, den: int) -> None:
        buffer = bytearray(BUFFER_SIZE)
        struct.pack_into("<QQ", buffer, NUM_OFFSET, num, den)
        for clk in SCALED_CLOCK_IDS:
            now = time.clock_gettime_ns(clk)
            offset = clk * CLOCK_SLOT_SIZE
            struct.pack_into("<QQ", buffer, offset, now, now)
        _write_verified(state_addr, _bytes_to_aob(bytes(buffer + buffer + b"\0" * 8)))

    def _rebase_state(self, new_num: int, new_den: int) -> None:
        state_addr = self._session.state_address
        active = _read_u64(state_addr + ACTIVE_OFFSET) & 1
        inactive = active ^ 1
        active_base = state_addr + active * BUFFER_SIZE
        inactive_base = state_addr + inactive * BUFFER_SIZE
        old_num = _read_u64(active_base + NUM_OFFSET) or self._session.num
        old_den = _read_u64(active_base + DEN_OFFSET) or self._session.den
        blob = bytearray(BUFFER_SIZE)
        struct.pack_into("<QQ", blob, NUM_OFFSET, new_num, new_den)
        for clk in SCALED_CLOCK_IDS:
            slot = active_base + clk * CLOCK_SLOT_SIZE
            real_base = _read_u64(slot)
            fake_base = _read_u64(slot + 8)
            now = time.clock_gettime_ns(clk)
            delta = max(0, now - real_base)
            new_fake = fake_base + delta * old_num // old_den
            offset = clk * CLOCK_SLOT_SIZE
            struct.pack_into("<QQ", blob, offset, now & 0xFFFFFFFFFFFFFFFF, new_fake & 0xFFFFFFFFFFFFFFFF)
        debugcore.write_memory(inactive_base, typedefs.VALUE_INDEX.AOB, list(blob))
        debugcore.write_memory(state_addr + ACTIVE_OFFSET, typedefs.VALUE_INDEX.AOB, list(struct.pack("<Q", inactive)))
        self._session.num, self._session.den = new_num, new_den


class WineSpeedhack(_Speedhack):
    _name = "Wine"
    _alloc_name = "PINCE_wine_speedhack"
    _session_type = _WineSession

    def _install_stopped(self, speed: float) -> bool:
        ratio = self._install_ratio(speed)
        if ratio is None:
            return False

        arch64 = host_arch64 = debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64
        if host_arch64:
            process_name = utils.get_process_name(debugcore.currentpid).lower()
            exes = sorted(
                (os.path.basename(path).lower() != process_name, int(start, 16))
                for start, _, _, offset, _, _, path in utils.get_regions(debugcore.currentpid)
                if path and int(offset, 16) == 0 and path.lower().endswith(".exe")
            )
            try:
                with debugcore.memory_handle() as mem:
                    for _, base in exes:
                        mem.seek(base)
                        if mem.read(2) != b"MZ":
                            continue
                        mem.seek(base + 0x3C)
                        pe = base + int.from_bytes(mem.read(4), "little")
                        mem.seek(pe)
                        if mem.read(4) != b"PE\x00\x00":
                            continue
                        mem.seek(pe + 0x18)
                        magic = int.from_bytes(mem.read(2), "little")
                        if magic in (0x10B, 0x20B):
                            arch64 = magic == 0x20B
                            break
            except (OSError, ValueError):
                pass
        symbol = "RtlQueryPerformanceCounter"
        address = _resolve_ntdll_export(debugcore.currentpid, symbol, arch64)
        if not address:
            logger.error("Wine speedhack couldn't resolve %s", symbol)
            return False
        address = _get_patch_address(address, arch64)
        if (target := _detour_target(address, arch64)) is not None:
            cave = target & -CAVE_SIZE
            if not _has_marker(target):
                logger.error("%s is already hooked", symbol)
                return False
            if not _read_u64(cave + WINE_NUM_OFFSET) or not _read_u64(cave + WINE_DEN_OFFSET):
                logger.error("Wine speedhack state is invalid")
                return False
            self._session = _WineSession(True, cave)
            self._rebase_state(ratio.numerator, ratio.denominator)
            return True
        if arch64:
            original_aob, patch_size = _read_patch_bytes(symbol, address)
        else:
            original_aob, patch_size = _read_patch_bytes(symbol, address, utils.cs_32, JUMP_SIZE_32)
        if original_aob is None:
            return False
        raw = bytes.fromhex(original_aob.replace(" ", ""))

        cave = debugcore.allocate_cave(CAVE_SIZE, self._alloc_name, 0x50000000 if host_arch64 and not arch64 else None)
        if not cave:
            logger.error("Failed to allocate Wine speedhack memory")
            return False

        installed = []
        try:
            self._initialize_state(cave, ratio.numerator, ratio.denominator)
            _ensure_writable(address)
            if not _step_threads_out_of_range(address, address + patch_size):
                raise RuntimeError("Couldn't step all threads out of the patch site")

            tramp_addr = (cave + WINE_STATE_SIZE + 15) & ~15
            trampoline = _build_trampoline(address, raw, arch64, tramp_addr)
            if trampoline is None:
                raise RuntimeError(f"Wine speedhack can't safely relocate the {symbol} prologue")
            wrapper_start = _write_cave(cave, tramp_addr, trampoline, symbol)
            wrapper_addr = wrapper_start + len(CAVE_MARKER)
            wrapper = (_build_qpc_wrapper if arch64 else _build_qpc_wrapper_32)(cave, tramp_addr)
            _write_cave(cave, wrapper_start, CAVE_MARKER + wrapper, symbol)

            if arch64:
                jump = b"\x48\xb8" + struct.pack("<Q", wrapper_addr) + b"\xff\xe0"
            else:
                jump = b"\xb8" + struct.pack("<I", wrapper_addr) + b"\xff\xe0"
            patch = jump + b"\x90" * (patch_size - (JUMP_SIZE if arch64 else JUMP_SIZE_32))
            installed.append((symbol, address, original_aob))
            _write_verified(address, _bytes_to_aob(patch))
        except Exception:
            logger.exception("Failed to install Wine speedhack")
            for hook in installed:
                _restore_hook(*hook)
            debugcore.free_cave(self._alloc_name)
            return False

        self._session = _WineSession(enabled=True, state_address=cave)
        return True

    def set_speed(self, speed: float) -> bool:
        """Change the speed multiplier without re-patching anything."""
        if not self._session.enabled:
            return self._install(speed)
        ratio = _speed_to_ratio(speed)
        if ratio is None:
            return False
        return _run_stopped(lambda: self._rebase_state(ratio.numerator, ratio.denominator))

    def _initialize_state(self, state_addr: int, num: int, den: int) -> None:
        blob = bytearray(WINE_STATE_SIZE)
        struct.pack_into("<QQ", blob, WINE_NUM_OFFSET, num, den)
        _write_verified(state_addr, _bytes_to_aob(bytes(blob)))

    def _rebase_state(self, new_num: int, new_den: int) -> bool:
        state_addr = self._session.state_address
        if _read_u64(state_addr + WINE_INIT_OFFSET):
            _write_u64(state_addr + WINE_REAL_BASE_OFFSET, _read_u64(state_addr + WINE_LAST_REAL_OFFSET))
            _write_u64(state_addr + WINE_FAKE_BASE_OFFSET, _read_u64(state_addr + WINE_LAST_FAKE_OFFSET))
        _write_u64(state_addr + WINE_NUM_OFFSET, new_num)
        _write_u64(state_addr + WINE_DEN_OFFSET, new_den)
        return True


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


def _resolve_vdso_function(pid: int, symbol: str, arch64: bool = True) -> int | None:
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
    try:
        expected_class = 2 if arch64 else 1  # ELFCLASS64 vs ELFCLASS32
        if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4] != expected_class:
            return None
        # The vDSO is linked at vaddr 0, so dynamic-segment offsets are direct blob indices.
        if arch64:
            e_phoff = struct.unpack_from("<Q", blob, 32)[0]
            e_phentsize = struct.unpack_from("<H", blob, 54)[0]
            e_phnum = struct.unpack_from("<H", blob, 56)[0]
            p_vaddr_off, p_filesz_off = 16, 32  # within Elf64_Phdr
            dyn_entry_size, dyn_fmt = 16, "<qQ"  # Elf64_Dyn: d_tag(8), d_un(8)
            sym_entry_size, st_value_off = 24, 8  # Elf64_Sym, st_value at +8
            value_fmt = "<Q"
        else:
            e_phoff = struct.unpack_from("<I", blob, 28)[0]
            e_phentsize = struct.unpack_from("<H", blob, 42)[0]
            e_phnum = struct.unpack_from("<H", blob, 44)[0]
            p_vaddr_off, p_filesz_off = 8, 16  # within Elf32_Phdr
            dyn_entry_size, dyn_fmt = 8, "<iI"  # Elf32_Dyn: d_tag(4), d_un(4)
            sym_entry_size, st_value_off = 16, 4  # Elf32_Sym, st_value at +4
            value_fmt = "<I"
        dyn_off = dyn_size = None
        for i in range(e_phnum):
            ph = e_phoff + i * e_phentsize
            if struct.unpack_from("<I", blob, ph)[0] == 2:  # PT_DYNAMIC (p_type is <I in both classes)
                dyn_off = struct.unpack_from(value_fmt, blob, ph + p_vaddr_off)[0]
                dyn_size = struct.unpack_from(value_fmt, blob, ph + p_filesz_off)[0]
                break
        if dyn_off is None:
            return None
        DT_NULL, DT_HASH, DT_STRTAB, DT_SYMTAB = 0, 4, 5, 6
        strtab = symtab = hashtab = None
        for i in range(0, dyn_size, dyn_entry_size):
            tag, val = struct.unpack_from(dyn_fmt, blob, dyn_off + i)
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
        nchain = struct.unpack_from("<I", blob, hashtab + 4)[0]  # hash table words are 32-bit in both classes
        target = symbol.encode() + b"\x00"
        for i in range(nchain):
            sym = symtab + i * sym_entry_size
            if sym + sym_entry_size > len(blob):
                break
            st_name = struct.unpack_from("<I", blob, sym)[0]
            if st_name == 0:
                continue
            name_start = strtab + st_name
            name_end = blob.find(b"\x00", name_start)
            if name_end < 0:
                continue
            if blob[name_start : name_end + 1] == target:
                return base + struct.unpack_from(value_fmt, blob, sym + st_value_off)[0]
        return None
    except (struct.error, IndexError, ValueError):
        logger.warning("Malformed vDSO encountered while resolving %s, falling back to syscall", symbol)
        return None


def _read_patch_bytes(symbol: str, address: int, disassembler: Cs = utils.cs_64, jump_size: int = JUMP_SIZE) -> tuple[str | None, int]:
    # Disassemble enough whole instructions at "address" to host a jump of "jump_size" bytes.
    # The defaults patch x86_64, Wine passes cs_32 for i386 inferiors.
    dump = debugcore.hex_dump(address, 32)
    if not dump or "??" in dump:
        logger.error("Failed to read %s instructions at 0x%x", symbol, address)
        return None, 0
    code = bytes(int(b, 16) for b in dump)
    disassembler.skipdata = False
    consumed = 0
    for _, size, _, _ in disassembler.disasm_lite(code, address):
        consumed += size
        if consumed >= jump_size:
            return _bytes_to_aob(code[:consumed]), consumed
    logger.error("Failed to find enough whole instructions to patch %s", symbol)
    return None, 0


def _get_patch_address(address: int, arch64: bool) -> int:
    endbr = ["F3", "0F", "1E", "FA" if arch64 else "FB"]
    return address + 4 if debugcore.hex_dump(address, 4) == endbr else address


def _detour_target(address: int, arch64: bool) -> int | None:
    raw = debugcore.hex_dump(address, JUMP_SIZE if arch64 else JUMP_SIZE_32)
    if not raw or "??" in raw:
        return None
    code = bytes(int(byte, 16) for byte in raw)
    prefix = b"\x48\xb8" if arch64 else b"\xb8"
    if code.startswith(prefix) and code.endswith(b"\xff\xe0"):
        return int.from_bytes(code[len(prefix) : -2], "little")
    return None


def _has_marker(target: int) -> bool:
    return debugcore.hex_dump(target - len(CAVE_MARKER), len(CAVE_MARKER)) == [f"{byte:02X}" for byte in CAVE_MARKER]


def _build_trampoline(address: int, raw: bytes, arch64: bool, tramp_addr: int) -> bytes | None:
    for insn in (_cs if arch64 else _cs_32).disasm(raw, address):
        if insn.group(capstone.CS_GRP_JUMP) or insn.group(capstone.CS_GRP_CALL) or insn.group(capstone.CS_GRP_RET) or insn.group(capstone.CS_GRP_BRANCH_RELATIVE):
            return None
        if arch64:
            for op in insn.operands:
                if op.type == cs_x86.X86_OP_MEM and op.mem.base == cs_x86.X86_REG_RIP:
                    return None
    prologue = (b"\xf3\x0f\x1e\xfa" if arch64 else b"\xf3\x0f\x1e\xfb") + raw
    target = address + len(raw)
    if arch64:
        return prologue + b"\x3e\xff\x25\x00\x00\x00\x00" + struct.pack("<Q", target)
    slot = tramp_addr + len(prologue) + 7
    return prologue + b"\x3e\xff\x25" + struct.pack("<I", slot) + struct.pack("<I", target)


def _write_cave(cave: int, address: int, blob: bytes, symbol: str) -> int:
    if address + len(blob) > cave + CAVE_SIZE:
        raise RuntimeError(f"Speedhack code cave is too small for {symbol}")
    _write_verified(address, _bytes_to_aob(blob))
    return (address + len(blob) + 15) & ~15


def _step_threads_out_of_range(low: int, high: int, max_steps: int = 64) -> bool:
    info = debugcore.send_command("-thread-info")
    if not info:
        logger.error("Speedhack couldn't query thread info")
        return False
    offenders = [
        tid
        for tid, addr in re.findall(r'id="(\d+)",[^}]*?frame=\{[^}]*?addr="(0x[0-9a-fA-F]+)"', info)
        if low <= int(addr, 16) < high
    ]
    if not offenders:
        return True
    current_match = re.search(r'current-thread-id="(\d+)"', info)
    scheduler_match = re.search(r'value="(\w+)"', debugcore.send_command("-gdb-show scheduler-locking"))
    if not current_match or not scheduler_match:
        logger.error("Speedhack couldn't query GDB thread state")
        return False
    current_thread = current_match.group(1)
    scheduler_mode = scheduler_match.group(1)

    success = True
    debugcore.send_command("-gdb-set scheduler-locking step")
    try:
        for tid in offenders:
            debugcore.send_command(f"thread {tid}")
            for _ in range(max_steps):
                pc = _current_pc()
                if pc is None:
                    success = False
                    break
                if not low <= pc < high:
                    break
                debugcore.step_instruction()
                if not debugcore.wait_for_stop(2):
                    debugcore.interrupt_inferior(typedefs.STOP_REASON.PAUSE)
                    success = False
                    break
            else:
                success = False
            if not success:
                logger.error("Speedhack couldn't step thread %s out of the patch site", tid)
                break
    finally:
        debugcore.send_command(f"thread {current_thread}")
        debugcore.send_command(f"-gdb-set scheduler-locking {scheduler_mode}")
    return success


def _current_pc() -> int | None:
    registers = debugcore.read_registers()
    if not registers:
        return None
    raw = registers.get("rip") or registers.get("eip")
    pc = utils.extract_hex_address(str(raw)) if raw is not None else None
    return int(pc, 16) if pc else None


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


def _vdso_call_or_syscall_32(vdso_addr: int | None, syscall_nr: int, arg_offsets: tuple[int, ...], syscall_regs: tuple[str, ...]) -> str:
    # i386 analogue of _vdso_call_or_syscall.
    # The hooked functions are cdecl so their args sit on the caller's stack,
    # reachable at the ebp-relative "arg_offsets" (8 and 12) once the prologue runs.
    # If "vdso_addr" is set, we push the args right-to-left, call it as a cdecl function and clean the
    # stack afterwards.
    # esp must be 16-aligned before "call", and the shared hook prologue (push ebp/ebx/esi/edi; sub esp, 64)
    # leaves esp % 16 == 12 here, so we pad by (12 - 4 * argc) % 16.
    # Otherwise we issue the raw int 0x80, which preserves every register but eax so the frame survives.
    if vdso_addr is not None:
        argc = len(arg_offsets)
        pad = (12 - 4 * argc) % 16
        pad_in = f"sub esp, {pad}" if pad else ""
        pushes = "\n".join(f"push dword ptr [ebp + {off}]" for off in reversed(arg_offsets))
        return f"""
            {pad_in}
            {pushes}
            mov eax, {hex(vdso_addr)}
            call eax
            add esp, {pad + 4 * argc}
        """
    loads = "\n".join(f"mov {reg}, dword ptr [ebp + {off}]" for reg, off in zip(syscall_regs, arg_offsets))
    return f"""
        {loads}
        mov eax, {syscall_nr}
        int 0x80
    """


def _scale64_asm(mul_off: int, div_off: int) -> str:
    # Shared 64-bit scaling kernel for the i386 hooks.
    # Requires esi == state block base. Computes: OUT (64-bit) = VAL (64-bit) * dword[esi + mul_off] / dword[esi + div_off]
    # via a 96-bit product divided word-by-word by the 32-bit divisor.
    # The top quotient word is dropped because the scaled result fits 64 bits for any real session (num/den keep it in range).
    # Fixed ebp-relative scratch slots, shared with the callers' surrounding asm:
    #   VAL = [ebp-16/-20] (input), OUT = [ebp-36/-40] (result), 96-bit product = [ebp-24/-28/-32].
    # Clobbers eax, ebx, ecx, edx. Leaves esi/edi/ebp untouched. OUT may alias VAL (VAL is fully read before OUT is written).
    return f"""
        mov eax, dword ptr [ebp - 16]
        mov ebx, dword ptr [esi + {mul_off}]
        mul ebx
        mov dword ptr [ebp - 24], eax
        mov ecx, edx
        mov eax, dword ptr [ebp - 20]
        mul ebx
        add eax, ecx
        mov dword ptr [ebp - 28], eax
        adc edx, 0
        mov dword ptr [ebp - 32], edx
        mov ebx, dword ptr [esi + {div_off}]
        xor edx, edx
        mov eax, dword ptr [ebp - 32]
        div ebx
        mov eax, dword ptr [ebp - 28]
        div ebx
        mov dword ptr [ebp - 40], eax
        mov eax, dword ptr [ebp - 24]
        div ebx
        mov dword ptr [ebp - 36], eax
    """


def _build_clock_gettime_hook(state_addr: int, vdso_addr: int | None) -> bytes:
    # rdi = clockid_t, rsi = struct timespec*.
    # endbr64 is there because libc's entry may be reached via an indirect branch on CET-enabled processes.
    invoke = _vdso_call_or_syscall(vdso_addr, SYS_CLOCK_GETTIME, ("rdi", "rsi"))
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
        mov r10, qword ptr [r11 + {ACTIVE_OFFSET}]
        and r10, 1
        imul r10, r10, {BUFFER_SIZE}
        add r11, r10
        mov r10d, edi
        shl r10, 4
        add r10, r11
        mov r8, qword ptr [rsi]
        imul r8, r8, 1000000000
        add r8, qword ptr [rsi + 8]
        sub r8, qword ptr [r10]
        jae delta_ok
        xor r8d, r8d
    delta_ok:
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
    invoke = _vdso_call_or_syscall(vdso_addr, SYS_GETTIMEOFDAY, ("rdi",))
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfa
        {invoke}
        test eax, eax
        jne done
        test rdi, rdi
        jz done
        mov r11, {hex(state_addr)}
        mov r10, qword ptr [r11 + {ACTIVE_OFFSET}]
        and r10, 1
        imul r10, r10, {BUFFER_SIZE}
        add r11, r10
        mov r8, qword ptr [rdi]
        imul r8, r8, 1000000000
        mov rax, qword ptr [rdi + 8]
        imul rax, rax, 1000
        add r8, rax
        sub r8, qword ptr [r11]
        jae delta_ok
        xor r8d, r8d
    delta_ok:
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
        mov r10, qword ptr [r11 + {ACTIVE_OFFSET}]
        and r10, 1
        imul r10, r10, {BUFFER_SIZE}
        add r11, r10
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


def _build_clock_gettime_hook_32(state_addr: int, vdso_addr: int | None) -> bytes:
    # i386 cdecl: [ebp+8] = clockid_t clk, [ebp+12] = struct timespec* tp (32-bit tv_sec/tv_nsec).
    # endbr32 so the jmp-eax detour lands on a valid IBT endbranch under CET.
    invoke = _vdso_call_or_syscall_32(vdso_addr, SYS_CLOCK_GETTIME_32, (8, 12), ("ebx", "ecx"))
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfb
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        sub esp, 64
        {invoke}
        test eax, eax
        jne done
        mov ecx, dword ptr [ebp + 8]
        cmp ecx, 7
        ja done
        cmp ecx, 2
        je done
        cmp ecx, 3
        je done
        cmp ecx, 5
        je done
        cmp ecx, 6
        je done
        mov esi, {hex(state_addr)}
        mov eax, dword ptr [esi + {ACTIVE_OFFSET}]
        and eax, 1
        imul eax, eax, {BUFFER_SIZE}
        add esi, eax
        mov edi, dword ptr [ebp + 12]
        mov eax, dword ptr [edi]
        mov ebx, 1000000000
        mul ebx
        add eax, dword ptr [edi + 4]
        adc edx, 0
        mov dword ptr [ebp - 16], eax
        mov dword ptr [ebp - 20], edx
        mov eax, dword ptr [ebp + 8]
        shl eax, 4
        add eax, esi
        mov dword ptr [ebp - 44], eax
        mov ecx, dword ptr [ebp - 44]
        mov eax, dword ptr [ebp - 16]
        sub eax, dword ptr [ecx]
        mov dword ptr [ebp - 16], eax
        mov eax, dword ptr [ebp - 20]
        sbb eax, dword ptr [ecx + 4]
        mov dword ptr [ebp - 20], eax
        jnc delta_ok
        mov dword ptr [ebp - 16], 0
        mov dword ptr [ebp - 20], 0
    delta_ok:
        {_scale64_asm(NUM_OFFSET, DEN_OFFSET)}
        mov ecx, dword ptr [ebp - 44]
        mov eax, dword ptr [ebp - 36]
        add eax, dword ptr [ecx + 8]
        mov dword ptr [ebp - 36], eax
        mov eax, dword ptr [ebp - 40]
        adc eax, dword ptr [ecx + 12]
        mov dword ptr [ebp - 40], eax
        mov ecx, 1000000000
        xor edx, edx
        mov eax, dword ptr [ebp - 40]
        div ecx
        mov eax, dword ptr [ebp - 36]
        div ecx
        mov dword ptr [edi], eax
        mov dword ptr [edi + 4], edx
        xor eax, eax
    done:
        add esp, 64
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
    """
    return _assemble_hook(asm, typedefs.INFERIOR_ARCH.ARCH_32)


def _build_gettimeofday_hook_32(state_addr: int, vdso_addr: int | None) -> bytes:
    # i386 cdecl: [ebp+8] = struct timeval* tv (32-bit tv_sec/tv_usec), [ebp+12] = struct timezone* tz (unused).
    # Scales around the CLOCK_REALTIME base stored at state+0 (real) / state+8 (fake), like the x64 hook.
    invoke = _vdso_call_or_syscall_32(vdso_addr, SYS_GETTIMEOFDAY_32, (8, 12), ("ebx", "ecx"))
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfb
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        sub esp, 64
        {invoke}
        test eax, eax
        jne done
        mov edi, dword ptr [ebp + 8]
        test edi, edi
        jz done
        mov esi, {hex(state_addr)}
        mov eax, dword ptr [esi + {ACTIVE_OFFSET}]
        and eax, 1
        imul eax, eax, {BUFFER_SIZE}
        add esi, eax
        mov eax, dword ptr [edi]
        mov ebx, 1000000000
        mul ebx
        mov dword ptr [ebp - 16], eax
        mov dword ptr [ebp - 20], edx
        mov eax, dword ptr [edi + 4]
        mov ebx, 1000
        mul ebx
        add dword ptr [ebp - 16], eax
        adc dword ptr [ebp - 20], edx
        mov eax, dword ptr [ebp - 16]
        sub eax, dword ptr [esi]
        mov dword ptr [ebp - 16], eax
        mov eax, dword ptr [ebp - 20]
        sbb eax, dword ptr [esi + 4]
        mov dword ptr [ebp - 20], eax
        jnc delta_ok
        mov dword ptr [ebp - 16], 0
        mov dword ptr [ebp - 20], 0
    delta_ok:
        {_scale64_asm(NUM_OFFSET, DEN_OFFSET)}
        mov eax, dword ptr [ebp - 36]
        add eax, dword ptr [esi + 8]
        mov dword ptr [ebp - 36], eax
        mov eax, dword ptr [ebp - 40]
        adc eax, dword ptr [esi + 12]
        mov dword ptr [ebp - 40], eax
        mov ecx, 1000000000
        xor edx, edx
        mov eax, dword ptr [ebp - 40]
        div ecx
        mov eax, dword ptr [ebp - 36]
        div ecx
        mov dword ptr [edi], eax
        mov eax, edx
        xor edx, edx
        mov ecx, 1000
        div ecx
        mov dword ptr [edi + 4], eax
        xor eax, eax
    done:
        add esp, 64
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
    """
    return _assemble_hook(asm, typedefs.INFERIOR_ARCH.ARCH_32)


def _build_nanosleep_hook_32(state_addr: int) -> bytes:
    # i386 cdecl: [ebp+8] = const struct timespec* req, [ebp+12] = struct timespec* rem (32-bit fields).
    # No vDSO entry for nanosleep, so always int 0x80 (syscall 162).
    # Scales the requested duration by den/num (inverse of the read scaling),
    # retries on EINTR until the full real duration elapses, then zeros the caller's rem.
    # Local kernel timespec at [ebp-48]=tv_sec / [ebp-44]=tv_nsec.
    asm = f"""
        .byte 0xf3, 0x0f, 0x1e, 0xfb
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        sub esp, 64
        mov esi, {hex(state_addr)}
        mov eax, dword ptr [esi + {ACTIVE_OFFSET}]
        and eax, 1
        imul eax, eax, {BUFFER_SIZE}
        add esi, eax
        mov edi, dword ptr [ebp + 8]
        mov eax, dword ptr [edi]
        mov ebx, 1000000000
        mul ebx
        add eax, dword ptr [edi + 4]
        adc edx, 0
        mov dword ptr [ebp - 16], eax
        mov dword ptr [ebp - 20], edx
        mov eax, dword ptr [esi + {NUM_OFFSET}]
        test eax, eax
        jz cleanup
        {_scale64_asm(DEN_OFFSET, NUM_OFFSET)}
        mov ecx, 1000000000
        xor edx, edx
        mov eax, dword ptr [ebp - 40]
        div ecx
        mov eax, dword ptr [ebp - 36]
        div ecx
        mov dword ptr [ebp - 48], eax
        mov dword ptr [ebp - 44], edx
    retry:
        lea ebx, [ebp - 48]
        lea ecx, [ebp - 48]
        mov eax, {SYS_NANOSLEEP_32}
        int 0x80
        test eax, eax
        jz cleanup
        cmp eax, -4
        je retry
    cleanup:
        mov edx, dword ptr [ebp + 12]
        test edx, edx
        jz done
        mov dword ptr [edx], 0
        mov dword ptr [edx + 4], 0
    done:
        xor eax, eax
        add esp, 64
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
    """
    return _assemble_hook(asm, typedefs.INFERIOR_ARCH.ARCH_32)


def _write_verified(address: int, aob: str) -> None:
    """write_memory swallows OSError/ValueError, so confirm the patch actually landed.
    Raises RuntimeError on mismatch so install/restore can detect a failed write."""
    debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, aob)
    expected = aob.split()
    readback = debugcore.hex_dump(address, len(expected))
    if [b.lower() for b in readback] != [b.lower() for b in expected]:
        raise RuntimeError(f"Speedhack write verification failed at {hex(address)}")


def _restore_hook(symbol: str, address: int, original_aob: str) -> None:
    try:
        _write_verified(address, original_aob)
    except Exception:
        logger.exception("Failed to restore %s", symbol)


def _assemble_hook(asm: str, arch: int = typedefs.INFERIOR_ARCH.ARCH_64) -> bytes:
    encoded = utils.assemble(asm, 0, arch)
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
    if not debugcore.mprotect_memory(start, 2 * page):
        logger.error(f"Failed to change protection for speedhack memory at {hex(address)}")


def _ensure_writable(address: int) -> None:
    region = utils.get_region_info(debugcore.currentpid, address)
    if region is not None and region.perms and "w" in region.perms and "x" in region.perms:
        return
    _mprotect_cave(address)


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
        mov r8, qword ptr [r11 + {WINE_INIT_OFFSET}]
        test r8, r8
        jnz scale
        mov qword ptr [r11 + {WINE_REAL_BASE_OFFSET}], rax
        mov qword ptr [r11 + {WINE_FAKE_BASE_OFFSET}], rax
        mov qword ptr [r11 + {WINE_INIT_OFFSET}], 1
    scale:
        mov r9, rax
        sub rax, qword ptr [r11 + {WINE_REAL_BASE_OFFSET}]
        jae delta_ok
        xor eax, eax
    delta_ok:
        mov r10, qword ptr [r11 + {WINE_NUM_OFFSET}]
        mul r10
        mov r10, qword ptr [r11 + {WINE_DEN_OFFSET}]
        div r10
        add rax, qword ptr [r11 + {WINE_FAKE_BASE_OFFSET}]
        mov qword ptr [r11 + {WINE_LAST_REAL_OFFSET}], r9
        mov qword ptr [r11 + {WINE_LAST_FAKE_OFFSET}], rax
        mov qword ptr [rcx], rax
        mov eax, 1
        pop rbp
        ret
    """
    return _assemble_hook(asm)


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
        mov eax, dword ptr [esi + {WINE_INIT_OFFSET}]
        or eax, dword ptr [esi + {WINE_INIT_OFFSET + 4}]
        jnz do_scale
        mov eax, dword ptr [ebp - 40]
        mov dword ptr [esi + {WINE_REAL_BASE_OFFSET}], eax
        mov dword ptr [esi + {WINE_FAKE_BASE_OFFSET}], eax
        mov eax, dword ptr [ebp - 44]
        mov dword ptr [esi + {WINE_REAL_BASE_OFFSET + 4}], eax
        mov dword ptr [esi + {WINE_FAKE_BASE_OFFSET + 4}], eax
        mov dword ptr [esi + {WINE_INIT_OFFSET}], 1
        mov dword ptr [esi + {WINE_INIT_OFFSET + 4}], 0
    do_scale:
        mov eax, dword ptr [ebp - 40]
        sub eax, dword ptr [esi + {WINE_REAL_BASE_OFFSET}]
        mov dword ptr [ebp - 16], eax
        mov eax, dword ptr [ebp - 44]
        sbb eax, dword ptr [esi + {WINE_REAL_BASE_OFFSET + 4}]
        mov dword ptr [ebp - 20], eax
        jnc delta_ok
        mov dword ptr [ebp - 16], 0
        mov dword ptr [ebp - 20], 0
    delta_ok:
        mov eax, dword ptr [ebp - 16]
        mov ebx, dword ptr [esi + {WINE_NUM_OFFSET}]
        mul ebx
        mov dword ptr [ebp - 24], eax
        mov ecx, edx
        mov eax, dword ptr [ebp - 20]
        mul ebx
        add eax, ecx
        mov dword ptr [ebp - 28], eax
        adc edx, 0
        mov dword ptr [ebp - 32], edx
        mov ebx, dword ptr [esi + {WINE_DEN_OFFSET}]
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
        add eax, dword ptr [esi + {WINE_FAKE_BASE_OFFSET}]
        mov ecx, eax
        mov eax, dword ptr [ebp - 28]
        adc eax, dword ptr [esi + {WINE_FAKE_BASE_OFFSET + 4}]
        mov dword ptr [edi], ecx
        mov dword ptr [edi + 4], eax
        mov edx, dword ptr [ebp - 40]
        mov dword ptr [esi + {WINE_LAST_REAL_OFFSET}], edx
        mov edx, dword ptr [ebp - 44]
        mov dword ptr [esi + {WINE_LAST_REAL_OFFSET + 4}], edx
        mov dword ptr [esi + {WINE_LAST_FAKE_OFFSET}], ecx
        mov dword ptr [esi + {WINE_LAST_FAKE_OFFSET + 4}], eax
        mov eax, 1
        add esp, 48
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret 4
    """
    return _assemble_hook(asm, typedefs.INFERIOR_ARCH.ARCH_32)


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
    opt = e_lfanew + 24
    if struct.unpack_from("<H", header, opt)[0] != (0x20B if arch64 else 0x10B):
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
        if export_rva <= func_rva < export_rva + export_size:
            logger.error("Wine speedhack: %s is a forwarder, can't hook", symbol)
            return None
        return base + func_rva
    return None
