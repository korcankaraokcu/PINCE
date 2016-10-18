# -*- coding: utf-8 -*-
"""
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>

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

# IMPORTANT: Any constant involving only PINCE.py should be declared in PINCE.py

import collections


class PATHS:
    PINCE_IPC_PATH = "/tmp/PINCE-connection/"
    IPC_FROM_PINCE_PATH = "/from_PINCE_file"
    IPC_TO_PINCE_PATH = "/to_PINCE_file"


class INFERIOR_STATUS:
    INFERIOR_RUNNING = 0
    INFERIOR_STOPPED = 1


class INFERIOR_ARCH:
    ARCH_32 = 0
    ARCH_64 = 1


class INJECTION_METHOD:
    SIMPLE_DLOPEN_CALL = 1
    ADVANCED_INJECTION = 2


class BREAKPOINT_TYPE:
    HARDWARE_BP = 1
    SOFTWARE_BP = 2


# represents the indexes of value types
# Also used in PINCE's value comboboxes
class VALUE_INDEX:
    INDEX_BYTE = 0
    INDEX_2BYTES = 1
    INDEX_4BYTES = 2
    INDEX_8BYTES = 3
    INDEX_FLOAT = 4
    INDEX_DOUBLE = 5
    INDEX_STRING = 6
    INDEX_AOB = 7  # Array of Bytes


# Represents the texts at indexes in combobox
index_to_text_dict = {
    VALUE_INDEX.INDEX_BYTE: "Byte",
    VALUE_INDEX.INDEX_2BYTES: "2 Bytes",
    VALUE_INDEX.INDEX_4BYTES: "4 Bytes",
    VALUE_INDEX.INDEX_8BYTES: "8 Bytes",
    VALUE_INDEX.INDEX_FLOAT: "Float",
    VALUE_INDEX.INDEX_DOUBLE: "Double",
    VALUE_INDEX.INDEX_STRING: "String",
    VALUE_INDEX.INDEX_AOB: "AoB"
}

text_to_index_dict = {
    "Byte": VALUE_INDEX.INDEX_BYTE,
    "2 Bytes": VALUE_INDEX.INDEX_2BYTES,
    "4 Bytes": VALUE_INDEX.INDEX_4BYTES,
    "8 Bytes": VALUE_INDEX.INDEX_8BYTES,
    "Float": VALUE_INDEX.INDEX_FLOAT,
    "Double": VALUE_INDEX.INDEX_DOUBLE
}

# A dictionary used to convert value_combobox index to gdb/mi x command
# Check GDB_Engine for an exemplary usage
index_to_gdbcommand_dict = {
    VALUE_INDEX.INDEX_BYTE: "db",
    VALUE_INDEX.INDEX_2BYTES: "dh",
    VALUE_INDEX.INDEX_4BYTES: "dw",
    VALUE_INDEX.INDEX_8BYTES: "dg",
    VALUE_INDEX.INDEX_FLOAT: "fw",
    VALUE_INDEX.INDEX_DOUBLE: "fg",
    VALUE_INDEX.INDEX_STRING: "xb",
    VALUE_INDEX.INDEX_AOB: "xb"
}

# first value is the length and the second one is the type
# Check ScriptUtils for an exemplary usage
index_to_valuetype_dict = {
    VALUE_INDEX.INDEX_BYTE: [1, "b"],
    VALUE_INDEX.INDEX_2BYTES: [2, "h"],
    VALUE_INDEX.INDEX_4BYTES: [4, "i"],
    VALUE_INDEX.INDEX_8BYTES: [8, "q"],
    VALUE_INDEX.INDEX_FLOAT: [4, "f"],
    VALUE_INDEX.INDEX_DOUBLE: [8, "d"],
    VALUE_INDEX.INDEX_STRING: [None, None],
    VALUE_INDEX.INDEX_AOB: [None, None]
}

# Check ScriptUtils for an exemplary usage
index_to_struct_pack_dict = {
    VALUE_INDEX.INDEX_BYTE: "B",
    VALUE_INDEX.INDEX_2BYTES: "H",
    VALUE_INDEX.INDEX_4BYTES: "I",
    VALUE_INDEX.INDEX_8BYTES: "Q",
    VALUE_INDEX.INDEX_FLOAT: "f",
    VALUE_INDEX.INDEX_DOUBLE: "d"
}

# number-->str, breakpoint_type-->str, address-->str, condition-->str
tuple_breakpoint_info = collections.namedtuple("breakpoint_info", "number breakpoint_type address condition")

# start-->str, end-->str, region-->psutil.Process.memory_maps[item]
tuple_region_info = collections.namedtuple("region_info", "start end region")
