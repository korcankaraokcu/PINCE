#!/usr/bin/python3
from re import search, split, match
from threading import Lock
from time import sleep
import pexpect

import SysUtils

child = object  # this object will be used with pexpect operations
infinite_thread_location = str  # location of the injected thread that runs forever at background
infinite_thread_id = str  # id of the injected thread that runs forever at background
lock = Lock()


# The comments next to the regular expressions shows the expected gdb output, an elucidating light for the future developers


# issues the command sent, str is command string
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


# self-explanatory, str is currentpid
def attach(pid=str):
    global child
    child = pexpect.spawnu('sudo gdb --interpreter=mi')
    child.setecho(False)

    # a creative and meaningful number for such a marvelous and magnificent program PINCE is
    child.timeout = 900000
    child.expect_exact("(gdb)")
    send_command("set disassembly-flavor intel")
    send_command("set target-async 1")
    send_command("set pagination off")
    send_command("set non-stop on")
    send_command("attach " + pid + "&")
    send_command("1")  # to swallow up the surplus output
    print("Injecting Thread")  # progress bar text change
    return inject_additional_threads()


# Farewell...
def detach():
    global child
    child.sendline("q")
    child.close()


# Injects a thread that runs forever at the background, it'll be used to execute GDB commands on
# Also saves the injected thread's location and ID as strings, then switches to that thread and stops it
def inject_additional_threads():
    global infinite_thread_location
    global infinite_thread_id
    send_command("interrupt")
    scriptdirectory = SysUtils.get_current_script_directory()
    injectionpath = '"' + scriptdirectory + '/Injection/AdditionalThreadInjection.so"'
    send_command("call dlopen(" + injectionpath + ", 2)")
    result = split("call injection", send_command("call injection()"))
    send_command("c &")
    filtered_result = search(r"New Thread\s*0x\w+", result[1])  # New Thread 0x7fab41ffb700 (LWP 7944)

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


# test
def await_inferior_exit():
    global child
    while True:
        sleep(0.0001)
        if match("exited-normally", child.after):
            print("kek")
            break


# return the value of the address if the address is valid, return the string "??" if not
# typeofaddress is derived from combobox_value_dict in GuiUtils
# typeofaddress can be byte, 2bytes, 4bytes, 8bytes, float and double
def read_single_address(address=str, typeofaddress=str):
    result = send_command("x/" + typeofaddress + " " + address)
    filteredresult = search(r"0x[0-9a-fA-F]+:\\t[0-9a-fA-F-,]+", result)  # 0x400000:\t1,3961517377359369e-309
    if filteredresult:
        return split("t", filteredresult.group(0))[-1]
    return "??"


def test():
    for x in range(0, 10):
        print(send_command("x/fg 0x00400000"))


def test2():
    for x in range(0, 10):
        print(send_command("disas /r 0x00400000,+10"))


def test3():
    global child
    while True:
        sleep(1)
        print(child.stdout)
