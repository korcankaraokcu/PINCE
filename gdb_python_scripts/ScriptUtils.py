import gdb
import struct
import sys

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

import type_defs

COMBOBOX_BYTE = type_defs.COMBOBOX_BYTE
COMBOBOX_2BYTES = type_defs.COMBOBOX_2BYTES
COMBOBOX_4BYTES = type_defs.COMBOBOX_4BYTES
COMBOBOX_8BYTES = type_defs.COMBOBOX_8BYTES
COMBOBOX_FLOAT = type_defs.COMBOBOX_FLOAT
COMBOBOX_DOUBLE = type_defs.COMBOBOX_DOUBLE
COMBOBOX_STRING = type_defs.COMBOBOX_STRING
COMBOBOX_AOB = type_defs.COMBOBOX_AOB

# first value is the length and the second one is the type
# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
index_to_valuetype_dict = type_defs.index_to_valuetype_dict


# This function is used to avoid errors in gdb scripts, because gdb scripts stop working when encountered an error
def issue_command(command):
    try:
        gdb.execute(command)
    except:
        gdb.execute('echo ??\n')


def read_single_address(address, value_type, length=0, unicode=False, zero_terminate=True):
    try:
        value_type = int(value_type)
        address = int(address, 16)
    except:
        return ""
    packed_data = index_to_valuetype_dict.get(value_type, -1)
    if value_type is COMBOBOX_STRING:
        try:
            length = int(length)
        except:
            return ""
        if unicode:
            length = length * 2
    elif value_type is COMBOBOX_AOB:
        try:
            length = int(length)
        except:
            return ""
    else:
        length = packed_data[0]
        data_type = packed_data[1]
    inferior = gdb.selected_inferior()
    pid = inferior.pid
    mem_file = "/proc/" + str(pid) + "/mem"
    FILE = open(mem_file, "rb")
    try:
        FILE.seek(address)
        readed = FILE.read(length)
    except:
        FILE.close()
        return ""
    FILE.close()
    if value_type is COMBOBOX_STRING:
        if unicode:
            returned_string = readed.decode("utf-8", "replace")
        else:
            returned_string = readed.decode("ascii", "replace")
        if zero_terminate:
            if returned_string.startswith('\x00'):
                returned_string = '\x00'
            else:
                returned_string = returned_string.split('\x00')[0]
        return returned_string[0:length]
    elif value_type is COMBOBOX_AOB:
        return " ".join(format(n, '02x') for n in readed)
    else:
        return struct.unpack_from(data_type, readed)[0]
