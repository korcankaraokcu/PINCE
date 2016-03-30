#!/usr/bin/python3
from re import search, split, findall
from threading import Lock, Thread
from time import sleep
import pexpect

import SysUtils

currentpid = 0
child = object  # this object will be used with pexpect operations
infinite_thread_location = str  # location of the injected thread that runs forever at background
infinite_thread_id = str  # id of the injected thread that runs forever at background
lock = Lock()

# A dictionary used to convert value_combobox index to gdb/mi command
valuetype_to_gdbcommand_dict = {
    0: "db",  # byte
    1: "dh",  # 2bytes
    2: "dw",  # 4bytes
    3: "dg",  # 8bytes
    4: "fw",  # float
    5: "fg",  # double
    6: "xb",  # string
    7: "xb"  # array of bytes
}


# The comments next to the regular expressions shows the expected gdb output, an elucidating light for the future developers


# issues the command sent
def send_command(command=str):
    global child
    with lock:
        child.sendline(command)
        child.expect_exact("(gdb)")
        return child.before


# only this function doesn't use the function send_command, because variable a is temporary
def can_attach(pid=str):
    a = pexpect.spawnu('sudo gdb --interpreter=mi')
    a.expect_exact("(gdb) ")
    a.sendline("attach " + pid)
    a.expect_exact("(gdb) ")

    # return true if attaching is successful, false if not, then quit
    if search(r"Operation not permitted", a.before):  # literal string
        a.sendline("q")
        a.close()
        return False
    a.sendline("q")
    a.close()
    return True


# self-explanatory
def attach(pid=str):
    address_table_update_thread = Thread(target=SysUtils.update_address_table, args=(pid,))
    address_table_update_thread.start()
    global child
    child = pexpect.spawnu('sudo gdb --interpreter=mi')
    child.cwd = SysUtils.get_current_script_directory()
    child.setecho(False)

    # a creative and meaningful number for such a marvelous and magnificent program PINCE is
    child.timeout = 900000
    child.expect_exact("(gdb)")
    send_command("attach " + pid + "&")
    send_command("1")  # to swallow up the surplus output
    print("Injecting Thread")  # progress bar text change
    global currentpid
    currentpid = int(pid)
    return inject_initial_codes()


# Farewell...
def detach():
    global child
    global currentpid
    child.sendline("q")
    SysUtils.do_cleanups(currentpid)
    currentpid = 0
    child.close()


# Injects a thread that runs forever at the background, it'll be used to execute GDB commands on
# Also saves the injected thread's location and ID as strings, then switches to that thread and stops it
def inject_initial_codes():
    global infinite_thread_location
    global infinite_thread_id
    send_command("interrupt")
    scriptdirectory = SysUtils.get_current_script_directory()
    injectionpath = '"' + scriptdirectory + '/Injection/InitialCodeInjections.so"'
    send_command("call dlopen(" + injectionpath + ", 2)")
    result = send_command("call inject_infinite_thread()")
    send_command("call inject_table_update_thread()")
    send_command("c &")
    filtered_result = search(r"New Thread\s*0x\w+", result)  # New Thread 0x7fab41ffb700 (LWP 7944)

    # Return True is injection is successful, False if not
    if not filtered_result:
        return False
    threadaddress = split(" ", filtered_result.group(0))[-1]
    match_from_info_threads = search(r"\d+\s*Thread\s*" + threadaddress,
                                     send_command("info threads")).group(0)  # 1 Thread 0x7fab41ffb700
    infinite_thread_id = split(" ", match_from_info_threads)[0]
    infinite_thread_location = threadaddress
    send_command("thread " + infinite_thread_id)
    send_command("interrupt")
    return True


# return a string corresponding to the selected index
# returns "out of bounds" string if the index doesn't match the dictionary
def valuetype_to_gdbcommand(index=int):
    return valuetype_to_gdbcommand_dict.get(index, "out of bounds")


# returns the value of the address if the address is valid, return the string "??" if not
# this function also can read symbols such as "_start", "malloc", "printf" and "scanf" as addresses
# typeofaddress is derived from valuetype_to_gdbcommand
# length parameter only gets passed when reading strings or array of bytes
# unicode and zero_terminate parameters are only for strings
def read_single_address(address, typeofaddress, length=None, is_unicode=False, zero_terminate=True):
    if search(r'\$|\s', address):  # These characters make gdb show it's value history, so they should be avoided
        return "??"
    if address is "":
        return "??"
    if length is "":
        return "??"
    if typeofaddress is 7:  # array of bytes
        typeofaddress = valuetype_to_gdbcommand(typeofaddress)
        try:
            expectedlength = str(int(length))  # length must be a legit number, so had to do this trick
        except:
            return "??"
        result = send_command("x/" + expectedlength + typeofaddress + " " + address)
        filteredresult = findall(r"\\t0x[0-9a-fA-F]+", result)  # 0x40c431:\t0x31\t0xed\t0x49\t...
        if filteredresult:
            returned_string = ''.join(filteredresult)  # combined all the matched results
            return returned_string.replace(r"\t0x", " ")
        return "??"
    elif typeofaddress is 6:  # string
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
    else:  # byte, 2bytes, 4bytes, 8bytes, float, double
        typeofaddress = valuetype_to_gdbcommand(typeofaddress)
        result = send_command("x/" + typeofaddress + " " + address)
        filteredresult = search(r":\\t[0-9a-fA-F-,]+", result)  # 0x400000:\t1,3961517377359369e-309
        if filteredresult:
            return split("t", filteredresult.group(0))[-1]
        return "??"


# Converts the given address to symbol if any symbol exists for it
def convert_address_to_symbol(string):
    if search(r"0x[0-9a-fA-F]+", string):  # if string is a valid address
        result = send_command("x/x " + string)
        filteredresult = search(r"<.+>:\\t", result)  # 0x40c435 <_start+4>:\t0x89485ed1\n
        if filteredresult:
            return split(">:", filteredresult.group(0))[0].split("<")[1]
    return string


# Converts the given symbol to address if symbol is valid
def convert_symbol_to_address(string):
    if not search(r"0x[0-9a-fA-F]+", string):  # if string is not an address
        result = send_command("x/x " + string)
        filteredresult = search(r"0x[0-9a-fA-F]+\s+<.+>:\\t", result)  # 0x40c435 <_start+4>:\t0x89485ed1\n
        if filteredresult:
            return split(" ", filteredresult.group(0))[0]
    return string


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
