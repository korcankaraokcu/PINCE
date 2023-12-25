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
import gdb, pickle, json, sys, re, struct, ctypes, os, shelve, distorm3
from collections import OrderedDict

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libpince.gdb_python_scripts import gdbutils
from libpince import utils, typedefs, regexes

inferior = gdb.selected_inferior()
pid = inferior.pid
recv_file = utils.get_ipc_from_pince_file(pid)
send_file = utils.get_ipc_to_pince_file(pid)

lib = None

# Format of info_list: [count, previous_pc_address, register_info, float_info, disas_info]
# Format of watchpoint_dict: {address1:info_list1, address2:info_list2, ...}
# Format of watchpoint_numbers: str([1,2,3,4,..])
# Format: {watchpoint_numbers1:watchpoint_dict1, watchpoint_numbers2:track_watchpoint_dict2, ...}
track_watchpoint_dict = {}

# Format of expression_info_dict: {value1:count1, value2:count2, ...}
# Format of register_expression_dict: {expression1:expression_info_dict1, expression2:expression_info_dict2, ...}
# Format: {breakpoint_number1:register_expression_dict1, breakpoint_number2:register_expression_dict2, ...}
track_breakpoint_dict = {}


def receive_from_pince():
    return pickle.load(open(recv_file, "rb"))


def send_to_pince(contents_send):
    pickle.dump(contents_send, open(send_file, "wb"))


gdbutils.gdbinit()


class IgnoreErrors(gdb.Command):
    def __init__(self):
        super(IgnoreErrors, self).__init__("ignore-errors", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            gdb.execute(arg, from_tty)
        except:
            pass


class CLIOutput(gdb.Command):
    def __init__(self):
        super(CLIOutput, self).__init__("cli-output", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        try:
            contents_send = gdb.execute(arg, from_tty, to_string=True)
        except Exception as e:
            contents_send = str(e)
        print(contents_send)
        send_to_pince(contents_send)


class ParseAndEval(gdb.Command):
    def __init__(self):
        super(ParseAndEval, self).__init__("pince-parse-and-eval", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        expression, cast = receive_from_pince()
        try:
            value = gdb.parse_and_eval(expression)
            parsed_value = cast(value)
        except Exception as e:
            print(e)
            print("Expression: " + expression)
            print("Cast type: " + str(cast))
            parsed_value = None
        send_to_pince(parsed_value)


class ReadRegisters(gdb.Command):
    def __init__(self):
        super(ReadRegisters, self).__init__("pince-read-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        registers = gdbutils.get_general_registers()
        registers.update(gdbutils.get_flag_registers())
        registers.update(gdbutils.get_segment_registers())
        send_to_pince(registers)


class ReadFloatRegisters(gdb.Command):
    def __init__(self):
        super(ReadFloatRegisters, self).__init__("pince-read-float-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        send_to_pince(gdbutils.get_float_registers())


class GetStackTraceInfo(gdb.Command):
    def __init__(self):
        super(GetStackTraceInfo, self).__init__("pince-get-stack-trace-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        stacktrace_info_list = []
        if gdbutils.current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            sp_register = "rsp"
        else:
            sp_register = "esp"
        stack_pointer = gdbutils.examine_expression(f"${sp_register}").address
        if not stack_pointer:
            print(f"Cannot get the value of ${sp_register}")
            send_to_pince(stacktrace_info_list)
            return
        stack_pointer = int(stack_pointer, 16)
        result = gdb.execute("bt", from_tty, to_string=True)
        max_frame = regexes.max_frame_count.findall(result)[-1]

        # +1 because frame numbers start from 0
        for item in range(int(max_frame) + 1):
            try:
                result = gdb.execute(f"info frame {item}", from_tty, to_string=True)
            except:
                break
            frame_address = regexes.frame_address.search(result).group(1)
            difference = hex(int(frame_address, 16) - stack_pointer)
            frame_address_with_difference = frame_address + "(" + sp_register + "+" + difference + ")"
            return_address = regexes.return_address.search(result)
            if return_address:
                return_address_with_info = gdbutils.examine_expression(return_address.group(1)).all
            else:
                return_address_with_info = "<>"
            stacktrace_info_list.append([return_address_with_info, frame_address_with_difference])
        send_to_pince(stacktrace_info_list)


class GetStackInfo(gdb.Command):
    def __init__(self):
        super(GetStackInfo, self).__init__("pince-get-stack-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        stack_info_list = []
        if gdbutils.current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            chunk_size = 8
            int_format = "Q"
            sp_register = "rsp"
        else:
            chunk_size = 4
            int_format = "I"
            sp_register = "esp"
        sp_address = gdbutils.examine_expression(f"${sp_register}").address
        if not sp_address:
            print(f"Cannot get the value of ${sp_register}")
            send_to_pince(stack_info_list)
            return
        sp_address = int(sp_address, 16)
        with open(gdbutils.mem_file, "rb") as FILE:
            try:
                old_position = FILE.seek(sp_address)
            except (OSError, ValueError):
                print(f"Cannot accesss the memory at {hex(sp_address)}")
                send_to_pince(stack_info_list)
                return
            for index in range(int(4096 / chunk_size)):
                current_offset = chunk_size * index
                stack_indicator = hex(sp_address + current_offset) + "(" + sp_register + "+" + hex(current_offset) + ")"
                try:
                    FILE.seek(old_position)
                    read = FILE.read(chunk_size)
                except (OSError, ValueError):
                    print("Can't access the stack after address " + stack_indicator)
                    break
                old_position = FILE.tell()
                int_addr = struct.unpack_from(int_format, read)[0]
                hex_repr = hex(int_addr)
                try:
                    FILE.seek(int_addr)
                    read_pointer = FILE.read(20)
                except (OSError, ValueError):
                    pointer_data = ""
                else:
                    symbol = gdbutils.examine_expression(hex_repr).symbol
                    if not symbol:
                        pointer_data = "(str)" + read_pointer.decode("utf-8", "ignore")
                    else:
                        pointer_data = "(ptr)" + symbol
                stack_info_list.append([stack_indicator, hex_repr, pointer_data])
        send_to_pince(stack_info_list)


class GetFrameReturnAddresses(gdb.Command):
    def __init__(self):
        super(GetFrameReturnAddresses, self).__init__("pince-get-frame-return-addresses", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        return_address_list = []
        result = gdb.execute("bt", from_tty, to_string=True)
        max_frame = regexes.max_frame_count.findall(result)[-1]

        # +1 because frame numbers start from 0
        for item in range(int(max_frame) + 1):
            try:
                result = gdb.execute(f"info frame {item}", from_tty, to_string=True)
            except:
                break
            return_address = regexes.return_address.search(result)
            if return_address:
                return_address_with_info = gdbutils.examine_expression(return_address.group(1)).all
            else:
                return_address_with_info = "<>"
            return_address_list.append(return_address_with_info)
        send_to_pince(return_address_list)


class GetFrameInfo(gdb.Command):
    def __init__(self):
        super(GetFrameInfo, self).__init__("pince-get-frame-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        frame_number = receive_from_pince()
        result = gdb.execute("bt", from_tty, to_string=True)
        max_frame = regexes.max_frame_count.findall(result)[-1]
        if 0 <= int(frame_number) <= int(max_frame):
            frame_info = gdb.execute("info frame " + frame_number, from_tty, to_string=True)
        else:
            print("Frame " + frame_number + " doesn't exist")
            frame_info = None
        send_to_pince(frame_info)


class GetTrackWatchpointInfo(gdb.Command):
    def __init__(self):
        super(GetTrackWatchpointInfo, self).__init__("pince-get-track-watchpoint-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        breakpoints = arg
        current_pc_int = int(utils.extract_address(str(gdb.parse_and_eval("$pc"))), 16)
        try:
            disas_output = gdb.execute("disas $pc-30,$pc", to_string=True)

            # Just before the line "End of assembler dump"
            last_instruction = disas_output.splitlines()[-2]
            previous_pc_address = utils.extract_address(last_instruction)
        except:
            previous_pc_address = hex(current_pc_int)
        global track_watchpoint_dict
        try:
            count = track_watchpoint_dict[breakpoints][current_pc_int][0] + 1
        except KeyError:
            if breakpoints not in track_watchpoint_dict:
                track_watchpoint_dict[breakpoints] = OrderedDict()
            count = 1
        register_info = gdbutils.get_general_registers()
        register_info.update(gdbutils.get_flag_registers())
        register_info.update(gdbutils.get_segment_registers())
        float_info = gdbutils.get_float_registers()
        disas_info = gdb.execute("disas " + previous_pc_address + ",+40", to_string=True).replace("=>", "  ")
        track_watchpoint_dict[breakpoints][current_pc_int] = [count, previous_pc_address, register_info, float_info,
                                                              disas_info]
        track_watchpoint_file = utils.get_track_watchpoint_file(pid, breakpoints)
        pickle.dump(track_watchpoint_dict[breakpoints], open(track_watchpoint_file, "wb"))


class GetTrackBreakpointInfo(gdb.Command):
    def __init__(self):
        super(GetTrackBreakpointInfo, self).__init__("pince-get-track-breakpoint-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        arg_list = arg.split(",")
        breakpoint_number = arg_list.pop()
        register_expressions = arg_list
        global track_breakpoint_dict
        if not breakpoint_number in track_breakpoint_dict:
            track_breakpoint_dict[breakpoint_number] = OrderedDict()
        for register_expression in register_expressions:
            if not register_expression:
                continue
            if not register_expression in track_breakpoint_dict[breakpoint_number]:
                track_breakpoint_dict[breakpoint_number][register_expression] = OrderedDict()
            try:
                address = gdbutils.examine_expression(register_expression).address
            except:
                address = None
            if address:
                if address not in track_breakpoint_dict[breakpoint_number][register_expression]:
                    track_breakpoint_dict[breakpoint_number][register_expression][address] = 1
                else:
                    track_breakpoint_dict[breakpoint_number][register_expression][address] += 1
        track_breakpoint_file = utils.get_track_breakpoint_file(pid, breakpoint_number)
        pickle.dump(track_breakpoint_dict[breakpoint_number], open(track_breakpoint_file, "wb"))


class PhaseOut(gdb.Command):
    def __init__(self):
        super(PhaseOut, self).__init__("phase-out", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        gdb.execute("detach")
        gdb.execute("echo Successfully detached from the target pid: " + str(pid))


class PhaseIn(gdb.Command):
    def __init__(self):
        super(PhaseIn, self).__init__("phase-in", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        gdb.execute("attach " + str(pid))
        gdb.execute("echo Successfully attached back to the target pid: " + str(pid))


class TraceInstructions(gdb.Command):
    def __init__(self):
        super(TraceInstructions, self).__init__("pince-trace-instructions", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        (breakpoint, max_trace_count, stop_condition, step_mode, stop_after_trace, collect_general_registers,
         collect_flag_registers, collect_segment_registers, collect_float_registers) = eval(arg)
        gdb.execute("delete " + breakpoint)
        trace_status_file = utils.get_trace_instructions_status_file(pid, breakpoint)

        # The reason we don't use a tree class is to make the tree json-compatible
        # tree format-->[node1, node2, node3, ...]
        # node-->[(line_info, register_dict), parent_index, child_index_list]
        tree = []
        current_index = 0  # Avoid calling len()
        current_root_index = 0
        root_index = 0

        # Root always be an empty node, it's up to you to use or delete it
        tree.append([("", None), None, []])
        for x in range(max_trace_count):
            try:
                output = pickle.load(open(trace_status_file, "rb"))
                if output[0] == typedefs.TRACE_STATUS.STATUS_CANCELED:
                    break
            except:
                pass
            line_info = gdb.execute("x/i $pc", to_string=True).splitlines()[0].split(maxsplit=1)[1]
            collect_dict = OrderedDict()
            if collect_general_registers:
                collect_dict.update(gdbutils.get_general_registers())
            if collect_flag_registers:
                collect_dict.update(gdbutils.get_flag_registers())
            if collect_segment_registers:
                collect_dict.update(gdbutils.get_segment_registers())
            if collect_float_registers:
                collect_dict.update(gdbutils.get_float_registers())
            current_index += 1
            tree.append([(line_info, collect_dict), current_root_index, []])
            tree[current_root_index][2].append(current_index)  # Add a child
            status_info = (typedefs.TRACE_STATUS.STATUS_TRACING,
                           line_info + "\n(" + str(x + 1) + "/" + str(max_trace_count) + ")")
            pickle.dump(status_info, open(trace_status_file, "wb"))
            if regexes.trace_instructions_ret.search(line_info):
                if tree[current_root_index][1] is None:  # If no parents exist
                    current_index += 1
                    tree.append([("", None), None, [current_root_index]])
                    tree[current_root_index][1] = current_index  # Set new parent
                    current_root_index = current_index  # current_node=current_node.parent
                    root_index = current_root_index  # set new root
                else:
                    current_root_index = tree[current_root_index][1]  # current_node=current_node.parent
            elif step_mode == typedefs.STEP_MODE.SINGLE_STEP:
                if regexes.trace_instructions_call.search(line_info):
                    current_root_index = current_index
            if stop_condition:
                try:
                    if str(gdb.parse_and_eval(stop_condition)) == "1":
                        break
                except:
                    pass
            if step_mode == typedefs.STEP_MODE.SINGLE_STEP:
                gdb.execute("stepi", to_string=True)
            elif step_mode == typedefs.STEP_MODE.STEP_OVER:
                gdb.execute("nexti", to_string=True)
        status_info = (typedefs.TRACE_STATUS.STATUS_PROCESSING, "")
        pickle.dump(status_info, open(trace_status_file, "wb"))
        trace_instructions_file = utils.get_trace_instructions_file(pid, breakpoint)
        json.dump((tree, root_index), open(trace_instructions_file, "w"))
        status_info = (typedefs.TRACE_STATUS.STATUS_FINISHED, "")
        pickle.dump(status_info, open(trace_status_file, "wb"))
        if not stop_after_trace:
            gdb.execute("c&")


class InitSoFile(gdb.Command):
    """Usage: pince-init-so-file so_file_path"""

    def __init__(self):
        super(InitSoFile, self).__init__("pince-init-so-file", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        global lib
        lib = ctypes.CDLL(arg)
        print("Successfully loaded so file from " + arg)


class GetSoFileInformation(gdb.Command):
    def __init__(self):
        super(GetSoFileInformation, self).__init__("pince-get-so-file-information", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        if not lib:
            print("so file isn't initialized, use the command pince-init-so-file")
            return
        print("Loaded so file:\n" + str(lib) + "\n")
        print("Available resources:")
        print(os.system("nm -D --defined-only " + lib._name))


class ExecuteFromSoFile(gdb.Command):
    """Usage: pince-execute-from-so-file lib.func(params)"""

    def __init__(self):
        super(ExecuteFromSoFile, self).__init__("pince-execute-from-so-file", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        global lib
        gdb.execute("p " + str(eval(arg.strip())))


class DissectCode(gdb.Command):
    def __init__(self):
        super(DissectCode, self).__init__("pince-dissect-code", gdb.COMMAND_USER)

    def is_memory_valid(self, int_address, discard_invalid_strings=False):
        try:
            self.memory.seek(int_address)
        except (OSError, ValueError):
            return False  # vsyscall is ignored if vDSO is present, so we can safely ignore vsyscall
        try:
            if discard_invalid_strings:
                data_read = self.memory.read(32)
                if data_read.startswith(b"\0"):
                    return False
                data_read = data_read.split(b"\0", maxsplit=1)[0]
                data_read.decode("utf-8")
            else:
                self.memory.read(1)
        except:
            return False
        return True

    def invoke(self, arg, from_tty):
        if gdbutils.current_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            disas_option = distorm3.Decode64Bits
        else:
            disas_option = distorm3.Decode32Bits
        referenced_strings_dict = shelve.open(utils.get_referenced_strings_file(pid), writeback=True)
        referenced_jumps_dict = shelve.open(utils.get_referenced_jumps_file(pid), writeback=True)
        referenced_calls_dict = shelve.open(utils.get_referenced_calls_file(pid), writeback=True)
        region_list, discard_invalid_strings = receive_from_pince()
        dissect_code_status_file = utils.get_dissect_code_status_file(pid)
        region_count = len(region_list)
        self.memory = open(gdbutils.mem_file, "rb")

        # Has the best record of 111 secs. Tested on Torchlight 2 with Intel i7-4702MQ CPU and 8GB RAM
        buffer = 0x10000  # Aligned to 2**16
        ref_str_count = len(referenced_strings_dict)
        ref_jmp_count = len(referenced_jumps_dict)
        ref_call_count = len(referenced_calls_dict)
        for region_index, (start_addr, end_addr) in enumerate(region_list):
            region_info = start_addr+"-"+end_addr, str(region_index + 1) + " / " + str(region_count)
            start_addr = int(start_addr, 16)  # Becomes address of the last disassembled instruction later on
            end_addr = int(end_addr, 16)
            region_finished = False
            while not region_finished:
                remaining_space = end_addr - start_addr
                if remaining_space < buffer:
                    offset = remaining_space
                    region_finished = True
                else:
                    offset = buffer
                status_info = region_info + (hex(start_addr)[2:] + "-" + hex(start_addr + offset)[2:],
                                             ref_str_count, ref_jmp_count, ref_call_count)
                pickle.dump(status_info, open(dissect_code_status_file, "wb"))
                try:
                    self.memory.seek(start_addr)
                except (OSError, ValueError):
                    break
                code = self.memory.read(offset)
                disas_data = distorm3.Decode(start_addr, code, disas_option)
                if not region_finished:
                    last_disas_addr = disas_data[-4][0]
                    for index in range(4):
                        del disas_data[-1]  # Get rid of last 4 instructions to ensure correct bytecode translation
                else:
                    last_disas_addr = 0
                for (instruction_offset, size, instruction, hexdump) in disas_data:
                    if isinstance(instruction, bytes):
                        instruction = instruction.decode()
                    if instruction.startswith("J") or instruction.startswith("LOOP"):
                        found = regexes.dissect_code_valid_address.search(instruction)
                        if found:
                            referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                            referenced_address_int = int(referenced_address_str, 16)
                            if self.is_memory_valid(referenced_address_int):
                                instruction_only = regexes.alphanumerics.search(instruction).group(0).casefold()
                                try:
                                    referenced_jumps_dict[referenced_address_str][instruction_offset] = instruction_only
                                except KeyError:
                                    referenced_jumps_dict[referenced_address_str] = {}
                                    referenced_jumps_dict[referenced_address_str][instruction_offset] = instruction_only
                                    ref_jmp_count += 1
                    elif instruction.startswith("CALL"):
                        found = regexes.dissect_code_valid_address.search(instruction)
                        if found:
                            referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                            referenced_address_int = int(referenced_address_str, 16)
                            if self.is_memory_valid(referenced_address_int):
                                try:
                                    referenced_calls_dict[referenced_address_str].add(instruction_offset)
                                except KeyError:
                                    referenced_calls_dict[referenced_address_str] = set()
                                    referenced_calls_dict[referenced_address_str].add(instruction_offset)
                                    ref_call_count += 1
                    else:
                        found = regexes.dissect_code_valid_address.search(instruction)
                        if found:
                            referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                            referenced_address_int = int(referenced_address_str, 16)
                            if self.is_memory_valid(referenced_address_int, discard_invalid_strings):
                                try:
                                    referenced_strings_dict[referenced_address_str].add(instruction_offset)
                                except KeyError:
                                    referenced_strings_dict[referenced_address_str] = set()
                                    referenced_strings_dict[referenced_address_str].add(instruction_offset)
                                    ref_str_count += 1
                start_addr = last_disas_addr
        self.memory.close()


class SearchReferencedCalls(gdb.Command):
    def __init__(self):
        super(SearchReferencedCalls, self).__init__("pince-search-referenced-calls", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        searched_str, case_sensitive, enable_regex = eval(arg)
        if enable_regex:
            try:
                if case_sensitive:
                    regex = re.compile(searched_str)
                else:
                    regex = re.compile(searched_str, re.IGNORECASE)
            except Exception as e:
                print("An exception occurred while trying to compile the given regex\n", str(e))
                return
        str_dict = shelve.open(utils.get_referenced_calls_file(pid), "r")
        returned_list = []
        for index, item in enumerate(str_dict):
            symbol = gdbutils.examine_expression(item).all
            if not symbol:
                continue
            if enable_regex:
                if not regex.search(symbol):
                    continue
            else:
                if case_sensitive:
                    if symbol.find(searched_str) == -1:
                        continue
                else:
                    if symbol.lower().find(searched_str.lower()) == -1:
                        continue
            returned_list.append((symbol, len(str_dict[item])))
        str_dict.close()
        send_to_pince(returned_list)


class ExamineExpressions(gdb.Command):
    def __init__(self):
        super(ExamineExpressions, self).__init__("pince-examine-expressions", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        data_read_list = []
        contents_recv = receive_from_pince()
        # contents_recv format: [expression1, expression2, ...]

        regions = utils.get_regions(pid)
        for expression in contents_recv:
            result_tuple = gdbutils.examine_expression(expression, regions)
            data_read_list.append(result_tuple)
        send_to_pince(data_read_list)


class SearchFunctions(gdb.Command):
    def __init__(self):
        super(SearchFunctions, self).__init__("pince-search-functions", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        expression, case_sensitive = receive_from_pince()
        function_list = []
        if case_sensitive:
            gdb.execute("set case-sensitive on")
        else:
            gdb.execute("set case-sensitive off")
        try:
            output = gdb.execute("info functions " + expression, to_string=True)
        except Exception as e:
            print("An exception occurred while trying to search functions:\n", e)
            output = ""
        gdb.execute("set case-sensitive auto")
        for line in output.splitlines():
            non_debugging = regexes.info_functions_non_debugging.search(line)
            if non_debugging:
                function_list.append((non_debugging.group(1), non_debugging.group(2)))
            else:
                if line.endswith(";"):  # defined
                    function_list.append((None, line[:-1]))
        send_to_pince(function_list)


IgnoreErrors()
CLIOutput()
ParseAndEval()
ReadRegisters()
ReadFloatRegisters()
GetStackTraceInfo()
GetStackInfo()
GetFrameReturnAddresses()
GetFrameInfo()
GetTrackWatchpointInfo()
GetTrackBreakpointInfo()
PhaseOut()
PhaseIn()
TraceInstructions()
InitSoFile()
GetSoFileInformation()
ExecuteFromSoFile()
DissectCode()
SearchReferencedCalls()
ExamineExpressions()
SearchFunctions()
