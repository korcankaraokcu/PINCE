from PyQt6.QtCore import QObject, QLocale, QT_TR_NOOP
from collections import OrderedDict

language_list = OrderedDict([("en_US", "English"), ("it_IT", "Italiano"), ("zh_CN", "简体中文")])


def get_locale() -> str:
    system_locale = QLocale.system().name()
    return system_locale if system_locale in language_list else "en_US"


class TranslationConstants(QObject):
    @staticmethod
    def translate() -> None:
        for key, value in vars(TranslationConstants).items():
            if not key.startswith("__") and isinstance(value, str):
                setattr(TranslationConstants, key, TranslationConstants.tr(value))

    PAUSE_HOTKEY = QT_TR_NOOP("Pause the process")
    BREAK_HOTKEY = QT_TR_NOOP("Break the process")
    CONTINUE_HOTKEY = QT_TR_NOOP("Continue the process")
    CANCEL_HOTKEY = QT_TR_NOOP("Cancel ongoing GDB command")
    TOGGLE_ATTACH_HOTKEY = QT_TR_NOOP("Toggle attach/detach")
    SPEEDHACK_TOGGLE_HOTKEY = QT_TR_NOOP("Toggle speedhack")
    SPEEDHACK_SPEED_UP_HOTKEY = QT_TR_NOOP("Speedhack - Increase speed")
    SPEEDHACK_SPEED_DOWN_HOTKEY = QT_TR_NOOP("Speedhack - Decrease speed")
    EXACT_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Exact")
    NOT_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Not")
    INC_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Increased")
    INC_BY_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Increased By")
    DEC_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Decreased")
    DEC_BY_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Decreased By")
    LESS_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Less Than")
    MORE_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - More Than")
    BETWEEN_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Between")
    CHANGED_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Changed")
    UNCHANGED_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Unchanged")
    ERROR = QT_TR_NOOP("Error")
    SUCCESS = QT_TR_NOOP("Success")
    INFO = QT_TR_NOOP("Information")
    UPDATE_CHECK_FAILED = QT_TR_NOOP("Could not check for updates.")
    UPDATE_AVAILABLE_MESSAGE = QT_TR_NOOP(
        "A newer PINCE AppImage is available.\n\n"
        "You can grab it from PINCE's GitHub releases or update this AppImage with AppImageUpdate/appimageupdatetool."
    )
    UPDATE_NOT_AVAILABLE = QT_TR_NOOP("This PINCE AppImage is up to date.")
    DISABLED_UNDER_WINE = QT_TR_NOOP("This feature is not available while attached to a WINE/Proton process!")
    SPEEDHACK_UNAVAILABLE = QT_TR_NOOP("Speedhack couldn't be enabled for this process.")
    GDB_INIT = QT_TR_NOOP("GDB isn't initialized yet")
    GDB_INIT_ERROR = QT_TR_NOOP(
        "Unable to initialize GDB\n"
        "You might want to reinstall GDB or use the system GDB\n"
        "To change the current GDB path, check Settings->Debug"
    )
    EDIT = QT_TR_NOOP("Edit")
    SHOW_HEX = QT_TR_NOOP("Show as hexadecimal")
    SHOW_DEC = QT_TR_NOOP("Show as decimal")
    SHOW_UNSIGNED = QT_TR_NOOP("Show as unsigned")
    SHOW_SIGNED = QT_TR_NOOP("Show as signed")
    TOGGLE = QT_TR_NOOP("Toggle")
    TOGGLE_CHILDREN = QT_TR_NOOP("Toggle including children")
    AUTO = QT_TR_NOOP("Auto")
    BROWSE_MEMORY_REGION = QT_TR_NOOP("Browse this memory region")
    DISASSEMBLE_ADDRESS = QT_TR_NOOP("Disassemble this address")
    DELETE = QT_TR_NOOP("Delete")
    DELETE_SELECTION = QT_TR_NOOP("Delete selection")
    CUT = QT_TR_NOOP("Cut")
    COPY = QT_TR_NOOP("Copy")
    PASTE = QT_TR_NOOP("Paste")
    STOP = QT_TR_NOOP("Stop")
    STOPPING = QT_TR_NOOP("Stopping")
    PASTE_INSIDE = QT_TR_NOOP("Paste inside")
    POINTER_SCAN = QT_TR_NOOP("Pointer scan for this address")
    POINTER_SCANNER = QT_TR_NOOP("Open pointer scanner")
    POINTER_SCAN_SUCCESS = QT_TR_NOOP("Pointer scan finished. Found {} valid pointer paths.")
    POINTER_FILTER_SUCCESS = QT_TR_NOOP("Pointer filtering finished. Found {} stable pointer paths.")
    SCANNING_POINTERS = QT_TR_NOOP("Scanning for pointers")
    RESOLVING_POINTERS = QT_TR_NOOP("Resolving pointer paths")
    BASE_ADDRESS = QT_TR_NOOP("Base Address")
    OFFSET = QT_TR_NOOP("Offset")
    POINTER_PATH_COUNT = QT_TR_NOOP("Pointer paths count: {}")
    WHAT_WRITES = QT_TR_NOOP("Find out what writes to this address")
    WHAT_READS = QT_TR_NOOP("Find out what reads this address")
    WHAT_ACCESSES = QT_TR_NOOP("Find out what accesses this address")
    ADD_GROUP = QT_TR_NOOP("Add to a new group")
    CREATE_GROUP = QT_TR_NOOP("Create a new group")
    GROUP = QT_TR_NOOP("Group")
    INVALID_CLIPBOARD = QT_TR_NOOP("Invalid clipboard content")
    NEW_SCAN = QT_TR_NOOP("New Scan")
    MATCH_COUNT_LIMITED = QT_TR_NOOP("Match count: {} ({} shown)")
    MATCH_COUNT = QT_TR_NOOP("Match count: {}")
    NO_DESCRIPTION = QT_TR_NOOP("No Description")
    OPEN_PCT_FILE = QT_TR_NOOP("Open PCT file(s)")
    OPEN_SCRIPT_FILE = QT_TR_NOOP("Open script file")
    SAVE_SCRIPT_FILE = QT_TR_NOOP("Save script file")
    UNTITLED = QT_TR_NOOP("(untitled)")
    SCRIPT_FAILED = QT_TR_NOOP("Script execution failed")
    UNSAVED_SCRIPT = QT_TR_NOOP("Unsaved script")
    SAVE_SCRIPT_CHANGES = QT_TR_NOOP("Save changes to {}?")
    SCRIPT_RUNNING = QT_TR_NOOP("--- Running {} ---")
    SCRIPT_FINISHED = QT_TR_NOOP("--- Finished ---")
    SCRIPT_NO_DISABLE = QT_TR_NOOP("This script has no [DISABLE] section")
    SEND_TO_TABLE = QT_TR_NOOP("Send to cheat table")
    SENT_TO_TABLE = QT_TR_NOOP("Sent to the cheat table")
    SCRIPT = QT_TR_NOOP("Script")
    EDIT_SCRIPT = QT_TR_NOOP("Edit script")
    SCRIPT_RUN_FAILED = QT_TR_NOOP("Running the script failed, see the details below.\n\n{}")

    # Keep file extensions such as (*.pct) while translating, it doesn't matter where it stays within the sentence
    # For instance, you can keep (*.pct) in the beginning of the sentence for right-to-left languages like arabic
    # Apply the same to similar entries below
    FILE_TYPES_PCT = QT_TR_NOOP("PINCE Cheat Table (*.pct)")
    FILE_TYPES_SCRIPT = QT_TR_NOOP("Python Scripts (*.py)")
    SHARED_OBJECT_TYPE = QT_TR_NOOP("Shared object library (*.so)")
    DLL_TYPE = QT_TR_NOOP("Dynamic-link library (*.dll)")
    FILE_TYPES_TRACE = QT_TR_NOOP("Trace File (*.trace)")
    FILE_TYPES_POINTER_MAP = QT_TR_NOOP("Pointer Scan Map (*.lmptr)")
    ADD_TO_ADDRESS_TABLE = QT_TR_NOOP("Add to address table")
    FILE_LOAD_ERROR = QT_TR_NOOP("File {} is inaccessible or contains invalid content")
    SAVE_PCT_FILE = QT_TR_NOOP("Save PCT file")
    FILE_SAVE_ERROR = QT_TR_NOOP("Cannot save to file")
    SMARTASS = QT_TR_NOOP("Nice try, smartass")
    PROCESS_NOT_VALID = QT_TR_NOOP("Selected process is not valid")
    ALREADY_DEBUGGING = QT_TR_NOOP("You're debugging this process already")
    ALREADY_TRACED = QT_TR_NOOP("That process is already being traced by {}, could not attach to the process")
    PERM_DENIED = QT_TR_NOOP("Permission denied, could not attach to the process")
    CREATE_PROCESS_ERROR = QT_TR_NOOP("An error occurred while trying to create process")
    SCAN_FOR = QT_TR_NOOP("Scan for")
    FIRST_SCAN = QT_TR_NOOP("First Scan")
    NO_PROCESS_SELECTED = QT_TR_NOOP("No Process Selected")
    STATUS_DETACHED = QT_TR_NOOP("[detached]")
    STATUS_STOPPED = QT_TR_NOOP("[stopped]")
    REQUIRE_PROCESS_STOP = QT_TR_NOOP("This requires the process to be stopped")
    ENTER_VALUE = QT_TR_NOOP("Enter the new value")
    ENTER_DESCRIPTION = QT_TR_NOOP("Enter the new description")
    ENTER_ADDRESS = QT_TR_NOOP("Enter the new address")
    EDIT_ADDRESS = QT_TR_NOOP("Edit Address")
    SELECT_PROCESS = QT_TR_NOOP("Please select a process first")
    SELECT_BINARY = QT_TR_NOOP("Select the target binary")
    ENTER_OPTIONAL_ARGS = QT_TR_NOOP("Enter the optional arguments")
    LD_PRELOAD_OPTIONAL = QT_TR_NOOP("LD_PRELOAD .so path (optional)")
    REFRESH = QT_TR_NOOP("Refresh")
    LENGTH_NOT_VALID = QT_TR_NOOP("Length is not valid")
    LENGTH_GT = QT_TR_NOOP("Length must be greater than 0")
    PARSE_ERROR = QT_TR_NOOP("Can't parse the input")
    IS_INVALID_REGEX = QT_TR_NOOP("{} isn't a valid regex")
    LANG_RESET = QT_TR_NOOP("Language settings will take effect upon the next restart")
    GDB_RESET = QT_TR_NOOP("You have changed the GDB path, reset GDB now?")
    RESET_DEFAULT_SETTINGS = QT_TR_NOOP("This will reset to the default settings\n" "Proceed?")
    MOUSE_OVER_EXAMPLES = QT_TR_NOOP("Mouse over on this text for examples")
    AUTO_ATTACH_TOOLTIP = QT_TR_NOOP(
        "asdf|qwer --> search for asdf or qwer\n"
        "[as]df --> search for both adf and sdf\n"
        "Use the char \\ to escape special chars such as [\n"
    )
    SEPARATE_PROCESSES_WITH = QT_TR_NOOP("Separate processes with {}")
    UNUSED_APPIMAGE_SETTING = QT_TR_NOOP("This setting is unused in AppImage builds")
    SELECT_GDB_BINARY = QT_TR_NOOP("Select the gdb binary")
    QUIT_SESSION_CRASH = QT_TR_NOOP("Quitting current session will crash PINCE")
    CONT_SESSION_CRASH = QT_TR_NOOP("Use global hotkeys or the commands 'interrupt' and 'c&' to stop/run the inferior")

    # For some languages, it might be hard to keep the pipe characters balanced
    # You are free to modify pipes and dashes as you like when translating
    # Check Chinese translation for an example
    GDB_CONSOLE_INIT = QT_TR_NOOP(
        "Hotkeys:\n"
        "-----------------------------\n"
        "Send: Enter                 |\n"
        "Multi-line mode: Ctrl+Enter |\n"
        "Complete command: Tab       |\n"
        "-----------------------------\n"
        "Commands:\n"
        "----------------------------------------------------------\n"
        "/clear: Clear the console                                |\n"
        "phase-out: Detach from the current process               |\n"
        "phase-in: Attach back to the previously detached process |\n"
        "---------------------------------------------------------------------------------------------------\n"
        "You can change the output mode from bottom right\n"
        "Changing output mode only affects commands sent. Any other output coming from external sources"
        "(e.g async output) will be shown in MI format"
    )
    BREAK = QT_TR_NOOP("Break[{}]")
    RUN = QT_TR_NOOP("Run[{}]")
    TOGGLE_ATTACH = QT_TR_NOOP("Toggle Attach[{}]")
    BREAKPOINT_FAILED = QT_TR_NOOP("Failed to set breakpoint at address {}")
    WATCHPOINT_FAILED = QT_TR_NOOP("Failed to set watchpoint at address {}")
    COPY_CLIPBOARD = QT_TR_NOOP("Copy to Clipboard")
    GO_TO_EXPRESSION = QT_TR_NOOP("Go to expression")
    ADD_TO_ADDRESS_LIST = QT_TR_NOOP("Add this address to address list")
    SET_WATCHPOINT = QT_TR_NOOP("Set Watchpoint")
    WRITE_ONLY = QT_TR_NOOP("Write Only")
    READ_ONLY = QT_TR_NOOP("Read Only")
    BOTH = QT_TR_NOOP("Both")
    CHANGE_BREAKPOINT_CONDITION = QT_TR_NOOP("Add/Change condition for breakpoint")
    SET_BREAKPOINT = QT_TR_NOOP("Set Breakpoint")
    TOGGLE_BREAKPOINT = QT_TR_NOOP("Toggle Breakpoint")
    DELETE_BREAKPOINT = QT_TR_NOOP("Delete Breakpoint")
    ENTER_EXPRESSION = QT_TR_NOOP("Enter the expression")
    INVALID = QT_TR_NOOP("{} is invalid")
    REGION_INFO = QT_TR_NOOP("Protection:{} | Base:{}-{} | Module:{}")
    INVALID_REGION = QT_TR_NOOP("Invalid Region")
    EXPRESSION_ACCESS_ERROR = QT_TR_NOOP("Cannot access memory at expression {}")
    REFERENCED_BY = QT_TR_NOOP("Referenced by:")
    SEE_REFERRERS = QT_TR_NOOP("Press 'Ctrl+E' to see a detailed list of referrers")
    MV_PAUSED = QT_TR_NOOP("Memory Viewer - Paused")
    MV_DEBUGGING = QT_TR_NOOP("Memory Viewer - Currently debugging {}")
    MV_RUNNING = QT_TR_NOOP("Memory Viewer - Running")
    ENTER_BP_CONDITION = QT_TR_NOOP(
        "Enter the expression for condition, for instance:\n\n"
        "$eax==0x523\n"
        "$rax>0 && ($rbp<0 || $rsp==0)\n"
        "printf($r10)==3"
    )
    BP_CONDITION_FAILED = QT_TR_NOOP("Failed to set condition for address {}\n" "Check terminal for details")
    FULL_STACK = QT_TR_NOOP("Full Stack")
    COPY_RETURN_ADDRESS = QT_TR_NOOP("Copy Return Address")
    COPY_FRAME_ADDRESS = QT_TR_NOOP("Copy Frame Address")
    STACKTRACE = QT_TR_NOOP("Stacktrace")
    TOGGLE_STACK_FROM_SP_BP = QT_TR_NOOP("Toggle stack from BP/SP register")
    COPY_ADDRESS = QT_TR_NOOP("Copy Address")
    COPY_VALUE = QT_TR_NOOP("Copy Value")
    COPY_POINTS_TO = QT_TR_NOOP("Copy Points to")
    DISASSEMBLE_VALUE_POINTER = QT_TR_NOOP("Disassemble 'value' pointer address")
    HEXVIEW_VALUE_POINTER = QT_TR_NOOP("Show 'value' pointer in HexView")
    BACK = QT_TR_NOOP("Back")
    HEXVIEW_ADDRESS = QT_TR_NOOP("Show this address in HexView")
    FOLLOW = QT_TR_NOOP("Follow")
    EXAMINE_REFERRERS = QT_TR_NOOP("Examine Referrers")
    BOOKMARK_ADDRESS = QT_TR_NOOP("Bookmark this address")
    DELETE_BOOKMARK = QT_TR_NOOP("Delete this bookmark")
    CHANGE_COMMENT = QT_TR_NOOP("Change comment")
    GO_TO_BOOKMARK_ADDRESS = QT_TR_NOOP("Go to bookmarked address")
    EDIT_INSTRUCTION = QT_TR_NOOP("Edit instruction")
    REPLACE_WITH_NOPS = QT_TR_NOOP("Replace instruction with NOPs")
    WHAT_ACCESSES_INSTRUCTION = QT_TR_NOOP("Find out which addresses this instruction accesses")
    TRACE_INSTRUCTION = QT_TR_NOOP("Break and trace instructions")
    DISSECT_REGION = QT_TR_NOOP("Dissect this region")
    COPY_BYTES = QT_TR_NOOP("Copy Bytes")
    COPY_INSTR = QT_TR_NOOP("Copy Instruction")
    COPY_COMMENT = QT_TR_NOOP("Copy Comment")
    COPY_ALL = QT_TR_NOOP("Copy All")
    ENTER_TRACK_BP_EXPRESSION = QT_TR_NOOP(
        "Enter the register expression(s) you want to track\n"
        "Register names must start with $\n"
        "Each expression must be separated with a comma\n\n"
        "For instance:\n"
        "Let's say the instruction is mov [rax+rbx],30\n"
        "Then you should enter $rax+$rbx\n"
        "So PINCE can track address [rax+rbx]\n\n"
        "Another example:\n"
        "If you enter $rax,$rbx*$rcx+4,$rbp\n"
        "PINCE will track down addresses [rax],[rbx*rcx+4] and [rbp]"
    )
    ALREADY_BOOKMARKED = QT_TR_NOOP("This address has already been bookmarked")
    ENTER_BOOKMARK_COMMENT = QT_TR_NOOP("Enter the comment for bookmarked address")
    SELECT_SO_FILE = QT_TR_NOOP("Select the shared object (.so) file")
    SO_INJECTED = QT_TR_NOOP("The shared object (.so) file has been injected")
    SO_INJECT_FAILED = QT_TR_NOOP("Failed to inject the shared object (.so) file")
    SELECT_DLL_FILE = QT_TR_NOOP("Select the DLL file")
    DLL_INJECTED = QT_TR_NOOP("The DLL has been injected at {}")
    DLL_INJECT_FAILED = QT_TR_NOOP("Failed to inject the DLL")
    DLL_INJECT_WINE_ONLY = QT_TR_NOOP("DLL injection is only supported for WINE/Proton processes")
    ENTER_CALL_EXPRESSION = QT_TR_NOOP(
        "Enter the expression for the function that'll be called from the inferior\n"
        "You can view functions list from View->Functions\n\n"
        "For instance:\n"
        'Calling printf("1234") will yield something like this\n'
        "↓\n"
        "$28 = 4\n\n"
        "$28 is the assigned convenience variable\n"
        "4 is the result\n"
        "You can use the assigned variable from the GDB Console"
    )
    CALL_EXPRESSION_FAILED = QT_TR_NOOP("Failed to call the expression {}")
    INVALID_EXPRESSION = QT_TR_NOOP("Invalid expression or address")
    INVALID_ENTRY = QT_TR_NOOP("Invalid entries detected, refreshing the page")
    ADD_ENTRY = QT_TR_NOOP("Add new entry")
    ENTER_REGISTER_VALUE = QT_TR_NOOP("Enter the new value of register {}")
    ENTER_FLAG_VALUE = QT_TR_NOOP("Enter the new value of flag {}")
    RESTORE_INSTRUCTION = QT_TR_NOOP("Restore this instruction")
    ENTER_HIT_COUNT = QT_TR_NOOP("Enter the hit count({} or higher)")
    HIT_COUNT_ASSERT_INT = QT_TR_NOOP("Hit count must be an integer")
    HIT_COUNT_ASSERT_LT = QT_TR_NOOP("Hit count can't be lower than {}")
    CHANGE_CONDITION = QT_TR_NOOP("Change condition")
    ENABLE = QT_TR_NOOP("Enable")
    DISABLE = QT_TR_NOOP("Disable")
    DISABLE_AFTER_HIT = QT_TR_NOOP("Disable after hit")
    DISABLE_AFTER_COUNT = QT_TR_NOOP("Disable after X hits")
    DELETE_AFTER_HIT = QT_TR_NOOP("Delete after hit")
    INSTR_WRITING_TO = QT_TR_NOOP("Instructions writing to the address {}")
    INSTR_READING_FROM = QT_TR_NOOP("Instructions reading from the address {}")
    INSTR_ACCESSING_TO = QT_TR_NOOP("Instructions accessing to the address {}")
    TRACK_WATCHPOINT_FAILED = QT_TR_NOOP("Unable to track watchpoint at expression {}")
    DELETE_WATCHPOINT_FAILED = QT_TR_NOOP("Unable to delete watchpoint at expression {}")
    CLOSE = QT_TR_NOOP("Close")
    ACCESSED_BY_INSTRUCTION = QT_TR_NOOP("Addresses accessed by instruction {}")
    TRACK_BREAKPOINT_FAILED = QT_TR_NOOP("Unable to track breakpoint at expression {}")
    ACCESSED_BY = QT_TR_NOOP("Accessed by {}")
    DELETE_BREAKPOINT_FAILED = QT_TR_NOOP("Unable to delete breakpoint at expression {}")
    MAX_TRACE_COUNT_ASSERT_GT = QT_TR_NOOP("Max trace count must be greater than or equal to {}")
    SAVE_TRACE_FILE = QT_TR_NOOP("Save trace file")
    OPEN_TRACE_FILE = QT_TR_NOOP("Open trace file")
    EXPAND_ALL = QT_TR_NOOP("Expand All")
    COLLAPSE_ALL = QT_TR_NOOP("Collapse All")
    SELECT_POINTER_MAP = QT_TR_NOOP("Select a pointer map file")
    SCAN = QT_TR_NOOP("Scan")
    SCANNING = QT_TR_NOOP("Scanning")
    FILTER = QT_TR_NOOP("Filter")
    FILTERING = QT_TR_NOOP("Filtering")
    DEFINED = QT_TR_NOOP("DEFINED")
    DEFINED_SYMBOL = QT_TR_NOOP(
        "This symbol is defined. You can use its body as a gdb expression. For instance:\n\n"
        "void func(param) can be used as 'func' as a gdb expression"
    )
    COPY_SYMBOL = QT_TR_NOOP("Copy Symbol")
    FUNCTIONS_INFO_HELPER = QT_TR_NOOP(
        "\tHere's some useful regex tips:\n"
        "^quaso --> search for everything that starts with quaso\n"
        "[ab]cd --> search for both acd and bcd\n\n"
        "\tHow to interpret symbols:\n"
        "A symbol that looks like 'func(param)@plt' consists of 3 pieces\n"
        "func, func(param), func(param)@plt\n"
        "These 3 functions will have different addresses\n"
        "@plt means this function is a subroutine for the original one\n"
        "There can be more than one of the same function\n"
        "It means that the function is overloaded"
    )
    NEW_INSTR = QT_TR_NOOP(
        "New instruction is {} bytes long but old instruction is only {} bytes long\n"
        "This will cause an overflow, proceed?"
    )
    IS_INVALID_EXPRESSION = QT_TR_NOOP("{} isn't a valid expression")
    LOG_FILE = QT_TR_NOOP("Log File of PID {}")
    LOG_CONTENTS = QT_TR_NOOP("Contents of {} (only last {} bytes are shown)")
    ON = QT_TR_NOOP("ON")
    OFF = QT_TR_NOOP("OFF")
    LOG_STATUS = QT_TR_NOOP("LOGGING: {}")
    LOG_READ_ERROR = QT_TR_NOOP("Unable to read log file at {}")
    SETTINGS_ENABLE_LOG = QT_TR_NOOP("Go to Settings->Debug to enable logging")
    INVALID_REGEX = QT_TR_NOOP("Invalid Regex")
    SEARCH_INSTR_HELPER = QT_TR_NOOP(
        "\tHere's some useful regex examples:\n"
        "call|rax --> search for instructions that contain call or rax\n"
        "[re]cx --> search for both rcx and ecx\n"
        "Use the char \\ to escape special chars such as [\n"
        r"\[rsp\] --> search for instructions that contain [rsp]"
    )
    COPY_ADDRESSES = QT_TR_NOOP("Copy Addresses")
    COPY_OFFSET = QT_TR_NOOP("Copy Offset")
    COPY_PATH = QT_TR_NOOP("Copy Path")
    START = QT_TR_NOOP("Start")
    CURRENT_SCAN_REGION = QT_TR_NOOP("Currently scanning region:")
    CANCEL = QT_TR_NOOP("Cancel")
    SCAN_FINISHED = QT_TR_NOOP("Scan finished")
    SCAN_CANCELED = QT_TR_NOOP("Scan was canceled")
    SELECT_ONE_REGION = QT_TR_NOOP("Select at least one region")
    DISSECT_CODE = QT_TR_NOOP("You need to dissect code first\n" "Proceed?")
    WAITING_FOR_BREAKPOINT = QT_TR_NOOP("Waiting for breakpoint to trigger")
    TRACING_COMPLETED = QT_TR_NOOP("Tracing has been completed")
    NOT = QT_TR_NOOP("Not")
    EXACT = QT_TR_NOOP("Exact")
    INCREASED = QT_TR_NOOP("Increased")
    INCREASED_BY = QT_TR_NOOP("Increased by")
    DECREASED = QT_TR_NOOP("Decreased")
    DECREASED_BY = QT_TR_NOOP("Decreased by")
    LESS_THAN = QT_TR_NOOP("Less Than")
    MORE_THAN = QT_TR_NOOP("More Than")
    BETWEEN = QT_TR_NOOP("Between")
    CHANGED = QT_TR_NOOP("Changed")
    UNCHANGED = QT_TR_NOOP("Unchanged")
    UNKNOWN_VALUE = QT_TR_NOOP("Unknown Value")
    BASIC = QT_TR_NOOP("Basic")
    NORMAL = QT_TR_NOOP("Normal")
    RW = QT_TR_NOOP("Read+Write")
    FULL = QT_TR_NOOP("Full")
    HOST = QT_TR_NOOP("Host")
    LITTLE = QT_TR_NOOP("Little")
    BIG = QT_TR_NOOP("Big")
    SHOW_HEXVIEW = QT_TR_NOOP("Show in HexView")
    SHOW_DISASSEMBLER = QT_TR_NOOP("Show in Disassembler")
    DARK = QT_TR_NOOP("Dark")
    LIGHT = QT_TR_NOOP("Light")
    SYSTEM_DEFAULT = QT_TR_NOOP("System Default")
    WONG = QT_TR_NOOP("Wong (Colorblind Friendly)")
    SAVE_SESSION_QUESTION_TITLE = QT_TR_NOOP("Session - Unsaved changes")
    SAVE_SESSION_QUESTION_PROMPT = QT_TR_NOOP("You have unsaved changes.\nDo you want to save the current session?")
    SESSION_PROCESS_CHANGED_TITLE = QT_TR_NOOP("Session - Process changed")
    SESSION_PROCESS_CHANGED_PROMPT = QT_TR_NOOP(
        "The process name has changed.\n" "Do you want to keep the current session with the new process?"
    )
    MONO_NOT_READY = QT_TR_NOOP("Mono collector is not connected")
    MONO_NO_RUNTIME = QT_TR_NOOP("No supported managed runtime found in this process")
    MONO_INVOKE = QT_TR_NOOP("Invoke...")
    MONO_INVOKE_INSTANCE = QT_TR_NOOP("Instance (this)")
    MONO_INVOKE_RESULT = QT_TR_NOOP("Result: {}")
    MONO_INVOKE_VOID = QT_TR_NOOP("Returned (void)")
    MONO_INVOKE_EXCEPTION = QT_TR_NOOP("Exception thrown (object @ {})")
    MONO_INVOKE_BAD_ARG = QT_TR_NOOP("Could not parse the argument values")
    MONO_INVOKE_BAD_INSTANCE = QT_TR_NOOP("Invalid instance pointer")
    MONO_INVOKE_UNSUPPORTED = QT_TR_NOOP("This method has a parameter type that can't be marshalled yet")
    MONO_INVOKE_STRUCT_HINT = QT_TR_NOOP("{} raw bytes (hex)")
    MONO_INVOKE_FIND_INSTANCE = QT_TR_NOOP("Find instance...")
    MONO_INVOKE_PICK_INSTANCE = QT_TR_NOOP("Select a live instance:")
    MONO_STATIC_UNAVAILABLE = QT_TR_NOOP("Static field address is unavailable for this runtime")
    MONO_DRILL_UNRESOLVABLE = QT_TR_NOOP("(type could not be resolved)")
    MONO_DRILL_MAX_DEPTH = QT_TR_NOOP("(maximum drill depth reached)")
    MONO_FIND_INSTANCES = QT_TR_NOOP("Find Instances")
    MONO_FIND_INSTANCES_TITLE = QT_TR_NOOP("Find Instances - {}")
    MONO_INSTANCES_FOUND = QT_TR_NOOP("{} instance(s) found")
    MONO_INSTANCES_TRUNCATED = QT_TR_NOOP("(showing first {})")
    MONO_NO_INSTANCES = QT_TR_NOOP("No live instances found")
    MONO_INSTANCE_MARKER_UNAVAILABLE = QT_TR_NOOP("Could not resolve an instance marker for this class")
    FIELDS = QT_TR_NOOP("Fields")
    METHODS = QT_TR_NOOP("Methods")
    DISASSEMBLE = QT_TR_NOOP("Disassemble")
    VIEW_AT_ADDRESS = QT_TR_NOOP("View at address…")
    DELETE_STRUCTURE = QT_TR_NOOP("Delete structure")
    DELETE_STRUCTURE_PROMPT = QT_TR_NOOP("Delete structure '{}'?")
    VIEW_AS_STRUCT = QT_TR_NOOP("View as structure")
    ENTER_BASE_ADDRESS = QT_TR_NOOP("Enter base address")
    VALUE_MEMBER = QT_TR_NOOP("Value")
    POINTER_MEMBER = QT_TR_NOOP("Pointer")
    INLINE_MEMBER = QT_TR_NOOP("Inline")
    STRUCTURE_NAME_TAKEN = QT_TR_NOOP("A structure with this name already exists")
    STRUCTURE_NAME_EMPTY = QT_TR_NOOP("Structure name cannot be empty")
    REPR_UNSIGNED = QT_TR_NOOP("Unsigned")
    REPR_SIGNED = QT_TR_NOOP("Signed")
    REPR_HEX = QT_TR_NOOP("Hex")
    EXPORT_AS_STRUCTURE = QT_TR_NOOP("Export as structure")
    DISSECT_AS_STRUCTURE = QT_TR_NOOP("Dissect as structure")
