#!/usr/bin/python3
import psutil
from re import match,search,IGNORECASE
from os import path

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
            if search(str,p.name(),IGNORECASE):
                processlist.append(p)
        return processlist

#returns a list that contains information about each memory region
    def getmemoryregions(int):
        maplist=[]
        p=psutil.Process(int)
        for m in p.memory_maps(grouped=False):
            maplist.append(m)
        return(maplist)

#returns a tuple based on the permissions given to the regions
    def getmemoryregionsByPerms(int):
        readable_only,writeable,executable,readable=[],[],[],[]
        p=psutil.Process(int)
        for m in p.memory_maps(grouped=False):
            if search("r--",m.perms):
                readable_only.append(m)
            if search("w",m.perms):
                writeable.append(m)
            if search("x",m.perms):
                executable.append(m)
            if search("r",m.perms):
                readable.append(m)
        return readable_only,writeable,executable,readable

#excludes the shared memory regions from the list, the list must be generated from the function getmemoryregionsByPerms or getmemoryregions
    def excludeSharedMemoryRegions(list):
        for m in list[:]:
            if search("s",m.perms):
                list.remove(m)
        return list

#excludes the system-related memory regions from the list, the list must be generated from the function getmemoryregionsByPerms or getmemoryregions
    def excludeSystemMemoryRegions(list):
        for m in list[:]:
            if match("7",m.addr):
                list.remove(m)
        return list

#returns name of the tracer if specified process is being traced
    def isTraced(pid):
        for line in open("/proc/%d/status" % pid).readlines():
            if line.startswith("TracerPid:"):
                tracerpid=line.split(":",1)[1].strip()
                if tracerpid=="0":
                    return False
                else:
                    return psutil.Process(int(tracerpid)).name()

    def isprocessvalid(pid):
        return path.exists("/proc/%d" % pid)