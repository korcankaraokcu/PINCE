# -*- coding: utf-8 -*-
import psutil
import os
import shutil
import sys
import type_defs
from re import match, search, IGNORECASE, split

PINCE_IPC_PATH = type_defs.PATHS.PINCE_IPC_PATH
IPC_FROM_PINCE_PATH = type_defs.PATHS.IPC_FROM_PINCE_PATH
IPC_TO_PINCE_PATH = type_defs.PATHS.IPC_TO_PINCE_PATH

INDEX_BYTE = type_defs.VALUE_INDEX.INDEX_BYTE
INDEX_2BYTES = type_defs.VALUE_INDEX.INDEX_2BYTES
INDEX_4BYTES = type_defs.VALUE_INDEX.INDEX_4BYTES
INDEX_8BYTES = type_defs.VALUE_INDEX.INDEX_8BYTES
INDEX_FLOAT = type_defs.VALUE_INDEX.INDEX_FLOAT
INDEX_DOUBLE = type_defs.VALUE_INDEX.INDEX_DOUBLE
INDEX_STRING = type_defs.VALUE_INDEX.INDEX_STRING
INDEX_AOB = type_defs.VALUE_INDEX.INDEX_AOB


def get_process_list():
    """Returns a list of psutil.Process objects corresponding to currently running processes

    Returns:
        list: List of psutil.Process objects
    """
    processlist = []
    for p in psutil.process_iter():
        processlist.append(p)
    return processlist


def get_process_information(pid):
    """Returns a psutil.Process object corresponding to given pid

    Args:
        pid (int): PID of the process

    Returns:
        psutil.Process: psutil.Process object corresponding to the given pid
    """
    p = psutil.Process(pid)
    return p


def search_in_processes_by_name(process_name):
    """Searches currently running processes and returns a list of psutil.Process objects corresponding to processes that
    has the str process_name in them

    Args:
        process_name (str): Name of the process that'll be searched for

    Returns:
        list: List of psutil.Process objects corresponding to the filtered processes
    """
    processlist = []
    for p in psutil.process_iter():
        if search(process_name, p.name(), IGNORECASE):
            processlist.append(p)
    return processlist


def get_memory_regions(pid):
    """Returns memory regions as a list of pmmap_ext objects

    Args:
        pid (int): PID of the process

    Returns:
        list: List of pmmap_ext objects corresponding to the given pid
    """
    maplist = []
    p = psutil.Process(pid)
    for m in p.memory_maps(grouped=False):
        maplist.append(m)
    return maplist


def get_memory_regions_by_perms(pid):
    """Returns a tuple of four lists based on the permissions given to them

    Args:
        pid (int): PID of the process

    Returns:
        tuple: A tuple of four different lists formed of pmmap_ext objects
        First list holds readable only regions
        Second list holds writeable regions
        Third list holds executable regions
        Fourth list holds readable regions
    """
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


def exclude_shared_memory_regions(generated_list):
    """Excludes the shared memory regions from the list

    Args:
        generated_list (list): The list must be generated from the function get_memory_regions_by_perms or
        get_memory_regions.

    Returns:
        list: List of the remaining pmmap_ext objects after exclusion
    """
    for m in generated_list[:]:
        if search("s", m.perms):
            generated_list.remove(m)
    return generated_list


def exclude_system_memory_regions(generated_list):
    """Excludes the system-related memory regions from the list

    Args:
        generated_list (list): The list must be generated from the function get_memory_regions_by_perms or
        get_memory_regions.

    Returns:
        list: List of the remaining pmmap_ext objects after exclusion
    """
    for m in generated_list[:]:
        if match("[7-f]", m.addr):
            generated_list.remove(m)
    return generated_list


def is_traced(pid):
    """Check if the process corresponding to given pid traced by any other process

    Args:
        pid (int): PID of the process

    Returns:
        str: Name of the tracer if the specified process is being traced
        bool: False, if the specified process is not being traced
    """
    for line in open("/proc/%d/status" % pid).readlines():
        if line.startswith("TracerPid:"):
            tracerpid = line.split(":", 1)[1].strip()
            if tracerpid == "0":
                return False
            else:
                return psutil.Process(int(tracerpid)).name()


def is_process_valid(pid):
    """Check if the process corresponding to given pid is valid

    Args:
        pid (int): PID of the process

    Returns:
        bool: True if the process is still running, False if not
    """
    return is_path_valid("/proc/%d" % pid)


def get_home_directory():
    """Get home directory of the current user

    Returns:
        str: A string pointing to the home directory
    """
    return os.path.expanduser("~")


def get_current_script_directory():
    """Get current working directory

    Returns:
        str: A string pointing to the current working directory
    """
    return sys.path[0]


def is_path_valid(dest_path, issue_path=""):
    """Check if the given path is valid

    Args:
        dest_path (str): Path
        issue_path (str): If this parameter is passed as "delete", given path will be deleted if it's valid.
        If this parameter is passed as "create", given path path will be created if it's not valid.

    Returns:
        bool: True if path is valid, False if not
    """
    if os.path.exists(dest_path):
        if issue_path is "delete":
            shutil.rmtree(dest_path)
        return True
    else:
        if issue_path is "create":
            os.makedirs(dest_path)
            fix_path_permissions(dest_path)
        return False


def fix_path_permissions(dest_path):
    """Gives the path permissions back to user

    Necessary because the inferior PINCE communicating with won't be able to access to the communication files at /tmp
    otherwise

    Args:
        dest_path (str): Path
    """
    uid = int(os.environ.get('SUDO_UID'))
    gid = int(os.environ.get('SUDO_GID'))
    os.chown(dest_path, uid, gid)


def do_cleanups(pid):
    """Deletes the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    is_path_valid(get_PINCE_IPC_directory(pid), "delete")


def create_PINCE_IPC_PATH(pid):
    """Creates the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    do_cleanups(pid)
    is_path_valid(get_PINCE_IPC_directory(pid), "create")


def get_PINCE_IPC_directory(pid):
    """Get the IPC directory of given pid

    Args:
        pid (int): PID of the process

    Returns:
        str: Path of IPC directory
    """
    return PINCE_IPC_PATH + str(pid)


def get_gdb_async_file(pid):
    """Get the path of gdb logfile of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb logfile
    """
    return get_PINCE_IPC_directory(pid) + "/gdb_async_output.txt"


def get_gdb_command_file(pid):
    """Get the path of gdb command file of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb command file
    """
    return get_PINCE_IPC_directory(pid) + "/gdb_command.txt"


def get_ipc_from_PINCE_file(pid):
    """Get the path of IPC file sent to custom gdb commands from PINCE for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + IPC_FROM_PINCE_PATH


def get_ipc_to_PINCE_file(pid):
    """Get the path of IPC file sent to PINCE from custom gdb commands for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + IPC_TO_PINCE_PATH


def parse_string(string, value_index):
    """Parses the string according to the given value_index

    Args:
        string (str): String that'll be parsed
        value_index (int): Determines the type of data. Can be a member of type_defs.VALUE_INDEX

    Returns:
        str: If the value_index is INDEX_STRING
        list: If the value_index is INDEX_AOB. A list of ints is returned
        float: If the value_index is INDEX_FLOAT or INDEX_DOUBLE
        int: If the value_index is anything else
        None: If the string is not parseable by using the parameter value_index

    Examples:
        string="42 DE AD BE EF 24",value_index=INDEX_AOB-->returned_list=[66, 222, 173, 190, 239, 36]
    """
    string = str(string)
    if not string:
        print("please enter a string first")
        return
    try:
        value_index = int(value_index)
    except:
        print(str(value_index) + " can't be converted to int")
        return
    if value_index is INDEX_STRING:
        return string
    string = string.strip()
    if value_index is INDEX_AOB:
        try:
            string = str(string)
            stripped_string = string.strip()
            string_list = split(r"\s+", stripped_string)
            for item in string_list:
                if len(item) > 2:
                    print(string + " can't be parsed as array of bytes")
                    return
            hex_list = [int(x, 16) for x in string_list]
            return hex_list
        except:
            print(string + " can't be parsed as array of bytes")
            return
    elif value_index is INDEX_FLOAT or value_index is INDEX_DOUBLE:
        try:
            string = float(string)
        except:
            try:
                string = float(int(string, 16))
            except:
                print(string + " can't be parsed as floating point variable")
                return
        return string
    else:
        try:
            string = int(string)
        except:
            try:
                string = int(string, 16)
            except:
                try:
                    string = int(float(string))
                except:
                    print(string + " can't be parsed as integer or hexadecimal")
                    return
        if value_index is INDEX_BYTE:
            string = string % 256
        elif value_index is INDEX_2BYTES:
            string = string % 65536
        elif value_index is INDEX_4BYTES:
            string = string % 4294967296
        elif value_index is INDEX_8BYTES:
            string = string % 18446744073709551616
        return string


def extract_address(string, search_for_location_changing_instructions=False):
    """Extracts hex address from the given string

    Args:
        string (str): The string that the hex address will be extracted from
        search_for_location_changing_instructions (bool): Searches for the location changing instructions such as Jcc,
        CALL and LOOPcc in the given string

    Returns:
        str: The hex address found
        None: If no hex address is found or no location changing instructions found(applies only if the parameter
        search_for_location_changing_instructions is passed as True)
    """
    if search_for_location_changing_instructions:
        result = search(r"(j|call|loop).*\s+0x[0-9a-fA-F]+", string)
        if result:
            result = result.group(0).split()[-1]
            return result
    else:
        result = search(r"0x[0-9a-fA-F]+", string)
        if result:
            return result.group(0)


def find_closest_address(pid, memory_address, look_to="start"):
    """Finds the closest valid starting/ending address to given address, assuming given address is in the valid address
    range

    Args:
        pid (int): PID of the process
        memory_address (int,str): Can be an int or a hex str
        look_to (str): If it's "start", closest starting address will be returned. If it's anything else, ending address
        will be returned

    Returns:
        str: starting/ending address as hex str
    """
    if type(pid) != int:
        pid = int(pid)
    if type(memory_address) != int:
        memory_address = int(memory_address, 16)
    region_list = get_memory_regions(pid)
    for item in region_list:
        splitted_address = item.addr.split("-")
        start = int(splitted_address[0], 16)
        end = int(splitted_address[1], 16)
        if start <= memory_address <= end:
            if look_to == "start":
                return hex(start)
            else:
                return hex(end)
