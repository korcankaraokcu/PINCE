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

# IMPORTANT: Any constant involving only PINCE.py should be declared in PINCE.py

import collections, os, queue


class CONST_TIME:
    GDB_INPUT_SLEEP = 0.0000001


class PATHS:
    PINCE_IPC_PATH = "/tmp/PINCE-connection/"
    IPC_FROM_PINCE_PATH = "/from_PINCE_file"
    IPC_TO_PINCE_PATH = "/to_PINCE_file"
    GDB_PATH = "./gdb_pince/gdb-8.0/bin/gdb"


class USER_PATHS:
    HOME_PATH = os.path.expanduser("~")
    ROOT_PATH = HOME_PATH + "/.config/PINCE/PINCE_USER_FILES/"
    TRACE_INSTRUCTIONS_PATH = ROOT_PATH + "TraceInstructions/"
    GDBINIT_PATH = ROOT_PATH + "gdbinit"
    GDBINIT_AA_PATH = ROOT_PATH + "gdbinit_after_attach"
    PINCEINIT_PATH = ROOT_PATH + "pinceinit.py"
    PINCEINIT_AA_PATH = ROOT_PATH + "pinceinit_after_attach.py"

    @staticmethod
    def get_init_directories():
        return USER_PATHS.ROOT_PATH, USER_PATHS.TRACE_INSTRUCTIONS_PATH

    @staticmethod
    def get_init_files():
        return USER_PATHS.GDBINIT_PATH, USER_PATHS.GDBINIT_AA_PATH, \
               USER_PATHS.PINCEINIT_PATH, USER_PATHS.PINCEINIT_AA_PATH


class INFERIOR_STATUS:
    INFERIOR_RUNNING = 1
    INFERIOR_STOPPED = 2


class INFERIOR_ARCH:
    ARCH_32 = 1
    ARCH_64 = 2


class INJECTION_METHOD:
    SIMPLE_DLOPEN_CALL = 1
    ADVANCED_INJECTION = 2


class BREAKPOINT_TYPE:
    HARDWARE_BP = 1
    SOFTWARE_BP = 2


class WATCHPOINT_TYPE:
    WRITE_ONLY = 1
    READ_ONLY = 2
    BOTH = 3


class BREAKPOINT_ON_HIT:
    BREAK = 1
    FIND_CODE = 2
    FIND_ADDR = 3
    TRACE = 4


class BREAKPOINT_MODIFY:
    CONDITION = 1
    ENABLE = 2
    DISABLE = 3
    ENABLE_ONCE = 4
    ENABLE_COUNT = 5
    ENABLE_DELETE = 6


class STEP_MODE:
    SINGLE_STEP = 1
    STEP_OVER = 2


class TRACE_STATUS:
    STATUS_IDLE = 1
    STATUS_TRACING = 2
    STATUS_CANCELED = 3
    STATUS_PROCESSING = 4
    STATUS_FINISHED = 5


class STOP_REASON:
    PAUSE = 1
    DEBUG = 2


class ATTACH_RESULT:
    ATTACH_SUCCESSFUL = 1
    PROCESS_NOT_VALID = 2
    ALREADY_DEBUGGING = 3
    ALREADY_TRACED = 4
    PERM_DENIED = 5


# represents the indexes of value types
# Also used in PINCE's value comboboxes
class VALUE_INDEX:
    INDEX_BYTE = 0
    INDEX_2BYTES = 1
    INDEX_4BYTES = 2
    INDEX_8BYTES = 3
    INDEX_FLOAT = 4
    INDEX_DOUBLE = 5

    # Beginning of the string indexes, new string indexes should be added between 6 and 9
    INDEX_STRING_ASCII = 6
    INDEX_STRING_UTF8 = 7
    INDEX_STRING_UTF16 = 8
    INDEX_STRING_UTF32 = 9
    # Ending of the string indexes, 69... not on purpose tho

    INDEX_AOB = 10  # Array of Bytes

    @staticmethod
    def is_string(value_index):
        return VALUE_INDEX.INDEX_STRING_ASCII <= value_index <= VALUE_INDEX.INDEX_STRING_UTF32

    @staticmethod
    def has_length(value_index):
        return VALUE_INDEX.INDEX_STRING_ASCII <= value_index <= VALUE_INDEX.INDEX_STRING_UTF32 or \
               value_index == VALUE_INDEX.INDEX_AOB


class GDB_OUTPUT_MODE:
    UNMUTED = 0
    ASYNC_OUTPUT_ONLY = 1
    MUTED = 2


gdb_output_mode_to_text = {
    GDB_OUTPUT_MODE.UNMUTED: "Unmuted",
    GDB_OUTPUT_MODE.ASYNC_OUTPUT_ONLY: "Async output only",
    GDB_OUTPUT_MODE.MUTED: "Muted",
}

on_hit_to_text_dict = {
    BREAKPOINT_ON_HIT.BREAK: "Break",
    BREAKPOINT_ON_HIT.FIND_CODE: "Find Code",
    BREAKPOINT_ON_HIT.FIND_ADDR: "Find Address",
    BREAKPOINT_ON_HIT.TRACE: "Trace"
}

# Represents the texts at indexes in combobox
index_to_text_dict = {
    VALUE_INDEX.INDEX_BYTE: "Byte",
    VALUE_INDEX.INDEX_2BYTES: "2 Bytes",
    VALUE_INDEX.INDEX_4BYTES: "4 Bytes",
    VALUE_INDEX.INDEX_8BYTES: "8 Bytes",
    VALUE_INDEX.INDEX_FLOAT: "Float",
    VALUE_INDEX.INDEX_DOUBLE: "Double",
    VALUE_INDEX.INDEX_STRING_ASCII: "String_ASCII",
    VALUE_INDEX.INDEX_STRING_UTF8: "String_UTF8",
    VALUE_INDEX.INDEX_STRING_UTF16: "String_UTF16",
    VALUE_INDEX.INDEX_STRING_UTF32: "String_UTF32",
    VALUE_INDEX.INDEX_AOB: "AoB"
}

text_to_index_dict = {}
for key in index_to_text_dict:
    text_to_index_dict[index_to_text_dict[key]] = key

string_index_to_encoding_dict = {
    VALUE_INDEX.INDEX_STRING_UTF8: ["utf-8", "surrogateescape"],
    VALUE_INDEX.INDEX_STRING_UTF16: ["utf-16", "replace"],
    VALUE_INDEX.INDEX_STRING_UTF32: ["utf-32", "replace"],
    VALUE_INDEX.INDEX_STRING_ASCII: ["ascii", "replace"],
}

string_index_to_multiplier_dict = {
    VALUE_INDEX.INDEX_STRING_UTF8: 2,
    VALUE_INDEX.INDEX_STRING_UTF16: 4,
    VALUE_INDEX.INDEX_STRING_UTF32: 8,
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
    VALUE_INDEX.INDEX_STRING_ASCII: "xb",
    VALUE_INDEX.INDEX_STRING_UTF8: "xb",
    VALUE_INDEX.INDEX_STRING_UTF16: "xb",
    VALUE_INDEX.INDEX_STRING_UTF32: "xb",
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
    VALUE_INDEX.INDEX_STRING_ASCII: [None, None],
    VALUE_INDEX.INDEX_STRING_UTF8: [None, None],
    VALUE_INDEX.INDEX_STRING_UTF16: [None, None],
    VALUE_INDEX.INDEX_STRING_UTF32: [None, None],
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

# Format: {tag:tag_description}
tag_to_string = collections.OrderedDict([
    ("MemoryRW", "Memory Read/Write"),
    ("ValueType", "Value Type"),
    ("Injection", "Injection"),
    ("Debug", "Debugging"),
    ("BreakWatchpoints", "Breakpoints&Watchpoints"),
    ("Threads", "Threads"),
    ("Registers", "Registers"),
    ("Stack", "Stack&StackTrace"),
    ("Assembly", "Disassemble&Assemble"),
    ("GDBExpressions", "GDB Expressions"),
    ("GDBCommunication", "GDB Communication"),
    ("Tools", "Tools"),
    ("Utilities", "Utilities"),
    ("Processes", "Processes"),
    ("GUI", "GUI"),
    ("ConditionsLocks", "Conditions&Locks"),
    ("GDBInformation", "GDB Information"),
    ("InferiorInformation", "Inferior Information"),

])

# size-->int, any other field-->str
tuple_breakpoint_info = collections.namedtuple("breakpoint_info", "number breakpoint_type \
                                                disp enabled address size on_hit hit_count enable_count condition")

# start-->str, end-->str, region-->psutil.Process.memory_maps()[item]
tuple_region_info = collections.namedtuple("region_info", "start end region")


class InferiorRunningException(Exception):
    def __init__(self, message="Inferior is running"):
        super(InferiorRunningException, self).__init__(message)


class GDBInitializeException(Exception):
    def __init__(self, message="GDB not initialized"):
        super(GDBInitializeException, self).__init__(message)


class RegisterQueue:
    def __init__(self):
        self.queue_list = []

    def register_queue(self):
        new_queue = queue.Queue()
        self.queue_list.append(new_queue)
        return new_queue

    def broadcast_message(self, message):
        for item in self.queue_list:
            item.put(message)

    def delete_queue(self, queue_instance):
        try:
            self.queue_list.remove(queue_instance)
        except ValueError:
            pass
