import gdb
import struct
import sys

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

import GuiUtils
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
index_to_struct_pack_dict=type_defs.index_to_struct_pack_dict


# This function is used to avoid errors in gdb scripts, because gdb scripts stop working when encountered an error
def issue_command(command, error_message=""):
    try:
        gdb.execute(command)
    except:
        if error_message:
            error_message = str(error_message)
            gdb.execute('echo ' + error_message + '\n')


def read_single_address(address, value_type, length=0, unicode=False, zero_terminate=True):
    try:
        value_type = int(value_type)
        address = int(address, 16)
    except:
        return ""
    packed_data = index_to_valuetype_dict.get(value_type, -1)
    if value_type is COMBOBOX_STRING:
        try:
            expected_length = int(length)
        except:
            return ""
        if unicode:
            expected_length = length * 2
    elif value_type is COMBOBOX_AOB:
        try:
            expected_length = int(length)
        except:
            return ""
    else:
        expected_length = packed_data[0]
        data_type = packed_data[1]
    inferior = gdb.selected_inferior()
    pid = inferior.pid
    mem_file = "/proc/" + str(pid) + "/mem"
    FILE = open(mem_file, "rb")
    try:
        FILE.seek(address)
        readed = FILE.read(expected_length)
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


def set_single_address(address, value_index, value):
    try:
        address = int(address, 16)
    except:
        print(str(address) + " is not a valid address")
        return
    valid, write_data = GuiUtils.parse_string(value, value_index)
    if not valid:
        return
    if value_index is COMBOBOX_STRING:
        write_data = bytearray(write_data, "utf-8", "replace")
    elif value_index is COMBOBOX_AOB:
        write_data = bytearray(write_data)
    else:
        print(write_data)
        data_type = index_to_struct_pack_dict.get(value_index, -1)
        write_data = struct.pack(data_type, write_data)
    inferior = gdb.selected_inferior()
    pid = inferior.pid
    mem_file = "/proc/" + str(pid) + "/mem"
    FILE = open(mem_file, "rb+")
    try:
        FILE.seek(address)
        FILE.write(write_data)
    except:
        FILE.close()
        print("can't access the address " + str(address))
        return ""
    FILE.close()
