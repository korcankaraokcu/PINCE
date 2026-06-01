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

import gdb, sys, traceback, functools
from collections import OrderedDict
from typing import Any, Callable

# This is some retarded hack
PINCE_PATH = gdb.parse_and_eval("$PINCE_PATH").string()
GDBINIT_AA_PATH = gdb.parse_and_eval("$GDBINIT_AA_PATH").string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libpince import typedefs, regexes, utils

inferior = gdb.selected_inferior()
pid = -1 if inferior.pid == 0 else inferior.pid
mem_file = "/proc/" + str(pid) + "/mem"

void_ptr = gdb.lookup_type("void").pointer()

if void_ptr.sizeof == 8:
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
    expression: str, regions: dict[str, list[str]] | None = None
) -> typedefs.tuple_examine_expression:
    try:
        value = gdb.parse_and_eval(expression).cast(void_ptr)
    except Exception:
        if regions:  # this check comes first for optimization
            offset = regexes.offset_expression.search(expression)
            if offset:
                offset = offset.group(0)
                expression = expression.split(offset[0])[0]
            else:
                offset = "+0"
            index = regexes.index.search(expression)
            if index:
                expression = expression[: index.start()]
                index = int(index.group(1))
            else:
                index = 0
            if expression in regions:
                start_address_list = regions[expression]
                if len(start_address_list) > index:
                    address = start_address_list[index]
                    try:
                        address = hex(eval(address + offset))
                    except Exception:
                        utils.logger.exception("An exception occurred while trying to extract address from region")
                        return typedefs.tuple_examine_expression(None, None, None)
                    return typedefs.tuple_examine_expression(f"{address} {expression}", address, expression)
            return typedefs.tuple_examine_expression(None, None, None)
        utils.logger.exception("An exception occurred while trying to evaluate a gdb expression")
        return typedefs.tuple_examine_expression(None, None, None)
    result = regexes.address_with_symbol.search(str(value))
    if not result:
        return typedefs.tuple_examine_expression(None, None, None)
    return typedefs.tuple_examine_expression(*result.groups())
