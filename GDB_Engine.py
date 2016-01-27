#!/usr/bin/python3
import pexpect,sys
class GDB_Engine(object):

#starts the gdb engine by making it go thru an infinite loop of script execution,int is currentpid
    def startgdb(int):
        p=pexpect.spawnu('sudo gdb')

#a creative and meaningful number for such a marvelous and magnificent program PINCE is
        p.timeout=1879048192
        p.logfile=sys.stdout
        p.expect("\r\n\(gdb\) ")
        p.sendline("attach " + int)
        p.expect("\r\n\(gdb\) ")
        print(p.before)