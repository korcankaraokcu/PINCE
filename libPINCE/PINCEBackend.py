"""
    GameConquerorBackend: communication with libscanmem

    Copyright (C) 2010,2011,2013 Wang Lu <coolwanglu(a)gmail.com>
    Copyright (C) 2018 Sebastian Parschauer <s.parschauer(a)gmx.de>

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

import ctypes, tempfile, os, sys
from ctypes import byref
import re

# taken from https://github.com/scanmem/scanmem/blob/6a5e2e86ebacd87bed132dea354433d722081abf/gui/backend.py
# see https://github.com/scanmem/scanmem/issues/225 for future improvements
class PINCEBackend():
    BACKEND_FUNCTIONS = {
        "sm_init": (ctypes.c_bool, ),
        "sm_cleanup": (None, ),
        "sm_set_backend": (None, ),
        "sm_backend_exec_cmd" : (None, ctypes.c_char_p),
        "sm_get_num_matches" : (ctypes.c_ulong, ),
        "sm_get_version" : (ctypes.c_char_p, ),
        "sm_get_scan_progress" : (ctypes.c_double, ),
        "sm_set_stop_flag" : (None, ctypes.c_bool),
        "sm_process_is_dead": (ctypes.c_bool, )
    }

    """
        scans the current dirrectory (PINCE/libPINCE) for libscanmem
        @param libname
    """
    def __init__(self, libname="scanmem.so"):
        self.lib = ctypes.CDLL(os.path.dirname(__file__) + os.path.sep + libname)
        self.libc = ctypes.CDLL("libc.so.6")
        self.init_sm_funcs()
        self.lib.sm_init()

    def init_sm_funcs(self):
        for k, v in PINCEBackend.BACKEND_FUNCTIONS.items():
            f = getattr(self.lib, k)
            f.restype = v[0]
            f.argtypes = v[1:]

    def sm_cleanup(self):
        self.lib.sm_cleanup()

    # Used for most of the things, like searching etc
    def sm_exec_cmd(self, cmd, get_output = False):
        if get_output:
            with tempfile.TemporaryFile() as directed_file:
                backup_stdout_fileno = os.dup(sys.stdout.fileno())
                os.dup2(directed_file.fileno(), sys.stdout.fileno())

                self.lib.sm_backend_exec_cmd(ctypes.c_char_p(cmd.encode("ascii")))

                os.dup2(backup_stdout_fileno, sys.stdout.fileno())
                os.close(backup_stdout_fileno)
                directed_file.seek(0)
                return directed_file.read()
        else:
            self.lib.sm_backend_exec_cmd(ctypes.c_char_p(cmd.encode("ascii")))
    def sm_get_num_matches(self):
        return self.lib.sm_get_num_matches()

    def sm_get_version(self):
        return self.lib.sm_get_version()

    def sm_get_scan_progress(self):
        return self.lib.sm_get_scan_progress()

    def sm_set_stop_flag(self, stop_flag):
        self.lib.sm_set_stop_flag(stop_flag)

    def sm_process_is_dead(self, pid):
        self.lib.sm_process_is_dead(pid)

    """
        @param string the string that's returned by libscanmem
        @returns a dictionary with the key as the n:th match, and value the rest of the structure that's returned
    """
    def parse_string(self, string):
        # based on information from the scanmem source, the format for a line from scanmem is:
        # n     address       region id* offset   region type   value   type(s)
        #[4425] 7fd3ef3cf488, 31 +       8cf488,  misc,         12,     [I8 ]
        # * region id = line number in /proc/pid/maps
        # region id can later be probably be used to get like "executable + offset"
        if string == None:
            return None
        ret = dict()
        string = string.decode("utf-8").splitlines()
        if string == None:
            return None
        line_match = re.compile(r"^\[ *(\d+)\] +([\da-f]+), +\d+ \+ +([\da-f]+), +(\w+), (.*), +\[([\w ]+)\]$")
        for row in string:
            (n, address, offset, region_type, value, t) = line_match.match(row).groups()
            ret[n] = {
                "address": address,
                "offset": offset,
                "region_type": region_type,
                "value": value,
                "type": t
            }
