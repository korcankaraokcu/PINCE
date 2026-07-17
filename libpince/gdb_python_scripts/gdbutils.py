# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

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

import gdb, sys, traceback, functools, re
from collections import OrderedDict
from typing import Any, Callable

PINCE_PATH = gdb.parse_and_eval("$PINCE_PATH").string()
GDBINIT_AA_PATH = gdb.parse_and_eval("$GDBINIT_AA_PATH").string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libpince import typedefs, regexes, utils

inferior = gdb.selected_inferior()
pid = -1 if inferior.pid == 0 else inferior.pid
mem_file = "/proc/" + str(pid) + "/mem"

try:
    arch = gdb.selected_frame().architecture()
except gdb.error:
    arch = inferior.architecture()

# Wine's segment selectors can make GDB mistake normal Win64 for x32, truncating pointers to 32 bits.
if (
    pid != -1
    and arch.name().startswith("i386:x64-32")
    and utils.is_wine_process(pid)
    and utils.get_effective_arch(pid) == typedefs.INFERIOR_ARCH.ARCH_64
):
    gdb.execute("set architecture i386:x86-64", to_string=True)
    try:
        arch = gdb.selected_frame().architecture()
    except gdb.error:
        arch = inferior.architecture()

try:
    void_ptr = gdb.lookup_type("void").pointer()
except gdb.error:
    void_ptr = gdb.parse_and_eval("0").type.pointer()

if arch.registers().find("rax") is not None:
    current_arch = typedefs.INFERIOR_ARCH.ARCH_64
else:
    current_arch = typedefs.INFERIOR_ARCH.ARCH_32


# Use this function instead of the .gdbinit file
# If you have to load a .gdbinit file, just load it in this function with command "source"
def gdbinit() -> None:
    try:
        gdb.execute("source " + GDBINIT_AA_PATH)
    except Exception:
        utils.logger.exception("An exception occurred while trying to source gdbinit")
    gdb.execute("set disassembly-flavor intel")
    gdb.execute("set case-sensitive auto")
    gdb.execute("set code-cache off")
    gdb.execute("set stack-cache off")


# A decorator for printing exception information because GDB doesn't give proper information about exceptions
# GDB also overrides sys.excepthook apparently. So this is a proper solution to the exception problem
def print_exception(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> None:
        try:
            func(*args, **kwargs)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

    return wrapper


def get_general_registers() -> OrderedDict[str, str | None]:
    contents_send = OrderedDict()
    if current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
        general_register_list = typedefs.REGISTERS.GENERAL_64
    else:
        general_register_list = typedefs.REGISTERS.GENERAL_32
    for item in general_register_list:
        contents_send[item] = examine_expression("$" + item).address
    return contents_send


def get_flag_registers() -> OrderedDict[str, str]:
    contents_send = OrderedDict()
    flags = int(gdb.parse_and_eval("$eflags")) & 0xFFFFFFFF
    contents_send["cf"] = str((flags >> 0) & 1)
    contents_send["pf"] = str((flags >> 2) & 1)
    contents_send["af"] = str((flags >> 4) & 1)
    contents_send["zf"] = str((flags >> 6) & 1)
    contents_send["sf"] = str((flags >> 7) & 1)
    contents_send["tf"] = str((flags >> 8) & 1)
    contents_send["if"] = str((flags >> 9) & 1)
    contents_send["df"] = str((flags >> 10) & 1)
    contents_send["of"] = str((flags >> 11) & 1)
    return contents_send


def get_segment_registers() -> OrderedDict[str, str | None]:
    contents_send = OrderedDict()
    for item in typedefs.REGISTERS.SEGMENT:
        contents_send[item] = examine_expression("$" + item).address
    return contents_send


def get_float_registers() -> OrderedDict[str, str]:
    contents_send = OrderedDict()
    for register in typedefs.REGISTERS.FLOAT.ST:
        value = gdb.parse_and_eval("$" + register)
        contents_send[register] = str(value)
    if current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
        xmm_registers = typedefs.REGISTERS.FLOAT.XMM_64
    else:
        xmm_registers = typedefs.REGISTERS.FLOAT.XMM_32
    for register in xmm_registers:
        value = gdb.parse_and_eval("$" + register + ".v4_float")
        contents_send[register] = str(value)
    return contents_send


def examine_expression(
    expression: str, regions: dict[str, list[str]] | None = None, module_bases: dict[str, str] | None = None
) -> typedefs.tuple_examine_expression:
    # Resolve one candidate through GDB's evaluator. Return None if it yields no address.
    def via_gdb(expr):
        try:
            value = gdb.parse_and_eval(expr)
            try:
                value = value.cast(void_ptr)
            except gdb.error:
                value = str(value)
            match = regexes.address_with_symbol.search(str(value))
        except Exception:
            return None
        return typedefs.tuple_examine_expression(*match.groups()) if match else None

    none = typedefs.tuple_examine_expression(None, None, None)
    # Try the expression first so real symbols win.
    resolved = via_gdb(expression)
    if resolved:
        return resolved
    if not regions and not module_bases:
        return none

    # Bare module names use logical load bases.
    # Explicit module[n] names retain raw VMA indexing.
    # Longest names match first so libc.so.6 wins over libc.so.
    names = "|".join(re.escape(name) for name in sorted(set(regions or ()) | set(module_bases or ()), key=len, reverse=True))

    def resolve_module(match):
        name, index = match.groups()
        if index is None:
            return module_bases.get(name, match.group(0)) if module_bases else match.group(0)
        addresses = regions.get(name, ()) if regions else ()
        index = int(index)
        return addresses[index] if index < len(addresses) else match.group(0)

    substituted = re.sub(
        regexes.module_reference.format(names),
        resolve_module,
        expression,
    )
    if substituted == expression:
        return none

    # Plain module+offset is now pure arithmetic so we'll evaluate in-process to skip a second gdb parse.
    # The whitelist keeps eval injection-safe and sends anything with a deref/cast/register to gdb instead.
    if regexes.hex_arithmetic.fullmatch(substituted) and "**" not in substituted.replace(" ", ""):
        try:
            address = hex(eval(substituted))
            return typedefs.tuple_examine_expression(address, address, None)
        except Exception:
            pass
    return via_gdb(substituted) or none
