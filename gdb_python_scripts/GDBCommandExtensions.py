import gdb
import pickle
import sys
import os
from re import split

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import ScriptUtils and GuiUtils
import gdb_python_scripts.ScriptUtils as ScriptUtils
import GuiUtils


# returns values from memory according to address table contents sent from PINCE
class ReadAddressTableContents(gdb.Command):
    def __init__(self):
        super(ReadAddressTableContents, self).__init__("pince-update-address-table", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        table_contents_send = []
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        directory_path = "/tmp/PINCE-connection/" + str(pid)
        recv_file = directory_path + "/address-table-from-PINCE.txt"
        send_file = directory_path + "/address-table-to-PINCE.txt"
        table_contents_recv = pickle.load(open(recv_file, "rb"))

        # table_contents_recv format: [[address1,string1],[address2,string2],..]
        for item in table_contents_recv:
            address = item[0]
            string = item[1]
            index, length, unicode, zero_terminate = GuiUtils.text_to_valuetype(string)
            readed = ScriptUtils.read_single_address(address, index, length, unicode, zero_terminate)
            table_contents_send.append(readed)
        pickle.dump(table_contents_send, open(send_file, "wb"))


class ReadSingleAddress(gdb.Command):
    def __init__(self):
        super(ReadSingleAddress, self).__init__("pince-read-single-address", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            parameters = eval(
                arg)  # more like EVIL mwahahahaha... HAHAHAHAHA... **muffled evil laughter from distance**

            # 5 is the number of parameters coming from PINCE
            address, value_type, length, unicode, zero_terminate = parameters + (None,) * (5 - len(parameters))
            address = hex(address)
        except:
            print("")
            return

        # python can't print a string that has null bytes in it, so we'll have to print the raw bytes instead and let PINCE do the parsing
        # Weird enough, even when python can't print those strings, pyqt can(in it's gui elements like labels)
        if value_type is 6:
            value_type = 7
        print(ScriptUtils.read_single_address(address, value_type, length, unicode, zero_terminate))


ReadAddressTableContents()
ReadSingleAddress()
