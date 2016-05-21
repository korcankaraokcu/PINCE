import gdb
import pickle
import sys
import os

# This is some retarded hack, fix your shit gdb
sys.path.append(os.path.expanduser("~"))  # Adds the home directory to PYTHONPATH to import ScriptUtils
import ScriptUtils
import GuiUtils


class PrintAddressTableContents(gdb.Command):
    def __init__(self):
        super(PrintAddressTableContents, self).__init__("pince-update-address-table", gdb.COMMAND_USER)

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
            readed = ScriptUtils.read_single_address(address, index, length, unicode, zero_terminate, return_mode=True)
            table_contents_send.append(readed)
        pickle.dump(table_contents_send, open(send_file, "wb"))


PrintAddressTableContents()
