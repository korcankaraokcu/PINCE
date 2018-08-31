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
import gdb, struct, sys
from collections import OrderedDict

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
gdbvalue = gdb.parse_and_eval("$GDBINIT_AA_PATH")
GDBINIT_AA_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libPINCE import SysUtils, type_defs, common_regexes

inferior = gdb.selected_inferior()
pid = inferior.pid
mem_file = "/proc/" + str(pid) + "/mem"

REGISTERS_32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]
REGISTERS_64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip", "r8", "r9", "r10", "r11", "r12",
                "r13", "r14", "r15"]
REGISTERS_SEGMENT = ["cs", "ss", "ds", "es", "fs", "gs"]

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


# This function is used to avoid errors in gdb scripts, because gdb scripts stop working when encountered an error
def issue_command(command, error_message=""):
    try:
        gdb.execute(command)
    except:
        if error_message:
            error_message = str(error_message)
            gdb.execute('echo ' + error_message + '\n')


# mem_handle parameter example-->open(ScriptUtils.mem_file, "rb"), don't forget to close the handle after you're done
def read_single_address(address, value_type, length=0, zero_terminate=True, only_bytes=False, mem_handle=None):
    try:
        value_type = int(value_type)
    except:
        print(str(value_type) + " is not a valid value index")
        return ""
    if not type(address) == int:
        try:
            address = int(address, 16)
        except:
            print(str(address) + " is not a valid address")
            return ""
    packed_data = type_defs.index_to_valuetype_dict.get(value_type, -1)
    if type_defs.VALUE_INDEX.is_string(value_type):
        try:
            int(length)
        except:
            print(str(length) + " is not a valid length")
            return ""
        expected_length = length * type_defs.string_index_to_multiplier_dict.get(value_type, 1)
    elif value_type is type_defs.VALUE_INDEX.INDEX_AOB:
        try:
            expected_length = int(length)
        except:
            print(str(length) + " is not a valid length")
            return ""
    else:
        expected_length = packed_data[0]
        data_type = packed_data[1]
    try:
        mem_handle.seek(address)
        data_read = mem_handle.read(expected_length)
    except (IOError, ValueError):
        print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + expected_length))
        return ""
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


# TODO: Implement an mem_handle parameter like in read_single_address function for optimization
def set_single_address(address, value_index, value):
    if not type(address) == int:
        try:
            address = int(address, 16)
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

    # Check SetMultipleAddresses class in GDBCommandExtensions.py to see why we moved away the try/except block
    FILE.seek(address)
    FILE.write(write_data)
    FILE.close()


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
    contents_send["cf"], contents_send["pf"], contents_send["af"], contents_send["zf"], contents_send["sf"], \
    contents_send["tf"], contents_send["if"], contents_send["df"], contents_send["of"] = ["0"] * 9
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


def remove_disas_comment(disas_str):
    index = disas_str.rfind("#")
    if index == -1:
        return disas_str
    else:
        return disas_str[:index]


def convert_address_to_symbol(expression, include_address=True):
    expression = expression.strip()
    if not expression:
        return ""
    try:
        result = gdb.execute("x/b " + expression, to_string=True)
    except Exception as e:
        result = common_regexes.cannot_access_memory.search(str(e))
        if result:
            return result.group(1)
        return ""
    filtered_result = common_regexes.address_with_symbol.search(result)  # 0x4125d0 <_start>:	0x31
    if filtered_result:
        return filtered_result.group(1) if include_address else filtered_result.group(3)
    else:
        filtered_result = common_regexes.address_without_symbol.search(result)  # 0x400000:	0x7f
        if filtered_result:
            return filtered_result.group(1)
    return ""


def convert_symbol_to_address(expression):
    expression = expression.strip()
    if not expression:
        return ""
    try:
        result = gdb.execute("x/b " + expression, to_string=True)
    except Exception as e:
        result = common_regexes.cannot_access_memory.search(str(e))
        if result:
            return result.group(1)
        return ""
    filtered_result = common_regexes.address_with_symbol.search(result)
    if filtered_result:
        return filtered_result.group(2)
    else:
        filtered_result = common_regexes.address_without_symbol.search(result)
        if filtered_result:
            return filtered_result.group(1)
    return ""
