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
import gdb, struct, sys, traceback, functools
from collections import OrderedDict

# This is some retarded hack
PINCE_PATH = gdb.parse_and_eval("$PINCE_PATH").string()
GDBINIT_AA_PATH = gdb.parse_and_eval("$GDBINIT_AA_PATH").string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libPINCE import SysUtils, type_defs, common_regexes

inferior = gdb.selected_inferior()
pid = inferior.pid
mem_file = "/proc/" + str(pid) + "/mem"

REGISTERS_32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]
REGISTERS_64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip", "r8", "r9", "r10", "r11", "r12",
                "r13", "r14", "r15"]
REGISTERS_SEGMENT = ["cs", "ss", "ds", "es", "fs", "gs"]

void_ptr = gdb.lookup_type("void").pointer()

if str(gdb.parse_and_eval("$rax")) == "void":
    current_arch = type_defs.INFERIOR_ARCH.ARCH_32
else:
    current_arch = type_defs.INFERIOR_ARCH.ARCH_64


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


# mem_handle parameter example-->open(ScriptUtils.mem_file, "rb"), don't forget to close the handle after you're done
def read_address(address, value_type, length=None, zero_terminate=True, only_bytes=False, mem_handle=None):
    try:
        value_type = int(value_type)
    except:
        print(str(value_type) + " is not a valid value index")
        return
    if not type(address) == int:
        try:
            address = int(address, 0)
        except:
            print(str(address) + " is not a valid address")
            return
    packed_data = type_defs.index_to_valuetype_dict.get(value_type, -1)
    if type_defs.VALUE_INDEX.is_string(value_type):
        try:
            temp_len = int(length)
        except:
            print(str(length) + " is not a valid length")
            return
        if not temp_len > 0:
            print("length must be greater than 0")
            return
        expected_length = length * type_defs.string_index_to_multiplier_dict.get(value_type, 1)
    elif value_type is type_defs.VALUE_INDEX.INDEX_AOB:
        try:
            expected_length = int(length)
        except:
            print(str(length) + " is not a valid length")
            return
        if not expected_length > 0:
            print("length must be greater than 0")
            return
    else:
        expected_length = packed_data[0]
        data_type = packed_data[1]
    try:
        mem_handle.seek(address)
        data_read = mem_handle.read(expected_length)
    except (OSError, ValueError):
        print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + expected_length))
        return
    if only_bytes:
        return data_read
    if type_defs.VALUE_INDEX.is_string(value_type):
        encoding, option = type_defs.string_index_to_encoding_dict[value_type]
        returned_string = data_read.decode(encoding, option)
        if zero_terminate:
            if returned_string.startswith('\x00'):
                returned_string = '\x00'
            else:
                returned_string = returned_string.split('\x00')[0]
        return returned_string[0:length]
    elif value_type is type_defs.VALUE_INDEX.INDEX_AOB:
        return " ".join(format(n, '02x') for n in data_read)
    else:
        return struct.unpack_from(data_type, data_read)[0]


# TODO: Implement a mem_handle parameter for optimization, check read_address for an example
# If a file handle fails to write to an address, it becomes unusable. You have to reopen the file to continue writing
def write_address(address, value_index, value):
    if not type(address) == int:
        try:
            address = int(address, 0)
        except:
            print(str(address) + " is not a valid address")
            return
    write_data = SysUtils.parse_string(value, value_index)
    if write_data is None:
        return
    encoding, option = type_defs.string_index_to_encoding_dict.get(value_index, (None, None))
    if encoding is None:
        if value_index is type_defs.VALUE_INDEX.INDEX_AOB:
            write_data = bytearray(write_data)
        else:
            data_type = type_defs.index_to_struct_pack_dict.get(value_index, -1)
            write_data = struct.pack(data_type, write_data)
    else:
        write_data = write_data.encode(encoding, option)
    FILE = open(mem_file, "rb+")
    try:
        FILE.seek(address)
        FILE.write(write_data)
        FILE.close()
    except (OSError, ValueError):
        print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + len(write_data)))


def get_general_registers():
    contents_send = OrderedDict()
    if current_arch == type_defs.INFERIOR_ARCH.ARCH_64:
        general_register_list = REGISTERS_64
    else:
        general_register_list = REGISTERS_32
    for item in general_register_list:
        result = gdb.execute("p/x $" + item, to_string=True)
        parsed_result = common_regexes.hex_number.search(result).group(0)  # $6 = 0x7f0bc0b6bb40
        contents_send[item] = parsed_result
    return contents_send


def get_flag_registers():
    contents_send = OrderedDict()
    result = gdb.execute("p/t $eflags", to_string=True)
    parsed_result = common_regexes.convenience_variable_cli.search(result).group(2)  # $8 = 1010010011
    reversed_parsed_result = "".join(reversed(parsed_result))
    (contents_send["cf"], contents_send["pf"], contents_send["af"], contents_send["zf"], contents_send["sf"],
     contents_send["tf"], contents_send["if"], contents_send["df"], contents_send["of"]) = ["0"] * 9
    try:
        contents_send["cf"] = reversed_parsed_result[0]
        contents_send["pf"] = reversed_parsed_result[2]
        contents_send["af"] = reversed_parsed_result[4]
        contents_send["zf"] = reversed_parsed_result[6]
        contents_send["sf"] = reversed_parsed_result[7]
        contents_send["tf"] = reversed_parsed_result[8]
        contents_send["if"] = reversed_parsed_result[9]
        contents_send["df"] = reversed_parsed_result[10]
        contents_send["of"] = reversed_parsed_result[11]
    except IndexError:
        pass
    return contents_send


def get_segment_registers():
    contents_send = OrderedDict()
    for item in REGISTERS_SEGMENT:
        result = gdb.execute("p/x $" + item, to_string=True)
        parsed_result = common_regexes.hex_number.search(result).group(0)  # $6 = 0x7f0bc0b6bb40
        contents_send[item] = parsed_result
    return contents_send


def get_float_registers():
    contents_send = OrderedDict()

    # st0-7
    for index in range(8):
        current_register = "st" + str(index)
        value = gdb.parse_and_eval("$" + current_register)
        contents_send[current_register] = str(value)

    # xmm0-7
    for index in range(8):
        current_register = "xmm" + str(index)
        value = gdb.parse_and_eval("$" + current_register + ".v4_float")
        contents_send[current_register] = str(value)
    return contents_send


def examine_expression(expression):
    try:
        value = gdb.parse_and_eval(expression).cast(void_ptr)
    except Exception as e:
        print(e, "for expression " + expression)
        return type_defs.tuple_examine_expression(None, None, None)
    result = common_regexes.address_with_symbol.search(str(value))
    return type_defs.tuple_examine_expression(*result.groups())
