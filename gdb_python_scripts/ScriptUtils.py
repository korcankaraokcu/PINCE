import gdb
import struct

# first value is the length and the second one is the type
# dictionaries in GuiUtils, GDB_Engine and ScriptUtils are connected to each other
# any modification in one dictionary may require a rework in others
text_to_valuetype_dict = {
    0: [1, "b"],  # byte
    1: [2, "h"],  # 2 byte
    2: [4, "i"],  # 4 byte
    3: [8, "l"],  # 8 byte
    4: [4, "f"],  # float
    5: [8, "d"],  # double
    6: [None, None],  # string
    7: [None, None]  # array of bytes
}


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
    packed_data = text_to_valuetype_dict.get(value_type, -1)
    if value_type is 6 or value_type is 7:
        try:
            length = int(length)
        except:
            return ""
        if unicode:
            length = length * 2
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
    if value_type is 6:
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
    elif value_type is 7:
        return " ".join(format(n, '02x') for n in readed)
    else:
        return struct.unpack_from(data_type, readed)[0]
