#!/usr/bin/python3
from re import search,split
import pexpect
from threading import Lock
from SysUtils import *

p=object                                                #this object will be used with pexpect operations
InfiniteThreadLocation=str

class GDB_Engine():
    lock=Lock()

#issues the command sent, str is command string
    def send_command(str):
        global p
        with GDB_Engine.lock:
            p.sendline(str)
            p.expect_exact("(gdb)")
            return p.before

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
        GDB_Engine.send_command("set disassembly-flavor intel")
        GDB_Engine.send_command("set mi-async 1")
        GDB_Engine.send_command("set pagination off")
        GDB_Engine.send_command("set non-stop on")
        GDB_Engine.send_command("attach " + str + "&")
        GDB_Engine.send_command("1")                            #to swallow up the surplus output
        print("Injecting Thread")                               #progress bar text change
        return GDB_Engine.InjectAdditionalThread()

#Farewell...
    def deattach():
        global p
        p.sendline("q")
        p.close()

    def test():
        for x in range(0,10):
            print(GDB_Engine.send_command("find 0x00400000,+500,1"))

    def test2():
        for x in range(0,10):
            print(GDB_Engine.send_command("disas /r 0x00400000,+10"))
        print("kek")

#Injects a thread that runs forever at the background, it'll be used to execute GDB commands on. Also saves the injected thread's location as string
    def InjectAdditionalThread():
        global InfiniteThreadLocation
        GDB_Engine.send_command("interrupt")
        homedirectory=SysUtils.gethomedirectory()
        PATH='"' + homedirectory + '/PINCE/Injection/AdditionalThreadInjection.so"'
        GDB_Engine.send_command("call dlopen("+ PATH +", 2)")
        result=split("call injection",GDB_Engine.send_command("call injection()"))
        GDB_Engine.send_command("c &")
        threadaddress=search("0x\w*",result[1])

#Return True is injection is successful, False if not
        if not threadaddress:
            return False
        InfiniteThreadLocation=threadaddress.group(0)
        return True