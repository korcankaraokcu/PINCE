#!/usr/bin/python3
import psutil

class SysUtils(object):
#returns a list of currently working processes

    def getprocesslist(self):
        processlist=[]
        for p in psutil.process_iter():
            processlist.append(p.as_dict(attrs=['pid','username','name']))
        return processlist