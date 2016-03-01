#!/usr/bin/python3
from re import search, split, match
from threading import Lock, Thread
from time import sleep
import pexpect

import SysUtils

child = object  # this object will be used with pexpect operations
infinite_thread_location = str  # location of the injected thread that runs forever at background
lock = Lock()


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
    if search("Operation not permitted", a.before):
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


def test():
    for x in range(0, 10):
        print(send_command("find 0x00400000,+500,1"))


def test2():
    for x in range(0, 10):
        print(send_command("disas /r 0x00400000,+10"))


# Injects a thread that runs forever at the background, it'll be used to execute GDB commands on. Also saves the injected thread's location as string
def inject_additional_threads():
    global infinite_thread_location
    send_command("interrupt")
    scriptdirectory = SysUtils.get_current_script_directory()
    injectionpath = '"' + scriptdirectory + '/Injection/AdditionalThreadInjection.so"'
    send_command("call dlopen(" + injectionpath + ", 2)")
    result = split("call injection", send_command("call injection()"))
    send_command("c &")
    threadaddress = search("0x\w*", result[1])

    # Return True is injection is successful, False if not
    if not threadaddress:
        return False
    infinite_thread_location = threadaddress.group(0)
    return True


def await_inferior_exit():
    global child
    while True:
        sleep(0.0001)
        if match("exited-normally", child.after):
            print("kek")
            break


def test3():
    global child
    while True:
        sleep(1)
        print(child.stdout)
