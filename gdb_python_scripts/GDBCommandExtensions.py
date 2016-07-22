# -*- coding: utf-8 -*-
import gdb
import pickle
import sys
import re

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE
import gdb_python_scripts.ScriptUtils as ScriptUtils
import SysUtils
import type_defs

REGISTERS_32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]
REGISTERS_64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "rip", "r8", "r9", "r10", "r11", "r12",
                "r13", "r14", "r15"]
REGISTERS_SEGMENT = ["cs", "ss", "ds", "es", "fs", "gs"]

INDEX_BYTE = type_defs.VALUE_INDEX.INDEX_BYTE
INDEX_2BYTES = type_defs.VALUE_INDEX.INDEX_2BYTES
INDEX_4BYTES = type_defs.VALUE_INDEX.INDEX_4BYTES
INDEX_8BYTES = type_defs.VALUE_INDEX.INDEX_8BYTES
INDEX_FLOAT = type_defs.VALUE_INDEX.INDEX_FLOAT
INDEX_DOUBLE = type_defs.VALUE_INDEX.INDEX_DOUBLE
INDEX_STRING = type_defs.VALUE_INDEX.INDEX_STRING
INDEX_AOB = type_defs.VALUE_INDEX.INDEX_AOB

ARCH_32 = type_defs.INFERIOR_ARCH.ARCH_32
ARCH_64 = type_defs.INFERIOR_ARCH.ARCH_64


class ReadMultipleAddresses(gdb.Command):
    def __init__(self):
        super(ReadMultipleAddresses, self).__init__("pince-read-multiple-addresses", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = []
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        recv_file = SysUtils.get_ipc_from_PINCE_file(pid)
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)
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
        recv_file = SysUtils.get_ipc_from_PINCE_file(pid)
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
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)
        recv_file = SysUtils.get_ipc_from_PINCE_file(pid)
        file_contents_recv = pickle.load(open(recv_file, "rb"))
        address = file_contents_recv[0]
        value_index = file_contents_recv[1]
        length = file_contents_recv[2]
        is_unicode = file_contents_recv[3]
        zero_terminate = file_contents_recv[4]
        file_contents_send = ScriptUtils.read_single_address(address, value_index, length, is_unicode, zero_terminate)
        pickle.dump(file_contents_send, open(send_file, "wb"))


class IgnoreErrors(gdb.Command):
    def __init__(self):
        super(IgnoreErrors, self).__init__("ignore-errors", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            gdb.execute(arg, from_tty)
        except:
            pass


class CLIOutput(gdb.Command):
    def __init__(self):
        super(CLIOutput, self).__init__("cli-output", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)
        try:
            file_contents_send = gdb.execute(arg, from_tty, to_string=True)
        except Exception as e:
            file_contents_send = str(e)
        print(file_contents_send)
        pickle.dump(file_contents_send, open(send_file, "wb"))


class ParseConvenienceVariables(gdb.Command):
    def __init__(self):
        super(ParseConvenienceVariables, self).__init__("pince-parse-convenience-variables", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = []
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        recv_file = SysUtils.get_ipc_from_PINCE_file(pid)
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)
        file_contents_recv = pickle.load(open(recv_file, "rb"))
        for item in file_contents_recv:
            try:
                value = gdb.parse_and_eval(item)
                parsed_value = str(value)
            except:
                parsed_value = None
            file_contents_send.append(parsed_value)
        pickle.dump(file_contents_send, open(send_file, "wb"))


class ReadRegisters(gdb.Command):
    def __init__(self):
        super(ReadRegisters, self).__init__("pince-read-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = {"cf": "0", "pf": "0", "af": "0", "zf": "0", "sf": "0", "tf": "0", "if": "0", "df": "0",
                              "of": "0"}
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)
        if str(gdb.parse_and_eval("$rax")) == "void":
            current_arch = ARCH_32
        else:
            current_arch = ARCH_64
        if current_arch == ARCH_64:
            general_register_list = REGISTERS_64
        else:
            general_register_list = REGISTERS_32
        regex_register = re.compile(r"0x[0-9a-fA-F]+")  # $6 = 0x7f0bc0b6bb40
        for item in general_register_list:
            result = gdb.execute("p/x $" + item, from_tty, to_string=True)
            parsed_result = regex_register.search(result).group(0)
            file_contents_send[item] = parsed_result
        result = gdb.execute("p/t $eflags", from_tty, to_string=True)
        parsed_result = re.search(r"=\s+\d+", result).group(0).split()[-1]  # $8 = 1010010011
        reversed_parsed_result = "".join(reversed(parsed_result))
        try:
            file_contents_send["cf"] = reversed_parsed_result[0]
            file_contents_send["pf"] = reversed_parsed_result[2]
            file_contents_send["af"] = reversed_parsed_result[4]
            file_contents_send["zf"] = reversed_parsed_result[6]
            file_contents_send["sf"] = reversed_parsed_result[7]
            file_contents_send["tf"] = reversed_parsed_result[8]
            file_contents_send["if"] = reversed_parsed_result[9]
            file_contents_send["df"] = reversed_parsed_result[10]
            file_contents_send["of"] = reversed_parsed_result[11]
        except IndexError:
            pass
        for item in REGISTERS_SEGMENT:
            result = gdb.execute("p/x $" + item, from_tty, to_string=True)
            parsed_result = regex_register.search(result).group(0)
            file_contents_send[item] = parsed_result
        pickle.dump(file_contents_send, open(send_file, "wb"))


class ReadFloatRegisters(gdb.Command):
    def __init__(self):
        super(ReadFloatRegisters, self).__init__("pince-read-float-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        file_contents_send = {}
        inferior = gdb.selected_inferior()
        pid = inferior.pid
        send_file = SysUtils.get_ipc_to_PINCE_file(pid)

        # st0-7
        for index in range(8):
            current_register = "st" + str(index)
            value = gdb.parse_and_eval("$" + current_register)
            file_contents_send[current_register] = str(value)

        # xmm0-7
        for index in range(8):
            current_register = "xmm" + str(index)
            value = gdb.parse_and_eval("$" + current_register + ".uint128")
            file_contents_send[current_register] = str(value)
        pickle.dump(file_contents_send, open(send_file, "wb"))


IgnoreErrors()
CLIOutput()
ReadMultipleAddresses()
SetMultipleAddresses()
ReadSingleAddress()
ParseConvenienceVariables()
ReadRegisters()
ReadFloatRegisters()
