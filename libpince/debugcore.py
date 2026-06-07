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
from .utils import safe_str_to_int, safe_int_cast, logger
from typing import Any, Callable

self_pid = os.getpid()
libc = ctypes.CDLL("libc.so.6")
system_endianness = typedefs.ENDIANNESS.LITTLE if sys.byteorder == "little" else typedefs.ENDIANNESS.BIG

# A boolean value. True if gdb is initialized, False if not
gdb_initialized = False

# An integer. Can be a member of typedefs.INFERIOR_ARCH
inferior_arch = -1

# An integer. Can be a member of typedefs.INFERIOR_STATUS
inferior_status = -1

# An integer. PID of the current attached/created process
currentpid = -1

# An integer. Can be a member of typedefs.STOP_REASON
stop_reason = -1

# A dictionary. Holds breakpoint numbers and what to do on hit
# Format: {bp_num1:on_hit1, bp_num2:on_hit2, ...}
breakpoint_on_hit_dict = {}

# A dictionary. Holds address and aob of instructions that were nop'ed out
# Format: {identity: {address1:orig_instruction1_aob, address2:orig_instruction2_aob, ...}, ...}
# where identity = (pid, start_time) tuple
modified_instructions_dict = {}

# Identity (pid, start_time) of the current process, or None when detached
current_process_identity: tuple[int, int | None] | None = None

# If an action such as deletion or condition modification happens in one of the breakpoints in a list, others in the
# same list will get affected as well
# Format: [[bp_num1, bp_num2, ...], [bp_num1, ...], ...]
chained_breakpoints = []

breakpoints_changed = typedefs.Signal()
instructions_changed = typedefs.Signal()

child = object  # this object will be used with pexpect operations

# This Lock is used by the function send_command to ensure synchronous execution
lock_send_command = Lock()

# This condition is notified whenever status of the inferior changes
# Use the variable inferior_status to get information about inferior's status
# See CheckInferiorStatus class for an example
status_changed_condition = Condition()

# This condition is notified if the current inferior gets terminated
# See AwaitProcessExit class for an example
process_exited_condition = Condition()

# This condition is notified if gdb starts to wait for the prompt output
# See function send_command for an example
gdb_waiting_for_prompt_condition = Condition()

# A string. Stores the output of the last command. None means no output has been received yet.
gdb_output = None

# An instance of typedefs.RegisterQueue. Updated whenever GDB receives an async event such as breakpoint modification
# See AwaitAsyncOutput class for an example of usage
gdb_async_output = typedefs.RegisterQueue()

# A boolean value. Used to cancel the last gdb command sent
# Use the function cancel_ongoing_command to make use of this variable
# Return value of the current send_command call will be an empty string
cancel_send_command = False

# A boolean value. Used by state_observe_thread to check if a trace session is active
active_trace = False

# A boolean value. Used by dissect_code() to mark an ongoing code dissection.
dissect_code_active = False

# A boolean value. Set to True when a tracking breakpoint (on_hit != BREAK) was the last stop
# This prevents the subsequent *running event from notifying the UI
last_stop_was_tracking = False

# A string. Holds the last command sent to gdb
last_gdb_command = ""

# A list of booleans. Used to adjust gdb output
# Use the function set_gdb_output_mode to make use of this variable
gdb_output_mode = typedefs.gdb_output_mode(True, True, True)

# A string. Memory file of the currently attached/created process
mem_file = "/proc/" + str(currentpid) + "/mem"

# A string. Determines which signal to use to interrupt the process
interrupt_signal = "SIGINT"

# Dictionary that maps an id or name to allocated memory.
# If an user allocates memory without a name, it will be given a random ID set as string.
allocated_memory_chunks: dict[str, typedefs.AllocatedMemory] = {}

# ID generator used for the above
allocated_memory_gen_id = 0

# A string. Holds the main executable's basename. Used by is_address_static() and _refresh_main_module_info()
_main_module_name: str | None = None

# A bool. Used by is_address_static() and _refresh_main_module_info() to mark if the main executable is PIE enabled or not.
_main_module_is_static: bool = False

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


def set_gdb_output_mode(output_mode_tuple: typedefs.gdb_output_mode) -> None:
    """Adjusts gdb output

    Args:
        output_mode_tuple (typedefs.gdb_output_mode): Setting any field True will enable the output that's associated
        with that field. Setting it False will disable the associated output
    """
    global gdb_output_mode
    gdb_output_mode = output_mode_tuple


def cancel_ongoing_command() -> bool:
    """Cancels the last gdb command sent if it's still present

    Returns:
        bool: True if cancel was successful, False if nothing to cancel
    """
    if lock_send_command.locked():
        global cancel_send_command
        cancel_send_command = True
        return True
    return False


def send_command(
    command: str,
    control: bool = False,
    cli_output: bool = False,
    send_with_file: bool = False,
    file_contents_send: Any = None,
    recv_with_file: bool = False,
) -> Any:
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
        gdb_output = None
        if send_with_file:
            send_file = utils.get_from_pince_file(currentpid)
            with open(send_file, "wb") as send_file_handle:
                pickle.dump(file_contents_send, send_file_handle)
        if recv_with_file or cli_output:
            recv_file = utils.get_to_pince_file(currentpid)

            # Truncating the recv_file because we wouldn't like to see output of previous command in case of errors
            with open(recv_file, "w"):
                pass

        command = str(command)
        command = 'interpreter-exec mi "' + command + '"' if command.startswith("-") else command
        last_gdb_command = command if not control else "Ctrl+" + command
        if gdb_output_mode.command_info:
            logger.debug(f"Last gdb command: {last_gdb_command}")
        if control:
            child.sendcontrol(command)
        else:
            command_file = utils.get_gdb_command_file(currentpid)
            with open(command_file, "r+") as command_fd:
                command_fd.truncate()
                command_fd.write(command)
            if not cli_output:
                child.sendline("source " + command_file)
            else:
                child.sendline("cli-output source " + command_file)
        if not control:
            with gdb_waiting_for_prompt_condition:
                while gdb_output is None:
                    gdb_waiting_for_prompt_condition.wait(timeout=0.01)
                    if cancel_send_command:
                        break
            if not cancel_send_command:
                if recv_with_file or cli_output:
                    try:
                        with open(recv_file, "rb") as recv_file_handle:
                            output = pickle.load(recv_file_handle)
                    except (EOFError, pickle.UnpicklingError, OSError):
                        output = ""
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
                logger.debug(f"Processed gdb command in: {str(time1 - time0)}")
            except NameError:
                pass
        cancel_send_command = False
        return output


def state_observe_thread() -> None:
    """
    Observes the state of gdb, uses conditions to inform other functions and threads about gdb's state
    Also generates output for send_command function
    Should be called by creating a thread. Usually called in initialization process by attach function
    """

    def check_inferior_status() -> None:
        matches = regexes.gdb_state_observe.findall(child.before)
        if len(matches) > 0:
            global stop_reason
            global inferior_status
            global last_stop_was_tracking
            old_status = inferior_status
            for match in matches:
                if match[0].startswith('stopped,reason="exited'):
                    with process_exited_condition:
                        terminated_pid = currentpid
                        detach()
                        logger.info(f"Process terminated (PID: {terminated_pid})")
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

            # Check if the FINAL stopped event in this batch is a tracking breakpoint
            # We need to check the last *stopped event, not just any tracking bp in the batch
            # Because there might be multiple events arriving in same buffer
            if inferior_status == typedefs.INFERIOR_STATUS.STOPPED:
                # Find the LAST stopped event in matches (working backwards)
                last_stop_was_tracking = False
                for match in reversed(matches):
                    if match[0]:  # This is a *stopped event
                        bp_match = regexes.breakpoint_number.search(match[0])
                        if bp_match:
                            bp_num_str = bp_match.group(1)
                            # We'll use a default of BREAK as users might use the gdb console to place break conditions
                            # such as catchpoints, where they won't be added to breakpoint_on_hit_dict.
                            # Our own tracer which we must ignore will correctly use this dictionary so no worries there.
                            bp_on_hit = breakpoint_on_hit_dict.get(bp_num_str, typedefs.BREAKPOINT_ON_HIT.BREAK)
                            last_stop_was_tracking = bp_on_hit != typedefs.BREAKPOINT_ON_HIT.BREAK
                        # Found the last stopped event, stop searching
                        break
            # If we ended in RUNNING state, last_stop_was_tracking persists from previous STOPPED event

            # Don't notify UI if:
            # 1. Status hasn't changed
            # 2. Last stop was a tracking breakpoint
            # 3. A trace is active
            should_not_notify = old_status == inferior_status or last_stop_was_tracking or active_trace

            if not should_not_notify:
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
                    logger.debug(child.before)
            else:
                if gdb_output_mode.async_output:
                    logger.debug(child.before)
                gdb_async_output.broadcast_message(child.before)
    except (OSError, ValueError, pexpect.EOF) as e:
        if isinstance(e, pexpect.EOF):
            logger.exception(
                f"EOF exception caught within pexpect, here's the contents of child.before:\n{child.before}"
            )
        logger.info("Exiting state_observe_thread")


def execute_func_temporary_interruption(func: Callable, *args: Any, **kwargs: Any) -> Any:
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
    try:
        return func(*args, **kwargs)
    finally:
        if old_status == typedefs.INFERIOR_STATUS.RUNNING:
            continue_inferior()


def execute_with_temporary_interruption(func: Callable) -> Callable:
    """Decorator version of execute_func_temporary_interruption"""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return execute_func_temporary_interruption(func, *args, **kwargs)

    return wrapper


def can_attach(pid: int | str) -> bool:
    """Check if we can attach to the target

    Args:
        pid (int,str): PID of the process that'll be attached

    Returns:
        bool: True if attaching is successful, False otherwise
    """
    pid_int = safe_int_cast(pid)
    if pid_int == 0:
        return False
    result = libc.ptrace(16, pid_int, 0, 0)  # 16 is PTRACE_ATTACH, check ptrace.h for details
    if result == -1:
        return False
    os.waitpid(pid_int, 0)
    libc.ptrace(17, pid_int, 0, 0)  # 17 is PTRACE_DETACH
    sleep(0.01)
    return True


def wait_for_stop(timeout: float = 0) -> None:
    """Block execution till the inferior stops

    Args:
        timeout (float): Timeout time in seconds, passing 0 will wait for stop indefinitely
    """
    remaining_time = timeout
    while inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
        sleep(0.0001)
        if timeout == 0:
            continue
        remaining_time -= 0.0001
        if remaining_time < 0:
            break


def interrupt_inferior(interrupt_reason: int = typedefs.STOP_REASON.DEBUG) -> None:
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
    wait_for_stop(1)
    stop_reason = interrupt_reason


def continue_inferior() -> None:
    """Continue the inferior"""
    if currentpid == -1:
        return
    send_command("c&")


def step_instruction() -> None:
    """Step one assembly instruction"""
    send_command("stepi&")


def step_over_instruction() -> None:
    """Step over one assembly instruction"""
    send_command("nexti&")


def execute_till_return() -> None:
    """Continues inferior till current stack frame returns"""
    send_command("finish&")


def set_interrupt_signal(signal_name: str) -> None:
    """Decides on what signal to use to stop the process

    Args:
        signal_name (str): Name of the signal
    """
    global interrupt_signal
    handle_signal(signal_name, True, False)
    interrupt_signal = signal_name


def handle_signal(signal_name: str, stop: bool, pass_to_program: bool) -> None:
    """Decides on what will GDB do when the process recieves a signal

    Args:
        signal_name (str): Name of the signal
        stop (bool): Stop the program and print to the console
        pass_to_program (bool): Pass signal to program
    """
    params = [[signal_name, stop, pass_to_program]]
    send_command("pince-handle-signals", send_with_file=True, file_contents_send=params)


def handle_signals(signal_list: list) -> None:
    """Optimized version of handle_signal for multiple signals

    Args:
        signal_list (list): A list of the parameters of handle_signal
    """
    send_command("pince-handle-signals", send_with_file=True, file_contents_send=signal_list)


def init_gdb(gdb_path: str = utils.get_default_gdb_path()) -> bool:
    """Spawns gdb and initializes/resets some of the global variables

    Args:
        gdb_path (str): Path of the gdb binary

    Returns:
        bool: True if initialization is successful, False otherwise

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
    global last_stop_was_tracking
    utils.init_user_files()
    detach()

    # Temporary IPC_PATH, this little hack is needed because send_command requires a valid IPC_PATH
    utils.create_ipc_path(currentpid)
    utils.create_tmp_path(currentpid)

    breakpoint_on_hit_dict.clear()
    chained_breakpoints.clear()
    gdb_output = None
    cancel_send_command = False
    last_gdb_command = ""
    last_stop_was_tracking = False

    libpince_dir = utils.get_libpince_directory()
    child = pexpect.spawn(
        f"{gdb_path} --nx --interpreter=mi",
        cwd=libpince_dir,
        env=os.environ | {"LC_NUMERIC": "C"},
        encoding="utf-8",
        codec_errors="replace",
    )
    child.setecho(False)
    child.delaybeforesend = 0
    child.timeout = None
    try:
        child.expect_exact("(gdb)")
    except pexpect.EOF:
        logger.exception(f"EOF exception caught within pexpect, here's the contents of child.before:\n{child.before}")
        return False
    status_thread = Thread(target=state_observe_thread)
    status_thread.daemon = True
    status_thread.start()
    gdb_initialized = True
    set_logging(False)
    if not os.environ.get("APPDIR"):
        send_command("source ./gdbinit_venv")
    set_pince_paths()
    send_command("source " + utils.get_user_path(typedefs.USER_PATHS.GDBINIT))
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT))
    return True


def set_logging(state: bool) -> None:
    """Sets logging on or off

    Args:
        state (bool): Sets logging on if True, off if False
    """
    send_command("set logging enabled off")
    send_command("set logging file " + utils.get_logging_file(currentpid))
    if state:
        send_command("set logging enabled on")


def set_pince_paths() -> None:
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


def init_referenced_dicts(pid: int | str) -> None:
    """Initializes referenced dict shelve databases

    Args:
        pid (int,str): PID of the attached process
    """
    with shelve.open(utils.get_referenced_strings_file(pid), "c"):
        pass
    with shelve.open(utils.get_referenced_jumps_file(pid), "c"):
        pass
    with shelve.open(utils.get_referenced_calls_file(pid), "c"):
        pass


def attach(pid: int | str, gdb_path: str = utils.get_default_gdb_path()) -> int:
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
    global current_process_identity
    currentpid = pid
    current_process_identity = (currentpid, utils.get_process_start_time(currentpid))
    mem_file = "/proc/" + str(currentpid) + "/mem"
    utils.create_ipc_path(pid)
    utils.create_tmp_path(pid)
    send_command("attach " + str(pid))
    set_pince_paths()
    init_referenced_dicts(pid)
    inferior_arch = get_inferior_arch()
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT_AA))
    _refresh_main_module_info()
    return typedefs.ATTACH_RESULT.SUCCESSFUL


def create_process(
    process_path: str, args: str = "", ld_preload_path: str = "", gdb_path: str = utils.get_default_gdb_path()
) -> bool:
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
    global current_process_identity
    if currentpid != -1 or not gdb_initialized:
        init_gdb(gdb_path)
    output = send_command(f'file "{process_path}"')
    if regexes.gdb_error.search(output):
        logger.error(f"An error occurred while trying to create process from the file at {process_path}")
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
    if pid is None:
        logger.error("Failed to get inferior pid while creating process!")
        detach()
        return False
    currentpid = int(pid)
    current_process_identity = (currentpid, utils.get_process_start_time(currentpid))
    mem_file = "/proc/" + str(currentpid) + "/mem"
    utils.create_ipc_path(pid)
    utils.create_tmp_path(pid)
    set_pince_paths()
    init_referenced_dicts(pid)
    inferior_arch = get_inferior_arch()
    utils.execute_script(utils.get_user_path(typedefs.USER_PATHS.PINCEINIT_AA))
    _refresh_main_module_info()
    return True


def detach() -> None:
    """See you, space cowboy"""
    global gdb_initialized
    global currentpid
    global current_process_identity
    old_pid = currentpid
    current_process_identity = None
    if gdb_initialized:
        global child
        global inferior_status
        currentpid = -1
        inferior_status = -1
        gdb_initialized = False
        child.close()
    if old_pid != -1:
        utils.delete_ipc_path(old_pid)
    logger.info(f"Detached from the process with PID: {str(old_pid)}")


def toggle_attach() -> int | None:
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


def is_attached() -> bool:
    """Checks if gdb is attached to the current process

    Returns:
        bool: True if attached, False if not
    """
    if regexes.gdb_error.search(send_command("info proc")):
        return False
    return True


def inject_so(library_path: str) -> bool:
    """Injects the given .so file to the current process using dlopen.
    This function will first try to ask gdb to resolve "dlopen"/"__libc_dlopen_mode" by symbol name.
    If that fails (stripped binary or no libc symbol loaded yet), it will fallback to resolving
    the address manually by using /proc/<pid>/maps + the on-disk .dynsym and then calling the function.

    Args:
        library_path (str): Path to the .so file that'll be injected

    Returns:
        bool: True if the injection is successful, False if no dlopen found.
    """
    if currentpid == -1:
        return False
    quoted = '"' + library_path + '"'
    # Try using GDB to resolve the symbols.
    for func in ("dlopen", "__libc_dlopen_mode"):
        result = call_function_from_inferior(f"{func}({quoted}, 2)")[1]
        if result and result != "0":
            return True
    # Fallback to manual address resolution if GDB failed.
    _lib_regexes = [
        r"^libc\.so", r"^libc-[\d.]+\.so", r"libc\.musl", r"ld-musl",
        r"^libdl\.so", r"^libdl-[\d.]+\.so",
    ]
    _sym_names = ["dlopen", "__libc_dlopen_mode"]
    for regex in _lib_regexes:
        module = utils.get_module_load_bias(currentpid, regex)
        if module is None:
            continue
        load_bias, path = module
        symbols = utils.get_defined_dynamic_symbols(path, _sym_names)
        for sym in _sym_names:
            if sym not in symbols:
                continue
            addr = load_bias + symbols[sym]
            cmd = f'call ((void *(*)(char *, int)) {addr})("{library_path}", 2)'
            out = execute_func_temporary_interruption(send_command, cmd)
            m = regexes.convenience_variable.search(out)
            if not m:
                continue
            hex_m = regexes.hex_number_grouped.search(m.group(2))
            if hex_m and int(hex_m.group(1), 16) != 0:
                return True
    return False


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


def memory_handle(mode: str = "rb") -> io.BufferedReader:
    """
    Acquire the handle of the currently attached process

    Args:
        mode (str): string detailing the open mode, default "rb"

    Returns:
        BinaryIO: A file handle that points to the memory file of the current process
    """
    return open(mem_file, mode)


@execute_with_temporary_interruption
def allocate_memory(size: int, name: str | None) -> int:
    global allocated_memory_chunks
    global allocated_memory_gen_id
    if size == 0:
        return 0
    if name == None:
        allocated_memory_gen_id += 1
        name = str(allocated_memory_gen_id)
    output = send_command(f"p (void*)malloc({size})")
    match = regexes.hex_number.search(output)
    if match == None:
        logger.error("Memory allocation failed!")
        return 0
    allocated_address = safe_str_to_int(match[0], 16)
    if allocated_address == 0:
        logger.error(f"Couldn't find allocation address! Allocation output: {output}")
        return 0
    allocated_memory = typedefs.AllocatedMemory(allocated_address, size, current_process_identity)
    allocated_memory_chunks[name] = allocated_memory
    page_size = os.sysconf("SC_PAGE_SIZE")
    page_memory_addr = allocated_memory.address & ~(page_size - 1)
    end_addr = allocated_memory.address + size
    end_page_addr = (end_addr + page_size - 1) & ~(page_size - 1)
    mprotect_length = end_page_addr - page_memory_addr
    send_command(f"p (int)mprotect({page_memory_addr}, {mprotect_length}, 7)")  # PROT_READ | PROT_WRITE | PROT_EXEC = 7
    return allocated_memory.address


@execute_with_temporary_interruption
def free_memory(name: str) -> bool:
    global allocated_memory_chunks
    if not isinstance(name, str):
        logger.error(f"Passed wrong type '{type(name)}' instead of str")
        return False
    if name == "":
        logger.error(f"Passed empty str!")
        return False
    allocated_memory = allocated_memory_chunks.get(name)
    if allocated_memory is None:
        logger.error(f"Couldn't find allocated memory with name `{name}`!")
        return False
    if allocated_memory.identity != current_process_identity:
        logger.error(f"Refusing to free memory '{name}' belonging to a different process")
        return False
    # This shit will crash the process if you call it on invalid or already freed memory.
    send_command(f"p (void)free({allocated_memory.address})")
    del allocated_memory_chunks[name]
    return True


def read_memory(
    address: str | int,
    value_index: int,
    length: int = 0,
    zero_terminate: bool = True,
    value_repr: int = typedefs.VALUE_REPR.UNSIGNED,
    endian: int = typedefs.ENDIANNESS.HOST,
    mem_handle: io.BufferedReader | None = None,
) -> str | float | int | None:
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
        mem_handle (io.BufferedReader, None): A file handle that points to the memory file of the current process
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
        return
    if not type(address) == int:
        try:
            address = int(address, 0)
        except:
            return
    packed_data = typedefs.index_to_valuetype_dict.get(value_index, -1)
    if typedefs.VALUE_INDEX.is_string(value_index):
        try:
            length = int(length)
        except:
            return
        if not length > 0:
            return
        expected_length = length * typedefs.string_index_to_multiplier_dict.get(value_index, 1)
    elif value_index == typedefs.VALUE_INDEX.AOB:
        try:
            expected_length = int(length)
        except:
            return
        if not expected_length > 0:
            return
    else:
        expected_length = packed_data[0]
        data_type = packed_data[1]
    own_mem_handle = mem_handle is None
    try:
        if own_mem_handle:
            mem_handle = memory_handle()
        mem_handle.seek(address)
        data_read = mem_handle.read(expected_length)
        if (
            endian != typedefs.ENDIANNESS.HOST
            and system_endianness != endian
            and typedefs.VALUE_INDEX.is_number(value_index)
        ):
            data_read = data_read[::-1]
    except (OSError, ValueError):
        # TODO (read/write error output)
        # Disabled read error printing. If needed, find a way to implement error logging with this function
        # I've initially thought about enabling it on demand via a parameter but this function already has too many
        # Maybe creating a function that toggles logging on and off? Other functions could use it too
        # print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + expected_length))
        return
    finally:
        if own_mem_handle and mem_handle is not None:
            mem_handle.close()
    if len(data_read) < expected_length:
        return
    if typedefs.VALUE_INDEX.is_string(value_index):
        encoding, option = typedefs.resolve_string_encoding(value_index, endian, system_endianness)
        returned_string = data_read.decode(encoding, option)
        if zero_terminate:
            if returned_string.startswith("\x00"):
                returned_string = "\x00"
            else:
                returned_string = returned_string.split("\x00")[0]
        return returned_string[0:length]
    elif value_index == typedefs.VALUE_INDEX.AOB:
        return " ".join(format(n, "02x") for n in data_read)
    else:
        is_integer = typedefs.VALUE_INDEX.is_integer(value_index)
        if is_integer and value_repr == typedefs.VALUE_REPR.SIGNED:
            data_type = data_type.lower()
        result = struct.unpack_from(data_type, data_read)[0]
        if is_integer and value_repr == typedefs.VALUE_REPR.HEX:
            return hex(result)
        return result


def write_memory(
    address: str | int,
    value_index: int,
    value: str | int | float | list[int],
    zero_terminate: bool = True,
    endian: int = typedefs.ENDIANNESS.HOST,
) -> None:
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
            return
    if isinstance(value, str):
        write_data = utils.parse_string(value, value_index)
        if write_data is None:
            return
    else:
        write_data = value
    if typedefs.VALUE_INDEX.is_string(value_index):
        encoding, option = typedefs.resolve_string_encoding(value_index, endian, system_endianness)
        write_data = write_data.encode(encoding, option)
        if zero_terminate:
            write_data += b"\x00"
    else:
        if value_index is typedefs.VALUE_INDEX.AOB:
            write_data = bytearray(write_data)
        else:
            data_type = typedefs.index_to_struct_pack_dict.get(value_index, -1)
            write_data = struct.pack(data_type, write_data)
        if endian != typedefs.ENDIANNESS.HOST and system_endianness != endian and typedefs.VALUE_INDEX.is_number(value_index):
            write_data = write_data[::-1]
    try:
        with memory_handle("rb+") as mem_handle:
            mem_handle.seek(address)
            mem_handle.write(write_data)
    except (OSError, ValueError):
        # Refer to TODO (read/write error output)
        # print("Can't access the memory at address " + hex(address) + " or offset " + hex(address + len(write_data)))
        return


def aob_scan(
    pattern: str,
    writable: bool | None = None,
    executable: bool | None = None,
    limit: int | None = 1000,
) -> list[int]:
    """Scan readable memory regions of the attached process for a byte pattern.

    Args:
        pattern: Whitespace-separated hex tokens. Use '?' or '??' for wildcard bytes,
                 e.g. '48 8b 05 ?? ?? ?? ??'.
        writable: If True/False, restrict to writable/non-writable regions. None = either.
        executable: If True/False, restrict to executable/non-executable regions. None = either.
        limit: Stop after this many matches. None = unlimited.

    Returns:
        List of match addresses in ascending order. Empty list if no process is attached.
    """
    if currentpid == -1:
        return []
    parts = [b"." if "?" in t else re.escape(bytes([int(t, 16)])) for t in pattern.split()]
    if not parts:
        return []
    matcher = re.compile(b"".join(parts), re.DOTALL)
    overlap = len(parts) - 1
    results = []
    with memory_handle() as mem:
        for start, end, perms, *_ in utils.get_regions(currentpid):
            if "r" not in perms:
                continue
            if writable is not None and ("w" in perms) != writable:
                continue
            if executable is not None and ("x" in perms) != executable:
                continue
            position = int(start, 16)
            end_addr = int(end, 16)
            tail = b""
            while position < end_addr:
                read_size = min(1 << 20, end_addr - position)
                try:
                    mem.seek(position)
                    chunk = mem.read(read_size)
                except (OSError, ValueError):
                    position += read_size
                    tail = b""
                    continue
                data = tail + chunk
                base = position - len(tail)
                for match in matcher.finditer(data):
                    results.append(base + match.start())
                    if limit is not None and len(results) >= limit:
                        return results
                tail = data[-overlap:] if overlap else b""
                position += read_size
    return results


def disassemble(expression: str, offset_or_address: str) -> list[tuple[str, str, str]]:
    """Disassembles the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression
        offset_or_address (str): If you pass this parameter as an offset, you should add "+" in front of it
        (e.g "+42" or "+0x42"). If you pass this parameter as an hex address, the address range between the expression
        and the secondary address is disassembled
        If the second parameter is an address, it always should be bigger than the first address

    Returns:
        list: A list of str values in this format-->[(address1, bytes1, instr1), (address2, ...), ...]
    """
    output = send_command("disas /r " + expression + "," + offset_or_address)
    disas_data = []
    for line in output.splitlines():
        result = regexes.disassemble_output.search(line)
        if result:
            disas_data.append(result.groups())
    return disas_data


def convert_to_hex(expression: str) -> str:
    """Converts numeric values in the expression into their hex equivalents
    Respects edge cases like indexed maps and keeps indices as decimals

    Args:
        expression (str): Any gdb expression

    Returns:
        str: Converted str
    """
    # TODO (lldb): We'll most likely write our own expression parser once we switch to lldb
    # Merge this function with examine_expression and gdbutils.examine_expression once that happens
    return regexes.expression_with_hex.sub(
        lambda m: "0x" + m.group(1) if m.group(1) and not examine_expression(m.group(1)).symbol else m.group(0),
        expression,
    )


def examine_expression(expression: str) -> typedefs.tuple_examine_expression:
    """Evaluates the given expression and returns evaluated value, address and symbol

    Args:
        expression (str): Any gdb expression

    Returns:
        typedefs.tuple_examine_expression: Evaluated value, address and symbol in a tuple
        Any erroneous field will be returned as None instead of str
    """
    if currentpid == -1:
        return typedefs.tuple_examine_expression(None, None, None)
    result = send_command(
        "pince-examine-expressions", send_with_file=True, file_contents_send=[expression], recv_with_file=True
    )
    if not result:
        return typedefs.tuple_examine_expression(None, None, None)
    return result[0]


def examine_expressions(expression_list: list[str]) -> list[typedefs.tuple_examine_expression]:
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


def parse_and_eval(expression: str, cast: type = str) -> Any:
    """Calls gdb.parse_and_eval with the given expression and returns the value after casting with the given type
    Use examine_expression if your data can be expressed as an address or a symbol, use this function otherwise
    Unlike examine_expression, this function can read data that has void type or multiple type representations
    For instance:

    - $eflags has both str and int reprs
    - $_siginfo is a struct with many fields
    - x64 register convenience vars such as $rax are void if the process is x86

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


def _refresh_main_module_info() -> None:
    """Caches main module info for static address checking. Called by attach() and create_process().

    Identifies the main module and whether its address is static (no ASLR or PIE) or not:
    - Native Linux: main module is /proc/PID/exe. Static if ET_EXEC (non-PIE).
    - Windows PE under WINE: main module is the first .exe with executable permissions in /proc/PID/maps.
      Static if DllCharacteristics has the IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE bit cleared.
    """
    global _main_module_name, _main_module_is_static
    _main_module_name = None
    _main_module_is_static = False
    if currentpid == -1:
        return
    try:
        exe_link = os.readlink(f"/proc/{currentpid}/exe")
    except OSError:
        return

    if "wine" in os.path.basename(exe_link).lower():
        # Running under WINE, find the launched .exe in maps.
        # Note: WINE/Proton maps PE files as r--p (no x bit), so we don't filter on permissions.
        module_path = next(
            (path for _, _, _, _, _, _, path in utils.get_regions(currentpid) if path.lower().endswith(".exe")),
            None,
        )
        if module_path is None:
            return
    else:
        module_path = exe_link

    try:
        with open(module_path, "rb") as f:
            magic = f.read(4)
            if magic.startswith(b"\x7fELF"):
                f.seek(0x05)  # EI_DATA
                byteorder = {b"\x01": "little", b"\x02": "big"}.get(f.read(1))
                if byteorder is None:
                    return  # Invalid ELF data encoding
                f.seek(0x10)
                is_static = int.from_bytes(f.read(2), byteorder) == 2  # ET_EXEC
            elif magic[:2] == b"MZ":
                f.seek(0x3C)
                pe_offset = int.from_bytes(f.read(4), "little")  # PE mandates little endian, regardless of sys arch.
                f.seek(pe_offset)
                if f.read(4) != b"PE\x00\x00":
                    return
                f.seek(pe_offset + 4 + 20 + 0x46)  # COFF header + DllCharacteristics offset
                is_static = (int.from_bytes(f.read(2), "little") & 0x40) == 0  # IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE
            else:
                return
            _main_module_name = os.path.basename(module_path)
            _main_module_is_static = is_static
    except (OSError, ValueError):
        pass


def is_address_static(address: str | int) -> bool:
    """Checks if the given address is a static address

    Returns True only for addresses inside the main module when that module is loaded at a fixed base:
    - Native Linux: non-PIE ELF (ET_EXEC)
    - WINE/Proton Windows: PE without IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE
    Everything else is subject to ASLR.

    Args:
        address (str | int): Address to check, in either hex str or int format

    Returns:
        bool: True if the absolute address is static across restarts, False otherwise
    """
    if not _main_module_is_static:
        return False
    if isinstance(address, str):
        address_str = utils.extract_hex_address(address)
        if not address_str:
            logger.error(f"Invalid hex address string '{address}'")
            return False
        address = int(address_str, 16)
    elif not isinstance(address, int):
        logger.error(f"Passed wrong type '{type(address)}' instead of str or int")
        return False
    region_info = utils.get_region_info(currentpid, address)
    return region_info is not None and region_info.file_name == _main_module_name


def get_thread_info() -> str | None:
    """Invokes "info threads" command and returns the line corresponding to the current thread

    Returns:
        str: Current thread information
        None: If the output doesn't fit the regex
    """
    thread_info = send_command("info threads")
    current_thread = regexes.thread_info.search(thread_info)
    if not current_thread:
        return
    return re.sub(r'\\"', r'"', current_thread.group(1))


def find_closest_instruction_address(
    address: str, instruction_location: str = "next", instruction_count: int = 1
) -> str | None:
    """Finds address of the closest instruction next to the given address, assuming that the given address is valid

    Args:
        address (str): Hex address or any gdb expression that can be used in disas command
        instruction_location (str): If it's "next", instructions coming after the address is searched
        If it's "previous", the instructions coming before the address is searched instead
        instruction_count (int): Number of the instructions that'll be looked for

    Returns:
        str: The address found as hex string. If starting/ending of a valid memory range is reached, starting/ending
        address is returned instead as hex string.
        None: If the given address is not in a valid memory region.

    Note:
        From gdb version 7.12 and onwards, inputting negative numbers in x command are supported(x/-3i for instance)
        So, modifying this function according to the changes in 7.12 may speed up things a little bit but also breaks
        the backwards compatibility. The speed gain is not much of a big deal compared to backwards compatibility, so
        I'm not changing this function for now
    """
    if instruction_location not in ("next", "previous"):
        raise ValueError(f"invalid instruction_location: {instruction_location!r}")
    region_info = utils.get_region_info(currentpid, address)
    if region_info is None:
        return
    if instruction_location == "next":
        offset = "+" + str(instruction_count * 30)
        disas_data = disassemble(address, address + offset)
    else:
        offset = "-" + str(instruction_count * 30)
        disas_data = disassemble(address + offset, address)
    if not disas_data:
        if instruction_location != "next":
            start_address = hex(region_info.start)
            disas_data = disassemble(start_address, address)
    if instruction_location == "next":
        try:
            return utils.extract_hex_address(disas_data[instruction_count][0])
        except IndexError:
            return hex(region_info.end)
    else:
        try:
            return utils.extract_hex_address(disas_data[-instruction_count][0])
        except IndexError:
            try:
                return start_address
            except UnboundLocalError:
                return hex(region_info.start)


def get_address_info(expression: str) -> str:
    """Runs the gdb command "info symbol" for given expression and returns the result of it

    Args:
        expression (str): Any gdb expression

    Returns:
        str: The result of the command "info symbol" for given expression
    """
    return send_command("info symbol " + expression, cli_output=True)


def get_symbol_info(expression: str) -> str:
    """Runs the gdb command "info address" for given expression and returns the result of it

    Args:
        expression (str): Any gdb expression

    Returns:
        str: The result of the command "info address" for given expression
    """
    return send_command("info address " + expression, cli_output=True)


def search_functions(expression: str, case_sensitive: bool = False) -> list:
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


def get_inferior_pid() -> str | None:
    """Get pid of the current inferior

    Returns:
        str: pid
        None: If the output doesn't fit the regex
    """
    output = send_command("info inferior")
    inferior_pid = regexes.inferior_pid.search(output)
    if not inferior_pid:
        return
    return inferior_pid.group(1)


def get_inferior_arch() -> int:
    """Returns the architecture of the current inferior

    Returns:
        int: A member of typedefs.INFERIOR_ARCH
    """
    if parse_and_eval("$rax") == "void":
        return typedefs.INFERIOR_ARCH.ARCH_32
    return typedefs.INFERIOR_ARCH.ARCH_64


def read_registers() -> dict[str, str | None]:
    """Returns the current registers

    Returns:
        dict[str, str | None]: A dict that holds general, flag and segment registers. Check typedefs.REGISTERS for the
        full list. Segment register values may be None when the register can't be resolved
    """
    return send_command("pince-read-registers", recv_with_file=True)


def read_float_registers() -> OrderedDict[str, str]:
    """Returns the current floating point registers

    Returns:
        OrderedDict[str, str]: A dict that holds floating point registers. Check typedefs.REGISTERS.FLOAT for the full list

    Note:
        Returned xmm values are based on xmm.v4_float
    """
    return send_command("pince-read-float-registers", recv_with_file=True)


def set_convenience_variable(variable: str, value: str) -> None:
    """Sets given convenience variable to given value
    Can be also used for modifying registers directly

    Args:
        variable (str): Any gdb convenience variable(with "$" character removed)
        value (str): Anything
    """
    send_command("set $" + variable + "=" + value)


def set_register_flag(flag: str, value: int | str) -> None:
    """Sets given register flag to given value

    Args:
        flag (str): A member of typedefs.REGISTERS.FLAG
        value (Union[int,str]): 0 or 1
    """
    value = str(value)
    if value != "0" and value != "1":
        raise Exception(value + " isn't valid value. It can be only 0 or 1")
    if flag not in typedefs.REGISTERS.FLAG:
        raise Exception(flag + " isn't a valid flag, must be a member of typedefs.REGISTERS.FLAG")
    flag_index = typedefs.REGISTERS.FLAG.index(flag)
    # EFLAGS has reserved gaps at bits 1, 3 and 5, which typedefs.REGISTERS.FLAG omits.
    flag_bit = flag_index + min(flag_index, 3)
    flag_mask = 1 << flag_bit
    eflags = parse_and_eval("$eflags", int)
    if eflags is None:
        raise Exception("Couldn't read $eflags")
    if value == "1":
        eflags |= flag_mask
    else:
        eflags &= ~flag_mask
    set_convenience_variable("eflags", hex(eflags))


def get_stacktrace_info() -> list:
    """Returns information about current stacktrace

    Returns:
        list: A list of str values in this format-->[[return_address_info1,frame_address_info1],[info2, ...], ...]

        return_address_info looks like this-->Return address of frame+symbol-->0x40c431 <_start>
        frame_address_info looks like this-->Beginning of frame+distance from stack pointer-->0x7ffe1e989a40(rsp+0x100)
    """
    return send_command("pince-get-stack-trace-info", recv_with_file=True)


def get_stack_info(from_base_pointer: bool = False) -> list[str]:
    """Returns information about current stack
    Also can view stack from EBP or RBP register

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
    if from_base_pointer:
        return send_command("pince-get-stack-info from-base-pointer", recv_with_file=True)
    else:
        return send_command("pince-get-stack-info", recv_with_file=True)


def get_stack_frame_return_addresses() -> list:
    """Returns return addresses of stack frames

    Returns:
        list: A list of str values in this format-->[return_address_info1,return_address_info2, ...]

        return_address_info looks like this-->Return address of frame+symbol-->0x40c431 <_start>
    """
    return send_command("pince-get-frame-return-addresses", recv_with_file=True)


def get_stack_frame_info(index: int | str) -> str:
    """Returns information about stack by the given index

    Args:
        index (int,str): Index of the frame

    Returns:
        str: Information that looks like this::

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


def hex_dump(address: int, offset: int) -> list[str]:
    """Returns hex dump of range (address to address+offset)

    Args:
        address (int): Self-explanatory
        offset (int): The range that'll be read

    Returns:
        list: List of byte values read as uppercase hex strings. Unreadable bytes are returned as "??".

    Examples:
        returned list-->["??","??","??","7f","43","67","40","??","??, ...]
    """
    hex_byte_list = []
    with memory_handle() as mem_handle:
        for i in range(offset):
            try:
                mem_handle.seek(address + i)
                byte = mem_handle.read(1)
                current_item = format(byte[0], "02X") if byte else "??"
            except (OSError, ValueError, IndexError):
                current_item = "??"
            hex_byte_list.append(current_item)
    return hex_byte_list


def get_modified_instructions() -> dict:
    """Returns currently modified instructions

    Returns:
        dict: A dictionary where the key is the start address of instruction and value is the aob before modifying

    """
    return modified_instructions_dict.get(current_process_identity, {})


def nop_instruction(start_address: int, length: int) -> None:
    """Writes length NOPs beginning at start_address

    Args:
        start_address (int): Self-explanatory
        length (int): how many NOPs

    Returns:
        None
    """
    old_aob = " ".join(hex_dump(start_address, length))
    table = modified_instructions_dict.setdefault(current_process_identity, {})
    if start_address not in table:
        table[start_address] = old_aob

    nop_aob = " ".join(["90"] * length)
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, nop_aob)
    instructions_changed.emit()


def modify_instruction(start_address: int, array_of_bytes: str) -> None:
    """Replaces an instruction's opcodes with new bytes

    Args:
        start_address (int): Self-explanatory
        array_of_bytes (str): String that contains the replacement bytes of the instruction

    Returns:
        None
    """
    length = len(array_of_bytes.split())
    old_aob = " ".join(hex_dump(start_address, length))

    table = modified_instructions_dict.setdefault(current_process_identity, {})
    if start_address not in table:
        table[start_address] = old_aob
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, array_of_bytes)
    instructions_changed.emit()


def restore_instruction(start_address: int) -> None:
    """Restores a modified instruction to its original opcodes

    Args:
        start_address (int): Self-explanatory

    Returns:
        None
    """
    table = modified_instructions_dict.get(current_process_identity)
    if not table or start_address not in table:
        return
    array_of_bytes = table.pop(start_address)
    write_memory(start_address, typedefs.VALUE_INDEX.AOB, array_of_bytes)
    instructions_changed.emit()


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
            address = utils.extract_hex_address(what)
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
        address = safe_str_to_int(address, 0)
        if address == 0:
            return breakpoint_list
    max_address = max(address, address + length - 1)
    min_address = min(address, address + length - 1)
    breakpoint_info = get_breakpoint_info()
    for item in breakpoint_info:
        breakpoint_address = safe_str_to_int(item.address, 16)
        if not (max_address < breakpoint_address or min_address > breakpoint_address + item.size - 1):
            breakpoint_list.append(item)
    return breakpoint_list


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


def add_breakpoint(
    expression: str,
    breakpoint_type: int = typedefs.BREAKPOINT_TYPE.HARDWARE,
    on_hit: int = typedefs.BREAKPOINT_ON_HIT.BREAK,
) -> int | None:
    """Adds a breakpoint at the address evaluated by the given expression. Uses a software breakpoint if all hardware
    breakpoint slots are being used

    Args:
        expression (str): Any gdb expression
        breakpoint_type (int): Can be a member of typedefs.BREAKPOINT_TYPE
        on_hit (int): Can be a member of typedefs.BREAKPOINT_ON_HIT

    Returns:
        int: Number of the breakpoint set
        None: If setting breakpoint fails
    """
    output = ""
    str_address = examine_expression(expression).address
    if not str_address:
        logger.error(f"Failed to add breakpoint. Expression {expression} is not valid")
        return
    if get_breakpoints_in_range(str_address):
        logger.error(f"Breakpoint/Watchpoint for address {str_address} is already set")
        return
    if breakpoint_type == typedefs.BREAKPOINT_TYPE.HARDWARE:
        if hardware_breakpoint_available():
            output = send_command("hbreak *" + str_address)
        else:
            logger.warning("All hardware breakpoint slots are being used, using a software breakpoint instead")
            output = send_command("break *" + str_address)
    elif breakpoint_type == typedefs.BREAKPOINT_TYPE.SOFTWARE:
        output = send_command("break *" + str_address)
    if regexes.breakpoint_created.search(output):
        global breakpoint_on_hit_dict
        breakpoint_number = regexes.breakpoint_number.search(output)
        if not breakpoint_number:
            logger.error(f"Failed to extract breakpoint number from GDB output: {output}")
            return
        number = breakpoint_number.group(1)
        breakpoint_on_hit_dict[number] = on_hit
        breakpoints_changed.emit()
        return int(number)
    else:
        return


@execute_with_temporary_interruption
def add_watchpoint(
    expression: str,
    length: int = 4,
    watchpoint_type: int = typedefs.WATCHPOINT_TYPE.BOTH,
    on_hit: int = typedefs.BREAKPOINT_ON_HIT.BREAK,
) -> list[str] | None:
    """Adds a watchpoint at the address evaluated by the given expression

    Args:
        expression (str): Any gdb expression
        length (int): Length of the watchpoint
        watchpoint_type (int): Can be a member of typedefs.WATCHPOINT_TYPE
        on_hit (int): Can be a member of typedefs.BREAKPOINT_ON_HIT

    Returns:
        list: Numbers of the successfully set breakpoints as strings
        None: If setting watchpoint fails
    """
    str_address = examine_expression(expression).address
    if not str_address:
        logger.error(f"Expression '{expression}' for watchpoint is not valid")
        return
    if watchpoint_type == typedefs.WATCHPOINT_TYPE.WRITE_ONLY:
        watch_command = "watch"
    elif watchpoint_type == typedefs.WATCHPOINT_TYPE.READ_ONLY:
        watch_command = "rwatch"
    elif watchpoint_type == typedefs.WATCHPOINT_TYPE.BOTH:
        watch_command = "awatch"
    remaining_length = length
    breakpoints_set = []
    breakpoints_nums = []
    arch = get_inferior_arch()
    str_address_int = int(str_address, 16)
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
            logger.error(f"Breakpoint/Watchpoint for address {hex(str_address_int)} is already set. Bailing out...")
            break
        if not hardware_breakpoint_available():
            logger.error("All hardware breakpoint slots are being used, unable to set a new watchpoint. Bailing out...")
            break
        cmd = f"{watch_command} * (char[{breakpoint_length}] *) {hex(str_address_int)}"
        output = execute_func_temporary_interruption(send_command, cmd)
        if not regexes.breakpoint_created.search(output):
            logger.error(f"Failed to create a watchpoint at address {hex(str_address_int)}. Bailing out...")
            break
        breakpoint_number_match = regexes.breakpoint_number.search(output)
        if not breakpoint_number_match:
            logger.error(f"Failed to extract watchpoint number from GDB output: {output}")
            break
        breakpoint_number = breakpoint_number_match.group(1)
        breakpoints_set.append(breakpoint_number)
        breakpoints_nums.append(safe_int_cast(breakpoint_number))
        global breakpoint_on_hit_dict
        breakpoint_on_hit_dict[breakpoint_number] = on_hit
        remaining_length -= max_length
        str_address_int += max_length
    global chained_breakpoints
    chained_breakpoints.append(breakpoints_nums)
    if breakpoints_set:
        breakpoints_changed.emit()
    return breakpoints_set


def modify_breakpoint(
    breakpoint_number: int, modify_what: int, condition: str | None = None, count: int | None = None
) -> bool:
    """Adds a condition to an existing breakpoint

    Args:
        breakpoint_number (int): Breakpoint number in gdb
        modify_what (typedefs.BREAKPOINT_MODIFY): This param controls how the function modifies the breakpoint:
        - Modifies condition of the breakpoint if CONDITION
        - Enables the breakpoint if ENABLE
        - Disables the breakpoint if DISABLE
        - Enables once then disables after hit if ENABLE_ONCE
        - Enables for specified count then disables after the count is reached if ENABLE_COUNT
        - Enables once then deletes the breakpoint if ENABLE_DELETE
        condition (str | None): Any gdb condition expression. This parameter is only used if modify_what passed as CONDITION
        count (int | None): Only used if modify_what passed as ENABLE_COUNT

    Returns:
        bool: True if the condition has been set successfully, False otherwise

    Examples:
        modify_what-->typedefs.BREAKPOINT_MODIFY.CONDITION
        condition-->$eax==0x523
        condition-->$rax>0 && ($rbp<0 || $rsp==0)
        condition-->printf($r10)==3

        modify_what-->typedefs.BREAKPOINT_MODIFY.ENABLE_COUNT
        count-->10
    """
    modification_list = [breakpoint_number]
    global chained_breakpoints
    for _, item in enumerate(chained_breakpoints):
        for breakpoint in item:
            if breakpoint == breakpoint_number:
                modification_list = item
                break
    for breakpoint in modification_list:
        if modify_what == typedefs.BREAKPOINT_MODIFY.CONDITION:
            if condition is None:
                logger.error("Missing condition for breakpoint modification")
                return False
            send_command(f"condition {breakpoint} {condition}")
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE:
            send_command(f"enable {breakpoint}")
        elif modify_what == typedefs.BREAKPOINT_MODIFY.DISABLE:
            send_command(f"disable {breakpoint}")
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_ONCE:
            send_command(f"enable once {breakpoint}")
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_COUNT:
            if count is None:
                logger.error("Missing count parameter for ENABLE_COUNT breakpoint modification")
                return False
            elif count < 1:
                logger.error(f"Count parameter can't be less than 1 for ENABLE_COUNT breakpoint modification")
                return False
            send_command(f"enable count {count} {breakpoint}")
        elif modify_what == typedefs.BREAKPOINT_MODIFY.ENABLE_DELETE:
            send_command(f"enable delete {breakpoint}")
        else:
            logger.error("Parameter modify_what is not valid")
            return False
    breakpoints_changed.emit()
    return True


def delete_breakpoint(breakpoint_number: int) -> bool:
    """Deletes a breakpoint by given number

    Args:
        breakpoint_number (int)

    Returns:
        bool: True if the breakpoint has been deleted successfully, False otherwise
    """
    deletion_list = [breakpoint_number]
    global chained_breakpoints
    for n, item in enumerate(chained_breakpoints):
        if breakpoint_number in item:
            deletion_list = item
            del chained_breakpoints[n]
            break
    for breakpoint in deletion_list:
        global breakpoint_on_hit_dict
        try:
            del breakpoint_on_hit_dict[str(breakpoint)]
        except KeyError:
            pass
        send_command(f"delete {breakpoint}")
    breakpoints_changed.emit()
    return True


@execute_with_temporary_interruption
def track_watchpoint(expression: str, length: int, watchpoint_type: int) -> list[str] | None:
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


def get_track_watchpoint_info(watchpoint_list: list) -> dict | str:
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
        with open(track_watchpoint_file, "rb") as track_watchpoint_handle:
            output = pickle.load(track_watchpoint_handle)
    except:
        output = ""
    return output


@execute_with_temporary_interruption
def track_breakpoint(expression: str, register_expressions: str) -> int | None:
    """Starts tracking a value by setting a breakpoint at the address holding it
    Use get_track_breakpoint_info() to get info about the breakpoint you set

    Args:
        expression (str): Any gdb expression
        register_expressions (str): Register expressions, separated by a comma. Registers should start with "$"
        PINCE will gather info about values presented by register expressions every time the breakpoint is reached
        For instance, passing "$rax,$rcx+5,$rbp+$r12" will make PINCE track values rax, rcx+5 and rbp+r12

    Returns:
        int: Number of the breakpoint set
        None: If fails to set any breakpoint
    """
    breakpoint = add_breakpoint(expression, on_hit=typedefs.BREAKPOINT_ON_HIT.FIND_ADDR)
    if not breakpoint:
        return
    # TODO (lldb): When we switch to LLDB, remove c& and only continue if there isn't an active trace
    # Apply the same for track_watchpoint
    send_command(
        f"commands {breakpoint}\npince-get-track-breakpoint-info {register_expressions.replace(' ', '')},{breakpoint}\nc&\nend"
    )
    return breakpoint


def get_track_breakpoint_info(breakpoint_number: int) -> dict | str:
    """Gathers the information for the tracked breakpoint

    Args:
        breakpoint_number (int): breakpoint number, must be returned from track_breakpoint()

    Returns:
        dict: Holds the register expressions as keys and their info as values
        Format of dict--> {expression1:expression_info_dict1, expression2:expression_info_dict2, ...}
        expression-->(str) The register expression
        Format of expression_info_dict--> {value1:count1, value2:count2, ...}
        value-->(str) Value calculated by given register expression as hex str
        count-->(int) How many times this expression has been reached
    """
    track_breakpoint_file = utils.get_track_breakpoint_file(currentpid, breakpoint_number)
    try:
        with open(track_breakpoint_file, "rb") as track_breakpoint_handle:
            output = pickle.load(track_breakpoint_handle)
    except:
        output = ""
    return output


class Tracer:
    def __init__(self) -> None:
        """Use set_breakpoint after init and if it succeeds, use tracer_loop within a thread
        There can be only one trace session at a time. Don't create new trace sessions before finishing the last one"""
        self.bp_num = -1
        self.max_trace_count = 1000
        self.stop_condition = ""
        self.step_mode = typedefs.STEP_MODE.SINGLE_STEP
        self.stop_after_trace = False
        self.collect_registers = True
        self.trace_status = typedefs.TRACE_STATUS.IDLE
        self.current_trace_count = 0
        self.trace_data = ([], None)
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
    ) -> int | None:
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
            int: Number of the breakpoint set
            None: If fails to set any breakpoint or if max_trace_count is not valid
        """
        if type(max_trace_count) != int:
            logger.error(f"max_trace_count must be an integer. Was given type '{type(max_trace_count)}'")
            return
        if max_trace_count < 1:
            logger.error("max_trace_count must be greater than or equal to 1")
            return
        breakpoint = add_breakpoint(expression, on_hit=typedefs.BREAKPOINT_ON_HIT.TRACE)
        if not breakpoint:
            return
        modify_breakpoint(breakpoint, typedefs.BREAKPOINT_MODIFY.CONDITION, condition=trigger_condition)
        (
            self.bp_num,
            self.max_trace_count,
            self.stop_condition,
            self.step_mode,
            self.stop_after_trace,
            self.collect_registers,
        ) = (breakpoint, max_trace_count, stop_condition, step_mode, stop_after_trace, collect_registers)
        send_command(f"commands {breakpoint}\npince-trace-instructions\nend")
        return breakpoint

    def tracer_loop(self) -> None:
        """The main tracer loop, call within a thread"""
        self.current_trace_count = 0
        trace_status_file = utils.get_trace_status_file(currentpid)
        while not (self.trace_status != typedefs.TRACE_STATUS.IDLE or self.cancel or currentpid == -1):
            try:
                with open(trace_status_file, "r") as trace_file:
                    self.trace_status = int(trace_file.read())
            except (ValueError, FileNotFoundError):
                pass
            sleep(0.1)
        if self.cancel or currentpid == -1:
            delete_breakpoint(self.bp_num)
            self.trace_status = typedefs.TRACE_STATUS.FINISHED
            return
        global active_trace
        active_trace = True
        delete_breakpoint(self.bp_num)
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
                output_lines = send_command("x/i $pc", cli_output=True).splitlines()
                if not output_lines:
                    logger.warning("empty GDB output, stopping trace")
                    break
                line_parts = output_lines[0].split(maxsplit=1)
                if len(line_parts) < 2:
                    logger.warning("unexpected GDB output format, stopping trace")
                    break
                line_info = line_parts[1]
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

    def cancel_trace(self) -> None:
        """Prematurely ends the trace session, trace data will still be collected"""
        self.cancel = True


def call_function_from_inferior(expression: str) -> tuple[str, str] | tuple[bool, bool]:
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


def find_entry_point() -> str | None:
    """Finds entry point of the inferior

    Returns:
        str: Entry point as hex str
        None: If fails to find an entry point
    """
    result = send_command("info file")
    filtered_result = regexes.entry_point.search(result)
    if filtered_result:
        return filtered_result.group(1)


def search_instr(
    searched_str: str,
    starting_address: str,
    ending_address_or_offset: str,
    case_sensitive: bool = False,
    enable_regex: bool = False,
) -> list | None:
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
        list: A list of str values in this format-->[[address1, instr1],[address2, ...], ...]
        None: If enable_regex is True and given regex isn't valid
    """
    if enable_regex:
        try:
            if case_sensitive:
                regex = re.compile(searched_str)
            else:
                regex = re.compile(searched_str, re.IGNORECASE)
        except Exception:
            logger.exception(f"An exception occurred while trying to compile the given regex '{searched_str}'")
            return
    else:
        searched_str = regexes.whitespaces.sub(" ", searched_str).strip()
    returned_list = []
    disas_output = disassemble(starting_address, ending_address_or_offset)
    for item in disas_output:
        address = item[0]
        instr = item[2]
        corrected_instruction = regexes.whitespaces.sub(" ", instr).strip()
        if enable_regex:
            if not regex.search(corrected_instruction):
                continue
        else:
            if case_sensitive:
                if corrected_instruction.find(searched_str) == -1:
                    continue
            else:
                if corrected_instruction.lower().find(searched_str.lower()) == -1:
                    continue
        returned_list.append([address, instr])
    return returned_list


def dissect_code(region_list: list, discard_invalid_strings: bool = True) -> None:
    """Searches given regions for jumps, calls and string references
    Use function get_dissect_code_data() to gather the results

    Args:
        region_list (list): A list of (start_address, end_address) -> (str, str)
        Can be returned from functions like utils.filter_regions
        discard_invalid_strings (bool): Entries that can't be decoded as utf-8 won't be included in referenced strings
    """
    global dissect_code_active
    dissect_code_active = True
    try:
        send_command(
            "pince-dissect-code", send_with_file=True, file_contents_send=(region_list, discard_invalid_strings)
        )
    finally:
        dissect_code_active = False


def get_dissect_code_status() -> tuple:
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
        with open(dissect_code_status_file, "rb") as dissect_code_status_handle:
            output = pickle.load(dissect_code_status_handle)
    except:
        output = "", "", "", 0, 0, 0
    return output


def cancel_dissect_code() -> None:
    """Finishes the current dissect code process early on"""
    if dissect_code_active:
        cancel_ongoing_command()


def get_dissect_code_data(
    referenced_strings: bool = True, referenced_jumps: bool = True, referenced_calls: bool = True
) -> list[shelve.Shelf]:
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
        Format of referenced_by_dict: {address1:instr1, address2:instr2, ...}

        referenced_calls_dict-->(shelve.DbfilenameShelf object) Holds referenced call addresses
        Format: {referenced_address1:referrer_address_set1, referenced_address2:referrer_address_set2, ...}
    """
    dict_list = []
    try:
        if referenced_strings:
            dict_list.append(shelve.open(utils.get_referenced_strings_file(currentpid), "r"))
        if referenced_jumps:
            dict_list.append(shelve.open(utils.get_referenced_jumps_file(currentpid), "r"))
        if referenced_calls:
            dict_list.append(shelve.open(utils.get_referenced_calls_file(currentpid), "r"))
    except Exception:
        for opened_dict in dict_list:
            opened_dict.close()
        raise
    return dict_list


def search_referenced_strings(
    searched_str: str,
    value_index: int = typedefs.VALUE_INDEX.STRING_UTF8,
    case_sensitive: bool = False,
    enable_regex: bool = False,
) -> list | None:
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
        except Exception:
            logger.exception(f"An exception occurred while trying to compile the given regex '{searched_str}'")
            return
    str_dict = get_dissect_code_data(True, False, False)[0]
    try:
        returned_list = []
        with memory_handle() as mem_handle:
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
    finally:
        str_dict.close()
    return returned_list


def search_referenced_calls(searched_str: str, case_sensitive: bool = True, enable_regex: bool = False) -> list | None:
    """Searches for given str in the referenced calls

    Args:
        searched_str (str): String that will be searched
        case_sensitive (bool): If True, search will be case sensitive
        enable_regex (bool): If True, searched_str will be treated as a regex expression

    Returns:
        list: [[referenced_address1, found_string1], ...]
        None: If enable_regex is True and searched_str isn't a valid regex expression
    """
    return send_command(
        "pince-search-referenced-calls",
        send_with_file=True,
        file_contents_send=(searched_str, case_sensitive, enable_regex),
        recv_with_file=True,
    )


def complete_command(gdb_command: str) -> list[str]:
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
