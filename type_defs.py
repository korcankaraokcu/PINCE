PINCE_IPC_PATH = "/tmp/PINCE-connection/"
INITIAL_INJECTION_PATH = "/Injection/InitialCodeInjections.so"

INFERIOR_RUNNING = 0
INFERIOR_STOPPED = 1

NO_INJECTION = 0
SIMPLE_DLOPEN_CALL = 1
LINUX_INJECT = 2

INJECTION_SUCCESSFUL = 1
INJECTION_FAILED = 0
NO_INJECTION_ATTEMPT = -1

# represents the index of columns in address table
FROZEN_COL = 0  # Frozen
DESC_COL = 1  # Description
ADDR_COL = 2  # Address
TYPE_COL = 3  # Type
VALUE_COL = 4  # Value

# represents the index of valuetype combobox
# any change at indexes may require rework on the other dictionaries
INDEX_BYTE = 0
INDEX_2BYTES = 1
INDEX_4BYTES = 2
INDEX_8BYTES = 3
INDEX_FLOAT = 4
INDEX_DOUBLE = 5
INDEX_STRING = 6
INDEX_AOB = 7  # Array of Bytes

# represents the index of columns in disassemble table
DISAS_ADDR_COL = 0
DISAS_BYTES_COL = 1
DISAS_OPCODES_COL = 2
DISAS_COMMENT_COL = 3

# Represents the texts at indexes in combobox
index_to_text_dict = {
    INDEX_BYTE: "Byte",
    INDEX_2BYTES: "2 Bytes",
    INDEX_4BYTES: "4 Bytes",
    INDEX_8BYTES: "8 Bytes",
    INDEX_FLOAT: "Float",
    INDEX_DOUBLE: "Double",
    INDEX_STRING: "String",
    INDEX_AOB: "AoB"
}

text_to_index_dict = {
    "Byte": INDEX_BYTE,
    "2 Bytes": INDEX_2BYTES,
    "4 Bytes": INDEX_4BYTES,
    "8 Bytes": INDEX_8BYTES,
    "Float": INDEX_FLOAT,
    "Double": INDEX_DOUBLE
}

# A dictionary used to convert value_combobox index to gdb/mi x command
# Check GDB_Engine for an exemplary usage
index_to_gdbcommand_dict = {
    INDEX_BYTE: "db",
    INDEX_2BYTES: "dh",
    INDEX_4BYTES: "dw",
    INDEX_8BYTES: "dg",
    INDEX_FLOAT: "fw",
    INDEX_DOUBLE: "fg",
    INDEX_STRING: "xb",
    INDEX_AOB: "xb"
}

# first value is the length and the second one is the type
# Check ScriptUtils for an exemplary usage
index_to_valuetype_dict = {
    INDEX_BYTE: [1, "b"],
    INDEX_2BYTES: [2, "h"],
    INDEX_4BYTES: [4, "i"],
    INDEX_8BYTES: [8, "q"],
    INDEX_FLOAT: [4, "f"],
    INDEX_DOUBLE: [8, "d"],
    INDEX_STRING: [None, None],
    INDEX_AOB: [None, None]
}

# Check ScriptUtils for an exemplary usage
index_to_struct_pack_dict = {
    INDEX_BYTE: "B",
    INDEX_2BYTES: "H",
    INDEX_4BYTES: "I",
    INDEX_8BYTES: "Q",
    INDEX_FLOAT: "f",
    INDEX_DOUBLE: "d"
}
