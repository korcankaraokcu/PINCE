# -*- coding: utf-8 -*-
"""
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Fixes the ImportError problem in GDBCommandExtensions.py for Archlinux
# This makes any psutil based function that's called from GDB unusable for Archlinux
# Currently there's none but we can't take it for granted, can we?
# TODO: Research the reason behind it or at least find a workaround
try:
    import psutil
except ImportError:
    print("WARNING: GDB couldn't locate the package psutil, psutil based user-defined functions won't work\n" +
          "If you are getting this message without invoking GDB, it means that installation has failed, well, sort of")
import os
import shutil
import sys
from . import type_defs
from re import match, search, IGNORECASE, split


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


def get_region_info(pid, address):
    """Finds the closest valid starting/ending address and region to given address, assuming given address is in the
    valid address range

    Args:
        pid (int): PID of the process
        address (int,str): Can be an int or a hex str

    Returns:
        type_defs.tuple_region_info: Starting address as hex str, ending address as hex str and region corresponding to
        the given address as pmmap_ext object
    """
    if type(pid) != int:
        pid = int(pid)
    if type(address) != int:
        address = int(address, 16)
    region_list = get_memory_regions(pid)
    for item in region_list:
        splitted_address = item.addr.split("-")
        start = int(splitted_address[0], 16)
        end = int(splitted_address[1], 16)
        if start <= address <= end:
            return type_defs.tuple_region_info(hex(start), hex(end), item)


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


def get_libpince_directory():
    """Get libPINCE directory

    Returns:
        str: A string pointing to the libPINCE directory

    Note:
        In fact this function returns the directory where SysUtils in and considering the fact that SysUtils resides in
        libPINCE, it works. So, please don't move out SysUtils outside of libPINCE folder!
    """
    return os.path.dirname(os.path.realpath(__file__))


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
        return False


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
    return type_defs.PATHS.PINCE_IPC_PATH + str(pid)


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


def get_track_watchpoint_file(pid, watchpoint_list):
    """Get the path of track watchpoint file for given pid

    Args:
        pid (int,str): PID of the process
        watchpoint_list (list,str): Numbers of the watchpoints

    Returns:
        str: Path of track watchpoint file
    """
    return get_PINCE_IPC_directory(pid) + "/" + str(watchpoint_list) + "_track_watchpoint.txt"


def get_ipc_from_PINCE_file(pid):
    """Get the path of IPC file sent to custom gdb commands from PINCE for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + type_defs.PATHS.IPC_FROM_PINCE_PATH


def get_ipc_to_PINCE_file(pid):
    """Get the path of IPC file sent to PINCE from custom gdb commands for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + type_defs.PATHS.IPC_TO_PINCE_PATH


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
        string="42 DE AD BE EF 24",value_index=type_defs.VALUE_INDEX.INDEX_AOB--▼
        returned_list=[66, 222, 173, 190, 239, 36]
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
    if value_index is type_defs.VALUE_INDEX.INDEX_STRING:
        return string
    string = string.strip()
    if value_index is type_defs.VALUE_INDEX.INDEX_AOB:
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
    elif value_index is type_defs.VALUE_INDEX.INDEX_FLOAT or value_index is type_defs.VALUE_INDEX.INDEX_DOUBLE:
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
        if value_index is type_defs.VALUE_INDEX.INDEX_BYTE:
            string = string % 256
        elif value_index is type_defs.VALUE_INDEX.INDEX_2BYTES:
            string = string % 65536
        elif value_index is type_defs.VALUE_INDEX.INDEX_4BYTES:
            string = string % 4294967296
        elif value_index is type_defs.VALUE_INDEX.INDEX_8BYTES:
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


def aob_to_ascii(list_of_bytes):
    """Converts given array of hex strings to ascii str

    Args:
        list_of_bytes (list): Must be returned from GDB_Engine.hex_dump()

    Returns:
        str: Ascii equivalent of array
    """

    # 3f is ascii hex representation of char "?"
    return bytes.fromhex("".join(list_of_bytes).replace("??", "3f")).decode("ascii", "replace")
