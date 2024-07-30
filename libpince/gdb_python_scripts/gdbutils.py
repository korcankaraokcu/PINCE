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

# This is some retarded hack
PINCE_PATH = gdb.parse_and_eval("$PINCE_PATH").string()
GDBINIT_AA_PATH = gdb.parse_and_eval("$GDBINIT_AA_PATH").string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libpince import typedefs, regexes

inferior = gdb.selected_inferior()
pid = -1 if inferior.pid == 0 else inferior.pid
mem_file = "/proc/" + str(pid) + "/mem"

void_ptr = gdb.lookup_type("void").pointer()

if str(gdb.parse_and_eval("$rax")) == "void":
    current_arch = typedefs.INFERIOR_ARCH.ARCH_32
else:
    current_arch = typedefs.INFERIOR_ARCH.ARCH_64


# Use this function instead of the .gdbinit file
# If you have to load a .gdbinit file, just load it in this function with command "source"
def gdbinit():
    try:
        gdb.execute("source " + GDBINIT_AA_PATH)
    except Exception as e:
        print(e)
    gdb.execute("set disassembly-flavor intel")
    gdb.execute("set case-sensitive auto")
    gdb.execute("set code-cache off")
    gdb.execute("set stack-cache off")


# A decorator for printing exception information because GDB doesn't give proper information about exceptions
# GDB also overrides sys.excepthook apparently. So this is a proper solution to the exception problem
def print_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            traceback.print_exception(type(e), e, e.__traceback__)

    return wrapper


def get_general_registers():
    contents_send = OrderedDict()
    if current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
        general_register_list = typedefs.REGISTERS.GENERAL_64
    else:
        general_register_list = typedefs.REGISTERS.GENERAL_32
    for item in general_register_list:
        contents_send[item] = examine_expression("$" + item).address
    return contents_send


def get_flag_registers():
    contents_send = OrderedDict()
    bitwise_flags = bin(int(gdb.parse_and_eval("$eflags")))[2:]
    reversed_bitwise_flags = "".join(reversed(bitwise_flags))
    (
        contents_send["cf"],
        contents_send["pf"],
        contents_send["af"],
        contents_send["zf"],
        contents_send["sf"],
        contents_send["tf"],
        contents_send["if"],
        contents_send["df"],
        contents_send["of"],
    ) = ["0"] * 9
    try:
        contents_send["cf"] = reversed_bitwise_flags[0]
        contents_send["pf"] = reversed_bitwise_flags[2]
        contents_send["af"] = reversed_bitwise_flags[4]
        contents_send["zf"] = reversed_bitwise_flags[6]
        contents_send["sf"] = reversed_bitwise_flags[7]
        contents_send["tf"] = reversed_bitwise_flags[8]
        contents_send["if"] = reversed_bitwise_flags[9]
        contents_send["df"] = reversed_bitwise_flags[10]
        contents_send["of"] = reversed_bitwise_flags[11]
    except IndexError:
        pass
    return contents_send


def get_segment_registers():
    contents_send = OrderedDict()
    for item in typedefs.REGISTERS.SEGMENT:
        contents_send[item] = examine_expression("$" + item).address
    return contents_send


def get_float_registers():
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


def examine_expression(expression: str, regions=None):
    try:
        value = gdb.parse_and_eval(expression).cast(void_ptr)
    except Exception as e:
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
                    except Exception as e:
                        print(e)
                        return typedefs.tuple_examine_expression(None, None, None)
                    return typedefs.tuple_examine_expression(f"{address} {expression}", address, expression)
            return typedefs.tuple_examine_expression(None, None, None)
        print(e)
        return typedefs.tuple_examine_expression(None, None, None)
    result = regexes.address_with_symbol.search(str(value))
    return typedefs.tuple_examine_expression(*result.groups())
