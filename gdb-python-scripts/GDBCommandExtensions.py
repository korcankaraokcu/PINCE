import gdb
import pickle
import sys
import os

# This is some retarded hack, fix your shit gdb
sys.path.append(os.path.expanduser("~"))  # Adds the home directory to PYTHONPATH to import ScriptUtils
import ScriptUtils


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
        mem_file = "/proc/" + str(pid) + "/mem"
        table_contents_recv = pickle.load(open(recv_file, "rb"))
        for item in table_contents_recv:
            address = int(item[0], 16)
            FILE = open(mem_file, "rb")
            FILE.seek(address)
            item = FILE.read(10)
            table_contents_send.append(item)
            FILE.close()
        pickle.dump(table_contents_send, open(send_file, "wb"))


PrintAddressTableContents()
