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

import collections.abc, logging, queue, struct, sys
from typing import Any, Callable, Literal
from libpince import regexes

_logger = logging.getLogger("PINCE")


class PATHS:
    GDB = "/bin/gdb"  # Use utils.get_default_gdb_path()
    TMP = "/tmp/PINCE/"  # Use utils.get_tmp_path()
    IPC = "/dev/shm/PINCE_IPC/"  # Use utils.get_ipc_path()
    FROM_PINCE = "/from_PINCE"  # Use utils.get_from_pince_file()
    TO_PINCE = "/to_PINCE"  # Use utils.get_to_pince_file()


class USER_PATHS:
    # Use utils.get_user_path() to make use of these
    CONFIG = ".config/"
    ROOT = CONFIG + "PINCE/"
    GDBINIT = ROOT + "gdbinit"
    GDBINIT_AA = ROOT + "gdbinit_after_attach"
    PINCEINIT = ROOT + "pinceinit.py"
    PINCEINIT_AA = ROOT + "pinceinit_after_attach.py"

    @staticmethod
    def get_init_files() -> tuple[str, str, str, str]:
        return (
            USER_PATHS.GDBINIT,
            USER_PATHS.GDBINIT_AA,
            USER_PATHS.PINCEINIT,
            USER_PATHS.PINCEINIT_AA,
        )


class INFERIOR_STATUS:
    RUNNING = 1
    STOPPED = 2


class INFERIOR_ARCH:
    ARCH_32 = 1
    ARCH_64 = 2


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
    FINISHED = 3


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
    GENERAL_64 = [
        "rax",
        "rbx",
        "rcx",
        "rdx",
        "rsi",
        "rdi",
        "rbp",
        "rsp",
        "rip",
        "r8",
        "r9",
        "r10",
        "r11",
        "r12",
        "r13",
        "r14",
        "r15",
    ]
    SEGMENT = ["cs", "ss", "ds", "es", "fs", "gs"]
    FLAG = ["cf", "pf", "af", "zf", "sf", "tf", "if", "df", "of"]

    class FLOAT:
        ST = ["st" + str(i) for i in range(8)]
        XMM_32 = ["xmm" + str(i) for i in range(8)]
        XMM_64 = ["xmm" + str(i) for i in range(16)]


class FREEZE_TYPE:
    DEFAULT = 0
    ALLOW_INCREMENT = 1
    ALLOW_DECREMENT = 2


class VALUE_REPR:
    UNSIGNED = 0
    SIGNED = 1
    HEX = 2


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


# GDB already provides breakpoint info in English, no need to make these translatable
on_hit_to_text_dict = {
    BREAKPOINT_ON_HIT.BREAK: "Break",
    BREAKPOINT_ON_HIT.FIND_CODE: "Find Code",
    BREAKPOINT_ON_HIT.FIND_ADDR: "Find Address",
    BREAKPOINT_ON_HIT.TRACE: "Trace",
}

# Represents the texts at indexes in scan combobox
# TODO: Consider integrating this UI helper into the UI completely
scan_index_to_text_dict = collections.OrderedDict(
    [
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
        (SCAN_INDEX.AOB, "ByteArray"),
    ]
)


# TODO: Consider integrating this UI helper into the UI completely
class SCAN_TYPE:
    EXACT = 0
    NOT = 1
    INCREASED = 2
    INCREASED_BY = 3
    DECREASED = 4
    DECREASED_BY = 5
    LESS = 6
    MORE = 7
    BETWEEN = 8
    CHANGED = 9
    UNCHANGED = 10
    UNKNOWN = 11

    @staticmethod
    def get_list(scan_mode: int, value_type: int) -> list[int]:
        if scan_mode == SCAN_MODE.NEW:
            if value_type == SCAN_INDEX.STRING or value_type == SCAN_INDEX.AOB:
                list = [
                    SCAN_TYPE.EXACT,
                    SCAN_TYPE.UNKNOWN,
                ]
            else:
                list = [
                    SCAN_TYPE.EXACT,
                    SCAN_TYPE.NOT,
                    SCAN_TYPE.LESS,
                    SCAN_TYPE.MORE,
                    SCAN_TYPE.BETWEEN,
                    SCAN_TYPE.UNKNOWN,
                ]
        else:
            if value_type == SCAN_INDEX.STRING or value_type == SCAN_INDEX.AOB:
                list = [SCAN_TYPE.EXACT]
            else:
                list = [
                    SCAN_TYPE.EXACT,
                    SCAN_TYPE.NOT,
                    SCAN_TYPE.INCREASED,
                    SCAN_TYPE.INCREASED_BY,
                    SCAN_TYPE.DECREASED,
                    SCAN_TYPE.DECREASED_BY,
                    SCAN_TYPE.LESS,
                    SCAN_TYPE.MORE,
                    SCAN_TYPE.BETWEEN,
                    SCAN_TYPE.CHANGED,
                    SCAN_TYPE.UNCHANGED,
                ]

        return list


class SCAN_MODE:
    NEW = 0
    ONGOING = 1


class ENDIANNESS:
    HOST = 0
    LITTLE = 1
    BIG = 2


_HOST_ENDIANNESS = ENDIANNESS.LITTLE if sys.byteorder == "little" else ENDIANNESS.BIG

# size-->int, any other field-->str
tuple_breakpoint_info = collections.namedtuple(
    "tuple_breakpoint_info",
    "number breakpoint_type disp enabled address size on_hit hit_count enable_count condition",
)

# start, end-->int, perms-->str, file_name-->str
tuple_region_info = collections.namedtuple("tuple_region_info", "start end perms file_name region_index")

# all fields-->str/None
tuple_examine_expression = collections.namedtuple("tuple_examine_expression", "all address symbol")

# all fields-->bool
gdb_output_mode = collections.namedtuple("gdb_output_mode", "async_output command_output command_info")


class GDBInitializeException(Exception):
    def __init__(self, message: str = "GDB not initialized") -> None:
        super(GDBInitializeException, self).__init__(message)


class Frozen:
    def __init__(self, value: Any, freeze_type: int = FREEZE_TYPE.DEFAULT) -> None:
        self.value = value
        self.freeze_type = freeze_type
        self.enabled = False


class ScriptEntry:
    """An address table row that runs a Libpince Engine script when toggled instead of freezing a value.

    Only the script is serialized to the cheat table.
    Namespace is built on first enable and kept so variables set by the [ENABLE] section survive
    into a later [DISABLE] run within the same session.
    """

    def __init__(self, script: str = "") -> None:
        self.script = script
        self.namespace: dict[str, Any] | None = None


class ValueType:
    def __init__(self) -> None:
        if type(self) is ValueType:
            raise TypeError("ValueType is a base class. Construct a concrete value type")

    def serialize(self) -> tuple[int, ...]:
        return (
            _SERIALIZED_IDS_BY_TYPE[type(self), self._serialization_args()],
            getattr(self, "length", 10),
            getattr(self, "zero_terminate", True),
            getattr(self, "value_repr", VALUE_REPR.UNSIGNED),
            getattr(self, "endian", ENDIANNESS.HOST),
        )

    @staticmethod
    def deserialize(data: tuple | list) -> "ValueType":
        if not data or type(data[0]) is not int:
            raise TypeError("Serialized value types must start with an integer ID")
        serialized_id = data[0]
        value_type_class, constructor_args = _SERIALIZED_TYPE_IDS[serialized_id]
        if value_type_class is BitFieldValueType:
            if len(data) != 4:
                raise TypeError("Serialized BitField types must contain four fields")
            _, bits, start_bit, value_repr = data
            return value_type_class(bits, start_bit, value_repr=value_repr)
        if len(data) == 4:
            data = (*data, ENDIANNESS.HOST)
        elif len(data) != 5:
            raise TypeError("Serialized value types must contain four or five fields")
        serialized_id, length, zero_terminate, value_repr, endian = data
        value_type = value_type_class(*constructor_args)
        for name, value in (("length", length), ("zero_terminate", zero_terminate), ("value_repr", value_repr), ("endian", endian)):
            if hasattr(value_type, name):
                setattr(value_type, name, value)
        return value_type

    def _serialization_args(self) -> tuple[Any, ...]:
        return ()

    def _endian_suffix(self) -> str:
        if self.endian == ENDIANNESS.LITTLE:
            return "<L>"
        if self.endian == ENDIANNESS.BIG:
            return "<B>"
        return ""

    def _repr_suffix(self) -> str:
        if self.value_repr == VALUE_REPR.SIGNED:
            return "(s)"
        if self.value_repr == VALUE_REPR.HEX:
            return "(h)"
        return ""

    def _apply_endian(self, data: bytes) -> bytes:
        if self.endian != ENDIANNESS.HOST and self.endian != _HOST_ENDIANNESS:
            return data[::-1]
        return data

    @property
    def read_size(self) -> int | None:
        """Number of bytes required for a memory read."""
        raise NotImplementedError

    def parse(self, text: str) -> Any | None:
        raise NotImplementedError

    def decode(self, data: bytes) -> Any:
        raise NotImplementedError

    def encode(self, value: Any) -> bytes | None:
        raise NotImplementedError

    def text(self) -> str:
        raise NotImplementedError


class IntegerValueType(ValueType):
    _struct_code_by_bits = {8: "B", 16: "H", 32: "I", 64: "Q"}

    def __init__(
        self,
        bits: Literal[8, 16, 32, 64] = 32,
        *,
        value_repr: int = VALUE_REPR.UNSIGNED,
        endian: int = ENDIANNESS.HOST,
    ) -> None:
        if type(bits) is not int or bits not in self._struct_code_by_bits:
            raise ValueError("Integer bits must be 8, 16, 32, or 64")
        self.bits = bits
        self.value_repr = value_repr
        self.endian = endian

    def _serialization_args(self) -> tuple[int]:
        return (self.bits,)

    @property
    def read_size(self) -> int:
        return self.bits // 8

    def parse(self, text: str) -> int | None:
        if not text:
            _logger.error("Missing string parameter")
            return None
        text = text.strip()
        try:
            value = int(text, 0)
        except ValueError:
            try:
                value = int(float(text))
            except (ValueError, TypeError, OverflowError):
                try:
                    if regexes.hex_arithmetic.fullmatch(text) and "**" not in text:
                        return int(eval(text)) % (1 << self.bits)
                except Exception:
                    pass
                _logger.error(f"{text} can't be parsed as integer or hexadecimal")
                return None
        return value % (1 << self.bits)

    def decode(self, data: bytes) -> str | int:
        data_type = self._struct_code_by_bits[self.bits]
        if self.value_repr == VALUE_REPR.SIGNED:
            data_type = data_type.lower()
        result = struct.unpack_from(data_type, self._apply_endian(data))[0]
        return hex(result) if self.value_repr == VALUE_REPR.HEX else result

    def encode(self, value: Any) -> bytes | None:
        if isinstance(value, str):
            value = self.parse(value)
            if value is None:
                return None
        elif isinstance(value, int):
            value %= 1 << self.bits
        return self._apply_endian(struct.pack(self._struct_code_by_bits[self.bits], value))

    def text(self) -> str:
        return f"Int{self.bits}{self._repr_suffix()}{self._endian_suffix()}"


class BitFieldValueType(ValueType):
    def __init__(
        self,
        bits: int = 1,
        start_bit: int = 0,
        *,
        value_repr: int = VALUE_REPR.UNSIGNED,
    ) -> None:
        if type(bits) is not int or not 1 <= bits <= 64:
            raise ValueError("BitField bits must be between 1 and 64")
        if type(start_bit) is not int or not 0 <= start_bit <= 7:
            raise ValueError("BitField start bit must be between 0 and 7")
        if type(value_repr) is not int or value_repr not in (VALUE_REPR.UNSIGNED, VALUE_REPR.SIGNED, VALUE_REPR.HEX):
            raise ValueError("Invalid BitField representation")
        self.bits = bits
        self.start_bit = start_bit
        self.value_repr = value_repr

    def serialize(self) -> tuple[int, int, int, int]:
        return _SERIALIZED_IDS_BY_TYPE[type(self), self._serialization_args()], self.bits, self.start_bit, self.value_repr

    @property
    def read_size(self) -> int:
        return (self.start_bit + self.bits + 7) // 8

    def _validated(self, value: Any) -> int | None:
        limit = 1 << self.bits
        minimum, maximum = (-limit // 2, limit // 2 - 1) if self.value_repr == VALUE_REPR.SIGNED else (0, limit - 1)
        if type(value) is not int or not minimum <= value <= maximum:
            _logger.error(f"{value!r} is outside the range [{minimum}, {maximum}] for {self.text()}")
            return None
        return value

    def parse(self, text: str) -> int | None:
        if not text:
            _logger.error("Missing string parameter")
            return None
        try:
            value = int(text, 0)
        except ValueError:
            try:
                if any(op in text for op in "+-*/") and regexes.hex_arithmetic.fullmatch(text) and "**" not in text:
                    return self._validated(int(eval(text)))
            except Exception:
                pass
            _logger.error(f"{text!r} can't be parsed as BitField value")
            return None
        return self._validated(value)

    def decode(self, data: bytes) -> str | int:
        result = (int.from_bytes(data, "little") >> self.start_bit) & ((1 << self.bits) - 1)
        if self.value_repr == VALUE_REPR.SIGNED and result >= 1 << (self.bits - 1):
            result -= 1 << self.bits
        return hex(result) if self.value_repr == VALUE_REPR.HEX else result

    def encode(self, value: Any) -> bytes | None:
        raise TypeError("BitField values require existing bytes, use encode_into()")

    def encode_into(self, current: bytes, value: Any) -> bytes | None:
        if len(current) != self.read_size:
            raise ValueError(f"{self.text()} requires exactly {self.read_size} existing bytes")
        value = self.parse(value) if isinstance(value, str) else self._validated(value)
        if value is None:
            return None
        value_mask = (1 << self.bits) - 1
        field_mask = value_mask << self.start_bit
        current_value = int.from_bytes(current, "little")
        result = (current_value & ~field_mask) | ((value & value_mask) << self.start_bit)
        return result.to_bytes(self.read_size, "little")

    def text(self) -> str:
        return f"BitField[{self.bits}]@{self.start_bit}{self._repr_suffix()}"


class FloatValueType(ValueType):
    _struct_code_by_bits = {32: "f", 64: "d"}

    def __init__(
        self,
        bits: Literal[32, 64] = 32,
        *,
        endian: int = ENDIANNESS.HOST,
    ) -> None:
        if type(bits) is not int or bits not in self._struct_code_by_bits:
            raise ValueError("Float bits must be 32 or 64")
        self.bits = bits
        self.endian = endian

    def _serialization_args(self) -> tuple[int]:
        return (self.bits,)

    @property
    def read_size(self) -> int:
        return self.bits // 8

    def parse(self, text: str) -> float | None:
        if not text:
            _logger.error("Missing string parameter")
            return None
        text = text.strip().replace(",", ".")
        try:
            return float(text)
        except ValueError:
            try:
                return float(int(text, 0))
            except (ValueError, TypeError, OverflowError):
                try:
                    if regexes.hex_arithmetic.fullmatch(text) and "**" not in text:
                        return float(eval(text))
                except Exception:
                    pass
                _logger.error(f"{text} can't be parsed as floating point variable")
                return None

    def decode(self, data: bytes) -> float:
        return struct.unpack_from(self._struct_code_by_bits[self.bits], self._apply_endian(data))[0]

    def encode(self, value: Any) -> bytes | None:
        if isinstance(value, str):
            value = self.parse(value)
            if value is None:
                return None
        return self._apply_endian(struct.pack(self._struct_code_by_bits[self.bits], value))

    def text(self) -> str:
        return f"Float{self.bits}" + self._endian_suffix()


class StringValueType(ValueType):
    def __init__(
        self,
        encoding: Literal["ascii", "utf-8", "utf-16", "utf-32"],
        *,
        length: int = 10,
        zero_terminate: bool = True,
        endian: int = ENDIANNESS.HOST,
    ) -> None:
        if encoding not in ("ascii", "utf-8", "utf-16", "utf-32"):
            raise ValueError(f"Unsupported string encoding: {encoding}")
        self.encoding = encoding
        self.length = length
        self.zero_terminate = zero_terminate
        self.endian = endian

    def _serialization_args(self) -> tuple[str]:
        return (self.encoding,)

    @property
    def read_size(self) -> int | None:
        try:
            length = int(self.length)
        except (TypeError, ValueError, OverflowError):
            return None
        if length <= 0:
            return None
        return length * (1 if self.encoding == "ascii" else 4)

    def parse(self, text: str) -> str | None:
        if not text:
            _logger.error("Missing string parameter")
            return None
        return text

    def _codec(self) -> tuple[str, str]:
        encoding = self.encoding
        if encoding in ("utf-16", "utf-32"):
            target_endian = _HOST_ENDIANNESS if self.endian == ENDIANNESS.HOST else self.endian
            encoding += "-le" if target_endian == ENDIANNESS.LITTLE else "-be"
        errors = "surrogateescape" if self.encoding == "utf-8" else "replace"
        return encoding, errors

    def decode(self, data: bytes) -> str:
        encoding, errors = self._codec()
        result = data.decode(encoding, errors)
        if self.zero_terminate:
            result = "\x00" if result.startswith("\x00") else result.split("\x00")[0]
        return result[: int(self.length)]

    def encode(self, value: Any) -> bytes | None:
        if not isinstance(value, str) or self.parse(value) is None:
            return None
        encoding, errors = self._codec()
        result = value.encode(encoding, errors)
        if self.zero_terminate:
            result += "\x00".encode(encoding, errors)
        return result

    def text(self) -> str:
        returned_string = f"String_{self.encoding.replace('-', '').upper()}[{self.length}]"
        if not self.zero_terminate:
            returned_string += ",NZT"
        return returned_string + self._endian_suffix()


class ByteArrayValueType(ValueType):
    def __init__(self, length: int = 10) -> None:
        self.length = length

    @property
    def read_size(self) -> int | None:
        try:
            length = int(self.length)
        except (TypeError, ValueError, OverflowError):
            return None
        return length if length > 0 else None

    def parse(self, text: str) -> list[int] | None:
        if not text:
            _logger.error("Missing string parameter")
            return None
        tokens = text.split()
        if not tokens or any(len(token) > 2 or any(char not in "0123456789abcdefABCDEF" for char in token) for token in tokens):
            _logger.error(f"{text.strip()} can't be parsed as array of bytes")
            return None
        return [int(token, 16) for token in tokens]

    def decode(self, data: bytes) -> str:
        return data.hex(" ")

    def encode(self, value: Any) -> bytes | None:
        if isinstance(value, str):
            value = self.parse(value)
            if value is None:
                return None
        return bytes(value)

    def text(self) -> str:
        return f"ByteArray[{self.length}]"


class StructValueType(ValueType):
    @property
    def read_size(self) -> None:
        return None

    def parse(self, text: str) -> None:
        return None

    def decode(self, data: bytes) -> None:
        return None

    def encode(self, value: Any) -> None:
        return None

    def text(self) -> str:
        return "Struct"


# These numeric IDs are stored by existing .pct files.
# Runtime code should use the concrete ValueType families instead.
# NEVER renumber these entries while old tables are supported.
_SERIALIZED_TYPE_IDS: dict[int, tuple[type[ValueType], tuple[Any, ...]]] = {
    0: (IntegerValueType, (8,)),
    1: (IntegerValueType, (16,)),
    2: (IntegerValueType, (32,)),
    3: (IntegerValueType, (64,)),
    4: (FloatValueType, (32,)),
    5: (FloatValueType, (64,)),
    6: (StringValueType, ("ascii",)),
    7: (StringValueType, ("utf-8",)),
    8: (StringValueType, ("utf-16",)),
    9: (StringValueType, ("utf-32",)),
    10: (ByteArrayValueType, ()),
    11: (StructValueType, ()),
    12: (BitFieldValueType, ()),
}
_SERIALIZED_IDS_BY_TYPE = {value: key for key, value in _SERIALIZED_TYPE_IDS.items()}


class StructureMember:
    """One field of a Structure: a value at an offset or a link to another structure.

    Exactly one of value_type / struct_ref is set.
    Nested members (struct_ref set) are pointer members when is_pointer else inline/embedded.
    """

    def __init__(
        self,
        name: str,
        offset: int,
        value_type: "ValueType | None" = None,
        struct_ref: str | None = None,
        is_pointer: bool = False,
    ) -> None:
        if (value_type is None) == (struct_ref is None):
            raise ValueError("StructureMember needs exactly one of value_type or struct_ref")
        self.name = name
        self.offset = offset
        self.value_type = value_type
        self.struct_ref = struct_ref
        self.is_pointer = is_pointer

    def serialize(self) -> tuple:
        vt = self.value_type.serialize() if self.value_type is not None else None
        return self.name, self.offset, vt, self.struct_ref, self.is_pointer

    @classmethod
    def deserialize(cls, data: tuple) -> "StructureMember":
        name, offset, vt, struct_ref, is_pointer = data
        return cls(name, offset, ValueType.deserialize(vt) if vt is not None else None, struct_ref, is_pointer)


class Structure:
    """A named, ordered list of StructureMembers. Offsets are explicit and relative to a base."""

    def __init__(self, name: str, members: "list[StructureMember] | None" = None) -> None:
        self.name = name
        self.members = members if members else []

    def serialize(self) -> tuple:
        return self.name, [m.serialize() for m in self.members]

    @classmethod
    def deserialize(cls, data: tuple) -> "Structure":
        name, members = data
        return cls(name, [StructureMember.deserialize(m) for m in members])


class PointerChainResult:
    def __init__(self) -> None:
        self.pointer_chain: list[int] = []

    def get_pointer_by_index(self, index: int) -> int | None:
        if index >= len(self.pointer_chain):
            return None
        return self.pointer_chain[index]

    def get_final_address(self) -> int | None:
        return self.pointer_chain[-1] if self.pointer_chain else None

    def get_final_address_as_hex(self) -> str | None:
        """
        Returns the hex representation of this pointer chain's final/destination address
        """
        return hex(self.pointer_chain[-1]) if self.pointer_chain else None


class PointerChainRequest:
    def __init__(self, base_address: str | int, offsets_list: list[int] | None = None) -> None:
        """
        Args:
            base_address (str, int): The base address of where this pointer chain starts from. Can be str expression or int.
            offsets_list (list): List of offsets to reach the final pointed data. Can be None for no offsets.
            Last offset in list won't be dereferenced to emulate CE behaviour.
        """
        self.base_address: str | int = base_address
        self.offsets_list: list[int] = [] if not offsets_list else offsets_list

    def serialize(self) -> tuple[str | int, list[int]]:
        return self.base_address, self.offsets_list

    def get_base_address_as_str(self) -> str:
        """
        Returns the text representation of this pointer's base address
        """
        return hex(self.base_address) if type(self.base_address) != str else self.base_address


class RegisterQueue:
    def __init__(self) -> None:
        self.queue_list: list[queue.Queue] = []

    def register_queue(self) -> queue.Queue:
        new_queue = queue.Queue()
        self.queue_list.append(new_queue)
        return new_queue

    def broadcast_message(self, message: Any) -> None:
        for item in self.queue_list:
            item.put(message)

    def delete_queue(self, queue_instance: queue.Queue) -> None:
        try:
            self.queue_list.remove(queue_instance)
        except ValueError:
            pass


class Signal:
    def __init__(self) -> None:
        self.callbacks: list[Callable] = []

    def connect(self, callback: Callable) -> None:
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def disconnect(self, callback: Callable) -> None:
        try:
            self.callbacks.remove(callback)
        except ValueError:
            pass

    def emit(self, *args: Any, **kwargs: Any) -> None:
        for callback in self.callbacks.copy():
            callback(*args, **kwargs)


class KeyboardModifiersTupleDict(collections.abc.Mapping):
    def __init__(self, OrderedDict_like_list: collections.abc.Iterable[tuple[Any, Any]]) -> None:
        new_dict = {}
        for keycomb, value in OrderedDict_like_list:
            new_dict[keycomb] = value
        self._storage = new_dict

    def __getitem__(self, keycomb: Any) -> Any:
        return self._storage[keycomb]

    def __iter__(self) -> collections.abc.Iterator[Any]:
        return iter(self._storage)

    def __len__(self) -> int:
        return len(self._storage)


class AllocatedMemory:
    def __init__(self, address: int, size: int, identity: tuple[int, int | None] | None = None) -> None:
        self.address = address
        self.size = size
        self.identity = identity
        # TODO BRK: Maybe expand with starting page address and old protection to restore state after deleting allocated memory
