#!/usr/bin/python3
import psutil
import os
import shutil
import sys
import type_defs
from re import match, search, IGNORECASE

PINCE_IPC_PATH = type_defs.PINCE_IPC_PATH


# returns a list of currently working processes
def get_process_list():
    processlist = []
    for p in psutil.process_iter():
        processlist.append(p)
    return processlist


# returns the information about the given process
def get_process_information(pid=int):
    p = psutil.Process(pid)
    return p


# self-explanatory, returns a list
def search_in_processes_by_name(searchstring=str):
    processlist = []
    for p in psutil.process_iter():
        if search(searchstring, p.name(), IGNORECASE):
            processlist.append(p)
    return processlist


# returns a list that contains information about each memory region
def get_memory_regions(pid=int):
    maplist = []
    p = psutil.Process(pid)
    for m in p.memory_maps(grouped=False):
        maplist.append(m)
    return maplist


# returns a tuple based on the permissions given to the regions
def get_memory_regions_by_perms(pid=int):
    readable_only, writeable, executable, readable = [], [], [], []
    p = psutil.Process(pid)
    for m in p.memory_maps(grouped=False):
        if search("r--", m.perms):
            readable_only.append(m)
        if search("w", m.perms):
            writeable.append(m)
        if search("x", m.perms):
            executable.append(m)
        if search("r", m.perms):
            readable.append(m)
    return readable_only, writeable, executable, readable


# excludes the shared memory regions from the list
# the list must be generated from the function getmemoryregionsByPerms or getmemoryregions
def exclude_shared_memory_regions(generatedlist):
    for m in generatedlist[:]:
        if search("s", m.perms):
            generatedlist.remove(m)
    return generatedlist


# excludes the system-related memory regions from the list
# the list must be generated from the function getmemoryregionsByPerms or getmemoryregions
def exclude_system_memory_regions(generatedlist):
    for m in generatedlist[:]:
        if match("[7-f]", m.addr):
            generatedlist.remove(m)
    return generatedlist


# returns name of the tracer if specified process is being traced
def is_traced(pid=int):
    for line in open("/proc/%d/status" % pid).readlines():
        if line.startswith("TracerPid:"):
            tracerpid = line.split(":", 1)[1].strip()
            if tracerpid == "0":
                return False
            else:
                return psutil.Process(int(tracerpid)).name()


# return True if the process is still running, False if not
def is_process_valid(pid=int):
    return is_path_valid("/proc/%d" % pid)


# returns a string pointing to the home directory
def get_home_directory():
    return os.path.expanduser("~")


# returns a string pointing to the py file currently working
def get_current_script_directory():
    return sys.path[0]


def is_path_valid(dest_path, issue_path=""):
    if os.path.exists(dest_path):
        if issue_path is "delete":
            shutil.rmtree(dest_path)
        return True
    else:
        if issue_path is "create":
            os.makedirs(dest_path)
            fix_path_permissions(dest_path)
        return False


# this function is necessary because PINCE gets opened with the root permissions
# the inferior PINCE communicating with won't be able to access to the communication files at /tmp otherwise
def fix_path_permissions(dest_path):
    uid = int(os.environ.get('SUDO_UID'))
    gid = int(os.environ.get('SUDO_GID'))
    os.chown(dest_path, uid, gid)


# removes the corresponding pid file
def do_cleanups(pid):
    is_path_valid(get_PINCE_IPC_directory(pid), "delete")


def create_PINCE_IPC_PATH(pid):
    do_cleanups(pid)
    is_path_valid(get_PINCE_IPC_directory(pid), "create")


def get_PINCE_IPC_directory(pid):
    return PINCE_IPC_PATH + str(pid)


def get_gdb_async_file(pid):
    return get_PINCE_IPC_directory(pid) + "/gdb_async_output.txt"
