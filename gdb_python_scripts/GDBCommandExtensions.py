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

        # table_contents_recv format: [[address1,value_type1],[address2,value_type2],..]
        for item in table_contents_recv:
            try:
                address = int(item[0], 16)
            except:
                table_contents_send.append("")
                continue
            value_type = item[1]
            length = ScriptUtils.convert_type_to_length(value_type)
            if length is 0:
                table_contents_send.append("")
                continue
            FILE = open(mem_file, "rb")
            try:
                FILE.seek(address)
                readed = FILE.read(length)
            except:
                table_contents_send.append("")
                FILE.close()
                continue
            readed_text = ScriptUtils.convert_binary_to_text(readed, value_type)
            table_contents_send.append(readed_text)
            FILE.close()
        pickle.dump(table_contents_send, open(send_file, "wb"))


PrintAddressTableContents()
