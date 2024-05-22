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
from threading import Lock, Thread, Condition
from time import sleep, time
from collections import OrderedDict, defaultdict
import pexpect, os, sys, ctypes, pickle, shelve, re, struct, io, traceback
from . import utils, typedefs, regexes

self_pid = os.getpid()
libc = ctypes.CDLL("libc.so.6")
system_endianness = typedefs.ENDIANNESS.LITTLE if sys.byteorder == "little" else typedefs.ENDIANNESS.BIG

#:tag:GDBInformation
#:doc:
# A boolean value. True if gdb is initialized, False if not
gdb_initialized = False

#:tag:InferiorInformation
#:doc:
# An integer. Can be a member of typedefs.INFERIOR_ARCH
inferior_arch = int

#:tag:InferiorInformation
#:doc:
# An integer. Can be a member of typedefs.INFERIOR_STATUS
inferior_status = -1

#:tag:InferiorInformation
#:doc:
# An integer. PID of the current attached/created process
currentpid = -1

#:tag:GDBInformation
#:doc:
# An integer. Can be a member of typedefs.STOP_REASON
stop_reason = int

#:tag:GDBInformation
#:doc:
# A dictionary. Holds breakpoint numbers and what to do on hit
# Format: {bp_num1:on_hit1, bp_num2:on_hit2, ...}
breakpoint_on_hit_dict = {}

#:tag:GDBInformation
#:doc:
# A dictionary. Holds address and aob of instructions that were nop'ed out
# Format: {address1:orig_instruction1_aob, address2:orig_instruction2_aob, ...}
modified_instructions_dict = {}

#:tag:GDBInformation
#:doc:
# If an action such as deletion or condition modification happens in one of the breakpoints in a list, others in the
# same list will get affected as well
# Format: [[[address1, size1], [address2, size2], ...], [[address1, size1], ...], ...]
chained_breakpoints = []

child = object  # this object will be used with pexpect operations

#:tag:ConditionsLocks
#:doc:
# This Lock is used by the function send_command to ensure synchronous execution
lock_send_command = Lock()

#:tag:ConditionsLocks
#:doc:
# This condition is notified whenever status of the inferior changes
# Use the variable inferior_status to get information about inferior's status
# See PINCE's CheckInferiorStatus class for an example
status_changed_condition = Condition()

#:tag:ConditionsLocks
#:doc:
# This condition is notified if the current inferior gets terminated
# See PINCE's AwaitProcessExit class for an example
process_exited_condition = Condition()

#:tag:ConditionsLocks
#:doc:
# This condition is notified if gdb starts to wait for the prompt output
# See function send_command for an example
gdb_waiting_for_prompt_condition = Condition()

#:tag:GDBInformation
#:doc:
# A string. Stores the output of the last command
gdb_output = ""

#:tag:GDBInformation
#:doc:
# An instance of typedefs.RegisterQueue. Updated whenever GDB receives an async event such as breakpoint modification
# See PINCE's AwaitAsyncOutput class for an example of usage
gdb_async_output = typedefs.RegisterQueue()

#:tag:GDBInformation
#:doc:
# A boolean value. Used to cancel the last gdb command sent
# Use the function cancel_last_command to make use of this variable
# Return value of the current send_command call will be an empty string
cancel_send_command = False

# A boolean value. Used by state_observe_thread to check if a trace session is active
active_trace = False

#:tag:GDBInformation
#:doc:
# A string. Holds the last command sent to gdb
last_gdb_command = ""

#:tag:GDBInformation
#:doc:
# A list of booleans. Used to adjust gdb output
# Use the function set_gdb_output_mode to make use of this variable
gdb_output_mode = typedefs.gdb_output_mode(True, True, True)

#:tag:InferiorInformation
#:doc:
# A string. memory file of the currently attached/created process
mem_file = "/proc/" + str(currentpid) + "/mem"

#:tag:Debug
#:doc:
# A string. Determines which signal to use to interrupt the process
interrupt_signal = "SIGINT"

"""
When PINCE was first launched, it used gdb 7.7.1, which is a very outdated version of gdb
interpreter-exec mi command of gdb showed some buggy behaviour at that time
Because of that, PINCE couldn't support gdb/mi commands for a while
But PINCE is now updated with the new versions of gdb as much as possible and the interpreter-exec works much better
So, old parts of codebase still get their required information by parsing gdb console output
New parts can try to rely on gdb/mi output
"""

"""
Functions that require breakpoint commands, such as track_watchpoint and track_breakpoint, requires process to be
stopped beforehand. If the process is running before we give the breakpoint its commands, there's a chance that the
breakpoint will be triggered before we give it commands. The process must be stopped to avoid this race condition
It's also necessary to stop the process to run commands like "watch"
"""


#:tag:GDBCommunication
def set_gdb_output_mode(output_mode_tuple):
    """Adjusts gdb output

    Args:
        output_mode_tuple (typedefs.gdb_output_mode): Setting any field True will enable the output that's associated
        with that field. Setting it False will disable the associated output
    """
    global gdb_output_mode
    gdb_output_mode = output_mode_tuple


#:tag:GDBCommunication
def cancel_last_command():
    """Cancels the last gdb command sent if it's still present"""
    if lock_send_command.locked():
        global cancel_send_command
        cancel_send_command = True


#:tag:GDBCommunication
def send_command(
    command, control=False, cli_output=False, send_with_file=False, file_contents_send=None, recv_with_file=False
):
    """Issues the command sent, raises an exception if gdb isn't initiated

    Args:
        command (str): The command that'll be sent
        control (bool): This param should be True if the command sent is ctrl+key instead of the regular command
        cli_output (bool): If True, returns a readable cli output instead of gdb/mi output
        send_with_file (bool): Custom commands declared in gdbextensions.py requires file communication. If
        called command has any parameters, pass this as True
        file_contents_send (any): Arguments for the custom gdb command called
        recv_with_file (bool): Pass this as True if the called custom gdb command returns something

    Examples:
        send_command(c,control=True)--> Sends ctrl+c instead of the str "c"
        send_command("pince-read-addresses", file_contents_send=nested_list, recv_file=True)--> This line calls the
        custom gdb command "pince-read-addresses" with parameter nested_list and since that gdb command returns the
        addresses read as a list, we also pass the parameter recv_file as True

    Returns:
        str: Result of the command sent, commands in the form of "ctrl+key" always returns a null string
        ???: If recv_with_file is True. Content of the returned thing depends on the command sent

    Note:
        TODO:This bug doesn't seem like to exist anymore. Remove the unnecessary file communication layer of IPC
        File communication system is used to avoid BEL emitting bug of pexpect. If you send more than a certain amount
        of characters to gdb, the input will be sheared at somewhere and gdb won't be receiving all of the input
        Visit this page for more information-->http://pexpect.readthedocs.io/en/stable/commonissues.html

        You don't have to write interpreter-exec while sending a gdb/mi command. Just pass the gdb/mi command as itself.
        This function will convert it automatically.
    """
    global child
    global gdb_output
    global cancel_send_command
    global last_gdb_command
    with lock_send_command:
        if gdb_output_mode.command_info:
            time0 = time()
        if not gdb_initialized:
            raise typedefs.GDBInitializeException
        gdb_output = ""
        if send_with_file:
            send_file = utils.get_from_pince_file(currentpid)
            pickle.dump(file_contents_send, open(send_file, "wb"))
        if recv_with_file or cli_output:
            recv_file = utils.get_to_pince_file(currentpid)

            # Truncating the recv_file because we wouldn't like to see output of previous command in case of errors
            open(recv_file, "w").close()
        command = str(command)
        command = 'interpreter-exec mi "' + command + '"' if command.startswith("-") else command
        last_gdb_command = command if not control else "Ctrl+" + command
        if gdb_output_mode.command_info:
            print("Last command: " + last_gdb_command)
        if control:
            child.sendcontrol(command)
        else:
            command_file = utils.get_gdb_command_file(currentpid)
            command_fd = open(command_file, "r+")
            command_fd.truncate()
            command_fd.write(command)
            command_fd.close()
            if not cli_output:
                child.sendline("source " + command_file)
            else:
                child.sendline("cli-output source " + command_file)
        if not control:
            while not gdb_output:
                sleep(typedefs.CONST_TIME.GDB_INPUT_SLEEP)
                if cancel_send_command:
                    break
            if not cancel_send_command:
                if recv_with_file or cli_output:
                    output = pickle.load(open(recv_file, "rb"))
                else:
                    output = gdb_output
            else:
                output = ""
                child.sendcontrol("c")
                with gdb_waiting_for_prompt_condition:
                    gdb_waiting_for_prompt_condition.wait()
        else:
            output = ""
        if gdb_output_mode.command_info:
            time1 = time()
            try:
                print(time1 - time0)
            except NameError:
                pass
        cancel_send_command = False
        return output


def state_observe_thread():
    """
    Observes the state of gdb, uses conditions to inform other functions and threads about gdb's state
    Also generates output for send_command function
    Should be called by creating a thread. Usually called in initialization process by attach function
    """

    def check_inferior_status():
        matches = regexes.gdb_state_observe.findall(child.before)
        if len(matches) > 0:
            global stop_reason
            global inferior_status
            old_status = inferior_status
            for match in matches:
                if match[0].startswith('stopped,reason="exited'):
                    with process_exited_condition:
                        detach()
                        print(f"Process terminated (PID:{currentpid})")
                        process_exited_condition.notify_all()
                        return

            # For multiline outputs, only the last async event is important
            # Get the last match only to optimize parsing
            stop_info = matches[-1][0]
            if stop_info:
                stop_reason = typedefs.STOP_REASON.DEBUG
                inferior_status = typedefs.INFERIOR_STATUS.STOPPED
            else:
                inferior_status = typedefs.INFERIOR_STATUS.RUNNING
            bp_num = regexes.breakpoint_number.search(stop_info)
            # Return -1 for invalid breakpoints to ignore racing conditions
            if not (
                old_status == inferior_status
                or (bp_num and breakpoint_on_hit_dict.get(bp_num.group(1), -1) != typedefs.BREAKPOINT_ON_HIT.BREAK)
                or active_trace
            ):
                with status_changed_condition:
                    status_changed_condition.notify_all()

    global child
    global gdb_output
    try:
        while True:
            child.expect_exact("\r\n")  # A new line for TTY devices
            child.before = child.before.strip()
            if not child.before:
                continue
            check_inferior_status()
            command_file = re.escape(utils.get_gdb_command_file(currentpid))
            if regexes.gdb_command_source(command_file).search(child.before):
                child.expect_exact("(gdb)")
                child.before = child.before.strip()
                check_inferior_status()
                gdb_output = child.before
                with gdb_waiting_for_prompt_condition:
                    gdb_waiting_for_prompt_condition.notify_all()
                if gdb_output_mode.command_output:
                    print(child.before)
            else:
                if gdb_output_mode.async_output:
                    print(child.before)
                gdb_async_output.broadcast_message(child.before)
    except (OSError, ValueError):
        print("Exiting state_observe_thread")


#:tag:GDBCommunication
def execute_func_temporary_interruption(func, *args, **kwargs):
    """Interrupts the inferior before executing the given function, continues inferior's execution after calling the
    given function

    !!!WARNING!!! This function is NOT thread-safe. Use it with caution!

    Args:
        func (function): The function that'll be called between interrupt&continue routine
        *args (args): Arguments for the function that'll be called
        **kwargs (kwargs): Keyword arguments for the function that'll be called

    Returns:
        ???: Result of the given function. Return type depends on the given function
    """
    old_status = inferior_status
    if old_status == typedefs.INFERIOR_STATUS.RUNNING:
        interrupt_inferior(typedefs.STOP_REASON.PAUSE)
    result = func(*args, **kwargs)
    if old_status == typedefs.INFERIOR_STATUS.RUNNING:
        continue_inferior()
    return result


#:tag:GDBCommunication
def execute_with_temporary_interruption(func):
    """Decorator version of execute_func_temporary_interruption"""

    def wrapper(*args, **kwargs):
        return execute_func_temporary_interruption(func, *args, **kwargs)

    return wrapper


#:tag:Debug
def can_attach(pid):
    """Check if we can attach to the target

    Args:
        pid (int,str): PID of the process that'll be attached

    Returns:
        bool: True if attaching is successful, False otherwise
    """
    result = libc.ptrace(16, int(pid), 0, 0)  # 16 is PTRACE_ATTACH, check ptrace.h for details
    if result == -1:
        return False
    os.waitpid(int(pid), 0)
    libc.ptrace(17, int(pid), 0, 17)  # 17 is PTRACE_DETACH, check ptrace.h for details
    sleep(0.01)
    return True


#:tag:Debug
def wait_for_stop(timeout=0):
    """Block execution till the inferior stops

    Args:
        timeout (float): Timeout time in seconds, passing 0 will wait for stop indefinitely
    """
    remaining_time = timeout
    while inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
        sleep(typedefs.CONST_TIME.GDB_INPUT_SLEEP)
        if timeout == 0:
            continue
        remaining_time -= typedefs.CONST_TIME.GDB_INPUT_SLEEP
        if remaining_time < 0:
            break


#:tag:Debug
def interrupt_inferior(interrupt_reason=typedefs.STOP_REASON.DEBUG):
    """Interrupt the inferior

    Args:
        interrupt_reason (int): Just changes the global variable stop_reason. Can be a member of typedefs.STOP_REASON
    """
    if currentpid == -1:
        return
    global stop_reason
    if interrupt_signal == "SIGINT":
        send_command("interrupt")
    elif inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
        sig_num = interrupt_signal[3:]
        if sig_num.isnumeric():
            os.system(f"kill -{sig_num} {currentpid}")
        else:
            os.system(f"kill -s {interrupt_signal} {currentpid}")
    wait_for_stop()
    stop_reason = interrupt_reason


#:tag:Debug
def continue_inferior():
    """Continue the inferior"""
    if currentpid == -1:
        return
    send_command("c&")


#:tag:Debug
def step_instruction():
    """Step one assembly instruction"""
    send_command("stepi&")


#:tag:Debug
def step_over_instruction():
    """Step over one assembly instruction"""
    send_command("nexti&")


#:tag:Debug
def execute_till_return():
    """Continues inferior till current stack frame returns"""
    send_command("finish&")


#:tag:Debug
def set_interrupt_signal(signal_name):
    """Decides on what signal to use to stop the process

    Args:
        signal_name (str): Name of the signal
    """
    global interrupt_signal
    handle_signal(signal_name, True, False)
    interrupt_signal = signal_name


#:tag:Debug
def handle_signal(signal_name: str, stop: bool, pass_to_program: bool) -> None:
    """Decides on what will GDB do when the process recieves a signal

    Args:
        signal_name (str): Name of the signal
        stop (bool): Stop the program and print to the console
        pass_to_program (bool): Pass signal to program
    """
    params = [[signal_name, stop, pass_to_program]]
    send_command("pince-handle-signals", send_with_file=True, file_contents_send=params)


#:tag:Debug
def handle_signals(signal_list):
    """Optimized version of handle_signal for multiple signals

    Args:
        signal_list (list): A list of the parameters of handle_signal
    """
    send_command("pince-handle-signals", send_with_file=True, file_contents_send=signal_list)


#:tag:GDBCommunication
def init_gdb(gdb_path=utils.get_default_gdb_path()):
    """Spawns gdb and initializes/resets some of the global variables

    Args:
        gdb_path (str): Path of the gdb binary

    Note:
        Calling init_gdb() will reset the current session
    """
    global child
    global gdb_initialized
    global breakpoint_on_hit_dict
    global chained_breakpoints
    global gdb_output
    global cancel_send_command
    global last_gdb_command
    utils.init_user_files()
    detach()

    # Temporary IPC_PATH, this little hack is needed because send_command requires a valid IPC_PATH
    utils.create_ipc_path(currentpid)
    utils.create_tmp_path(currentpid)

    breakpoint_on_hit_dict.clear()
    chained_breakpoints.clear()
    gdb_output = ""
    cancel_send_command = False
    last_gdb_command = ""

    libpince_dir = utils.get_libpince_directory()
    is_appimage = os.environ.get("APPDIR")
    python_home_env = f"PYTHONHOME={os.environ.get('PYTHONHOME')}" if is_appimage else ""
    child = pexpect.spawn(
        f"sudo -E --preserve-env=PATH LC_NUMERIC=C {python_home_env} {gdb_path} --nx --interpreter=mi",
        cwd=libpince_dir,
        env=os.environ,
        encoding="utf-8",
    )
    child.setecho(False)
    child.delaybeforesend = 0
    child.timeout = None
    child.expect_exact("(gdb)")
    status_thread = Thread(target=state_observe_thread)
    status_thread.daemon = True
    status_thread.start()
    gdb_initialized = True
    set_logging(False)
    if not is_appimage:
        send_command("source ./gdbinit_venv")
    set_pince_paths()
    send_command("source " + utils.get_user_path(typedefs.USER_PATHS.GDBINIT))
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT))


#:tag:GDBCommunication
def set_logging(state):
    """Sets logging on or off

    Args:
        state (bool): Sets logging on if True, off if False
    """
    send_command("set logging enabled off")
    send_command("set logging file " + utils.get_logging_file(currentpid))
    if state:
        send_command("set logging enabled on")


#:tag:GDBCommunication
def set_pince_paths():
    """Initializes $PINCE_PATH and $GDBINIT_AA_PATH convenience variables to make commands in gdbextensions.py
    and gdbutils.py work. GDB scripts need to know libpince and .config directories, unfortunately they don't start
    from the place where script exists
    """
    libpince_dir = utils.get_libpince_directory()
    pince_dir = os.path.dirname(libpince_dir)
    gdbinit_aa_dir = utils.get_user_path(typedefs.USER_PATHS.GDBINIT_AA)
    send_command("set $GDBINIT_AA_PATH=" + '"' + gdbinit_aa_dir + '"')
    send_command("set $PINCE_PATH=" + '"' + pince_dir + '"')
    send_command("source gdb_python_scripts/gdbextensions.py")


def init_referenced_dicts(pid):
    """Initializes referenced dict shelve databases

    Args:
        pid (int,str): PID of the attached process
    """
    shelve.open(utils.get_referenced_strings_file(pid), "c")
    shelve.open(utils.get_referenced_jumps_file(pid), "c")
    shelve.open(utils.get_referenced_calls_file(pid), "c")


#:tag:Debug
def attach(pid, gdb_path=utils.get_default_gdb_path()):
    """Attaches gdb to the target and initializes some of the global variables

    Args:
        pid (int,str): PID of the process that'll be attached to
        gdb_path (str): Path of the gdb binary

    Returns:
        int: A member of typedefs.ATTACH_RESULT

    Note:
        If gdb is already initialized, gdb_path will be ignored
    """
    global currentpid
    pid = int(pid)
    traced_by = utils.is_traced(pid)
    pid_control_list = [
        # Attaching PINCE to itself makes PINCE freeze immediately because gdb freezes the target on attach
        (lambda: pid == self_pid, typedefs.ATTACH_RESULT.ATTACH_SELF),
        (lambda: not utils.is_process_valid(pid), typedefs.ATTACH_RESULT.PROCESS_NOT_VALID),
        (lambda: pid == currentpid, typedefs.ATTACH_RESULT.ALREADY_DEBUGGING),
        (lambda: traced_by is not None, typedefs.ATTACH_RESULT.ALREADY_TRACED),
        (lambda: not can_attach(pid), typedefs.ATTACH_RESULT.PERM_DENIED),
    ]
    for control_func, attach_result in pid_control_list:
        if control_func():
            return attach_result
    if currentpid != -1 or not gdb_initialized:
        init_gdb(gdb_path)
    global inferior_arch
    global mem_file
    currentpid = pid
    mem_file = "/proc/" + str(currentpid) + "/mem"
    utils.create_ipc_path(pid)
    utils.create_tmp_path(pid)
    send_command("attach " + str(pid))
    set_pince_paths()
    init_referenced_dicts(pid)
    inferior_arch = get_inferior_arch()
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT_AA))
    return typedefs.ATTACH_RESULT.SUCCESSFUL


#:tag:Debug
def create_process(process_path, args="", ld_preload_path="", gdb_path=utils.get_default_gdb_path()):
    """Creates a new process for debugging and initializes some of the global variables
    Current process will be detached even if the create_process call fails
    Make sure to save your data before calling this monstrosity

    Args:
        process_path (str): Absolute path of the target binary
        args (str): Arguments of the inferior, optional
        ld_preload_path (str): Path of the preloaded .so file, optional
        gdb_path (str): Path of the gdb binary

    Returns:
        bool: True if the process has been created successfully, False otherwise

    Note:
        If gdb is already initialized, gdb_path will be ignored
    """
    global currentpid
    global inferior_arch
    global mem_file
    if currentpid != -1 or not gdb_initialized:
        init_gdb(gdb_path)
    output = send_command("file " + process_path)
    if regexes.gdb_error.search(output):
        print("An error occurred while trying to create process from the file at " + process_path)
        detach()
        return False
    send_command("starti")
    wait_for_stop()
    entry_point = find_entry_point()
    if entry_point:
        send_command("tbreak *" + entry_point)
    else:
        send_command("tbreak _start")
    send_command("set args " + args)
    if ld_preload_path:
        send_command("set exec-wrapper env 'LD_PRELOAD=" + ld_preload_path + "'")
    send_command("run")

    # We have to wait till breakpoint hits
    wait_for_stop()
    pid = get_inferior_pid()
    currentpid = int(pid)
    mem_file = "/proc/" + str(currentpid) + "/mem"
    utils.create_ipc_path(pid)
    utils.create_tmp_path(pid)
    set_pince_paths()
    init_referenced_dicts(pid)
    inferior_arch = get_inferior_arch()
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT_AA))
    return True


#:tag:Debug
def detach():
    """See you, space cowboy"""
    global gdb_initialized
    global currentpid
    old_pid = currentpid
    if gdb_initialized:
        global child
        global inferior_status
        currentpid = -1
        inferior_status = -1
        gdb_initialized = False
        child.close()
    if old_pid != -1:
        utils.delete_ipc_path(old_pid)
    print("Detached from the process with PID:" + str(old_pid))


#:tag:Debug
def toggle_attach():
    """Detaches from the current process without ending the season if currently attached. Attaches back if detached

    Returns:
        int: The new state of the process as a member of typedefs.TOGGLE_ATTACH
        None: If detaching or attaching fails
    """
    if currentpid == -1:
        return
    if is_attached():
        if regexes.gdb_error.search(send_command("phase-out")):
            return
        return typedefs.TOGGLE_ATTACH.DETACHED
    if regexes.gdb_error.search(send_command("phase-in")):
        return
    return typedefs.TOGGLE_ATTACH.ATTACHED


#:tag:Debug
def is_attached():
    """Checks if gdb is attached to the current process

    Returns:
        bool: True if attached, False if not
    """
    if regexes.gdb_error.search(send_command("info proc")):
        return False
    return True


#:tag:Injection
def inject_with_advanced_injection(library_path):
    """Injects the given .so file to current process

    Args:
        library_path (str): Path to the .so file that'll be injected

    Returns:
        bool: Result of the injection

    Note:
        This function was reserved for linux-inject and since linux-inject is no more(F to pay respects), I'll leave
        this function as a template for now
    """
    raise NotImplementedError


#:tag:Injection
def inject_with_dlopen_call(library_path):
    """Injects the given .so file to current process
    This is a variant of the function inject_with_advanced_injection
    This function won't break the target process unlike other complex injection methods
    The downside is it fails if the target doesn't support dlopen calls or simply doesn't have the library

    Args:
        library_path (str): Path to the .so file that'll be injected

    Returns:
        bool: Result of the injection
    """
    # TODO: Merge injection functions and rename them to inject_so once advanced injection is implemented
    injectionpath = '"' + library_path + '"'
    result = call_function_from_inferior("dlopen(" + injectionpath + ", 1)")[1]
    if result == "0" or not result:
        new_result = call_function_from_inferior("__libc_dlopen_mode(" + injectionpath + ", 1)")[1]
        if new_result == "0" or not new_result:
            return False
        return True
    return True


#:tag:MemoryRW
def read_pointer_chain(pointer_request: typedefs.PointerChainRequest) -> typedefs.PointerChainResult | None:
    """Reads the addresses pointed by this pointer chain

    Args:
        pointer_request (typedefs.PointerChainRequest): class containing a base_address and an offsets list

    Returns:
        typedefs.PointerChainResult: Class containing every pointer dereference result while walking the chain
        None: If an error occurs while reading the given pointer chain
    """
    if not isinstance(pointer_request, typedefs.PointerChainRequest):
        raise TypeError("Passed non-PointerChainRequest type to read_pointer_chain!")

    if inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32:
        value_index = typedefs.VALUE_INDEX.INT32
    else:
        value_index = typedefs.VALUE_INDEX.INT64

    # Simple addresses first, examine_expression takes much longer time, especially for larger tables
    try:
        start_address = int(pointer_request.base_address, 0)
    except (ValueError, TypeError):
        start_address = examine_expression(pointer_request.base_address).address

    pointer_results: typedefs.PointerChainResult = typedefs.PointerChainResult()
    try:
        with memory_handle() as mem_handle:
            # Dereference the first address which is the base or (base + offset)
            deref_address = read_memory(start_address, value_index, mem_handle=mem_handle)
            if deref_address is None:
                # Simply return None because no point reading further if base is not valid
                return None
            pointer_results.pointer_chain.append(deref_address)

            for index, offset in enumerate(pointer_request.offsets_list):
                # If deref_address is 0, we found an invalid read in the chain
                # so we can just keep adding 0 until the end of offsets list
                if deref_address == 0:
                    pointer_results.pointer_chain.append(0)
                    continue
                offset_address = deref_address + offset
                if index != len(pointer_request.offsets_list) - 1:  # CE derefs every offset except for the last one
                    deref_address = read_memory(offset_address, value_index, mem_handle=mem_handle)
                    if deref_address is None:
                        deref_address = 0
                else:
                    deref_address = offset_address
                pointer_results.pointer_chain.append(deref_address)
    except OSError:
        return None
    return pointer_results


def memory_handle():
    """
    Acquire the handle of the currently attached process

    Returns:
        BinaryIO: A file handle that points to the memory file of the current process
    """
    return open(mem_file, "rb")


#:tag:MemoryRW
def read_memory(
    address,
    value_index,
    length=None,
    zero_terminate=True,
    value_repr=typedefs.VALUE_REPR.UNSIGNED,
    endian=typedefs.ENDIANNESS.HOST,
    mem_handle=None,
):
    """Reads value from the given address

    Args:
        address (str, int): Can be a hex string or an integer.
        value_index (int): Determines the type of data read. Can be a member of typedefs.VALUE_INDEX
        length (int): Length of the data that'll be read. Must be greater than 0. Only used when the value_index is
        STRING or AOB. Ignored otherwise
        zero_terminate (bool): If True, data will be split when a null character has been read. Only used when
        value_index is STRING. Ignored otherwise
        value_repr (int): Can be a member of typedefs.VALUE_REPR. Only usable with integer types
        endian (int): Can be a member of typedefs.ENDIANNESS
        mem_handle (BinaryIO): A file handle that points to the memory file of the current process
        This parameter is used for optimization, See memory_handle
        Don't forget to close the handle after you're done if you use this parameter manually

    Returns:
        str: If the value_index is STRING or AOB, also when value_repr is HEX
        float: If the value_index is FLOAT32 or FLOAT64
        int: If the value_index is anything else
        None: If an error occurs while reading the given address
    """
    try:
        value_index = int(value_index)
    except:
        # print(str(value_index) + " is not a valid value index")
        return
    if not type(address) == int:
        try:
            address = int(address, 0)
        except:
            # print(str(address) + " is not a valid address")
            return
    packed_data = typedefs.index_to_valuetype_dict.get(value_index, -1)
    if typedefs.VALUE_INDEX.is_string(value_index):
        try:
            length = int(length)
        except:
            # print(str(length) + " is not a valid length")
            return
        if not length > 0:
            # print("length must be greater than 0")
            return
        expected_length = length * typedefs.string_index_to_multiplier_dict.get(value_index, 1)
    elif value_index is typedefs.VALUE_INDEX.AOB:
        try:
            expected_length = int(length)
        except:
            # print(str(length) + " is not a valid length")
            return
        if not expected_length > 0:
            # print("length must be greater than 0")
            return
    else:
        expected_length = packed_data[0]
        data_type = packed_data[1]
    try:
        if not mem_handle:
            mem_handle = open(mem_file, "rb")
        mem_handle.seek(address)
        data_read = mem_handle.read(expected_length)
        if endian != typedefs.ENDIANNESS.HOST and system_endianness != endian:
            data_read = data_read[::-1]
    except (OSError, ValueError):
        # TODO (read/write error output)
        # Disabled read error printing. If needed, find a way to implement error logging with this function
        # I've initially thought about enabling it on demand via a parameter but this function already has too many
        # Maybe creating a function that toggles logging on and off? Other functions could use it too
        # print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + expected_length))
        return
    if typedefs.VALUE_INDEX.is_string(value_index):
        encoding, option = typedefs.string_index_to_encoding_dict[value_index]
        returned_string = data_read.decode(encoding, option)
        if zero_terminate:
            if returned_string.startswith("\x00"):
                returned_string = "\x00"
            else:
                returned_string = returned_string.split("\x00")[0]
        return returned_string[0:length]
    elif value_index is typedefs.VALUE_INDEX.AOB:
        return " ".join(format(n, "02x") for n in data_read)
    else:
        is_integer = typedefs.VALUE_INDEX.is_integer(value_index)
        if is_integer and value_repr == typedefs.VALUE_REPR.SIGNED:
            data_type = data_type.lower()
        result = struct.unpack_from(data_type, data_read)[0]
        if is_integer and value_repr == typedefs.VALUE_REPR.HEX:
            return hex(result)
        return result


#:tag:MemoryRW
def write_memory(
    address: str | int,
    value_index: int,
    value: str | int | float | list[int],
    zero_terminate=True,
    endian=typedefs.ENDIANNESS.HOST,
):
    """Sets the given value to the given address

    If any errors occurs while setting value to the according address, it'll be ignored but the information about
    error will be printed to the terminal.

    Args:
        address (str, int): Can be a hex string or an integer
        value_index (int): Can be a member of typedefs.VALUE_INDEX
        value (str, int, float, list): The value that'll be written to the given address
        zero_terminate (bool): If True, appends a null byte to the value. Only used when value_index is STRING
        endian (int): Can be a member of typedefs.ENDIANNESS

    Notes:
        TODO: Implement a mem_handle parameter for optimization, check read_memory for an example
        If a file handle fails to write to an address, it becomes unusable
        You have to reopen the file to continue writing
    """
    if not type(address) == int:
        try:
            address = int(address, 0)
        except:
            # print(str(address) + " is not a valid address")
            return
    if isinstance(value, str):
        write_data = utils.parse_string(value, value_index)
        if write_data is None:
            return
    else:
        write_data = value
    encoding, option = typedefs.string_index_to_encoding_dict.get(value_index, (None, None))
    if encoding is None:
        if value_index is typedefs.VALUE_INDEX.AOB:
            write_data = bytearray(write_data)
        else:
            data_type = typedefs.index_to_struct_pack_dict.get(value_index, -1)
            write_data = struct.pack(data_type, write_data)
    else:
        write_data = write_data.encode(encoding, option)
        if zero_terminate:
            write_data += b"\x00"
    if endian != typedefs.ENDIANNESS.HOST and system_endianness != endian:
        write_data = write_data[::-1]
    FILE = open(mem_file, "rb+")
    try:
        FILE.seek(address)
        FILE.write(write_data)
        FILE.close()
    except (OSError, ValueError):
        # Refer to TODO (read/write error output)
        # print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + len(write_data)))
        return


#:tag:Assembly
def disassemble(expression, offset_or_address):
    """Disassembles the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression
        offset_or_address (str): If you pass this parameter as an offset, you should add "+" in front of it
        (e.g "+42" or "+0x42"). If you pass this parameter as an hex address, the address range between the expression
        and the secondary address is disassembled
        If the second parameter is an address, it always should be bigger than the first address

    Returns:
        list: A list of str values in this format-->[(address1, bytes1, opcodes1), (address2, ...), ...]
    """
    output = send_command("disas /r " + expression + "," + offset_or_address)
    disas_data = []
    for line in output.splitlines():
        result = regexes.disassemble_output.search(line)
        if result:
            disas_data.append(result.groups())
    return disas_data


#:tag:GDBExpressions
def examine_expression(expression):
    """Evaluates the given expression and returns evaluated value, address and symbol

    Args:
        expression (str): Any gdb expression

    Returns:
        typedefs.tuple_examine_expression: Evaluated value, address and symbol in a tuple
        Any erroneous field will be returned as None instead of str
    """
    if currentpid == -1:
        return typedefs.tuple_examine_expression(None, None, None)
    return send_command(
        "pince-examine-expressions", send_with_file=True, file_contents_send=[expression], recv_with_file=True
    )[0]


def examine_expressions(expression_list):
    """Optimized version of examine_expression for multiple inputs

    Args:
        expression_list (list): List of gdb expressions as str

    Returns:
        list: List of typedefs.tuple_examine_expression
    """
    if not expression_list:
        return []
    if currentpid == -1:
        return [typedefs.tuple_examine_expression(None, None, None) for _ in range(len(expression_list))]
    return send_command(
        "pince-examine-expressions", send_with_file=True, file_contents_send=expression_list, recv_with_file=True
    )


#:tag:GDBExpressions
def parse_and_eval(expression, cast=str):
    """Calls gdb.parse_and_eval with the given expression and returns the value after casting with the given type
    Use examine_expression if your data can be expressed as an address or a symbol, use this function otherwise
    Unlike examine_expression, this function can read data that has void type or multiple type representations
    For instance:
        $eflags has both str and int reprs
        $_siginfo is a struct with many fields
        x64 register convenience vars such as $rax are void if the process is x86

    Args:
        expression (str): Any gdb expression
        cast (type): Evaluated value will be cast to this type in gdb

    Returns:
        cast: Self-explanatory
        None: If casting fails
    """
    return send_command(
        "pince-parse-and-eval", send_with_file=True, file_contents_send=(expression, cast), recv_with_file=True
    )


#:tag:Threads
def get_thread_info():
    """Invokes "info threads" command and returns the line corresponding to the current thread

    Returns:
        str: Current thread information
        None: If the output doesn't fit the regex
    """
    thread_info = send_command("info threads")
    return re.sub(r'\\"', r'"', regexes.thread_info.search(thread_info).group(1))


#:tag:Assembly
def find_closest_instruction_address(address, instruction_location="next", instruction_count=1):
    """Finds address of the closest instruction next to the given address, assuming that the given address is valid

    Args:
        address (str): Hex address or any gdb expression that can be used in disas command
        instruction_location (str): If it's "next", instructions coming after the address is searched
        If it's "previous", the instructions coming before the address is searched instead
        instruction_count (int): Number of the instructions that'll be looked for

    Returns:
        str: The address found as hex string. If starting/ending of a valid memory range is reached, starting/ending
        address is returned instead as hex string.

    Note:
        From gdb version 7.12 and onwards, inputting negative numbers in x command are supported(x/-3i for instance)
        So, modifying this function according to the changes in 7.12 may speed up things a little bit but also breaks
        the backwards compatibility. The speed gain is not much of a big deal compared to backwards compatibility, so
        I'm not changing this function for now
    """
    assert instruction_location in ["next", "previous"], "invalid instruction_location"
    if instruction_location == "next":
        offset = "+" + str(instruction_count * 30)
        disas_data = disassemble(address, address + offset)
    else:
        offset = "-" + str(instruction_count * 30)
        disas_data = disassemble(address + offset, address)
    if not disas_data:
        if instruction_location != "next":
            start_address = hex(utils.get_region_info(currentpid, address).start)
            disas_data = disassemble(start_address, address)
    if instruction_location == "next":
        try:
            return utils.extract_address(disas_data[instruction_count][0])
        except IndexError:
            return hex(utils.get_region_info(currentpid, address).end)
    else:
        try:
            return utils.extract_address(disas_data[-instruction_count][0])
        except IndexError:
            try:
                return start_address
            except UnboundLocalError:
                return hex(utils.get_region_info(currentpid, address).start)


#:tag:GDBExpressions
def get_address_info(expression):
    """Runs the gdb command "info symbol" for given expression and returns the result of it

    Args:
        expression (str): Any gdb expression

    Returns:
        str: The result of the command "info symbol" for given expression
    """
    return send_command("info symbol " + expression, cli_output=True)


#:tag:GDBExpressions
def get_symbol_info(expression):
    """Runs the gdb command "info address" for given expression and returns the result of it

    Args:
        expression (str): Any gdb expression

    Returns:
        str: The result of the command "info address" for given expression
    """
    return send_command("info address " + expression, cli_output=True)


#:tag:Tools
def search_functions(expression, case_sensitive=False):
    """Runs the gdb command "info functions" for given expression and returns the result of it

    Args:
        expression (str): Any gdb expression
        case_sensitive (bool): If True, search will be case sensitive

    Returns:
        list: A list of str-->[(address1, symbol1), (address2, symbol2), ...]
            address will be None if the corresponding symbol is in defined category

    Todo:
        GDB-MI wiki points out to the command -symbol-list-functions but apparently it isn't implemented yet
        If the feature below gets implemented, use it instead
        https://sourceware.org/bugzilla/show_bug.cgi?id=23796

        Add ability to show addresses of defined symbols when it gets implemented by gdb
        Please don't try to write a symbol parser for every single language out there, it's an overkill
        https://sourceware.org/bugzilla/show_bug.cgi?id=23899
    """
    return send_command(
        "pince-search-functions",
        send_with_file=True,
        file_contents_send=(expression, case_sensitive),
        recv_with_file=True,
    )


#:tag:InferiorInformation
def get_inferior_pid():
    """Get pid of the current inferior

    Returns:
        str: pid
    """
    output = send_command("info inferior")
    return regexes.inferior_pid.search(output).group(1)


#:tag:InferiorInformation
def get_inferior_arch():
    """Returns the architecture of the current inferior

    Returns:
        int: A member of typedefs.INFERIOR_ARCH
    """
    if parse_and_eval("$rax") == "void":
        return typedefs.INFERIOR_ARCH.ARCH_32
    return typedefs.INFERIOR_ARCH.ARCH_64


#:tag:Registers
def read_registers():
    """Returns the current registers

    Returns:
        dict: A dict that holds general, flag and segment registers. Check typedefs.REGISTERS for the full list
    """
    return send_command("pince-read-registers", recv_with_file=True)


#:tag:Registers
def read_float_registers():
    """Returns the current floating point registers

    Returns:
        dict: A dict that holds floating point registers. Check typedefs.REGISTERS.FLOAT for the full list

    Note:
        Returned xmm values are based on xmm.v4_float
    """
    return send_command("pince-read-float-registers", recv_with_file=True)


#:tag:GDBExpressions
#:tag:Registers
def set_convenience_variable(variable, value):
    """Sets given convenience variable to given value
    Can be also used for modifying registers directly

    Args:
        variable (str): Any gdb convenience variable(with "$" character removed)
        value (str): Anything
    """
    send_command("set $" + variable + "=" + value)


#:tag:Registers
def set_register_flag(flag, value):
    """Sets given register flag to given value

    Args:
        flag (str): A member of typedefs.REGISTERS.FLAG
        value (Union[int,str]): 0 or 1
    """
    registers = read_registers()
    value = str(value)
    registers[flag] = value
    if value != "0" and value != "1":
        raise Exception(value + " isn't valid value. It can be only 0 or 1")
    if flag not in typedefs.REGISTERS.FLAG:
        raise Exception(flag + " isn't a valid flag, must be a member of typedefs.REGISTERS.FLAG")
    eflags_hex_value = hex(
        int(
            registers["of"]
            + registers["df"]
            + registers["if"]
            + registers["tf"]
            + registers["sf"]
            + registers["zf"]
            + "0"
            + registers["af"]
            + "0"
            + registers["pf"]
            + "0"
            + registers["cf"],
            2,
        )
    )
    set_convenience_variable("eflags", eflags_hex_value)


#:tag:Stack
def get_stacktrace_info():
    """Returns information about current stacktrace

    Returns:
        list: A list of str values in this format-->[[return_address_info1,frame_address_info1],[info2, ...], ...]

        return_address_info looks like this-->Return address of frame+symbol-->0x40c431 <_start>
        frame_address_info looks like this-->Beginning of frame+distance from stack pointer-->0x7ffe1e989a40(rsp+0x100)
    """
    return send_command("pince-get-stack-trace-info", recv_with_file=True)


#:tag:Stack
def get_stack_info():
    """Returns information about current stack

    Returns:
        list: A list of str values in this format--▼
        [[stack_pointer_info1,hex_value1,pointer_info1],[stack_pointer_info2, ...], ...]

        stack_pointer_info looks like this-->Hex address+distance from stack pointer-->0x7ffd0d232f88(rsp+0xff8)
        hex_value looks like this-->Value hold by corresponding address-->0x1bfda20
        pointer_info shows the value hold by hex_value address. It looks like this--▼
        if points to a string-->(str)Some String
        if points to a symbol-->(ptr)<function_name>
        pointer_info becomes a null string if pointer isn't valid
    """
    return send_command("pince-get-stack-info", recv_with_file=True)


#:tag:Stack
def get_stack_frame_return_addresses():
    """Returns return addresses of stack frames

    Returns:
        list: A list of str values in this format-->[return_address_info1,return_address_info2, ...]

        return_address_info looks like this-->Return address of frame+symbol-->0x40c431 <_start>
    """
    return send_command("pince-get-frame-return-addresses", recv_with_file=True)


#:tag:Stack
def get_stack_frame_info(index):
    """Returns information about stack by the given index

    Args:
        index (int,str): Index of the frame

    Returns:
        str: Information that looks like this--▼
        Stack level 0, frame at 0x7ffc5f87f6a0:
            rip = 0x7fd1d639412d in poll (../sysdeps/unix/syscall-template.S:81); saved rip = 0x7fd1d27fcfe4
            called by frame at 0x7ffc5f87f700
            source language asm.
            Arglist at 0x7ffc5f87f688, args:
            Locals at 0x7ffc5f87f688, Previous frame's sp is 0x7ffc5f87f6a0
            Saved registers:
                rip at 0x7ffc5f87f698
    """
    return send_command("pince-get-frame-info", send_with_file=True, file_contents_send=str(index), recv_with_file=True)


#:tag:MemoryRW
def hex_dump(address, offset):
    """Returns hex dump of range (address to address+offset)

    Args:
        address (int): Self-explanatory
        offset (int): The range that'll be read

    Returns:
        list: List of strings read as str. If an error occurs while reading a memory cell, that cell is returned as "??"
        An empty list is returned if an error occurs

    Examples:
        returned list-->["??","??","??","7f","43","67","40","??","??, ...]
    """
    hex_byte_list = []
    with open(mem_file, "rb") as FILE:
        try:
            FILE.seek(address)
        except (OSError, ValueError):
            pass
        for item in range(offset):
            try:
                current_item = " ".join(format(n, "02x") for n in FILE.read(1))
            except OSError:
                current_item = "??"
                try:
                    FILE.seek(1, io.SEEK_CUR)  # Necessary since read() failed to execute
                except (OSError, ValueError):
                    pass
            hex_byte_list.append(utils.upper_hex(current_item))
    return hex_byte_list


#:tag:MemoryRW
def get_modified_instructions():
    """Returns currently modified instructions

    Returns:
        dict: A dictionary where the key is the start address of instruction and value is the aob before modifying

    """
    global modified_instructions_dict
    return modified_instructions_dict


#:tag:MemoryRW
def nop_instruction(start_address, length_of_instr):
    """Replaces an instruction's opcodes with NOPs

    Args:
        start_address (int): Self-explanatory
        length_of_instr (int): Length of the instruction that'll be NOP'ed

    Returns:
        None
    """
    old_aob = " ".join(hex_dump(start_address, length_of_instr))
    global modified_instructions_dict
    if start_address not in modified_instructions_dict:
        modified_instructions_dict[start_address] = old_aob

    nop_aob = "90 " * length_of_instr
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, nop_aob)


#:tag:MemoryRW
def modify_instruction(start_address, array_of_bytes):
    """Replaces an instruction's opcodes with a new AOB

    Args:
        start_address (int): Self-explanatory
        array_of_bytes (str): String that contains the replacement bytes of the instruction

    Returns:
        None
    """
    length = len(array_of_bytes.split())
    old_aob = " ".join(hex_dump(start_address, length))

    global modified_instructions_dict
    if start_address not in modified_instructions_dict:
        modified_instructions_dict[start_address] = old_aob
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, array_of_bytes)


#:tag:MemoryRW
def restore_instruction(start_address):
    """Restores a modified instruction to it's original opcodes

    Args:
        start_address (int): Self-explanatory

    Returns:
        None
    """
    global modified_instructions_dict
    array_of_bytes = modified_instructions_dict.pop(start_address)
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, array_of_bytes)


#:tag:BreakWatchpoints
def get_breakpoint_info() -> list[typedefs.tuple_breakpoint_info]:
    """Returns current breakpoint/watchpoint list

    Returns:
        list: A list of typedefs.tuple_breakpoint_info where;
            number is the gdb breakpoint number
            breakpoint_type is the breakpoint type
            disp shows what will be done after breakpoint hits
            enabled shows if the breakpoint enabled or disabled
            address is the address of breakpoint
            size is the size of breakpoint
            on_hit is the action that'll happen when the breakpoint is reached
            hit_count shows how many times the breakpoint has been hit
            enable_count shows how many times the breakpoint will get hit before it gets disabled
            condition is the condition of breakpoint

            size-->int
            everything else-->str

    Note:
        GDB's python API can't detect hardware breakpoints, that's why we are using parser for this job
    """
    returned_list = []
    multiple_break_data = OrderedDict()
    raw_info = send_command("-break-list")
    # Temporary fix for https://sourceware.org/bugzilla/show_bug.cgi?id=9659
    # TODO:Delete this line when gdb or pygdbmi fixes the problem
    raw_info = re.sub(r"script={(.*?)}", r"script=[\g<1>]", raw_info)  # Please refer to issue #53
    for item in utils.parse_response(raw_info)["payload"]["BreakpointTable"]["body"]:
        item = defaultdict(lambda: "", item)
        number, breakpoint_type, disp, enabled, address, what, condition, hit_count, enable_count = (
            item["number"],
            item["type"],
            item["disp"],
            item["enabled"],
            item["addr"],
            item["what"],
            item["cond"],
            item["times"],
            item["enable"],
        )
        if address == "<MULTIPLE>":
            multiple_break_data[number] = (breakpoint_type, disp, condition, hit_count)
            continue
        if not breakpoint_type:
            number = number.split(".")[0]
            breakpoint_type, disp, condition, hit_count = multiple_break_data[number]
        if what:
            address = utils.extract_address(what)
            if not address:
                address = examine_expression(what).address
        on_hit_dict_value = breakpoint_on_hit_dict.get(number, typedefs.BREAKPOINT_ON_HIT.BREAK)
        on_hit = typedefs.on_hit_to_text_dict.get(on_hit_dict_value, "Unknown")
        if breakpoint_type.find("breakpoint") >= 0:
            size = 1
        else:
            possible_size = regexes.breakpoint_size.search(what)
            if possible_size:
                size = int(possible_size.group(1))
            else:
                size = 1
        returned_list.append(
            typedefs.tuple_breakpoint_info(
                number, breakpoint_type, disp, enabled, address, size, on_hit, hit_count, enable_count, condition
            )
        )
    return returned_list


#:tag:BreakWatchpoints
def get_breakpoints_in_range(address: str | int, length: int = 1) -> list[typedefs.tuple_breakpoint_info]:
    """Checks if given address exists in breakpoint list

    Args:
        address (str,int): Start address of the range, hex address or an int
        length (int): If this parameter is bigger than 1, the range between address and address+length-1 will be
        checked instead of just the address itself

    Returns:
        list: A list of typedefs.tuple_breakpoint_info, info of the existing breakpoints for given address range
    """
    breakpoint_list = []
    if type(address) != int:
        address = int(address, 0)
    max_address = max(address, address + length - 1)
    min_address = min(address, address + length - 1)
    breakpoint_info = get_breakpoint_info()
    for item in breakpoint_info:
        breakpoint_address = int(item.address, 16)
        if not (max_address < breakpoint_address or min_address > breakpoint_address + item.size - 1):
            breakpoint_list.append(item)
    return breakpoint_list


#:tag:BreakWatchpoints
def hardware_breakpoint_available() -> bool:
    """Checks if there is an available hardware breakpoint slot

    Returns:
        bool: True if there is at least one available slot, False if not

    Todo:
        Check debug registers to determine hardware breakpoint state rather than relying on gdb output because inferior
        might modify its own debug registers
    """
    breakpoint_info = get_breakpoint_info()
    hw_bp_total = 0
    for item in breakpoint_info:
        if regexes.hw_breakpoint_count.search(item.breakpoint_type):
            hw_bp_total += 1

    # Maximum number of hardware breakpoints is limited to 4 in x86 architecture
    return hw_bp_total < 4


#:tag:BreakWatchpoints
def add_breakpoint(
    expression, breakpoint_type=typedefs.BREAKPOINT_TYPE.HARDWARE, on_hit=typedefs.BREAKPOINT_ON_HIT.BREAK
):
    """Adds a breakpoint at the address evaluated by the given expression. Uses a software breakpoint if all hardware
    breakpoint slots are being used

    Args:
        expression (str): Any gdb expression
        breakpoint_type (int): Can be a member of typedefs.BREAKPOINT_TYPE
        on_hit (int): Can be a member of typedefs.BREAKPOINT_ON_HIT

    Returns:
        str: Number of the breakpoint set
        None: If setting breakpoint fails
    """
    output = ""
    str_address = examine_expression(expression).address
    if not str_address:
        print("expression for breakpoint is not valid")
        return
    if get_breakpoints_in_range(str_address):
        print("breakpoint/watchpoint for address " + str_address + " is already set")
        return
    if breakpoint_type == typedefs.BREAKPOINT_TYPE.HARDWARE:
        if hardware_breakpoint_available():
            output = send_command("hbreak *" + str_address)
        else:
            print("All hardware breakpoint slots are being used, using a software breakpoint instead")
            output = send_command("break *" + str_address)
    elif breakpoint_type == typedefs.BREAKPOINT_TYPE.SOFTWARE:
        output = send_command("break *" + str_address)
    if regexes.breakpoint_created.search(output):
        global breakpoint_on_hit_dict
        number = regexes.breakpoint_number.search(output).group(1)
        breakpoint_on_hit_dict[number] = on_hit
        return number
    else:
        return


@execute_with_temporary_interruption
#:tag:BreakWatchpoints
def add_watchpoint(
    expression: str,
    length: int = 4,
    watchpoint_type: int = typedefs.WATCHPOINT_TYPE.BOTH,
    on_hit: int = typedefs.BREAKPOINT_ON_HIT.BREAK,
) -> list[str]:
    """Adds a watchpoint at the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression
        length (int): Length of the watchpoint
        watchpoint_type (int): Can be a member of typedefs.WATCHPOINT_TYPE
        on_hit (int): Can be a member of typedefs.BREAKPOINT_ON_HIT

    Returns:
        list: Numbers of the successfully set breakpoints as strings
    """
    str_address = examine_expression(expression).address
    if not str_address:
        print("expression for watchpoint is not valid")
        return
    if watchpoint_type == typedefs.WATCHPOINT_TYPE.WRITE_ONLY:
        watch_command = "watch"
    elif watchpoint_type == typedefs.WATCHPOINT_TYPE.READ_ONLY:
        watch_command = "rwatch"
    elif watchpoint_type == typedefs.WATCHPOINT_TYPE.BOTH:
        watch_command = "awatch"
    remaining_length = length
    breakpoints_set = []
    arch = get_inferior_arch()
    str_address_int = int(str_address, 16)
    breakpoint_addresses = []
    if arch == typedefs.INFERIOR_ARCH.ARCH_64:
        max_length = 8
    else:
        max_length = 4
    while remaining_length > 0:
        if remaining_length >= max_length:
            breakpoint_length = max_length
        else:
            breakpoint_length = remaining_length
        if get_breakpoints_in_range(str_address_int, breakpoint_length):
            print("breakpoint/watchpoint for address " + hex(str_address_int) + " is already set. Bailing out...")
            break
        if not hardware_breakpoint_available():
            print("All hardware breakpoint slots are being used, unable to set a new watchpoint. Bailing out...")
            break
        cmd = f"{watch_command} * (char[{breakpoint_length}] *) {hex(str_address_int)}"
        output = execute_func_temporary_interruption(send_command, cmd)
        if regexes.breakpoint_created.search(output):
            breakpoint_addresses.append([str_address_int, breakpoint_length])
        else:
            print("Failed to create a watchpoint at address " + hex(str_address_int) + ". Bailing out...")
            break
        breakpoint_number = regexes.breakpoint_number.search(output).group(1)
        breakpoints_set.append(breakpoint_number)
        global breakpoint_on_hit_dict
        breakpoint_on_hit_dict[breakpoint_number] = on_hit
        remaining_length -= max_length
        str_address_int += max_length
    global chained_breakpoints
    chained_breakpoints.append(breakpoint_addresses)
    return breakpoints_set


#:tag:BreakWatchpoints
def modify_breakpoint(expression, modify_what, condition=None, count=None):
    """Adds a condition to the breakpoint at the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression
        modify_what (int): Can be a member of typedefs.BREAKPOINT_MODIFY_TYPES
        This function modifies condition of the breakpoint if CONDITION, enables the breakpoint if ENABLE, disables the
        breakpoint if DISABLE, enables once then disables after hit if ENABLE_ONCE, enables for specified count then
        disables after the count is reached if ENABLE_COUNT, enables once then deletes the breakpoint if ENABLE_DELETE
        condition (str): Any gdb condition expression. This parameter is only used if modify_what passed as CONDITION
        count (int): Only used if modify_what passed as ENABLE_COUNT

    Returns:
        bool: True if the condition has been set successfully, False otherwise

    Examples:
        modify_what-->typedefs.BREAKPOINT_MODIFY_TYPES.CONDITION
        condition-->$eax==0x523
        condition-->$rax>0 && ($rbp<0 || $rsp==0)
        condition-->printf($r10)==3

        modify_what-->typedefs.BREAKPOINT_MODIFY_TYPES.ENABLE_COUNT
        count-->10
    """
    str_address = examine_expression(expression).address
    if not str_address:
        print("expression for breakpoint is not valid")
        return False
    str_address_int = int(str_address, 16)
    modification_list = [[str_address_int]]
    for n, item in enumerate(chained_breakpoints):
        for breakpoint in item:
            if breakpoint[0] <= str_address_int <= breakpoint[0] + breakpoint[1] - 1:
                modification_list = item
                break
    for breakpoint in modification_list:
        found_breakpoint = get_breakpoints_in_range(breakpoint[0])
        if not found_breakpoint:
            print("no such breakpoint exists for address " + str_address)
            continue
        else:
            breakpoint_number = found_breakpoint[0].number
        if modify_what == typedefs.BREAKPOINT_MODIFY.CONDITION:
            if condition is None:
                print("Please set condition first")
                return False
            send_command("condition " + breakpoint_number + " " + condition)
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE:
            send_command("enable " + breakpoint_number)
        elif modify_what == typedefs.BREAKPOINT_MODIFY.DISABLE:
            send_command("disable " + breakpoint_number)
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_ONCE:
            send_command("enable once " + breakpoint_number)
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_COUNT:
            if count is None:
                print("Please set count first")
                return False
            elif count < 1:
                print("Count can't be lower than 1")
                return False
            send_command("enable count " + str(count) + " " + breakpoint_number)
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_DELETE:
            send_command("enable delete " + breakpoint_number)
        else:
            print("Parameter modify_what is not valid")
            return False
    return True


#:tag:BreakWatchpoints
def delete_breakpoint(expression):
    """Deletes a breakpoint at the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression

    Returns:
        bool: True if the breakpoint has been deleted successfully, False otherwise
    """
    str_address = examine_expression(expression).address
    if not str_address:
        print("expression for breakpoint is not valid")
        return False
    str_address_int = int(str_address, 16)
    deletion_list = [[str_address_int]]
    global chained_breakpoints
    for n, item in enumerate(chained_breakpoints):
        for breakpoint in item:
            if breakpoint[0] <= str_address_int <= breakpoint[0] + breakpoint[1] - 1:
                deletion_list = item
                del chained_breakpoints[n]
                break
    for breakpoint in deletion_list:
        found_breakpoint = get_breakpoints_in_range(breakpoint[0])
        if not found_breakpoint:
            print("no such breakpoint exists for address " + str_address)
            continue
        else:
            breakpoint_number = found_breakpoint[0].number
        global breakpoint_on_hit_dict
        try:
            del breakpoint_on_hit_dict[breakpoint_number]
        except KeyError:
            pass
        send_command("delete " + breakpoint_number)
    return True


@execute_with_temporary_interruption
#:tag:BreakWatchpoints
def track_watchpoint(expression, length, watchpoint_type):
    """Starts tracking a value by setting a watchpoint at the address holding it
    Use get_track_watchpoint_info() to get info about the watchpoint you set

    Args:
        expression (str): Any gdb expression
        length (int): Length of the watchpoint
        watchpoint_type (int): Can be a member of typedefs.WATCHPOINT_TYPE

    Returns:
        list: Numbers of the successfully set breakpoints as strings
        None: If fails to set any watchpoint
    """
    breakpoints = add_watchpoint(expression, length, watchpoint_type, typedefs.BREAKPOINT_ON_HIT.FIND_CODE)
    if not breakpoints:
        return
    for breakpoint in breakpoints:
        send_command(
            "commands " + breakpoint + "\npince-get-track-watchpoint-info " + str(breakpoints) + "\nc&" + "\nend"
        )
    return breakpoints


#:tag:BreakWatchpoints
def get_track_watchpoint_info(watchpoint_list):
    """Gathers the information for the tracked watchpoint(s)

    Args:
        watchpoint_list (list): A list that holds the watchpoint numbers, must be returned from track_watchpoint()

    Returns:
        dict: Holds the program counter addresses at the moment watchpoint hits as keys
        Format of dict--> {address1:info_list1, address2:info_list2, ...}
        Format of info_list--> [count, previous_pc_address, register_info, float_info, disas_info]
        count-->(int) Count of the hits for the same pc address
        previous_pc_address-->(str) The address of the instruction that comes before the instruction pc address
        holds. If there's no previous address available(end of region etc.), previous_pc_address=pc_address
        register_info-->(dict) Same dict returned from read_registers()
        float_info-->(dict) Same dict returned from read_float_registers()
        disas_info-->(str) A small section that's disassembled just after previous_pc_counter
    """
    track_watchpoint_file = utils.get_track_watchpoint_file(currentpid, watchpoint_list)
    try:
        output = pickle.load(open(track_watchpoint_file, "rb"))
    except:
        output = ""
    return output


@execute_with_temporary_interruption
#:tag:BreakWatchpoints
def track_breakpoint(expression, register_expressions):
    """Starts tracking a value by setting a breakpoint at the address holding it
    Use get_track_breakpoint_info() to get info about the breakpoint you set

    Args:
        expression (str): Any gdb expression
        register_expressions (str): Register expressions, separated by a comma. Registers should start with "$"
        PINCE will gather info about values presented by register expressions every time the breakpoint is reached
        For instance, passing "$rax,$rcx+5,$rbp+$r12" will make PINCE track values rax, rcx+5 and rbp+r12

    Returns:
        str: Number of the breakpoint set
        None: If fails to set any breakpoint
    """
    breakpoint = add_breakpoint(expression, on_hit=typedefs.BREAKPOINT_ON_HIT.FIND_ADDR)
    if not breakpoint:
        return
    send_command(
        "commands "
        + breakpoint
        + "\npince-get-track-breakpoint-info "
        + register_expressions.replace(" ", "")
        + ","
        + breakpoint
        + "\nc&"
        + "\nend"
    )
    return breakpoint


#:tag:BreakWatchpoints
def get_track_breakpoint_info(breakpoint):
    """Gathers the information for the tracked breakpoint

    Args:
        breakpoint (str): breakpoint number, must be returned from track_breakpoint()

    Returns:
        dict: Holds the register expressions as keys and their info as values
        Format of dict--> {expression1:expression_info_dict1, expression2:expression_info_dict2, ...}
        expression-->(str) The register expression
        Format of expression_info_dict--> {value1:count1, value2:count2, ...}
        value-->(str) Value calculated by given register expression as hex str
        count-->(int) How many times this expression has been reached
    """
    track_breakpoint_file = utils.get_track_breakpoint_file(currentpid, breakpoint)
    try:
        output = pickle.load(open(track_breakpoint_file, "rb"))
    except:
        output = ""
    return output


class Tracer:
    def __init__(self) -> None:
        """Use set_breakpoint after init and if it succeeds, use tracer_loop within a thread
        There can be only one trace session at a time. Don't create new trace sessions before finishing the last one"""
        self.expression = ""
        self.max_trace_count = 1000
        self.stop_condition = ""
        self.step_mode = typedefs.STEP_MODE.SINGLE_STEP
        self.stop_after_trace = False
        self.collect_registers = True
        self.trace_status = typedefs.TRACE_STATUS.IDLE
        self.current_trace_count = 0
        self.trace_data = []
        self.cancel = False
        utils.change_trace_status(currentpid, self.trace_status)

    @execute_with_temporary_interruption
    def set_breakpoint(
        self,
        expression: str,
        max_trace_count: int = 1000,
        trigger_condition: str = "",
        stop_condition: str = "",
        step_mode: typedefs.STEP_MODE = typedefs.STEP_MODE.SINGLE_STEP,
        stop_after_trace: bool = False,
        collect_registers: bool = True,
    ) -> str:
        """Sets the breakpoint for tracing instructions at the address evaluated by the given expression

        Args:
            expression (str): Any gdb expression
            max_trace_count (int): Maximum number of steps taken while tracing. Must be greater than or equal to 1
            trigger_condition (str): Optional, any gdb expression. Tracing will start if the condition is met
            stop_condition (str): Optional, any gdb expression. Tracing will stop whenever the condition is met
            step_mode (int): Can be a member of typedefs.STEP_MODE
            stop_after_trace (bool): Inferior won't be continuing after the tracing process
            collect_registers (bool): Collect registers while stepping

        Returns:
            str: Number of the breakpoint set
            None: If fails to set any breakpoint or if max_trace_count is not valid
        """
        if max_trace_count < 1:
            print("max_trace_count must be greater than or equal to 1")
            return
        if type(max_trace_count) != int:
            print("max_trace_count must be an integer")
            return
        breakpoint = add_breakpoint(expression, on_hit=typedefs.BREAKPOINT_ON_HIT.TRACE)
        if not breakpoint:
            return
        modify_breakpoint(expression, typedefs.BREAKPOINT_MODIFY.CONDITION, condition=trigger_condition)
        (
            self.expression,
            self.max_trace_count,
            self.stop_condition,
            self.step_mode,
            self.stop_after_trace,
            self.collect_registers,
        ) = (expression, max_trace_count, stop_condition, step_mode, stop_after_trace, collect_registers)
        send_command("commands " + breakpoint + "\npince-trace-instructions\nend")
        return breakpoint

    def tracer_loop(self):
        """The main tracer loop, call within a thread"""
        global active_trace
        active_trace = True
        self.current_trace_count = 0
        trace_status_file = utils.get_trace_status_file(currentpid)
        while not (self.trace_status != typedefs.TRACE_STATUS.IDLE or self.cancel or currentpid == -1):
            try:
                with open(trace_status_file, "r") as trace_file:
                    self.trace_status = int(trace_file.read())
            except (ValueError, FileNotFoundError):
                pass
            sleep(0.1)
        delete_breakpoint(self.expression)
        self.trace_status = typedefs.TRACE_STATUS.TRACING

        # The reason we don't use a tree class is to make the tree json-compatible
        # tree format-->[node1, node2, node3, ...]
        # node-->[(line_info, register_dict), parent_index, child_index_list]
        tree = []
        current_index = 0  # Avoid calling len()
        current_root_index = 0
        root_index = 0

        # Root always be an empty node, it's up to you to use or delete it
        tree.append([("", None), None, []])
        try:  # In case process exits during the trace session
            for x in range(self.max_trace_count):
                if self.cancel or currentpid == -1:
                    break
                line_info = send_command("x/i $pc", cli_output=True).splitlines()[0].split(maxsplit=1)[1]
                collect_dict = OrderedDict()
                if self.collect_registers:
                    collect_dict.update(read_registers())
                    collect_dict.update(read_float_registers())
                current_index += 1
                tree.append([(line_info, collect_dict), current_root_index, []])
                tree[current_root_index][2].append(current_index)  # Add a child
                self.current_trace_count = x + 1
                if regexes.trace_instructions_ret.search(line_info):
                    if tree[current_root_index][1] is None:  # If no parents exist
                        current_index += 1
                        tree.append([("", None), None, [current_root_index]])
                        tree[current_root_index][1] = current_index  # Set new parent
                        current_root_index = current_index  # current_node=current_node.parent
                        root_index = current_root_index  # set new root
                    else:
                        current_root_index = tree[current_root_index][1]  # current_node=current_node.parent
                elif self.step_mode == typedefs.STEP_MODE.SINGLE_STEP:
                    if regexes.trace_instructions_call.search(line_info):
                        current_root_index = current_index
                if self.stop_condition:
                    try:
                        if str(parse_and_eval(self.stop_condition)) == "1":
                            break
                    except:
                        pass
                if self.step_mode == typedefs.STEP_MODE.SINGLE_STEP:
                    step_instruction()
                elif self.step_mode == typedefs.STEP_MODE.STEP_OVER:
                    step_over_instruction()
                wait_for_stop()
        except:
            traceback.print_exc()
        self.trace_data = (tree, root_index)
        self.trace_status = typedefs.TRACE_STATUS.FINISHED
        active_trace = False
        if not self.stop_after_trace:
            continue_inferior()

    def cancel_trace(self):
        """Prematurely ends the trace session, trace data will still be collected"""
        self.cancel = True


#:tag:Tools
def call_function_from_inferior(expression):
    """Calls the given function expression from the inferior

    Args:
        expression (str): Any gdb expression

    Returns:
        tuple: A tuple containing assigned value and result, both as str
        Returns a tuple of (False, False) if the call fails

    Examples:
        call_function_from_inferior("printf('123')") returns ("$26","3")
    """
    result = execute_func_temporary_interruption(send_command, f"call (void*(*)(char*, int)) {expression}")
    filtered_result = regexes.convenience_variable.search(result)
    if filtered_result:
        return filtered_result.group(1), filtered_result.group(2)
    return False, False


#:tag:InferiorInformation
def find_entry_point():
    """Finds entry point of the inferior

    Returns:
        str: Entry point as hex str
        None: If fails to find an entry point
    """
    result = send_command("info file")
    filtered_result = regexes.entry_point.search(result)
    if filtered_result:
        return filtered_result.group(1)


#:tag:Tools
def search_opcode(searched_str, starting_address, ending_address_or_offset, case_sensitive=False, enable_regex=False):
    """Searches for the given str in the disassembled output

    Args:
        searched_str (str): String that will be searched
        starting_address (str): Any gdb expression
        ending_address_or_offset (str): If you pass this parameter as an offset, you should add "+" in front of it
        (e.g "+42" or "+0x42"). If you pass this parameter as an hex address, the address range between the expression
        and the secondary address is disassembled.
        If the second parameter is an address. it always should be bigger than the first address.
        case_sensitive (bool): If True, search will be case sensitive
        enable_regex (bool): If True, searched_str will be treated as a regex expression

    Returns:
        list: A list of str values in this format-->[[address1,opcodes1],[address2, ...], ...]
        None: If enable_regex is True and given regex isn't valid
    """
    if enable_regex:
        try:
            if case_sensitive:
                regex = re.compile(searched_str)
            else:
                regex = re.compile(searched_str, re.IGNORECASE)
        except Exception as e:
            print("An exception occurred while trying to compile the given regex\n", str(e))
            return
    returned_list = []
    disas_output = disassemble(starting_address, ending_address_or_offset)
    for item in disas_output:
        address = item[0]
        opcode = item[2]
        if enable_regex:
            if not regex.search(opcode):
                continue
        else:
            if case_sensitive:
                if opcode.find(searched_str) == -1:
                    continue
            else:
                if opcode.lower().find(searched_str.lower()) == -1:
                    continue
        returned_list.append([address, opcode])
    return returned_list


#:tag:Tools
def dissect_code(region_list, discard_invalid_strings=True):
    """Searches given regions for jumps, calls and string references
    Use function get_dissect_code_data() to gather the results

    Args:
        region_list (list): A list of (start_address, end_address) -> (str, str)
        Can be returned from functions like utils.filter_regions
        discard_invalid_strings (bool): Entries that can't be decoded as utf-8 won't be included in referenced strings
    """
    send_command("pince-dissect-code", send_with_file=True, file_contents_send=(region_list, discard_invalid_strings))


#:tag:Tools
def get_dissect_code_status():
    """Returns the current state of dissect code process

    Returns:
        tuple:(current_region, current_region_count, referenced_strings_count,
                               referenced_jumps_count, referenced_calls_count)

        current_region-->(str) Currently scanned memory region
        current_region_count-->(str) "Region x of y"
        current_range-->(str) Currently scanned memory range(current buffer)
        referenced_strings_count-->(int) Count of referenced strings
        referenced_jumps_count-->(int) Count of referenced jumps
        referenced_calls_count-->(int) Count of referenced calls

        Returns a tuple of ("", "", "", 0, 0, 0) if fails to gather info
    """
    dissect_code_status_file = utils.get_dissect_code_status_file(currentpid)
    try:
        output = pickle.load(open(dissect_code_status_file, "rb"))
    except:
        output = "", "", "", 0, 0, 0
    return output


#:tag:Tools
def cancel_dissect_code():
    """Finishes the current dissect code process early on"""
    if last_gdb_command.find("pince-dissect-code") != -1:
        cancel_last_command()


#:tag:Tools
def get_dissect_code_data(referenced_strings=True, referenced_jumps=True, referenced_calls=True):
    """Returns shelve.DbfilenameShelf objects of referenced dicts

    Args:
        referenced_strings (bool): If True, include referenced strings in the returned list
        referenced_jumps (bool): If True, include referenced jumps in the returned list
        referenced_calls (bool): If True, include referenced calls in the returned list

    Returns:
        list: A list of shelve.DbfilenameShelf objects. Can be used as dicts, they are backwards compatible

        For instance, if you call this function with default params, you'll get this--▼
        [referenced_strings_dict,referenced_jumps_dict,referenced_calls_dict]

        And if you, let's say, pass referenced_jumps as False, you'll get this instead--▼
        [referenced_strings_dict,referenced_calls_dict]

        referenced_strings_dict-->(shelve.DbfilenameShelf object) Holds referenced string addresses
        Format: {referenced_address1:referrer_address_set1, referenced_address2:referrer_address_set2, ...}

        referenced_jumps_dict-->(shelve.DbfilenameShelf object) Holds referenced jump addresses
        Format: {referenced_address1:referenced_by_dict1, referenced_address2:referenced_by_dict2, ...}
        Format of referenced_by_dict: {address1:opcode1, address2:opcode2, ...}

        referenced_calls_dict-->(shelve.DbfilenameShelf object) Holds referenced call addresses
        Format: {referenced_address1:referrer_address_set1, referenced_address2:referrer_address_set2, ...}
    """
    dict_list = []
    if referenced_strings:
        dict_list.append(shelve.open(utils.get_referenced_strings_file(currentpid), "r"))
    if referenced_jumps:
        dict_list.append(shelve.open(utils.get_referenced_jumps_file(currentpid), "r"))
    if referenced_calls:
        dict_list.append(shelve.open(utils.get_referenced_calls_file(currentpid), "r"))
    return dict_list


#:tag:Tools
def search_referenced_strings(
    searched_str, value_index=typedefs.VALUE_INDEX.STRING_UTF8, case_sensitive=False, enable_regex=False
):
    """Searches for given str in the referenced strings

    Args:
        searched_str (str): String that will be searched
        value_index (int): Can be a member of typedefs.VALUE_INDEX
        case_sensitive (bool): If True, search will be case sensitive
        enable_regex (bool): If True, searched_str will be treated as a regex expression

    Returns:
        list: [[referenced_address1, reference_count1, found_value1], ...]
        None: If enable_regex is True and searched_str isn't a valid regex expression
    """
    if enable_regex:
        try:
            if case_sensitive:
                regex = re.compile(searched_str)
            else:
                regex = re.compile(searched_str, re.IGNORECASE)
        except Exception as e:
            print("An exception occurred while trying to compile the given regex\n", str(e))
            return
    str_dict = get_dissect_code_data(True, False, False)[0]
    mem_handle = memory_handle()
    returned_list = []
    for address, refs in str_dict.items():
        value = read_memory(int(address, 16), value_index, 100, mem_handle=mem_handle)
        value_str = "" if value is None else str(value)
        if not value_str:
            continue
        if enable_regex:
            if not regex.search(value_str):
                continue
        else:
            if case_sensitive:
                if value_str.find(searched_str) == -1:
                    continue
            else:
                if value_str.lower().find(searched_str.lower()) == -1:
                    continue
        returned_list.append((address, len(refs), value))
    str_dict.close()
    mem_handle.close()
    return returned_list


#:tag:Tools
def search_referenced_calls(searched_str, case_sensitive=True, enable_regex=False):
    """Searches for given str in the referenced calls

    Args:
        searched_str (str): String that will be searched
        case_sensitive (bool): If True, search will be case sensitive
        enable_regex (bool): If True, searched_str will be treated as a regex expression

    Returns:
        list: [[referenced_address1, found_string1], ...]
        None: If enable_regex is True and searched_str isn't a valid regex expression
    """
    param_str = (searched_str, case_sensitive, enable_regex)
    return send_command("pince-search-referenced-calls " + str(param_str), recv_with_file=True)


def complete_command(gdb_command):
    """Tries to complete the given gdb command and returns completion possibilities

    Args:
        gdb_command (str): The gdb command that'll be completed

    Returns:
        list: Possible completions as a list of str
    """
    returned_list = []
    for item in send_command("complete " + gdb_command, cli_output=True).splitlines():
        if not regexes.max_completions_reached.search(item):
            returned_list.append(item)
    return returned_list
