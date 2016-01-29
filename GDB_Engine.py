#!/usr/bin/python3
from re import search
import pexpect

p=object
class GDB_Engine(object):

    def canattach(str):
        a=pexpect.spawnu('sudo gdb')
        a.expect_exact("(gdb) ")
        a.sendline("attach " + str)
        a.expect_exact("(gdb) ")

#return true if attaching is successful, false if not, then quit
        if search("Operation not permitted",a.before):
            a.sendline("q")
            a.sendline("y")
            return False
        a.sendline("q")
        a.sendline("y")
        return True

#self-explanatory, str is currentpid
    def attachgdb(str):
        global p
        p=pexpect.spawnu('sudo gdb')

#a creative and meaningful number for such a marvelous and magnificent program PINCE is
        p.timeout=1879048192
        p.expect_exact("(gdb) ")
        p.sendline("attach " + str)
        p.expect_exact("(gdb) ")
        #self.p.sendline("c")
        #self.p.expect_exact("Continuing")

#Farewell...
    def deattachgdb():
        global p
        p.sendcontrol("c")
        p.sendline("q")
        p.sendline("y")
        p.close()