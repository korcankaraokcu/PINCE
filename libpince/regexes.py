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
from re import compile, VERBOSE, MULTILINE

# The comments near regular expressions shows the expected gdb output, hope it helps to the future developers

# --------------------------------------------debugcore----------------------------------------------------------------

gdb_state_observe = compile(r"^\*(stopped.+)|^\*(running)", MULTILINE)
gdb_error = compile(r"\^error")
hex_plain = compile(r"[0-9a-fA-F]+")
hex_number = compile(r"0x" + hex_plain.pattern)
hex_number_grouped = compile(r"(" + hex_number.pattern + r")")
address_with_symbol = compile(r"(" + hex_number_grouped.pattern + r"\s*(<.+>)?)")  # 0x7f3067f1174d <poll+45>\n
thread_info = compile(r"\*\s+\d+\s+(.*)\\n")
inferior_pid = compile(r"process\s+(\d+)")
hw_breakpoint_count = compile(r"(hw|read|acc)")
breakpoint_size = compile(r"char\[(\d+)\]")
breakpoint_created = compile(r"breakpoint-created")
breakpoint_number = compile(r"(?:number|bkptno)=\"(\d+)\"")
convenience_variable = compile(r'"(\$\d+)\s+=\s+(.*)"')  # "$26 = 3"
entry_point = compile(r"Entry\s+point:\s+" + hex_number_grouped.pattern)
# The command will always start with the word "source", check debugcore.send_command function for the cause
gdb_command_source = lambda command_file: compile(r"&\".*source\s" + command_file + r"\\n\"")  # &"command\n"
# 0x00007fd81d4c7400 <__printf+0>:\t48 81 ec d8 00 00 00\tsub    rsp,0xd8\n
disassemble_output = compile(r"""
    ([0-9a-fA-F]+.*)\\t                     # Address with symbol
    (.*?[0-9a-fA-F]{2})\s*\\t               # Bytes, ignore padding
    (.+)\\n                                 # Opcode
""", VERBOSE)
info_functions_non_debugging = compile(hex_number_grouped.pattern + r"\s+(.*)")
max_completions_reached = compile(r"\*\*\*\s+List\s+may\s+be\s+truncated,\s+max-completions\s+reached\.\s+\*\*\*")

# --------------------------------------------utils------------------------------------------------------------------

instruction_follow = compile(r"(j|call|loop).*\s+" + hex_number_grouped.pattern)
docstring_variable = compile(r"(\w+)\s*=")
docstring_function_or_variable = compile(r"def\s+(\w+)|" + docstring_variable.pattern)
whitespaces = compile(r"\s+")
ps = compile(r"""
    \s+(\d+)\s+                             # PID
    (\S+)\s+                                # Username
    (.*)$                                   # Process name
""", VERBOSE)
maps = compile(r"""
    ([0-9a-f]+)-([0-9a-f]+)\s+              # Address (start-end)
    (\S+)\s+                                # Permissions
    ([0-9a-f]+)\s+                          # Map offset
    (\S+)\s+                                # Device node
    (\d+)\s+                                # Inode
    (.*)$                                   # Pathname
""", VERBOSE)

# --------------------------------------------guiutils------------------------------------------------------------------

reference_mark = compile(r"\{\d*\}")
float_number = compile(r"-?[0-9]+[.,]?[0-9]*")
bytearray_input = compile(r"^(([A-Fa-f0-9?]{2} +)+)$")
decimal_number = compile(r"-?\d+")
hex_number_gui = compile(r"-?(0x)?[0-9a-fA-F]*") # contains optional 0x prefix

# --------------------------------------------gdbextensions------------------------------------------------------

max_frame_count = compile(r"#(\d+)\s+.*")
frame_address = compile(r"frame\s+at\s+" + hex_number_grouped.pattern)  # frame at 0x7ffe1e989950
return_address = compile(r"saved.*=\s+" + hex_number_grouped.pattern)  # saved rip = 0x7f633a853fe4
trace_instructions_ret = compile(r":\s+ret")  # 0x7f71a4dc5ff8 <poll+72>:	ret
trace_instructions_call = compile(r":\s+call")  # 0x7f71a4dc5fe4 <poll+52>:	call   0x7f71a4de1100
dissect_code_valid_address = compile(r"(\s+|\[|,)" + hex_number.pattern + r"(\s+|\]|,|$)")
alphanumerics = compile(r"\w+")
file_with_extension = compile(r".+?\.\w+")
offset_expression = compile(r"[/*+\-][0-9a-fA-FxX/*+\-\[\]]+$")
index = compile(r"\[(\d+)\]$")
