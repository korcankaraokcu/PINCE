#!/usr/bin/python3
from re import search
import pexpect
from multiprocessing import Process,Queue

p=object                             #this object will be used with pexpect operations
class GDB_Engine(Process):
    jobqueue=Queue()                 #format=([function1,params1],[function2,params2],...)
    resultqueue=Queue()              #same with jobqueue, but it holds only results instead
    def __init__(self):
        super(GDB_Engine, self).__init__()
        self.jobqueue=GDB_Engine.jobqueue
        self.resultqueue=GDB_Engine.resultqueue
        self.daemon=True

    def run(self):
        while True:
            func=self.jobqueue.get()
            if len(func)==1:
                result=getattr(GDB_Engine,func[0])()
            else:
                result=getattr(GDB_Engine,func[0])(func[1])
            if not result==None:
                self.resultqueue.put(result)


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
    def attach(str):
        global p
        p=pexpect.spawnu('sudo gdb')

#a creative and meaningful number for such a marvelous and magnificent program PINCE is
        p.timeout=1879048192
        p.expect_exact("(gdb) ")
        p.sendline("attach " + str)
        p.expect_exact("(gdb) ")
        p.sendline("c")
        p.expect_exact("Continuing")

#Farewell...
    def deattach():
        global p
        p.sendcontrol("c")
        p.sendline("q")
        p.sendline("y")
        p.close()