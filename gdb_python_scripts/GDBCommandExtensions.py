# -*- coding: utf-8 -*-
import gdb
import pickle
import sys

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE
import gdb_python_scripts.ScriptUtils as ScriptUtils
import SysUtils
import type_defs

INDEX_BYTE = type_defs.VALUE_INDEX.INDEX_BYTE
INDEX_2BYTES = type_defs.VALUE_INDEX.INDEX_2BYTES
INDEX_4BYTES = type_defs.VALUE_INDEX.INDEX_4BYTES
INDEX_8BYTES = type_defs.VALUE_INDEX.INDEX_8BYTES
INDEX_FLOAT = type_defs.VALUE_INDEX.INDEX_FLOAT
INDEX_DOUBLE = type_defs.VALUE_INDEX.INDEX_DOUBLE
INDEX_STRING = type_defs.VALUE_INDEX.INDEX_STRING
INDEX_AOB = type_defs.VALUE_INDEX.INDEX_AOB


class ReadMultipleAddresses(gdb.Command):
    def __init__(self):
        super(ReadMultipleAddresses, self).__init__("pince-read-multiple-addresses", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = []
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        directory_path = SysUtils.get_PINCE_IPC_directory(pid)
        recv_file = directory_path + "/read-list-from-PINCE.txt"
        send_file = directory_path + "/read-list-to-PINCE.txt"
        file_contents_recv = pickle.load(open(recv_file, "rb"))

        # file_contents_recv format: [[address1, index1, length1, unicode1, zero_terminate1],[address2, ...], ...]
        for item in file_contents_recv:
            address = item[0]
            index = item[1]
            try:
                length = item[2]
            except IndexError:
                length = 0
            try:
                unicode = item[3]
            except IndexError:
                unicode = False
            try:
                zero_terminate = item[4]
            except IndexError:
                zero_terminate = True
            readed = ScriptUtils.read_single_address(address, index, length, unicode, zero_terminate)
            file_contents_send.append(readed)
        pickle.dump(file_contents_send, open(send_file, "wb"))


class SetMultipleAddresses(gdb.Command):
    def __init__(self):
        super(SetMultipleAddresses, self).__init__("pince-set-multiple-addresses", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        directory_path = SysUtils.get_PINCE_IPC_directory(pid)
        recv_file = directory_path + "/set-list-from-PINCE.txt"
        file_contents_recv = pickle.load(open(recv_file, "rb"))

        # last item of file_contents_recv is always value, so we pop it from the list first
        value = file_contents_recv.pop()

        # file_contents_recv format after popping the value: [[address1, index1],[address2, index2], ...]
        for item in file_contents_recv:
            address = item[0]
            index = item[1]
            ScriptUtils.set_single_address(address, index, value)


class ReadSingleAddress(gdb.Command):
    def __init__(self):
        super(ReadSingleAddress, self).__init__("pince-read-single-address", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            parameters = eval(
                arg)  # more like EVIL mwahahahaha... HAHAHAHAHA... **muffled evil laughter from distance**

            # 5 is the number of parameters coming from PINCE
            address, value_index, length, unicode, zero_terminate = parameters + (None,) * (5 - len(parameters))
            address = hex(address)
        except:
            print("")
            return

        # python can't print a string that has null bytes in it, so we'll have to print the raw bytes instead and let PINCE do the parsing
        # Weird enough, even when python can't print those strings, pyqt can(in it's gui elements like labels)
        if value_index is INDEX_STRING:
            value_index = INDEX_AOB
            if unicode:
                try:
                    length = int(length)
                    length = length * 2
                except:
                    print("")
        print(ScriptUtils.read_single_address(address, value_index, length, unicode, zero_terminate))


class IgnoreErrors(gdb.Command):
    def __init__(self):
        super(IgnoreErrors, self).__init__("ignore-errors", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            gdb.execute(arg, from_tty)
        except:
            pass


class ParseConvenienceVariables(gdb.Command):
    def __init__(self):
        super(ParseConvenienceVariables, self).__init__("pince-parse-convenience-variables", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = []
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        directory_path = SysUtils.get_PINCE_IPC_directory(pid)
        recv_file = directory_path + "/variables-from-PINCE.txt"
        send_file = directory_path + "/variables-to-PINCE.txt"
        file_contents_recv = pickle.load(open(recv_file, "rb"))
        for item in file_contents_recv:
            try:
                value = gdb.parse_and_eval(item)
                parsed_value = str(value)
            except:
                parsed_value = None
            file_contents_send.append(parsed_value)
        pickle.dump(file_contents_send, open(send_file, "wb"))


IgnoreErrors()
ReadMultipleAddresses()
SetMultipleAddresses()
ReadSingleAddress()
ParseConvenienceVariables()
