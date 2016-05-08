import gdb
import threading
from time import sleep
class Executor:
    def __init__(self, cmd):
        self.__cmd = cmd

    def __call__(self):
        gdb.execute(self.__cmd)

def event_handler(event):
    gdb.execute("set scheduler-locking on") # to avoid parallel signals in other threads

    gdb.write("\n[ME] SIG " + event.stop_signal)
    frame = gdb.selected_frame()
    while frame:
        gdb.write("\n[ME] FN " + str(frame.name()))
        frame = frame.older()
    gdb.execute("set scheduler-locking off") # otherwise just this thread is continued, leading to a deadlock   
    gdb.post_event(Executor("echo kek")) # and post the continue command to gdb

def asdf():
	sleep(10)
	#gdb.execute("thread 1")
	#gdb.execute("interrupt")
	#gdb.execute("x 0x00400000")
	#gdb.events.stop.connect(event_handler)
	'''
	while True:
		FILE=open("/proc/11575/mem", "rb+")
		FILE.seek(0x00400000)
		FILE.write(b"leeeeeeel")
		FILE.seek(0x00400000)
		thing=FILE.read(50)
		FILE.close()
		FILE=open("asdfqwe.txt", "ab+")
		FILE.write(thing)
		FILE.close()
		sleep(1)
	'''
t1 = threading.Thread(target=asdf)
t1.setDaemon(True)
t1.start()
