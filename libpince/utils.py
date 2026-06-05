# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

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

import os, shutil, sys, binascii, pickle, json, traceback, re, pwd, pathlib, logging, subprocess, shlex, struct
from . import typedefs, regexes
from capstone import Cs, CsError, CS_ARCH_X86, CS_MODE_32, CS_MODE_64
from keystone import Ks, KsError, KS_ARCH_X86, KS_MODE_32, KS_MODE_64
from collections import OrderedDict
from importlib.machinery import SourceFileLoader
from pygdbmi import gdbmiparser
from types import ModuleType
from typing import Any, Callable

# Capstone initialization
cs_32 = Cs(CS_ARCH_X86, CS_MODE_32)
cs_64 = Cs(CS_ARCH_X86, CS_MODE_64)

# Keystone initialization
ks_32 = Ks(KS_ARCH_X86, KS_MODE_32)
ks_64 = Ks(KS_ARCH_X86, KS_MODE_64)

# Initialize logging
logger = logging.getLogger("PINCE")


def __init_logging() -> None:
    global logger
    if len(logger.handlers) != 0:
        return
    logger.setLevel(logging.DEBUG)
    log_format = logging.Formatter("[%(levelname)s][%(funcName)s] %(message)s")
    # File logging
    file_handler = logging.FileHandler("/var/log/pince.log", mode="w")  # Maybe change this to be per-process
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    # Terminal logging
    terminal_handler = logging.StreamHandler(sys.stdout)
    terminal_handler.setLevel(logging.DEBUG)
    terminal_handler.setFormatter(log_format)
    ##################
    logger.addHandler(file_handler)
    logger.addHandler(terminal_handler)


__init_logging()


def get_process_list() -> list[tuple[str, str, str]]:
    """Returns a list of processes

    Returns:
        list: List of (pid, user, process_name) -> (str, str, str)
    """
    process_list = []
    for line in os.popen("ps -eo pid:11,user,comm").read().splitlines():
        info = regexes.ps.match(line)
        if info:
            process_list.append(info.groups())
    return process_list


def get_process_name(pid: int | str) -> str:
    """Returns the process name of given pid

    Args:
        pid (int, str): PID of the process

    Returns:
        str: Process name
    """
    with open(f"/proc/{pid}/comm") as f:
        return f.read().splitlines()[0]


def search_processes(name_or_pid: str | int) -> list[tuple[str, str, str]]:
    """Searches processes and returns a list of the ones that contain given process name or pid

    Args:
        name_or_pid (str): Name or PID of the process that'll be searched for

    Returns:
        list: List of (pid, user, process_name) -> (str, str, str)
    """
    needle = str(name_or_pid).lower()
    processlist = []
    for pid, user, name in get_process_list():
        if needle in name.lower() or needle == pid:
            processlist.append((pid, user, name))
    return processlist


def get_regions(pid: int) -> list[tuple[str, ...]]:
    """Returns memory regions of a process

    Args:
        pid (int): PID of the process

    Returns:
        list: List of (start_address, end_address, permissions, map_offset, device_node, inode, path) -> all str
    """
    with open("/proc/" + str(pid) + "/maps") as f:
        regions = []
        for line in f.read().splitlines():
            regions.append(regexes.maps.match(line).groups())
        return regions


def get_module_load_bias(pid: int, name_regex: str) -> tuple[int, str] | None:
    """Finds the first mapped file whose basename matches name_regex and returns its load bias and absolute path.

    Args:
        pid (int): PID of the process
        name_regex (str): Regular expression to match against the basename of mapped files

    Returns:
        tuple: (load_bias, absolute_path) where load_bias is an int and absolute_path is a str
        None: If no matching module is found
    """
    compiled = re.compile(name_regex)
    per_file: dict[str, list[tuple[int, int]]] = {}
    for start, _, _, offset, _, _, path in get_regions(pid):
        if not path:
            continue
        if compiled.search(os.path.basename(path)):
            per_file.setdefault(path, []).append((int(start, 16), int(offset, 16)))
    for path, mappings in per_file.items():
        return min(start - offset for start, offset in mappings), path
    return None


def get_defined_dynamic_symbols(elf_path: str, symbol_names: list[str]) -> dict[str, int]:
    """Parses the .dynsym/.dynstr of an ELF file and returns {name: st_value} for each
    requested symbol that is defined in the file.
    Handles ELFCLASS32/64 and both endiannesses.

    Args:
        elf_path (str): Path to the ELF file on disk
        symbol_names (list[str]): List of symbol names to look up

    Returns:
        dict: {symbol_name: st_value} for each defined symbol found
        Empty dict on failure or if no section headers are present
    """
    try:
        with open(elf_path, "rb") as elf_file:
            data = elf_file.read()
    except OSError:
        return {}
    if data[:4] != b"\x7fELF":
        return {}
    is64 = data[4] == 2
    endian = "<" if data[5] == 1 else ">"
    if is64:
        e_shoff = struct.unpack_from(endian + "Q", data, 0x28)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(endian + "HHH", data, 0x3A)
        shdr_fmt, sym_fmt, default_sym_size = endian + "IIQQQQIIQQ", endian + "IBBHQQ", 24
    else:
        e_shoff = struct.unpack_from(endian + "I", data, 0x20)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(endian + "HHH", data, 0x2E)
        shdr_fmt, sym_fmt, default_sym_size = endian + "IIIIIIIIII", endian + "IIIBBH", 16
    if e_shoff == 0 or e_shnum == 0:
        return {}

    def read_shdr(i):
        return struct.unpack_from(shdr_fmt, data, e_shoff + i * e_shentsize)

    def read_cstr(base):
        try:
            return data[base:data.index(b"\x00", base)].decode("latin-1")
        except (ValueError, IndexError):
            return ""

    shstr_offset = read_shdr(e_shstrndx)[4]
    dynsym = dynstr = None
    for i in range(e_shnum):
        sh = read_shdr(i)
        nm = read_cstr(shstr_offset + sh[0])
        if nm == ".dynsym":
            dynsym = sh
        elif nm == ".dynstr":
            dynstr = sh
    if dynsym is None or dynstr is None:
        return {}
    dynsym_offset, dynsym_size, dynsym_entsize = dynsym[4], dynsym[5], dynsym[9]
    dynstr_offset = dynstr[4]
    sym_size = dynsym_entsize or default_sym_size
    wanted, found = set(symbol_names), {}
    for i in range(dynsym_size // sym_size):
        f = struct.unpack_from(sym_fmt, data, dynsym_offset + i * sym_size)
        st_name, st_value, st_shndx = (f[0], f[4], f[3]) if is64 else (f[0], f[1], f[5])
        if st_shndx == 0 or st_value == 0:
            continue
        name = read_cstr(dynstr_offset + st_name)
        if name in wanted:
            found[name] = st_value
            if len(found) == len(wanted):
                break
    return found


def get_region_dict(pid: int) -> dict[str, list[str]]:
    """Returns memory regions of a process as a dictionary where key is the path tail and value is the list of the
    corresponding start addresses of the tail, empty paths will be ignored. Also adds shortcuts for file extensions,
    returned dict will include both sonames, with and without version information

    Args:
        pid (int): PID of the process

    Returns:
        dict: {file_name:start_address_list}
    """
    region_dict: dict[str, list[str]] = {}
    for item in get_regions(pid):
        start_addr, _, _, _, _, _, path = item
        if not path:
            continue
        _, tail = os.path.split(path)
        start_addr = "0x" + start_addr
        # Always append, never assign: a versioned soname's unversioned alias (e.g. libEGL.so.1 -> libEGL.so)
        # must not clobber the list of a different file that has the same basename
        region_dict.setdefault(tail, []).append(start_addr)
        short_name = regexes.file_with_extension.search(tail)
        if short_name:
            short_name = short_name.group(0)
            if short_name != tail:
                region_dict.setdefault(short_name, []).append(start_addr)
    return region_dict


def get_region_info(pid: int | str, address: int | str) -> typedefs.tuple_region_info | None:
    """Finds the closest valid starting/ending address and region to given address, assuming given address is in the
    valid address range

    Args:
        pid (int): PID of the process
        address (int,str): Can be an int or a hex str

    Returns:
        list: List of (start_address, end_address, permissions, file_name) -> (int, int, str, str)
        None: If the given address isn't in any valid address range
    """
    if type(pid) != int:
        pid = safe_int_cast(pid)
    if type(address) != int:
        address = safe_str_to_int(address, 0)
    region_list = get_regions(pid)
    region_dict = get_region_dict(pid)
    for start, end, perms, _, _, _, path in region_list:
        start_int = safe_str_to_int(start, 16)
        end_int = safe_str_to_int(end, 16)
        if start_int <= address < end_int:
            file_name = os.path.split(path)[1]
            address_list = region_dict.get(file_name, [])
            try:
                region_index = address_list.index("0x" + start)
            except ValueError:
                region_index = 0
            return typedefs.tuple_region_info(start_int, end_int, perms, file_name, region_index)


def filter_regions(pid: int, attribute: str, regex: str, case_sensitive: bool = False) -> list[tuple[str, ...]]:
    """Filters memory regions by searching for the given regex within the given attribute

    Args:
        pid (int): PID of the process
        attribute (str): The attribute that'll be filtered. Can be one of the below
        start_address, end_address, permissions, map_offset, device_node, inode, path
        regex (str): Regex statement that'll be searched
        case_sensitive (bool): If True, search will be case sensitive

    Returns:
        list: List of (start_address, end_address, permissions, map_offset, device_node, inode, path) -> all str
    """
    attributes = ["start_address", "end_address", "permissions", "map_offset", "device_node", "inode", "path"]
    if attribute not in attributes:
        raise Exception("Invalid attribute")
    index = attributes.index(attribute)
    if case_sensitive:
        compiled_regex = re.compile(regex)
    else:
        compiled_regex = re.compile(regex, re.IGNORECASE)
    filtered_regions = []
    for region in get_regions(pid):
        if compiled_regex.search(region[index]):
            filtered_regions.append(region)
    return filtered_regions


def is_traced(pid: int) -> str | None:
    """Check if the process corresponding to given pid traced by any other process

    Args:
        pid (int): PID of the process

    Returns:
        str: Name of the tracer if the specified process is being traced
        None: if the specified process is not being traced or the process doesn't exist anymore
    """
    try:
        status_file = open(f"/proc/{pid}/status")
    except FileNotFoundError:
        return
    with status_file:
        for line in status_file:
            if line.startswith("TracerPid:"):
                tracer_pid = line.split(":", 1)[1].strip()
                if tracer_pid != "0":
                    try:
                        return get_process_name(tracer_pid)
                    except FileNotFoundError:
                        return "<unknown tracer>"
                return


def is_process_valid(pid: int) -> bool:
    """Check if the process corresponding to given pid is valid

    Args:
        pid (int): PID of the process

    Returns:
        bool: True if the process is still running, False if not
    """
    return os.path.exists("/proc/%d" % pid)


def is_wine_process(pid: int) -> bool:
    """Check if the inferior is running under Wine or Proton.

    Scans /proc/<pid>/maps for WINE, Proton, or Steam pressure-vessel libraries.
    Mostly used to gate features that don't yet work reliably under WINE in the GUI.

    Args:
        pid (int): PID of the process

    Returns:
        bool: True if Wine/Proton/pressure-vessel libraries are mapped into the process
    """
    if pid <= 0:
        return False
    try:
        with open(f"/proc/{pid}/maps", "r") as maps_file:
            for line in maps_file:
                lower = line.lower()
                if "wine" in lower or "proton" in lower or "pressure-vessel" in lower:
                    return True
    except OSError:
        pass
    return False


def get_script_directory() -> str:
    """Get main script directory

    Returns:
        str: A string pointing to the main script directory
    """
    return sys.path[0]


def get_media_directory() -> str:
    """Get media directory

    Returns:
        str: A string pointing to the media directory
    """
    return get_script_directory() + "/media"


def get_logo_directory() -> str:
    """Get logo directory

    Returns:
        str: A string pointing to the logo directory
    """
    return get_script_directory() + "/media/logo"


def get_libpince_directory() -> str:
    """Get libpince directory

    Returns:
        str: A string pointing to the libpince directory

    Note:
        In fact this function returns the directory where utils in and considering the fact that utils resides in
        libpince, it works. So, please don't move out utils outside of libpince folder!
    """
    return os.path.dirname(os.path.realpath(__file__))


def delete_ipc_path(pid: int | str) -> None:
    """Deletes the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    path = get_ipc_path(pid)
    if os.path.exists(path):
        shutil.rmtree(path)


def create_ipc_path(pid: int | str) -> None:
    """Creates the IPC directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    path = get_ipc_path(pid)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

    # Opening the command file with 'w' each time debugcore.send_command() gets invoked slows down the process
    # Instead, here we create the command file for only once when IPC path gets initialized
    # Then, open the command file with 'r' in debugcore.send_command() to get a better performance
    command_file = get_gdb_command_file(pid)
    open(command_file, "w").close()


def create_tmp_path(pid: int | str) -> None:
    """Creates the tmp directory of given pid

    Args:
        pid (int,str): PID of the process
    """
    path = get_tmp_path(pid)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def get_ipc_path(pid: int | str) -> str:
    """Get the IPC directory of given pid

    Args:
        pid (int): PID of the process

    Returns:
        str: Path of IPC directory
    """
    return typedefs.PATHS.IPC + str(pid)


def get_tmp_path(pid: int | str) -> str:
    """Get the tmp directory of given pid

    Args:
        pid (int): PID of the process

    Returns:
        str: Path of tmp directory
    """
    return typedefs.PATHS.TMP + str(pid)


def get_logging_file(pid: int | str) -> str:
    """Get the path of gdb logfile of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb logfile
    """
    return get_tmp_path(pid) + "/gdb_log.txt"


def get_gdb_command_file(pid: int | str) -> str:
    """Get the path of gdb command file of given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of gdb command file
    """
    return get_ipc_path(pid) + "/gdb_command.txt"


def get_track_watchpoint_file(pid: int | str, watchpoint_list: list | str) -> str:
    """Get the path of track watchpoint file for given pid and watchpoint

    Args:
        pid (int,str): PID of the process
        watchpoint_list (list,str): Numbers of the watchpoints

    Returns:
        str: Path of track watchpoint file
    """
    return get_ipc_path(pid) + "/" + str(watchpoint_list) + "_track_watchpoint.txt"


def get_track_breakpoint_file(pid: int | str, breakpoint_number: int | str) -> str:
    """Get the path of track breakpoint file for given pid and breakpoint

    Args:
        pid (int,str): PID of the process
        breakpoint_number (int)

    Returns:
        str: Path of track breakpoint file
    """
    return f"{get_ipc_path(pid)}/{breakpoint_number}_track_breakpoint.txt"


def append_file_extension(string: str, extension: str) -> str:
    """Appends the given extension to the given string if it doesn't end with the given extension

    Args:
        string (str): Self-explanatory
        extension (str): Self-explanatory, you don't have to include the dot

    Returns:
        str: Given string with the extension
    """
    extension = extension.strip(".")
    return string if string.endswith("." + extension) else string + "." + extension


def save_file(data: Any, file_path: str, save_method: str = "json") -> bool:
    """Saves the specified data to given path

    Args:
        data (??): Saved data, can be anything, must be supported by save_method
        file_path (str): Path of the saved file
        save_method (str): Can be "json" or "pickle"

    Returns:
        bool: True if saved successfully, False if not
    """
    if save_method == "json":
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as save_file:
                json.dump(data, save_file)
            return True
        except Exception:
            logger.exception("Encountered an exception while dumping the data in JSON format\n")
            return False
    elif save_method == "pickle":
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as save_file:
                pickle.dump(data, save_file)
            return True
        except Exception:
            logger.exception("Encountered an exception while pickling the data\n")
            return False
    else:
        logger.error("Unsupported save_method, bailing out...")
        return False


def load_file(file_path: str, load_method: str = "json") -> Any:
    """Loads data from the given path

    Args:
        file_path (str): Path of the saved file
        load_method (str): Can be "json" or "pickle"

    Returns:
        ??: file_path is like a box of chocolates, you never know what you're gonna get
        None: If loading fails
    """
    if load_method == "json":
        try:
            with open(file_path, "r") as load_file:
                return json.load(load_file, object_pairs_hook=OrderedDict)
        except Exception:
            logger.exception("Encountered an exception while loading the JSON data")
            return
    elif load_method == "pickle":
        try:
            with open(file_path, "rb") as load_file:
                return pickle.load(load_file)
        except Exception:
            logger.exception("Encountered an exception while unpickling the data")
            return
    else:
        logger.error("Unsupported load_method, bailing out...")
        return


def get_trace_status_file(pid: int | str) -> str:
    """Get the path of trace status file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of trace status file
    """
    return get_ipc_path(pid) + "/_trace_status.txt"


def change_trace_status(pid: int | str, trace_status: int) -> None:
    """Change trace status for given pid

    Args:
        pid (int,str): PID of the process
        trace_status (int): New trace status, can be a member of typedefs.TRACE_STATUS
    """
    trace_status_file = get_trace_status_file(pid)
    with open(trace_status_file, "w") as trace_file:
        trace_file.write(str(trace_status))


def get_dissect_code_status_file(pid: int | str) -> str:
    """Get the path of dissect code status file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of dissect code status file
    """
    return get_ipc_path(pid) + "/dissect_code_status.txt"


def get_referenced_strings_file(pid: int | str) -> str:
    """Get the path of referenced strings dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced strings dict file
    """
    return get_tmp_path(pid) + "/referenced_strings_dict.txt"


def get_referenced_jumps_file(pid: int | str) -> str:
    """Get the path of referenced jumps dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced jumps dict file
    """
    return get_tmp_path(pid) + "/referenced_jumps_dict.txt"


def get_referenced_calls_file(pid: int | str) -> str:
    """Get the path of referenced strings dict file for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of referenced calls dict file
    """
    return get_tmp_path(pid) + "/referenced_calls_dict.txt"


def get_from_pince_file(pid: int | str) -> str:
    """Get the path of IPC file sent to custom gdb commands from PINCE for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_ipc_path(pid) + typedefs.PATHS.FROM_PINCE


def get_to_pince_file(pid: int | str) -> str:
    """Get the path of IPC file sent to PINCE from custom gdb commands for given pid

    Args:
        pid (int,str): PID of the process

    Returns:
        str: Path of IPC file
    """
    return get_ipc_path(pid) + typedefs.PATHS.TO_PINCE


def parse_string(string: str, value_index: int) -> str | list[int] | float | int | None:
    """Parses the string according to the given value_index

    Args:
        string (str): String that'll be parsed
        value_index (int): Determines the type of data. Can be a member of typedefs.VALUE_INDEX

    Returns:
        str: If the value_index is STRING
        list: If the value_index is AOB. A list of ints is returned
        float: If the value_index is FLOAT32 or FLOAT64
        int: If the value_index is anything else
        None: If the string is not parsable by using the parameter value_index

    Examples:
        string="42 DE AD BE EF 24",value_index=typedefs.VALUE_INDEX.AOB--▼
        returned_list=[66, 222, 173, 190, 239, 36]
    """
    if not string:
        logger.error("Missing string parameter")
        return
    try:
        value_index = int(value_index)
    except:
        logger.exception(f"Value index ({value_index}) can't be converted to int")
        return
    if typedefs.VALUE_INDEX.is_string(value_index):
        return string
    string = string.strip()
    if value_index == typedefs.VALUE_INDEX.AOB:
        try:
            string_list = regexes.whitespaces.split(string)
            for item in string_list:
                if len(item) > 2:
                    logger.error(f"{string} can't be parsed as array of bytes")
                    return
            hex_list = [int(x, 16) for x in string_list]
            return hex_list
        except:
            logger.exception(f"{string} can't be parsed as array of bytes")
            return
    elif typedefs.VALUE_INDEX.is_float(value_index):
        try:
            string = float(string)
        except:
            try:
                string = float(int(string, 0))
            except:
                logger.exception(f"{string} can't be parsed as floating point variable")
                return
        return string
    else:
        try:
            string = int(string, 0)
        except:
            try:
                string = int(float(string))
            except:
                logger.exception(f"{string} can't be parsed as integer or hexadecimal")
                return
        if value_index == typedefs.VALUE_INDEX.INT8:
            string = string % 0x100  # 256
        elif value_index == typedefs.VALUE_INDEX.INT16:
            string = string % 0x10000  # 65536
        elif value_index == typedefs.VALUE_INDEX.INT32:
            string = string % 0x100000000  # 4294967296
        elif value_index == typedefs.VALUE_INDEX.INT64:
            string = string % 0x10000000000000000  # 18446744073709551616
        return string


def instruction_follow_address(string: str) -> str | None:
    """Searches for the location changing instructions such as Jcc, CALL and LOOPcc in the given string. Returns the hex
    address the instruction jumps to

    Args:
        string (str): An assembly expression

    Returns:
        str: Hex address
        None: If no hex address is found or no location changing instructions found
    """
    result = regexes.instruction_follow.search(string)
    if result:
        return result.group(2)


def extract_hex_address(string: str) -> str | None:
    """Extracts hex address from the given string

    Args:
        string (str): The string that the hex address will be extracted from

    Returns:
        str: Hex address
        None: If no hex address is found
    """
    if type(string) != str:
        return
    result = regexes.hex_number.search(string)
    if result:
        return result.group(0)


def modulo_address(int_address: int, arch_type: int) -> int:
    """Calculates the modulo of the given integer based on the given architecture type to make sure that it doesn't
    exceed the borders of the given architecture type (0xffffffff->x86, 0xffffffffffffffff->x64)

    Args:
        int_address (int): Self-explanatory
        arch_type (int): Architecture type (x86, x64). Can be a member of typedefs.INFERIOR_ARCH

    Returns:
        int: Modulo of the given integer based on the given architecture type
    """
    if arch_type == typedefs.INFERIOR_ARCH.ARCH_32:
        return int_address % 0x100000000
    elif arch_type == typedefs.INFERIOR_ARCH.ARCH_64:
        return int_address % 0x10000000000000000
    raise Exception("arch_type must be a member of typedefs.INFERIOR_ARCH")


def disassemble(aob: str, address: int, inferior_arch: int) -> str | None:
    """Returns the instructions from the given array of bytes

    Args:
        aob (str): Opcode bytes of the instruction as an array of bytes
        address (int): The address where the instruction starts from
        inferior_arch (int): Architecture type (x86, x64). Can be a member of typedefs.INFERIOR_ARCH

    Returns:
        str: Instructions, multiple entries are separated with ;
        None: If there was an error
    """
    if inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64:
        disassembler = cs_64
    else:
        disassembler = cs_32
    disassembler.skipdata = True
    try:
        bytecode = bytes.fromhex(aob.replace(" ", ""))
    except ValueError:
        return
    try:
        disas_data = disassembler.disasm_lite(bytecode, address)
        return "; ".join([f"{data[2]} {data[3]}" if data[3] != "" else data[2] for data in disas_data])
    except CsError:
        logger.exception("Failed to disassemble bytes")


def instruction_aligned_size(aob: bytes, minimum_bytes: int, inferior_arch: int) -> int:
    """Walks instructions from offset 0 of `aob` until cumulative size meets
    or exceeds `minimum_bytes`. Used by code-injection hooks where the patch
    must end on an instruction boundary so the next instruction decodes cleanly.

    Args:
        aob (bytes): Instruction stream starting at offset 0.
        minimum_bytes (int): Minimum number of bytes the result must cover.
        inferior_arch (int): Member of typedefs.INFERIOR_ARCH.

    Returns:
        int: Smallest instruction-aligned size >= minimum_bytes, or 0 if the
        bytes couldn't be decoded far enough.
    """
    if minimum_bytes <= 0:
        return 0
    disassembler = cs_64 if inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else cs_32
    disassembler.skipdata = True
    size = 0
    try:
        for _, instr_size, _, _ in disassembler.disasm_lite(bytes(aob), 0):
            size += instr_size
            if size >= minimum_bytes:
                return size
    except CsError:
        return 0
    return 0


def assemble(instructions: str, address: int, inferior_arch: int) -> tuple[list[int], int] | None:
    """Assembles the given instructions

    Args:
        instructions (str): A string of instructions, multiple entries separated by ;
        address (int): Starting address of the instructions
        inferior_arch (int): Can be a member of typedefs.INFERIOR_ARCH

    Returns:
        tuple: A tuple of (list, int) --> Assembled bytes (list of int) and instruction count (int)
        None: If there was an error
    """
    try:
        if inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            return ks_64.asm(instructions, address)
        else:
            return ks_32.asm(instructions, address)
    except KsError:
        logger.exception("Failed to assemble bytes")


def aob_to_str(
    list_of_bytes: list[int | str] | int | str, encoding: str = "ascii", replace_unprintable: bool = True
) -> str:
    """Converts given array of hex strings to str

    Args:
        list_of_bytes (list): Must be returned from debugcore.hex_dump()
        encoding (str): See here-->https://docs.python.org/3/library/codecs.html#standard-encodings
        replace_unprintable (bool): If True, replaces non-printable characters with a period (.)

    Returns:
        str: str equivalent of array
    """

    ### make an actual list of bytes
    hexString = ""
    byteList = list_of_bytes
    if isinstance(list_of_bytes, list):
        byteList = list_of_bytes
    else:
        byteList = []
        byteList.append(list_of_bytes)
    for sByte in byteList:
        if sByte == "??":
            hexString += f"{63:02x}"  # replace ?? with a single ?
        else:
            if isinstance(sByte, int):
                byte = sByte
            else:
                byte = safe_str_to_int(sByte, 16)
            if replace_unprintable and ((byte < 32) or (byte > 126)):
                hexString += f"{46:02x}"  # replace non-printable chars with a period (.)
            else:
                hexString += f"{byte:02x}"
    hexBytes = bytes.fromhex(hexString)
    return hexBytes.decode(encoding, "surrogateescape")


def str_to_aob(string: str, encoding: str = "ascii") -> str:
    """Converts given string to aob string

    Args:
        string (str): Any string
        encoding (str): See here-->https://docs.python.org/3/library/codecs.html#standard-encodings

    Returns:
        str: AoB equivalent of the given string
    """
    s = str(binascii.hexlify(string.encode(encoding, "surrogateescape")), encoding).upper()
    return " ".join(s[i : i + 2] for i in range(0, len(s), 2))


def split_symbol(symbol_string: str) -> list[str]:
    """Splits symbol part of typedefs.tuple_function_info into smaller fractions
    Fraction count depends on the the symbol_string. See Examples section for demonstration

    Args:
        symbol_string (str): symbol part of typedefs.tuple_function_info

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
    p_count = 0
    # this algorithm searches for balanced parentheses and removes the outer group
    # using string reversing with recursive re.split makes the code confusing as hell, going with this one instead
    # searching for balanced parentheses works because apparently no demangled symbol can finish with <.*>
    # XXX: run this code to test while attached to a process and open a detailed issue if you get a result
    """
    from libpince import debugcore
    import re
    result=debugcore.search_functions("")
    for address, symbol in result:
        if re.search("<.*>[^()]+$", symbol):
            print(symbol)
    """
    for index, letter in enumerate(symbol_string[::-1]):
        if letter == ")":
            p_count += 1
        elif letter == "(":
            p_count -= 1
            if p_count == 0:
                returned_list.append((symbol_string[: -(index + 1)]))
                break
            if p_count < 0:
                raise ValueError(
                    symbol_string + " contains unhealthy amount of left parentheses\nGotta give him some"
                    ' right parentheses. Like Bob always says "everyone needs a friend"'
                )
    if p_count != 0:
        raise ValueError(symbol_string + " contains unbalanced parentheses")
    if "@plt" in symbol_string:
        returned_list.append(symbol_string.rsplit("@plt", maxsplit=1)[0])
    returned_list.append(symbol_string)
    return returned_list


def extract_symbol_name(symbol_string: str) -> str:
    """Extract symbol name from examine_expression result

    Args:
        symbol_string (str): A string that contains a symbol in format <symbol_name>

    Returns:
        str: Symbol name without brackets or empty string if no symbol is found
    """
    result = regexes.symbol.search(symbol_string)
    return result.group(1) if result else ""


def execute_command_as_user(command: str) -> None:
    """Executes given command as the original user who invoked PINCE

    Args:
        command (str): Command that'll be invoked from the shell
    """
    uid, _ = get_user_ids()
    if not uid.isdigit():
        logger.error(f"Invalid uid {uid!r}, refusing to drop privileges")
        return
    subprocess.run(["sudo", "-Eu", f"#{uid}"] + shlex.split(command), check=False)


def init_user_files() -> None:
    """Initializes user files"""
    root_path = get_user_path(typedefs.USER_PATHS.ROOT)
    if not os.path.exists(root_path):
        os.makedirs(root_path)
    for file in typedefs.USER_PATHS.get_init_files():
        file = get_user_path(file)
        pathlib.Path(file).touch(exist_ok=True)


def get_user_ids() -> tuple[str, str]:
    """Gets uid and gid of the current user

    Returns:
        tuple: (str, str)-->uid and gid of the current user
    """
    uid = os.getenv("SUDO_UID") or str(os.getuid())
    gid = os.getenv("SUDO_GID") or str(os.getgid())
    return uid, gid


def get_user_home_dir() -> str:
    """Returns the home directory of the current user

    Returns:
        str: Home directory of the current user
    """
    uid, _ = get_user_ids()
    return pwd.getpwuid(int(uid)).pw_dir


def get_user_path(user_path: str) -> str:
    """Returns the specified user path for the current user

    Args:
        user_path (str): Can be a member of typedefs.USER_PATHS

    Returns:
        str: Specified user path of the current user
    """
    # TODO: Use XDG specification
    homedir = get_user_home_dir()
    return os.path.join(homedir, user_path)


def get_default_gdb_path() -> str:
    appdir = os.environ.get("APPDIR")
    if appdir:
        return appdir + "/usr/bin/gdb"
    return typedefs.PATHS.GDB


def execute_script(file_path: str) -> tuple[ModuleType | None, str | None]:
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
    _, tail = os.path.split(file_path)
    file_name = tail.split(".", maxsplit=1)[0]
    try:
        module = SourceFileLoader(file_name, file_path).load_module()
    except Exception as e:
        logger.error(f"Encountered an exception while loading the script located at {file_path}")
        tb = traceback.format_exception(None, e, e.__traceback__)
        tb.insert(0, "------->You can ignore the importlib part if the source file is valid<-------\n")
        tb = "".join(tb)
        logger.error(tb)
        return None, tb
    return module, None


def parse_response(response: str, line_num: int = 0) -> dict:
    """Parses the given GDB/MI output. Wraps gdbmiparser.parse_response
    debugcore.send_command returns an additional "^done" output because of the "source" command
    This function is used to get rid of that output before parsing

    Args:
        response (str): GDB/MI response
        line_num (int): Which line of the response will be parsed

    Returns:
        dict: Contents of the dict depends on the response
    """
    return gdbmiparser.parse_response(response.splitlines()[line_num])


def search_files(directory: str, regex: str) -> list[str]:
    """Searches the files in given directory for given regex recursively

    Args:
        directory (str): Directory to search for
        regex (str): Regex to search for

    Returns:
        list: Sorted list of the relative paths(to the given directory) of the files found
    """
    file_list = []
    for file in pathlib.Path(directory).rglob("*"):
        if not file.is_file():
            continue
        result = re.search(regex, file.name, re.IGNORECASE)
        if result:
            file_list.append(str(file.relative_to(directory)))
    return sorted(file_list)


def ignore_exceptions(func: Callable) -> Callable:
    """A decorator to ignore exceptions"""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback.print_exc()

    return wrapper


def upper_hex(hex_str: str) -> str:
    """Converts the given hex string to uppercase while keeping the 'x' character lowercase"""
    # check if the given string is a hex string, if not return the string as is
    if not regexes.hex_number_gui.match(hex_str):
        return hex_str
    return hex_str.upper().replace("X", "x")


def return_optional_int(val: int) -> int | None:
    return None if val == 0 else val


# This is the main int() cast for strings that should be used until you're certain that the cast can never fail or has explicit handling.
# The reason for this is that you can catch stray errors or edge cases by safely returning a value and outputting useful log info
# instead of failing with an exception that will propagate upwards.
def safe_str_to_int(input: Any, base: int) -> int:
    try:
        return int(input, base)
    except ValueError:
        logger.error(
            f"ValueError: Tried to convert input '{input}' to base {base} for caller '{sys._getframe().f_back.f_code.co_qualname}'"
        )
        return 0
    except TypeError:
        logger.error(
            f"TypeError: Tried to convert input '{input}' to base {base} for caller '{sys._getframe().f_back.f_code.co_qualname}'"
        )
        return 0


# This is the non-base version of the above.
def safe_int_cast(input: Any) -> int:
    try:
        return int(input)
    except ValueError:
        logger.error(
            f"ValueError: Tried to convert input '{input}' for caller '{sys._getframe().f_back.f_code.co_qualname}'"
        )
        return 0
    except TypeError:
        logger.error(
            f"TypeError: Tried to convert input '{input}' for caller '{sys._getframe().f_back.f_code.co_qualname}'"
        )
        return 0
