#!/usr/bin/python3
from re import search, split, findall, escape
from threading import Lock, Thread, Condition
from time import sleep, time
import pexpect
import os
import ctypes
import struct
import pickle

libc = ctypes.CDLL('libc.so.6')
is_32bit = struct.calcsize("P") * 8 == 32

import SysUtils
import type_defs

INDEX_BYTE = type_defs.INDEX_BYTE
INDEX_2BYTES = type_defs.INDEX_2BYTES
INDEX_4BYTES = type_defs.INDEX_4BYTES
INDEX_8BYTES = type_defs.INDEX_8BYTES
INDEX_FLOAT = type_defs.INDEX_FLOAT
INDEX_DOUBLE = type_defs.INDEX_DOUBLE
INDEX_STRING = type_defs.INDEX_STRING
INDEX_AOB = type_defs.INDEX_AOB

INITIAL_INJECTION_PATH = type_defs.INITIAL_INJECTION_PATH

INFERIOR_RUNNING = type_defs.INFERIOR_RUNNING
INFERIOR_STOPPED = type_defs.INFERIOR_STOPPED

NO_INJECTION = type_defs.NO_INJECTION
SIMPLE_DLOPEN_CALL = type_defs.SIMPLE_DLOPEN_CALL
LINUX_INJECT = type_defs.LINUX_INJECT

INJECTION_SUCCESSFUL = type_defs.INJECTION_SUCCESSFUL
INJECTION_FAILED = type_defs.INJECTION_FAILED
NO_INJECTION_ATTEMPT = type_defs.NO_INJECTION_ATTEMPT

currentpid = 0
child = object  # this object will be used with pexpect operations
lock_send_command = Lock()
lock_read_multiple_addresses = Lock()
lock_set_multiple_addresses = Lock()
gdb_async_condition = Condition()
status_changed_condition = Condition()
inferior_status = -1
gdb_output = ""
gdb_async_output = ""

index_to_gdbcommand_dict = type_defs.index_to_gdbcommand_dict


# The comments next to the regular expressions shows the expected gdb output, an elucidating light for the future developers


# issues the command sent
# all CLI commands and ctrl+key are supported, GDB/MI commands aren't supported yet
def send_command(command, control=False):
    global child
    global gdb_output
    with lock_send_command:
        if inferior_status is INFERIOR_RUNNING and not control:
            print("inferior is running")
            return
        command = str(command)
        time0 = time()
        if control:
            child.sendcontrol(command)
        else:
            command_file = SysUtils.get_gdb_command_file(currentpid)
            command_fd = open(command_file, "w")
            command_fd.write(command)
            command_fd.close()
            child.sendline("source " + command_file)
        if not control:
            while gdb_output is "":
                sleep(0.00001)
        time1 = time()
        print(time1 - time0)
        if not control:
            output = gdb_output
        else:
            output = ""
        gdb_output = ""
        return output.strip()


# check if we can attach to the target
def can_attach(pid=str):
    result = libc.ptrace(16, int(pid), 0, 0)  # 16 is PTRACE_ATTACH, check ptrace.h for details
    if result is -1:
        return False
    os.waitpid(int(pid), 0)
    libc.ptrace(17, int(pid), 0, 17)  # 17 is PTRACE_DETACH, check ptrace.h for details
    sleep(0.01)
    return True


def state_observe_thread():
    global inferior_status
    global child
    global gdb_output
    global gdb_async_output
    while True:
        child.expect_exact("(gdb)")
        print(child.before)  # debug mode on!

        # Check .gdbinit file for these strings
        matches = findall(r"<\-\-STOPPED\-\->|\*running,thread\-id=\"all\"",
                          child.before)  # <--STOPPED-->  # *running,thread-id="all"
        if len(matches) > 0:
            if search(r"STOPPED", matches[-1]):
                inferior_status = INFERIOR_STOPPED
            else:
                inferior_status = INFERIOR_RUNNING
            with status_changed_condition:
                status_changed_condition.notify_all()
        try:
            # The command will always start with the word "source", check send_command function for the cause
            command_file = escape(SysUtils.get_gdb_command_file(currentpid))
            gdb_output = split(r"&\"source\s" + command_file + r"\\n\"", child.before, 1)[1]  # &"command\n"
        except:
            gdb_output = ""
            with gdb_async_condition:
                gdb_async_output = child.before
                gdb_async_condition.notify_all()


def interrupt_inferior():
    send_command("c", control=True)


def continue_inferior():
    send_command("c")


# Attaches gdb to the target pid
# Returns the status of the thread injection
def attach(pid=str, injection_method=SIMPLE_DLOPEN_CALL):
    global currentpid
    global child
    currentpid = int(pid)
    SysUtils.create_PINCE_IPC_PATH(pid)
    currentdir = SysUtils.get_current_script_directory()
    child = pexpect.spawn('sudo LC_NUMERIC=C gdb --interpreter=mi', cwd=currentdir, encoding="utf-8")
    child.setecho(False)
    child.delaybeforesend = 0
    child.timeout = None
    child.expect_exact("(gdb)")
    status_thread = Thread(target=state_observe_thread)
    status_thread.daemon = True
    status_thread.start()
    send_command("set logging file " + SysUtils.get_gdb_async_file(pid))
    send_command("set logging on")

    # gdb scripts needs to know PINCE directory, unfortunately they don't start from the place where script exists
    send_command('set $PINCE_PATH=' + '"' + currentdir + '"')
    send_command("source gdb_python_scripts/GDBCommandExtensions.py")
    injection_path = currentdir + INITIAL_INJECTION_PATH
    if not SysUtils.is_path_valid(injection_path):
        injection_method = NO_INJECTION  # no .so file found
    if injection_method is NO_INJECTION:
        codes_injected = NO_INJECTION_ATTEMPT
    elif injection_method is LINUX_INJECT:
        codes_injected = inject_with_linux_inject(injection_path, pid)
    send_command("attach " + pid)
    if injection_method is SIMPLE_DLOPEN_CALL:
        codes_injected = inject_with_dlopen_call(injection_path)
    continue_inferior()
    return codes_injected


# Farewell...
def detach():
    global child
    global currentpid
    global inferior_status
    child.sendcontrol("d")
    child.close()
    currentpid = 0
    inferior_status = -1


# Don't try to use this function after gdb is attached, try inject_with_dlopen_call instead
# FIXME: linux-inject is insufficient for multi-threaded programs, it makes big titles such as Torchlight to segfault
def inject_with_linux_inject(library_path, pid=str):
    scriptdirectory = SysUtils.get_current_script_directory()
    if is_32bit:
        result = pexpect.run("sudo ./inject32 -p " + pid + " " + library_path, cwd=scriptdirectory + "/linux-inject")
    else:
        result = pexpect.run("sudo ./inject -p " + pid + " " + library_path, cwd=scriptdirectory + "/linux-inject")
    print(result)  # for debug
    if search(b"successfully injected", result):  # literal string
        return INJECTION_SUCCESSFUL
    return INJECTION_FAILED


# variant of inject_with_linux_inject
def inject_with_dlopen_call(library_path):
    injectionpath = '"' + library_path + '"'
    result = send_command("call dlopen(" + injectionpath + ", 1)")
    filtered_result = search(r"\$\d+\s*=\s*\-*\d+", result)  # $1 = -1633996800
    if filtered_result:
        dlopen_return_value = split(" ", filtered_result.group(0))[-1]
        if dlopen_return_value is "0":
            result = send_command("call __libc_dlopen_mode(" + injectionpath + ", 1)")
            filtered_result = search(r"\$\d+\s*=\s*\-*\d+", result)  # $1 = -1633996800
            if filtered_result:
                dlopen_return_value = split(" ", filtered_result.group(0))[-1]
                if dlopen_return_value is "0":
                    return INJECTION_FAILED
                return INJECTION_SUCCESSFUL
            return INJECTION_FAILED
        return INJECTION_SUCCESSFUL
    result = send_command("call __libc_dlopen_mode(" + injectionpath + ", 1)")
    filtered_result = search(r"\$\d+\s*=\s*\-*\d+", result)  # $1 = -1633996800
    if filtered_result:
        dlopen_return_value = split(" ", filtered_result.group(0))[-1]
        if dlopen_return_value is "0":
            return INJECTION_FAILED
        return INJECTION_SUCCESSFUL
    return INJECTION_FAILED


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuetype_to_gdbcommand(index=int):
    return index_to_gdbcommand_dict.get(index, "out of bounds")


def check_for_restricted_gdb_symbols(string):
    string = str(string)
    string = string.strip()
    if string is "":
        return True
    if search(r"\".*\"", string) or search(r"\{.*\}", string):  # For string and array expressions
        return False
    if search(r'\$|\s', string):  # These characters make gdb show it's value history, so they should be avoided
        return True
    return False


# returns the value of the expression if it is valid, return the string "??" if not
# this function is mainly used for display in AddAddressManually dialog
# this function also can read symbols such as "_start", "malloc", "printf" and "scanf" as addresses
# typeofaddress is derived from valuetype_to_gdbcommand
# length parameter only gets passed when reading strings or array of bytes
# unicode and zero_terminate parameters are only for strings
# if you just want to get the value of an address, use the function read_value_from_single_address() instead
def read_single_address(address, typeofaddress, length=None, is_unicode=False, zero_terminate=True):
    if check_for_restricted_gdb_symbols(address):
        return "??"
    if length is "":
        return "??"
    if typeofaddress is INDEX_AOB:
        typeofaddress = valuetype_to_gdbcommand(typeofaddress)
        try:
            expectedlength = str(int(length))  # length must be a legit number, so had to do this trick
        except:
            return "??"
        result = send_command("x/" + expectedlength + typeofaddress + " " + address)
        filteredresult = findall(r"\\t0x[0-9a-fA-F]+", result)  # 0x40c431:\t0x31\t0xed\t0x49\t...
        if filteredresult:
            returned_string = ''.join(filteredresult)  # combine all the matched results
            return returned_string.replace(r"\t0x", " ")
        return "??"
    elif typeofaddress is INDEX_STRING:
        typeofaddress = valuetype_to_gdbcommand(typeofaddress)
        if not is_unicode:
            try:
                expectedlength = str(int(length))
            except:
                return "??"
            result = send_command("x/" + expectedlength + typeofaddress + " " + address)
        else:
            try:
                expectedlength = str(int(length) * 2)
            except:
                return "??"
            result = send_command("x/" + expectedlength + typeofaddress + " " + address)
        filteredresult = findall(r"\\t0x[0-9a-fA-F]+", result)  # 0x40c431:\t0x31\t0xed\t0x49\t...
        if filteredresult:
            filteredresult = ''.join(filteredresult)
            returned_string = filteredresult.replace(r"\t0x", "")
            if not is_unicode:
                returned_string = bytes.fromhex(returned_string).decode("ascii", "replace")
            else:
                returned_string = bytes.fromhex(returned_string).decode("utf-8", "replace")
            if zero_terminate:
                if returned_string.startswith('\x00'):
                    returned_string = '\x00'
                else:
                    returned_string = returned_string.split('\x00')[0]
            return returned_string[0:int(length)]
        return "??"
    else:
        typeofaddress = valuetype_to_gdbcommand(typeofaddress)
        result = send_command("x/" + typeofaddress + " " + address)
        filteredresult = search(r":\\t[0-9a-fA-F-,]+", result)  # 0x400000:\t1,3961517377359369e-309
        if filteredresult:
            return split("t", filteredresult.group(0))[-1]
        return "??"


# This function is the same with the read_single_address but it reads values from proc/pid/maps instead
# This function is usable even when thread injection fails but it's more primitive than read_single_address
# Use this if you only want to read some values from an address
# If you want PINCE to parse expressions, use read_single_address instead
def read_value_from_single_address(address, typeofaddress, length, unicode, zero_terminate):
    readed = send_command(
        "pince-read-single-address " + str(address) + "," + str(typeofaddress) + "," + str(length) + "," + str(
            unicode) + "," + str(zero_terminate))
    result = search(r"~\".*\\n\"", readed).group(0)  # ~"result\n"
    result = split(r'\"', result)[1]  # result\n"
    result = split(r"\\", result)[0]  # result

    # check ReadSingleAddress class in GDBCommandExtensions.py to understand why do we separate this parsing from others
    if typeofaddress is INDEX_STRING:
        returned_string = result.replace(" ", "")
        if not unicode:
            returned_string = bytes.fromhex(returned_string).decode("ascii", "replace")
        else:
            returned_string = bytes.fromhex(returned_string).decode("utf-8", "replace")
        if zero_terminate:
            if returned_string.startswith('\x00'):
                returned_string = '\x00'
            else:
                returned_string = returned_string.split('\x00')[0]
        return returned_string[0:int(length)]
    return result


# Optimized version of the function read_value_from_single_address
# Parameter format: [[address1, index1, length1, unicode1, zero_terminate1],[address2, ...], ...]
# If any errors occurs while reading addresses, it's ignored and the belonging address is returned as null string
# For instance: 4 addresses readed and 3rd one is problematic, the return value will be [return1,return2,"",return4]
def read_multiple_addresses(nested_list):
    directory_path = SysUtils.get_PINCE_IPC_directory(currentpid)
    send_file = directory_path + "/read-list-from-PINCE.txt"
    recv_file = directory_path + "/read-list-to-PINCE.txt"
    with lock_read_multiple_addresses:
        open(recv_file, "w").close()
        pickle.dump(nested_list, open(send_file, "wb"))
        send_command("pince-read-multiple-addresses")
        try:
            contents_recv = pickle.load(open(recv_file, "rb"))
        except EOFError:
            print("an error occurred while reading addresses")
            contents_recv = []
    return contents_recv


# Optimized version of the function set_value_from_single_address
# Parameter format: [[address1, index1, length1, unicode1, zero_terminate1],[address2, ...], ...]
# If any errors occurs while reading addresses, it'll be ignored but the information about error will be printed to the terminal
def set_multiple_addresses(nested_list):
    with lock_set_multiple_addresses:
        directory_path = SysUtils.get_PINCE_IPC_directory(currentpid)
        send_file = directory_path + "/set-list-from-PINCE.txt"
        pickle.dump(nested_list, open(send_file, "wb"))
        send_command("pince-set-multiple-addresses")


# If the second parameter is an offset, you should add "+" in front of it(e.g +42 or +0x42)
# Return format:[[address1,bytes1,opcodes1],[address2, ...], ...]
def disassemble(expression, offset_or_address):
    returned_list = []
    output = send_command("disas /r " + expression + "," + offset_or_address)
    filtered_output = findall(r"0x[0-9a-fA-F]+.*\\t.+\\t.+\\n",
                              output)  # 0x00007fd81d4c7400 <__printf+0>:\t48 81 ec d8 00 00 00\tsub    rsp,0xd8\n
    for item in filtered_output:
        returned_list.append(list(filter(None, split(r"\\t|\\n", item))))
    return returned_list


# Converts the given address to symbol if any symbol exists for it
# If your string contains one of the restricted symbols(such as $) pass the check parameter as False
def convert_address_to_symbol(string, check=True):
    if check:
        if check_for_restricted_gdb_symbols(string):
            return string
    result = send_command("x/x " + string)
    if search(r"Cannot\s*access\s*memory\s*at\s*address", result):
        return
    filteredresult = search(r"<.+>:\\t", result)  # 0x40c435 <_start+4>:\t0x89485ed1\n
    if filteredresult:
        return split(">:", filteredresult.group(0))[0].split("<")[1]


# Converts the given symbol to address if symbol is valid
# If your string contains one of the restricted symbols(such as $) pass the check parameter as False
def convert_symbol_to_address(string, check=True):
    if check:
        if check_for_restricted_gdb_symbols(string):
            return string
    result = send_command("x/x " + string)
    if search(r"Cannot\s*access\s*memory\s*at\s*address", result):
        return
    filteredresult = search(r"0x[0-9a-fA-F]+\s+<.+>:\\t", result)  # 0x40c435 <_start+4>:\t0x89485ed1\n
    if filteredresult:
        return split(" ", filteredresult.group(0))[0]
    else:
        filteredresult = search(r"0x[0-9a-fA-F]+:\\t", result)  # 0x1f58010:\t0x00647361\n
        if filteredresult:
            return split(":", filteredresult.group(0))[0]


# Parameters should be splitted by ","
def parse_convenience_variables(variables=str):
    variables = variables.replace(" ", "")
    variable_list = variables.split(",")
    directory_path = SysUtils.get_PINCE_IPC_directory(currentpid)
    send_file = directory_path + "/variables-from-PINCE.txt"
    recv_file = directory_path + "/variables-to-PINCE.txt"
    with lock_read_multiple_addresses:
        open(recv_file, "w").close()
        pickle.dump(variable_list, open(send_file, "wb"))
        send_command("pince-parse-convenience-variables")
        try:
            contents_recv = pickle.load(open(recv_file, "rb"))
        except EOFError:
            print("an error occurred while reading variables")
            contents_recv = []
    return contents_recv


def get_current_thread_information():
    thread_info = send_command("info threads")
    parsed_info = search(r"\*\s+\d+\s+Thread\s+0x[0-9a-fA-F]+\s+\(LWP\s+\d+\)",
                         thread_info).group(0)  # * 1    Thread 0x7f34730d77c0 (LWP 6189)
    return split(r"Thread\s+", parsed_info)[-1]


def test():
    for x in range(0, 10):
        print(send_command('x/x _start'))


def test2():
    for x in range(0, 10):
        print(send_command("disas /r 0x00400000,+10"))


def test3():
    global child
    while True:
        sleep(1)
        print(child.stdout)
