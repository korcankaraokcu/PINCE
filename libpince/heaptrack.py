# -*- coding: utf-8 -*-
"""Heap tracking and pointer-heuristic analysis for PINCE.

Allocations can be recorded by preloading ``libpince_heaptrack.so`` into the
target process (for example via the LD_PRELOAD field when creating a process).
The preload library writes events to ``/tmp/pince_heap_<pid>.log``.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass
from typing import Iterable

from . import debugcore, typedefs, utils


@dataclass
class HeapBlock:
    address: int
    size: int


def get_heap_log_path(pid: int | str | None = None) -> str:
    if pid is None:
        pid = debugcore.currentpid
    return f"/tmp/pince_heap_{int(pid)}.log"


def parse_heap_log(path: str) -> dict[int, HeapBlock]:
    blocks: dict[int, HeapBlock] = {}
    if not os.path.exists(path):
        return blocks
    with open(path, "r", errors="replace") as f:
        for line in f:
            parts = line.strip().split()
            if not parts:
                continue
            kind = parts[0]
            try:
                if kind in ("M", "C") and len(parts) >= 3:
                    addr = int(parts[1], 16)
                    size = int(parts[2])
                    if addr and size > 0:
                        blocks[addr] = HeapBlock(addr, size)
                elif kind == "F" and len(parts) >= 2:
                    addr = int(parts[1], 16)
                    blocks.pop(addr, None)
                elif kind == "R" and len(parts) >= 4:
                    new_addr = int(parts[1], 16)
                    size = int(parts[2])
                    old_addr = int(parts[3], 16)
                    blocks.pop(old_addr, None)
                    if new_addr and size > 0:
                        blocks[new_addr] = HeapBlock(new_addr, size)
            except ValueError:
                continue
    return blocks


def get_live_heap_blocks(pid: int | str | None = None) -> list[HeapBlock]:
    if pid is None:
        pid = debugcore.currentpid
    return list(parse_heap_log(get_heap_log_path(pid)).values())


def _region_ranges(pid: int) -> list[tuple[int, int, str]]:
    ranges: list[tuple[int, int, str]] = []
    try:
        for start, end, _perms, _size, _path, _offset, path in utils.get_regions(pid):
            ranges.append((start, end, path or ""))
    except Exception:
        pass
    return ranges


def is_pointer_like(value: int, regions: Iterable[tuple[int, int, str]]) -> bool:
    if value == 0:
        return False
    for start, end, _path in regions:
        if start <= value < end:
            return True
    return False


def scan_block_for_pointers(block: HeapBlock, pid: int | None = None, limit: int = 64) -> list[tuple[int, int]]:
    """Return (offset, pointer_value) pairs for pointer-like values inside a block."""
    if pid is None:
        pid = debugcore.currentpid
    if pid <= 0:
        return []
    regions = _region_ranges(pid)
    word = 8 if utils.get_effective_arch(pid) == typedefs.INFERIOR_ARCH.ARCH_64 else 4
    fmt = "<Q" if word == 8 else "<I"
    results: list[tuple[int, int]] = []
    try:
        with debugcore.memory_handle() as mem:
            mem.seek(block.address)
            data = mem.read(min(block.size, limit * word))
    except Exception:
        return []
    for off in range(0, len(data) - word + 1, word):
        value = struct.unpack_from(fmt, data, off)[0]
        if is_pointer_like(value, regions):
            results.append((off, value))
    return results


def summarize_heap(pid: int | None = None, max_blocks: int = 200) -> list[dict]:
    if pid is None:
        pid = debugcore.currentpid
    blocks = sorted(get_live_heap_blocks(pid), key=lambda b: b.address)[:max_blocks]
    summary = []
    for block in blocks:
        pointers = scan_block_for_pointers(block, pid)
        summary.append(
            {
                "address": block.address,
                "size": block.size,
                "pointer_fields": pointers,
            }
        )
    return summary
