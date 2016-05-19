import gdb
from re import search, sub
import struct

# first value is the length and the second one is the type
# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
text_to_type_dict = {
    "Byte": [1, "b"],
    "2 Bytes": [2, "h"],
    "4 Bytes": [4, "i"],
    "8 Bytes": [8, "l"],
    "Float": [4, "f"],
    "Double": [8, "d"]
}


# This function is used to avoid errors in gdb scripts, because gdb scripts stop working when encountered an error
def issue_command(command):
    try:
        gdb.execute(command)
    except:
        gdb.execute('echo ??\n')


def convert_type_to_length(value_type):
    length = text_to_type_dict.get(value_type, 0)[0]
    if length is 0:
        if search(r"String\[\d*\]", value_type):  # String[10],U,NZT
            length = sub("[^0-9]", "", value_type)
            if search(r",U", value_type):  # check if Unicode, literal string
                length = int(length) * 2
            else:
                length = int(length)
        elif search(r"AoB\[\d*\]", value_type):  # AoB[10]
            length = sub("[^0-9]", "", value_type)
            length = int(length)
    return length


def convert_binary_to_text(binary, value_type):
    binary_type = text_to_type_dict.get(value_type, 0)[1]
    if binary_type is 0:
        return struct.unpack_from("s", binary)[0]
    return struct.unpack_from(binary_type, binary)[0]
