#!/usr/bin/python3
import psutil
from re import search,IGNORECASE

class SysUtils(object):
#returns a list of currently working processes

    def getprocesslist(self):
        processlist=[]
        for p in psutil.process_iter():
            processlist.append(p)
        return processlist

#returns the information about the given process, int=pid
    def getprocessinformation(int):
        p = psutil.Process(int)
        return p

#self-explanatory, returns a list
    def searchinprocessesByName(self,str):
        processlist=[]
        for p in psutil.process_iter():
            searchObj= search(str,p.name(),IGNORECASE)
            if searchObj:
                processlist.append(p)
        return processlist