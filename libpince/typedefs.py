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

import collections.abc, queue, sys

class CONST_TIME:
    GDB_INPUT_SLEEP = sys.float_info.min


class PATHS:
    GDB = "/bin/gdb"
    TMP = "/tmp/PINCE/"  # Use utils.get_tmp_path()
    IPC = "/dev/shm/PINCE_IPC/"  # Use utils.get_ipc_path()
    FROM_PINCE = "/from_PINCE"  # Use utils.get_from_pince_file()
    TO_PINCE = "/to_PINCE"  # Use utils.get_to_pince_file()


class USER_PATHS:
    # Use utils.get_user_path() to make use of these
    CONFIG = ".config/"
    ROOT = CONFIG + "PINCE/PINCE_USER_FILES/"
    TRACE_INSTRUCTIONS = ROOT + "TraceInstructions/"
    CHEAT_TABLES = ROOT + "CheatTables/"
    GDBINIT = ROOT + "gdbinit"
    GDBINIT_AA = ROOT + "gdbinit_after_attach"
    PINCEINIT = ROOT + "pinceinit.py"
    PINCEINIT_AA = ROOT + "pinceinit_after_attach.py"

    @staticmethod
    def get_init_directories():
        return USER_PATHS.ROOT, USER_PATHS.TRACE_INSTRUCTIONS, USER_PATHS.CHEAT_TABLES

    @staticmethod
    def get_init_files():
        return USER_PATHS.GDBINIT, USER_PATHS.GDBINIT_AA, USER_PATHS.PINCEINIT, USER_PATHS.PINCEINIT_AA


class INFERIOR_STATUS:
    RUNNING = 1
    STOPPED = 2


class INFERIOR_ARCH:
    ARCH_32 = 1
    ARCH_64 = 2


class INJECTION_METHOD:
    DLOPEN = 1
    ADVANCED = 2


class BREAKPOINT_TYPE:
    HARDWARE = 1
    SOFTWARE = 2


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
    IDLE = 1
    TRACING = 2
    CANCELED = 3
    PROCESSING = 4
    FINISHED = 5


class STOP_REASON:
    PAUSE = 1
    DEBUG = 2


class ATTACH_RESULT:
    ATTACH_SELF = 1
    SUCCESSFUL = 2
    PROCESS_NOT_VALID = 3
    ALREADY_DEBUGGING = 4
    ALREADY_TRACED = 5
    PERM_DENIED = 6


class TOGGLE_ATTACH:
    ATTACHED = 1
    DETACHED = 2


class REGISTERS:
    GENERAL_32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]
    GENERAL_64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip", "r8", "r9", "r10", "r11", "r12",
                  "r13", "r14", "r15"]
    SEGMENT = ["cs", "ss", "ds", "es", "fs", "gs"]
    FLAG = ["cf", "pf", "af", "zf", "sf", "tf", "if", "df", "of"]

    class FLOAT:
        ST = ["st" + str(i) for i in range(8)]
        XMM = ["xmm" + str(i) for i in range(8)]


class FREEZE_TYPE:
    DEFAULT = 0
    INCREMENT = 1
    DECREMENT = 2


class VALUE_REPR:
    UNSIGNED = 0
    SIGNED = 1
    HEX = 2


class VALUE_INDEX:
    # Beginning of the integer indexes, new integer indexes should be added between 0 and 3
    INT8 = 0
    INT16 = 1
    INT32 = 2
    INT64 = 3
    # Ending of the integer indexes

    FLOAT32 = 4
    FLOAT64 = 5

    # Beginning of the string indexes, new string indexes should be added between 6 and 9
    STRING_ASCII = 6
    STRING_UTF8 = 7
    STRING_UTF16 = 8
    STRING_UTF32 = 9
    # Ending of the string indexes

    AOB = 10  # Array of Bytes

    @staticmethod
    def is_integer(value_index):
        return VALUE_INDEX.INT8 <= value_index <= VALUE_INDEX.INT64

    @staticmethod
    def is_string(value_index):
        return VALUE_INDEX.STRING_ASCII <= value_index <= VALUE_INDEX.STRING_UTF32

    @staticmethod
    def has_length(value_index):
        return VALUE_INDEX.STRING_ASCII <= value_index <= VALUE_INDEX.STRING_UTF32 or value_index == VALUE_INDEX.AOB


class SCAN_INDEX:
    INT_ANY = 0
    INT8 = 1
    INT16 = 2
    INT32 = 3
    INT64 = 4
    FLOAT_ANY = 5
    FLOAT32 = 6
    FLOAT64 = 7
    ANY = 8
    STRING = 9
    AOB = 10  # Array of Bytes


# GDB already provides breakpoint info in english, no need to make these translatable
on_hit_to_text_dict = {
    BREAKPOINT_ON_HIT.BREAK: "Break",
    BREAKPOINT_ON_HIT.FIND_CODE: "Find Code",
    BREAKPOINT_ON_HIT.FIND_ADDR: "Find Address",
    BREAKPOINT_ON_HIT.TRACE: "Trace"
}

# Represents the texts at indexes in the address table
# TODO: This class is mostly an UI helper, maybe integrate it into the the UI completely in the future?
index_to_text_dict = collections.OrderedDict([
    (VALUE_INDEX.INT8, "Int8"),
    (VALUE_INDEX.INT16, "Int16"),
    (VALUE_INDEX.INT32, "Int32"),
    (VALUE_INDEX.INT64, "Int64"),
    (VALUE_INDEX.FLOAT32, "Float32"),
    (VALUE_INDEX.FLOAT64, "Float64"),
    (VALUE_INDEX.STRING_ASCII, "String_ASCII"),
    (VALUE_INDEX.STRING_UTF8, "String_UTF8"),
    (VALUE_INDEX.STRING_UTF16, "String_UTF16"),
    (VALUE_INDEX.STRING_UTF32, "String_UTF32"),
    (VALUE_INDEX.AOB, "ByteArray")
])

text_to_index_dict = collections.OrderedDict()
for key in index_to_text_dict:
    text_to_index_dict[index_to_text_dict[key]] = key

scanmem_result_to_index_dict = collections.OrderedDict([
    ("I8", VALUE_INDEX.INT8),
    ("I8u", VALUE_INDEX.INT8),
    ("I8s", VALUE_INDEX.INT8),
    ("I16", VALUE_INDEX.INT16),
    ("I16u", VALUE_INDEX.INT16),
    ("I16s", VALUE_INDEX.INT16),
    ("I32", VALUE_INDEX.INT32),
    ("I32u", VALUE_INDEX.INT32),
    ("I32s", VALUE_INDEX.INT32),
    ("I64", VALUE_INDEX.INT64),
    ("I64u", VALUE_INDEX.INT64),
    ("I64s", VALUE_INDEX.INT64),
    ("F32", VALUE_INDEX.FLOAT32),
    ("F64", VALUE_INDEX.FLOAT64),
    ("string", VALUE_INDEX.STRING_UTF8),
    ("bytearray", VALUE_INDEX.AOB)
])

# Represents the texts at indexes in scan combobox
# TODO: Same as index_to_text_dict, consider integrating into UI completely
scan_index_to_text_dict = collections.OrderedDict([
    (SCAN_INDEX.INT_ANY, "Int(any)"),
    (SCAN_INDEX.INT8, "Int8"),
    (SCAN_INDEX.INT16, "Int16"),
    (SCAN_INDEX.INT32, "Int32"),
    (SCAN_INDEX.INT64, "Int64"),
    (SCAN_INDEX.FLOAT_ANY, "Float(any)"),
    (SCAN_INDEX.FLOAT32, "Float32"),
    (SCAN_INDEX.FLOAT64, "Float64"),
    (SCAN_INDEX.ANY, "Any(int, float)"),
    (SCAN_INDEX.STRING, "String"),
    (VALUE_INDEX.AOB, "ByteArray")
])

# Used in scan_data_type option of scanmem
scan_index_to_scanmem_dict = collections.OrderedDict([
    (SCAN_INDEX.INT_ANY, "int"),
    (SCAN_INDEX.INT8, "int8"),
    (SCAN_INDEX.INT16, "int16"),
    (SCAN_INDEX.INT32, "int32"),
    (SCAN_INDEX.INT64, "int64"),
    (SCAN_INDEX.FLOAT_ANY, "float"),
    (SCAN_INDEX.FLOAT32, "float32"),
    (SCAN_INDEX.FLOAT64, "float64"),
    (SCAN_INDEX.ANY, "number"),
    (SCAN_INDEX.STRING, "string"),
    (VALUE_INDEX.AOB, "bytearray")
])


# TODO: Same as index_to_text_dict, consider integrating into UI completely
class SCAN_TYPE:
    EXACT = 0
    INCREASED = 1
    INCREASED_BY = 2
    DECREASED = 3
    DECREASED_BY = 4
    LESS = 5
    MORE = 6
    BETWEEN = 7
    CHANGED = 8
    UNCHANGED = 9
    UNKNOWN = 10

    @staticmethod
    def get_list(scan_mode):
        if scan_mode == SCAN_MODE.NEW:
            return [SCAN_TYPE.EXACT, SCAN_TYPE.LESS, SCAN_TYPE.MORE, SCAN_TYPE.BETWEEN, SCAN_TYPE.UNKNOWN]
        else:
            return [SCAN_TYPE.EXACT, SCAN_TYPE.INCREASED, SCAN_TYPE.INCREASED_BY, SCAN_TYPE.DECREASED,
                    SCAN_TYPE.DECREASED_BY, SCAN_TYPE.LESS, SCAN_TYPE.MORE, SCAN_TYPE.BETWEEN,
                    SCAN_TYPE.CHANGED, SCAN_TYPE.UNCHANGED]


class SCAN_MODE:
    NEW = 0
    ONGOING = 1


class SCAN_SCOPE:
    BASIC = 1
    NORMAL = 2
    FULL_RW = 3
    FULL = 4

class ENDIANNESS:
    HOST = 0
    LITTLE = 1
    BIG = 2

string_index_to_encoding_dict = {
    VALUE_INDEX.STRING_UTF8: ["utf-8", "surrogateescape"],
    VALUE_INDEX.STRING_UTF16: ["utf-16", "replace"],
    VALUE_INDEX.STRING_UTF32: ["utf-32", "replace"],
    VALUE_INDEX.STRING_ASCII: ["ascii", "replace"],
}

string_index_to_multiplier_dict = {
    VALUE_INDEX.STRING_UTF8: 2,
    VALUE_INDEX.STRING_UTF16: 4,
    VALUE_INDEX.STRING_UTF32: 8,
}

# first value is the length and the second one is the type
# Check gdbutils for an exemplary usage
index_to_valuetype_dict = {
    VALUE_INDEX.INT8: [1, "B"],
    VALUE_INDEX.INT16: [2, "H"],
    VALUE_INDEX.INT32: [4, "I"],
    VALUE_INDEX.INT64: [8, "Q"],
    VALUE_INDEX.FLOAT32: [4, "f"],
    VALUE_INDEX.FLOAT64: [8, "d"],
    VALUE_INDEX.STRING_ASCII: [None, None],
    VALUE_INDEX.STRING_UTF8: [None, None],
    VALUE_INDEX.STRING_UTF16: [None, None],
    VALUE_INDEX.STRING_UTF32: [None, None],
    VALUE_INDEX.AOB: [None, None]
}

# Check gdbutils for an exemplary usage
index_to_struct_pack_dict = {
    VALUE_INDEX.INT8: "B",
    VALUE_INDEX.INT16: "H",
    VALUE_INDEX.INT32: "I",
    VALUE_INDEX.INT64: "Q",
    VALUE_INDEX.FLOAT32: "f",
    VALUE_INDEX.FLOAT64: "d"
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
tuple_breakpoint_info = collections.namedtuple("tuple_breakpoint_info", "number breakpoint_type \
                                                disp enabled address size on_hit hit_count enable_count condition")

# start, end-->int, perms-->str, file_name-->str
tuple_region_info = collections.namedtuple("tuple_region_info", "start end perms file_name")

# all fields-->str/None
tuple_examine_expression = collections.namedtuple("tuple_examine_expression", "all address symbol")

# all fields-->bool
gdb_output_mode = collections.namedtuple("gdb_output_mode", "async_output command_output command_info")


class GDBInitializeException(Exception):
    def __init__(self, message="GDB not initialized"):
        super(GDBInitializeException, self).__init__(message)


class Frozen:
    def __init__(self, value, freeze_type):
        self.value = value
        self.freeze_type = freeze_type


class ValueType:
    def __init__(self, value_index=VALUE_INDEX.INT32, length=10, zero_terminate=True,
                 value_repr=VALUE_REPR.UNSIGNED, endian=ENDIANNESS.HOST):
        """
        Args:
            value_index (int): Determines the type of data. Can be a member of VALUE_INDEX
            length (int): Length of the data. Only used when the value_index is STRING or AOB
            zero_terminate (bool): If False, ",NZT" will be appended to the text representation
            Only used when value_index is STRING. Ignored otherwise. "NZT" stands for "Non-Zero Terminate"
            value_repr (int): Determines how the data is represented. Can be a member of VALUE_REPR
            endian (int): Determines the endianness. Can be a member of ENDIANNESS
        """
        self.value_index = value_index
        self.length = length
        self.zero_terminate = zero_terminate
        self.value_repr = value_repr
        self.endian = endian

    def serialize(self):
        return self.value_index, self.length, self.zero_terminate, self.value_repr, self.endian

    def text(self):
        """Returns the text representation according to its members

        Returns:
            str: A str generated by given parameters

        Examples:
            value_index=VALUE_INDEX.STRING_UTF16, length=15, zero_terminate=False--▼
            returned str="String_UTF16[15],NZT"
            value_index=VALUE_INDEX.AOB, length=42-->returned str="AoB[42]"
        """
        returned_string = index_to_text_dict[self.value_index]
        if VALUE_INDEX.is_string(self.value_index):
            returned_string += f"[{self.length}]"
            if not self.zero_terminate:
                returned_string += ",NZT"
        elif self.value_index == VALUE_INDEX.AOB:
            returned_string += f"[{self.length}]"
        if VALUE_INDEX.is_integer(self.value_index):
            if self.value_repr == VALUE_REPR.SIGNED:
                returned_string += "(s)"
            elif self.value_repr == VALUE_REPR.HEX:
                returned_string += "(h)"
        if self.endian == ENDIANNESS.LITTLE:
            returned_string += "<L>"
        elif self.endian == ENDIANNESS.BIG:
            returned_string += "<B>"
        return returned_string


class PointerType:
    def __init__(self, base_address, offsets_list=None):
        """
        Args:
            base_address (str, int): The base address of where this pointer starts from. Can be str expression or int.
            offsets_list (list): List of offsets to reach the final pointed data. Can be None for no offsets.
            Last offset in list won't be dereferenced to emulate CE behaviour.
        """
        self.base_address = base_address
        self.offsets_list = [] if not offsets_list else offsets_list

    def serialize(self):
        return self.base_address, self.offsets_list

    def get_base_address(self):
        """
        Returns the text representation of this pointer's base address
        """
        return hex(self.base_address) if type(self.base_address) != str else self.base_address


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


class KeyboardModifiersTupleDict(collections.abc.Mapping):
    def __init__(self, OrderedDict_like_list):
        new_dict = {}
        for keycomb, value in OrderedDict_like_list:
            new_dict[keycomb] = value
        self._storage = new_dict

    def __getitem__(self, keycomb):
        return self._storage[keycomb]

    def __iter__(self):
        return iter(self._storage)

    def __len__(self):
        return len(self._storage)

