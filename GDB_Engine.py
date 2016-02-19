#!/usr/bin/python3
from re import search
import pexpect
import time
from threading import Lock

p=object                                                #this object will be used with pexpect operations

class GDB_Engine():
    lock=Lock()

#issues the command sent, str is command string
    def send_command(str):
        global p
        with GDB_Engine.lock:
            p.sendline(str)
            p.expect_exact("(gdb)")

    def send_asynccommand(str):
        global p


#only this function doesn't use the function send_command, because variable a is temporary
    def canattach(str):
        a=pexpect.spawnu('sudo gdb --interpreter=mi')
        a.expect_exact("(gdb) ")
        a.sendline("attach " + str)
        a.expect_exact("(gdb) ")

#return true if attaching is successful, false if not, then quit
        if search("Operation not permitted",a.before):
            a.sendline("q")
            a.close()
            return False
        a.sendline("q")
        a.close()
        return True

#self-explanatory, str is currentpid
    def attach(str):
        global p
        p=pexpect.spawnu('sudo gdb --interpreter=mi')
        p.setecho(False)

#a creative and meaningful number for such a marvelous and magnificent program PINCE is
        p.timeout=1879048192
        p.expect_exact("(gdb)")
        GDB_Engine.send_command("set target-async 1")
        GDB_Engine.send_command("set pagination off")
        GDB_Engine.send_command("set non-stop on")
        GDB_Engine.send_command("attach " + str + "&")
        GDB_Engine.send_command("1")                            #to swallow up the surplus output

#Farewell...
    def deattach():
        global p
        p.sendline("q")
        p.close()

    def test():
        for x in range(0,10):
            global p
            #time.sleep(0.1)
            GDB_Engine.send_command("find 0x00400000,+500,1")
            print(p.before)

    def test2():
        for x in range(0,100):
            global p
            #time.sleep(0.1)
            GDB_Engine.send_command("disas 0x00400000,+10")
            print(p.before)
        print("kek")

    def test3():
        print("2")