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
import gdb, pickle, sys, re, struct, ctypes, os, shelve, importlib
from capstone import Cs, CsError, CS_ARCH_X86, CS_MODE_32, CS_MODE_64
from collections import OrderedDict

# This is some retarded hack
gdbvalue = gdb.parse_and_eval("$PINCE_PATH")
PINCE_PATH = gdbvalue.string()
sys.path.append(PINCE_PATH)  # Adds the PINCE directory to PYTHONPATH to import libraries from PINCE

from libpince.gdb_python_scripts import gdbutils
from libpince import utils, typedefs, regexes
from libpince.utils import logger

importlib.reload(gdbutils)
pid = gdbutils.pid
recv_file = utils.get_from_pince_file(pid)
send_file = utils.get_to_pince_file(pid)
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
        logger.debug(contents_send)
        send_to_pince(contents_send)


class HandleSignals(gdb.Command):
    def __init__(self):
        super().__init__("pince-handle-signals", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        signal_data = receive_from_pince()
        for signal, stop, pass_to_program in signal_data:
            stop = "stop print" if stop else "nostop noprint"
            pass_to_program = "pass" if pass_to_program else "nopass"
            gdb.execute(f"handle {signal} {stop} {pass_to_program}", from_tty, to_string=True)


class ParseAndEval(gdb.Command):
    def __init__(self):
        super(ParseAndEval, self).__init__("pince-parse-and-eval", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        expression, cast = receive_from_pince()
        try:
            value = gdb.parse_and_eval(expression)
            parsed_value = cast(value)
        except Exception:
            logger.exception(f"An exception occurred while trying to parse expression '{expression}' and cast to type '{str(cast)}'")
            parsed_value = None
        send_to_pince(parsed_value)


class ReadRegisters(gdb.Command):
    def __init__(self):
        super(ReadRegisters, self).__init__("pince-read-registers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        registers = gdbutils.get_general_registers()
        for key, value in registers.items():
            registers[key] = utils.upper_hex(value)
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
            logger.error(f"Cannot get the value of ${sp_register}")
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

            if arg == "from-base-pointer":
                stack_register = "rbp"
            else:
                stack_register = "rsp"
        else:
            chunk_size = 4
            int_format = "I"

            if arg == "from-base-pointer":
                stack_register = "ebp"
            else:
                stack_register = "esp"

        sp_address = gdbutils.examine_expression(f"${stack_register}").address
        if not sp_address:
            logger.error(f"Cannot get the value of ${stack_register}")
            send_to_pince(stack_info_list)
            return
        sp_address = int(sp_address, 16)
        with open(gdbutils.mem_file, "rb") as FILE:
            try:
                old_position = FILE.seek(sp_address)
            except (OSError, ValueError):
                logger.exception(f"Cannot accesss the memory at {hex(sp_address)}")
                send_to_pince(stack_info_list)
                return
            for index in range(int(4096 / chunk_size)):
                current_offset = chunk_size * index
                stack_indicator = (
                    hex(sp_address + current_offset) + "(" + stack_register + "+" + hex(current_offset) + ")"
                )
                try:
                    FILE.seek(old_position)
                    read = FILE.read(chunk_size)
                except (OSError, ValueError):
                    logger.exception(f"Can't access the stack after address {stack_indicator}")
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
            logger.error(f"Frame {frame_number} doesn't exist")
            frame_info = None
        send_to_pince(frame_info)


class GetTrackWatchpointInfo(gdb.Command):
    def __init__(self):
        super(GetTrackWatchpointInfo, self).__init__("pince-get-track-watchpoint-info", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        breakpoints = arg
        current_pc = str(gdb.parse_and_eval("$pc"))
        current_pc_addr = utils.extract_hex_address(current_pc)
        # Sometimes GDB will return a decimal address str instead of a hex str
        if current_pc_addr is None:
            result = regexes.decimal_number.search(current_pc)
            if result:
                current_pc_addr = result.group(0)
            else:
                logger.error("Failed to grab address from $pc")
                return
        current_pc_int = int(current_pc_addr, 0)
        try:
            disas_output = gdb.execute("disas $pc-30,$pc", to_string=True)

            # Just before the line "End of assembler dump"
            last_instruction = disas_output.splitlines()[-2]
            previous_pc_address = utils.extract_hex_address(last_instruction)
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
        track_watchpoint_dict[breakpoints][current_pc_int] = [
            count,
            previous_pc_address,
            register_info,
            float_info,
            disas_info,
        ]
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
        utils.change_trace_status(pid, typedefs.TRACE_STATUS.TRACING)


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
            disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
        else:
            disassembler = Cs(CS_ARCH_X86, CS_MODE_32)
        disassembler.skipdata = True
        referenced_strings_dict = shelve.open(utils.get_referenced_strings_file(pid), writeback=True)
        referenced_jumps_dict = shelve.open(utils.get_referenced_jumps_file(pid), writeback=True)
        referenced_calls_dict = shelve.open(utils.get_referenced_calls_file(pid), writeback=True)
        region_list, discard_invalid_strings = receive_from_pince()
        dissect_code_status_file = utils.get_dissect_code_status_file(pid)
        region_count = len(region_list)
        self.memory = open(gdbutils.mem_file, "rb")
        ref_str_count = len(referenced_strings_dict)
        ref_jmp_count = len(referenced_jumps_dict)
        ref_call_count = len(referenced_calls_dict)
        for region_index, (start_addr, end_addr) in enumerate(region_list):
            region_info = start_addr + "-" + end_addr, str(region_index + 1) + " / " + str(region_count)
            start_addr = int(start_addr, 16)  # Becomes address of the last disassembled instruction later on
            end_addr = int(end_addr, 16)
            status_info = region_info + (
                hex(start_addr)[2:] + "-" + hex(end_addr)[2:],
                ref_str_count,
                ref_jmp_count,
                ref_call_count,
            )
            pickle.dump(status_info, open(dissect_code_status_file, "wb"))
            try:
                self.memory.seek(start_addr)
            except (OSError, ValueError):
                break
            buffer_size = end_addr - start_addr
            code = self.memory.read(buffer_size)
            try:
                disas_data = disassembler.disasm_lite(code, start_addr)
            except CsError:
                logger.exception("An exception occurred while trying to dissect code")
                break
            for instruction_addr, _, mnemonic, operands in disas_data:
                instruction = f"{mnemonic} {operands}" if operands != "" else mnemonic
                found = regexes.dissect_code_valid_address.search(instruction)
                if not found:
                    continue
                if instruction.startswith("j") or instruction.startswith("loop"):
                    referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                    referenced_address_int = int(referenced_address_str, 16)
                    if self.is_memory_valid(referenced_address_int):
                        instruction_only = regexes.alphanumerics.search(instruction).group(0).casefold()
                        try:
                            referenced_jumps_dict[referenced_address_str][instruction_addr] = instruction_only
                        except KeyError:
                            referenced_jumps_dict[referenced_address_str] = {}
                            referenced_jumps_dict[referenced_address_str][instruction_addr] = instruction_only
                            ref_jmp_count += 1
                elif instruction.startswith("call"):
                    referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                    referenced_address_int = int(referenced_address_str, 16)
                    if self.is_memory_valid(referenced_address_int):
                        try:
                            referenced_calls_dict[referenced_address_str].add(instruction_addr)
                        except KeyError:
                            referenced_calls_dict[referenced_address_str] = set()
                            referenced_calls_dict[referenced_address_str].add(instruction_addr)
                            ref_call_count += 1
                else:
                    referenced_address_str = regexes.hex_number.search(found.group(0)).group(0)
                    referenced_address_int = int(referenced_address_str, 16)
                    if self.is_memory_valid(referenced_address_int, discard_invalid_strings):
                        try:
                            referenced_strings_dict[referenced_address_str].add(instruction_addr)
                        except KeyError:
                            referenced_strings_dict[referenced_address_str] = set()
                            referenced_strings_dict[referenced_address_str].add(instruction_addr)
                            ref_str_count += 1
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
            except Exception:
                logger.exception(f"An exception occurred while trying to compile the given regex '{searched_str}'")
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

        regions = utils.get_region_dict(pid)
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
        except Exception:
            logger.exception("An exception occurred while trying to search functions")
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
HandleSignals()
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
DissectCode()
SearchReferencedCalls()
ExamineExpressions()
SearchFunctions()
