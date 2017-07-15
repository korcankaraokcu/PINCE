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
import os, shutil, sys, binascii, pickle, json, traceback
from . import type_defs
from re import match, search, IGNORECASE, split
from collections import OrderedDict
from importlib.machinery import SourceFileLoader


#:tag:Processes
def get_process_list():
    """Returns a list of psutil.Process objects corresponding to currently running processes

    Returns:
        list: List of psutil.Process objects
    """
    processlist = []
    for p in psutil.process_iter():
        processlist.append(p)
    return processlist


#:tag:Processes
def get_process_information(pid):
    """Returns a psutil.Process object corresponding to given pid

    Args:
        pid (int): PID of the process

    Returns:
        psutil.Process: psutil.Process object corresponding to the given pid
    """
    p = psutil.Process(pid)
    return p


#:tag:Processes
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


#:tag:Processes
def get_memory_regions(pid):
    """Returns memory regions as a list of pmmap_ext objects

    Args:
        pid (int): PID of the process

    Returns:
        list: List of pmmap_ext objects corresponding to the given pid
    """
    p = psutil.Process(pid)
    return p.memory_maps(grouped=False)


#:tag:Processes
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


#:tag:Processes
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


#:tag:Processes
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


#:tag:Processes
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


#:tag:Processes
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


#:tag:Processes
def is_process_valid(pid):
    """Check if the process corresponding to given pid is valid

    Args:
        pid (int): PID of the process

    Returns:
        bool: True if the process is still running, False if not
    """
    return is_path_valid("/proc/%d" % pid)


#:tag:Utilities
def get_current_script_directory():
    """Get current working directory

    Returns:
        str: A string pointing to the current working directory
    """
    return sys.path[0]


#:tag:Utilities
def get_libpince_directory():
    """Get libPINCE directory

    Returns:
        str: A string pointing to the libPINCE directory

    Note:
        In fact this function returns the directory where SysUtils in and considering the fact that SysUtils resides in
        libPINCE, it works. So, please don't move out SysUtils outside of libPINCE folder!
    """
    return os.path.dirname(os.path.realpath(__file__))


#:tag:Utilities
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


#:tag:GDBCommunication
def do_cleanups(pid):
    """Deletes the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    is_path_valid(get_PINCE_IPC_directory(pid), "delete")


#:tag:GDBCommunication
def create_PINCE_IPC_PATH(pid):
    """Creates the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    do_cleanups(pid)
    is_path_valid(get_PINCE_IPC_directory(pid), "create")


#:tag:GDBCommunication
def get_PINCE_IPC_directory(pid):
    """Get the IPC directory of given pid

    Args:
        pid (int): PID of the process

    Returns:
        str: Path of IPC directory
    """
    return type_defs.PATHS.PINCE_IPC_PATH + str(pid)


#:tag:GDBCommunication
def get_gdb_log_file(pid):
    """Get the path of gdb logfile of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb logfile
    """
    return get_PINCE_IPC_directory(pid) + "/gdb_log.txt"


#:tag:GDBCommunication
def get_gdb_command_file(pid):
    """Get the path of gdb command file of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb command file
    """
    return get_PINCE_IPC_directory(pid) + "/gdb_command.txt"


#:tag:BreakWatchpoints
def get_track_watchpoint_file(pid, watchpoint_list):
    """Get the path of track watchpoint file for given pid and watchpoint

    Args:
        pid (int,str): PID of the process
        watchpoint_list (list,str): Numbers of the watchpoints

    Returns:
        str: Path of track watchpoint file
    """
    return get_PINCE_IPC_directory(pid) + "/" + str(watchpoint_list) + "_track_watchpoint.txt"


#:tag:BreakWatchpoints
def get_track_breakpoint_file(pid, breakpoint):
    """Get the path of track breakpoint file for given pid and breakpoint

    Args:
        pid (int,str): PID of the process
        breakpoint (str): breakpoint number

    Returns:
        str: Path of track breakpoint file
    """
    return get_PINCE_IPC_directory(pid) + "/" + breakpoint + "_track_breakpoint.txt"


#:tag:Tools
def get_trace_instructions_file(pid, breakpoint):
    """Get the path of trace instructions file for given pid and breakpoint

    Args:
        pid (int,str): PID of the process
        breakpoint (str): breakpoint number

    Returns:
        str: Path of trace instructions file
    """
    return get_PINCE_IPC_directory(pid) + "/" + breakpoint + "_trace.txt"


#:tag:Utilities
def save_file(data, file_path, save_method="json"):
    """Saves the specified data to given path

    Args:
        data (??): Saved data, can be anything, but must be supported by save_method
        file_path (str): Path of the saved file
        save_method (str): Can be "json" or "pickle"

    Returns:
        bool: True if saved successfully, False if not

    Known extensions(name, ext, type):
        Trace File, .trace, json
    """
    if save_method == "json":
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            json.dump(data, open(file_path, "w"))
            chown_to_user(file_path)
            return True
        except Exception as e:
            print(e, "Encountered an exception while dumping the data")
            return False
    elif save_method == "pickle":
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            pickle.dump(data, open(file_path, "wb"))
            chown_to_user(file_path)
            return True
        except Exception as e:
            print(e, "Encountered an exception while dumping the data")
            return False
    else:
        print("Unsupported save_method, bailing out...")
        return False


#:tag:Utilities
def load_file(file_path, load_method="json", return_on_fail=None):
    """Loads data from the given path

    Args:
        file_path (str): Path of the saved file
        load_method (str): Can be "json" or "pickle"
        return_on_fail (??): Return this object if loading fails, None is the default

    Returns:
        ??: file_path is like a box of chocolates, you never know what you're gonna get
        Returns return_on_fail if loading fails, None is the default

    Known extensions(name, ext, type):
        Trace File, .trace, json
    """
    if load_method == "json":
        try:
            output = json.load(open(file_path, "r"), object_pairs_hook=OrderedDict)
        except Exception as e:
            print(e, "Encountered an exception while loading the data")
            return return_on_fail
    elif load_method == "pickle":
        try:
            output = pickle.load(open(file_path, "rb"))
        except Exception as e:
            print(e, "Encountered an exception while loading the data")
            return return_on_fail
    else:
        print("Unsupported load_method, bailing out...")
        return return_on_fail
    return output


#:tag:Tools
def get_trace_instructions_status_file(pid, breakpoint):
    """Get the path of trace instructions status file for given pid and breakpoint

    Args:
        pid (int,str): PID of the process
        breakpoint (str): breakpoint number

    Returns:
        str: Path of trace instructions status file
    """
    return get_PINCE_IPC_directory(pid) + "/" + breakpoint + "_trace_status.txt"


#:tag:Tools
def get_dissect_code_status_file(pid):
    """Get the path of dissect code status file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of dissect code status file
    """
    return get_PINCE_IPC_directory(pid) + "/dissect_code_status.txt"


#:tag:Tools
def get_referenced_strings_file(pid):
    """Get the path of referenced strings dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced strings dict file
    """
    return get_PINCE_IPC_directory(pid) + "/referenced_strings_dict.txt"


#:tag:Tools
def get_referenced_jumps_file(pid):
    """Get the path of referenced jumps dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced jumps dict file
    """
    return get_PINCE_IPC_directory(pid) + "/referenced_jumps_dict.txt"


#:tag:Tools
def get_referenced_calls_file(pid):
    """Get the path of referenced strings dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced calls dict file
    """
    return get_PINCE_IPC_directory(pid) + "/referenced_calls_dict.txt"


#:tag:GDBCommunication
def get_ipc_from_PINCE_file(pid):
    """Get the path of IPC file sent to custom gdb commands from PINCE for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + type_defs.PATHS.IPC_FROM_PINCE_PATH


#:tag:GDBCommunication
def get_ipc_to_PINCE_file(pid):
    """Get the path of IPC file sent to PINCE from custom gdb commands for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_PINCE_IPC_directory(pid) + type_defs.PATHS.IPC_TO_PINCE_PATH


#:tag:ValueType
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
        None: If the string is not parsable by using the parameter value_index

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
    if type_defs.VALUE_INDEX.is_string(value_index):
        return string
    string = string.strip()
    if value_index is type_defs.VALUE_INDEX.INDEX_AOB:
        try:
            string_list = split(r"\s+", string)
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


#:tag:Utilities
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


#:tag:ValueType
def aob_to_str(list_of_bytes, encoding="ascii"):
    """Converts given array of hex strings to str

    Args:
        list_of_bytes (list): Must be returned from GDB_Engine.hex_dump()
        encoding (str): See here-->https://docs.python.org/3/library/codecs.html#standard-encodings

    Returns:
        str: str equivalent of array
    """

    # 3f is ascii hex representation of char "?"
    return bytes.fromhex("".join(list_of_bytes).replace("??", "3f")).decode(encoding, "surrogateescape")


#:tag:ValueType
def str_to_aob(string, encoding="ascii"):
    """Converts given string to aob string

    Args:
        string (str): Any string
        encoding (str): See here-->https://docs.python.org/3/library/codecs.html#standard-encodings

    Returns:
        str: AoB equivalent of the given string
    """
    s = str(binascii.hexlify(string.encode(encoding, "surrogateescape")), "ascii")
    return " ".join(s[i:i + 2] for i in range(0, len(s), 2))


#:tag:GDBExpressions
def split_symbol(symbol_string):
    """Splits symbol part of type_defs.tuple_function_info into smaller fractions
    Fraction count depends on the the symbol_string. See Examples section for demonstration

    Args:
        symbol_string (str): symbol part of type_defs.tuple_function_info

    Returns:
        list: A list containing parts of the splitted symbol

    Examples:
        symbol_string-->"func(param)@plt"
        returned_list-->["func","func(param)","func(param)@plt"]

        symbol_string-->"malloc@plt"
        returned_list-->["malloc", "malloc@plt"]

        symbol_string-->"printf"
        returned_list-->["printf"]
    """
    returned_list = []
    if "(" in symbol_string:
        returned_list.append(symbol_string.split("(", maxsplit=1)[0])
    if "@" in symbol_string:
        returned_list.append(symbol_string.split("@", maxsplit=1)[0])
    returned_list.append(symbol_string)
    return returned_list


#:tag:Utilities
def execute_shell_command_as_user(command):
    """Executes given command as user

    Args:
        command (str): Command that'll be invoked from the shell
    """
    uid, gid = get_user_ids()
    os.system("sudo -u '#" + uid + "' " + command)


#:tag:Utilities
def get_docstrings(modules, search_for=""):
    """Gathers docstrings from a list of modules
    For now, this function only supports variables and functions
    See get_comments_of_variables function to learn documenting variables in PINCE style

    Args:
        modules (list): A list of modules
        search_for (str): String that will be searched in variables and functions

    Returns:
        dict: A dict containing docstrings for documented variables and functions
        Format-->{variable1:docstring1, variable2:docstring2, ...}
    """
    element_dict = {}
    variable_comment_dict = get_comments_of_variables(modules)
    for item in modules:
        for key, value in item.__dict__.items():
            name_with_module = get_module_name(item) + "." + key
            if name_with_module in variable_comment_dict:
                element_dict[name_with_module] = variable_comment_dict[name_with_module]
            else:
                element_dict[name_with_module] = value.__doc__
    for item in list(element_dict):
        if item.split(".")[-1].find(search_for) == -1:
            del element_dict[item]
    return element_dict


#:tag:Utilities
def get_comments_of_variables(modules, search_for=""):
    """Gathers comments from a list of modules
    Python normally doesn't allow modifying __doc__ variable of the variables
    This function is designed to bring a solution to this problem
    The documentation must be PINCE style. It must start with this--> "#:doc:"
    See examples for more details

    Args:
        modules (list): A list of modules
        search_for (str): String that will be searched in variables

    Returns:
        dict: A dict containing docstrings for documented variables
        Format-->{variable1:docstring1, variable2:docstring2, ...}

    Example for single line comments:
        Code--▼
            #:doc:
            #Documentation for the variable
            some_variable = blablabla
        Returns--▼
            {"some_variable":"Documentation for the variable"}

    Example for multi line comments:
        Code--▼
            #:doc:
            '''Some Header
            Documentation for the variable
            Some Ending Word'''
            some_variable = blablabla
        Returns--▼
            {"some_variable":"Some Header\nDocumentation for the variable\nSome Ending Word"}
    """
    comment_dict = {}
    source_files = []
    for module in modules:
        source_files.append(module.__file__)
    for index, file_path in enumerate(source_files):
        source_file = open(file_path, "r")
        lines = source_file.readlines()
        for row, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith("#:doc:"):
                docstring_list = []
                while True:
                    row += 1
                    current_line = lines[row].strip()
                    if current_line.startswith("#"):
                        docstring_list.append(current_line.replace("#", "", 1))
                    elif current_line.startswith("'''"):
                        current_line = current_line.replace("'''", "", 1)
                        if current_line.endswith("'''"):
                            current_line = current_line.replace("'''", "")
                            docstring_list.append(current_line)
                            continue
                        docstring_list.append(current_line)
                        while True:
                            row += 1
                            current_line = lines[row].strip()
                            if current_line.endswith("'''"):
                                current_line = current_line.replace("'''", "")
                                docstring_list.append(current_line)
                                break
                            docstring_list.append(current_line)
                    else:
                        while True:
                            stripped_current_line = search(r"(\w+)\s*=", current_line)
                            if stripped_current_line:
                                variable = stripped_current_line.group(1)
                                break
                            row += 1
                            current_line = lines[row].strip()
                        break
                if variable.find(search_for) == -1:
                    continue
                comment_dict[get_module_name(modules[index]) + "." + variable] = "\n".join(docstring_list)
    return comment_dict


#:tag:Utilities
def get_tags(modules, search_for=""):
    """Gathers tags from a python source file
    The documentation must be PINCE style. It must start like this--> "#:tag:tag_name"
    Tag names can be found in type_defs.tag_to_string
    For now, tagging system only supports variables and functions
    See examples for more details

    Args:
        modules (list): A list of modules
        search_for (str): String that will be searched in tags

    Returns:
        dict: A dict containing tag keys for tagged variables
        Format-->{tag1:variable_list1, tag2:variable_list2, ...}

    Examples:
        Code--▼
            #:tag:tag_name
            #Documentation for the variable
            some_variable = blablabla

            or

            #:tag:tag_name
            def func_name(...)
        Returns--▼
            {"tag_name":list of some_variables or func_names that have the tag tag_name}
    """
    tag_dict = {}
    source_files = []
    for module in modules:
        source_files.append(module.__file__)
    for index, file_path in enumerate(source_files):
        source_file = open(file_path, "r")
        lines = source_file.readlines()
        for row, line in enumerate(lines):
            stripped_line = line.strip()
            if stripped_line.startswith("#:tag:"):
                tag = stripped_line.replace("#:tag:", "", 1)
                while True:
                    row += 1
                    current_line = lines[row].strip()
                    stripped_current_line = search(r"def\s+(\w+)|(\w+)\s*=", current_line)
                    if stripped_current_line:
                        for item in stripped_current_line.groups():
                            if item:
                                if item.find(search_for) == -1:
                                    break
                                item = get_module_name(modules[index]) + "." + item
                                try:
                                    tag_dict[tag].append(item)
                                except KeyError:
                                    tag_dict[tag] = [item]
                                break
                            else:
                                continue
                        break
    return tag_dict


def get_module_name(module):
    """Gets the name of the given module without the package name

    Args:
        module (module): A module

    Returns:
        str: Name of the module
    """
    return module.__name__.replace(module.__package__ + ".", "", 1)


#:tag:Utilities
def init_user_files():
    """Initializes user files"""
    for directory in type_defs.USER_PATHS.get_init_directories():
        is_path_valid(directory, "create")
    for file in type_defs.USER_PATHS.get_init_files():
        try:
            open(file).close()
        except FileNotFoundError:
            open(file, "w").close()
    chown_to_user(type_defs.USER_PATHS.ROOT_PATH, recursive=True)


#:tag:Utilities
def chown_to_user(file_path, recursive=False):
    """Gives ownership of given path to user

    Args:
        file_path (str): Self-explanatory
        recursive (bool): If True, applies chown recursively
    """
    uid, gid = get_user_ids()
    os.system("sudo chown " + ("-R " if recursive else "") + uid + ":" + gid + " " + file_path)


#:tag:Utilities
def get_user_ids():
    """Gets uid and gid of the current user

    Returns:
        tuple: (str, str)-->uid and gid of the current user
    """
    uid = os.getenv("SUDO_UID") or str(os.getuid())
    gid = os.getenv("SUDO_GID") or str(os.getgid())
    return uid, gid


#:tag:Tools
def execute_script(file_path):
    """Loads and executes the script in the given path

    Args:
        file_path (str): Self-explanatory

    Returns:
        tuple: (module, exception)
        module--> Loaded script as module
        exception--> traceback as str

        Returns (None, exception) if fails to load the script
        Returns (module, None) if script gets loaded successfully
    """
    head, tail = os.path.split(file_path)
    file_name = tail.split(".", maxsplit=1)[0]
    try:
        module = SourceFileLoader(file_name, file_path).load_module()
    except Exception as e:
        print("Encountered an exception while loading the script located at " + file_path)
        tb = traceback.format_exception(None, e, e.__traceback__)
        tb.insert(0, "------->You can ignore the importlib part if the source file is valid<-------\n")
        tb = "".join(tb)
        print(tb)
        return None, tb
    return module, None
