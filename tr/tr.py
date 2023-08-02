from PyQt6.QtCore import QObject, QT_TR_NOOP


class TranslationConstants(QObject):
    @staticmethod
    def translate():
        for key, value in vars(TranslationConstants).items():
            if not key.startswith("__") and isinstance(value, str):
                setattr(TranslationConstants, key, TranslationConstants.tr(value))

    PAUSE_HOTKEY = QT_TR_NOOP("Pause the process")
    BREAK_HOTKEY = QT_TR_NOOP("Break the process")
    CONTINUE_HOTKEY = QT_TR_NOOP("Continue the process")
    TOGGLE_ATTACH_HOTKEY = QT_TR_NOOP("Toggle attach/detach")
    EXACT_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Exact")
    INC_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Increased")
    DEC_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Decreased")
    CHANGED_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Changed")
    UNCHANGED_SCAN_HOTKEY = QT_TR_NOOP("Next Scan - Unchanged")
    ERROR = QT_TR_NOOP("Error")
    GDB_INIT = QT_TR_NOOP("GDB isn't initialized yet")
    GDB_INIT_ERROR = QT_TR_NOOP("Unable to initialize GDB\n"
                                "You might want to reinstall GDB or use the system GDB\n"
                                "To change the current GDB path, check Settings->Debug")
    EDIT = QT_TR_NOOP("Edit")
    SHOW_HEX = QT_TR_NOOP("Show as hexadecimal")
    SHOW_DEC = QT_TR_NOOP("Show as decimal")
    SHOW_UNSIGNED = QT_TR_NOOP("Show as unsigned")
    SHOW_SIGNED = QT_TR_NOOP("Show as signed")
    TOGGLE_RECORDS = QT_TR_NOOP("Toggle selected records")
    FREEZE = QT_TR_NOOP("Freeze")
    DEFAULT = QT_TR_NOOP("Default")
    INCREMENTAL = QT_TR_NOOP("Incremental")
    DECREMENTAL = QT_TR_NOOP("Decremental")
    BROWSE_MEMORY_REGION = QT_TR_NOOP("Browse this memory region")
    DISASSEMBLE_ADDRESS = QT_TR_NOOP("Disassemble this address")
    CUT_RECORDS = QT_TR_NOOP("Cut selected records")
    COPY_RECORDS = QT_TR_NOOP("Copy selected records")
    CUT_RECORDS_RECURSIVE = QT_TR_NOOP("Cut selected records (recursive)")
    COPY_RECORDS_RECURSIVE = QT_TR_NOOP("Copy selected records (recursive)")
    PASTE_BEFORE = QT_TR_NOOP("Paste selected records before")
    PASTE_AFTER = QT_TR_NOOP("Paste selected records after")
    PASTE_INSIDE = QT_TR_NOOP("Paste selected records inside")
    DELETE_RECORDS = QT_TR_NOOP("Delete selected records")
    WHAT_WRITES = QT_TR_NOOP("Find out what writes to this address")
    WHAT_READS = QT_TR_NOOP("Find out what reads this address")
    WHAT_ACCESSES = QT_TR_NOOP("Find out what accesses this address")
    INVALID_CLIPBOARD = QT_TR_NOOP("Invalid clipboard content")
    NEW_SCAN = QT_TR_NOOP("New Scan")
    MATCH_COUNT_LIMITED = QT_TR_NOOP("Match count: {} ({} shown)")
    MATCH_COUNT = QT_TR_NOOP("Match count: {}")
    NO_DESCRIPTION = QT_TR_NOOP("No Description")
    OPEN_PCT_FILE = QT_TR_NOOP("Open PCT file(s)")

    # Keep (*.pct) and (*) while translating, it doesn't matter where it stays within the sentence
    # For instance, you can keep (*) in the beginning of the sentence for right-to-left languages like arabic
    # All entries are separated by ;; Please try to respect the original order of the file types
    FILE_TYPES_PCT = QT_TR_NOOP("PINCE Cheat Table (*.pct);;All files (*)")
    CLEAR_TABLE = QT_TR_NOOP("Clear address table?")
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
    ENTER_VALUE = QT_TR_NOOP("Enter the new value")
    ENTER_DESCRIPTION = QT_TR_NOOP("Enter the new description")
    EDIT_ADDRESS = QT_TR_NOOP("Edit Address")
    SELECT_PROCESS = QT_TR_NOOP("Please select a process first")
    SELECT_BINARY = QT_TR_NOOP("Select the target binary")
    ENTER_OPTIONAL_ARGS = QT_TR_NOOP("Enter the optional arguments")
    LD_PRELOAD_OPTIONAL = QT_TR_NOOP("LD_PRELOAD .so path (optional)")
    REFRESH = QT_TR_NOOP("Refresh")
    LENGTH_NOT_VALID = QT_TR_NOOP("Length is not valid")
    LENGTH_GT = QT_TR_NOOP("Length must be greater than 0")
    PARSE_ERROR = QT_TR_NOOP("Can't parse the input")
    UPDATE_ASSERT_INT = QT_TR_NOOP("Update interval must be an int")
    FREEZE_ASSERT_INT = QT_TR_NOOP("Freeze interval must be an int")
    INSTRUCTION_ASSERT_INT = QT_TR_NOOP("Instruction count must be an int")
    INSTRUCTION_ASSERT_LT = QT_TR_NOOP("Instruction count cannot be lower than {}")
    INTERVAL_ASSERT_NEGATIVE = QT_TR_NOOP("Interval cannot be a negative number")
    ASKING_FOR_TROUBLE = QT_TR_NOOP("You are asking for it, aren't you?")
    UPDATE_ASSERT_GT = QT_TR_NOOP("Update interval should be bigger than {} ms\n"
                                  "Setting update interval less than {} ms may cause slowdown\n"
                                  "Proceed?")
    IS_INVALID_REGEX = QT_TR_NOOP("{} isn't a valid regex")
    GDB_RESET = QT_TR_NOOP("You have changed the GDB path, reset GDB now?")
    RESET_DEFAULT_SETTINGS = QT_TR_NOOP("This will reset to the default settings\n"
                                        "Proceed?")
    MOUSE_OVER_EXAMPLES = QT_TR_NOOP("Mouse over on this text for examples")
    AUTO_ATTACH_TOOLTIP = QT_TR_NOOP("asdf|qwer --> search for asdf or qwer\n"
                                     "[as]df --> search for both adf and sdf\n"
                                     "Use the char \\ to escape special chars such as [\n"
                                     "\[asdf\] --> search for opcodes that contain [asdf]")
    SEPARATE_PROCESSES_WITH = QT_TR_NOOP("Separate processes with {}")
    SELECT_GDB_BINARY = QT_TR_NOOP("Select the gdb binary")
    QUIT_SESSION_CRASH = QT_TR_NOOP("Quitting current session will crash PINCE")
    CONT_SESSION_CRASH = QT_TR_NOOP("Use global hotkeys or the commands 'interrupt' and 'c&' to stop/run the inferior")
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
        "pince-init-so-file so_file_path: Initializes 'lib' variable                                       |\n"
        "pince-get-so-file-information: Get information about current lib                                  |\n"
        "pince-execute-from-so-file lib.func(params): Execute a function from lib                          |\n"
        "# Check https://github.com/korcankaraokcu/PINCE/wiki#extending-pince-with-so-files for an example |\n"
        "# CLI output mode doesn't work very well with .so extensions, use MI output mode instead          |\n"
        "---------------------------------------------------------------------------------------------------\n"
        "You can change the output mode from bottom right\n"
        "Changing output mode only affects commands sent. Any other output coming from external sources"
        "(e.g async output) will be shown in MI format")
    BREAK = QT_TR_NOOP("Break[{}]")
    RUN = QT_TR_NOOP("Run[{}]")
    TOGGLE_ATTACH = QT_TR_NOOP("Toggle Attach[{}]")
    BREAKPOINT_FAILED = QT_TR_NOOP("Failed to set breakpoint at address {}")
    ENTER_WATCHPOINT_LENGTH = QT_TR_NOOP("Enter the watchpoint length in size of bytes")
    PARSE_ERROR_INT = QT_TR_NOOP("{} can't be parsed as an integer")
    BREAKPOINT_ASSERT_LT = QT_TR_NOOP("Breakpoint length can't be lower than {}")
    WATCHPOINT_FAILED = QT_TR_NOOP("Failed to set watchpoint at address {}")
    COPY_CLIPBOARD = QT_TR_NOOP("Copy to Clipboard")
    GO_TO_EXPRESSION = QT_TR_NOOP("Go to expression")
    ADD_TO_ADDRESS_LIST = QT_TR_NOOP("Add this address to address list")
    SET_WATCHPOINT = QT_TR_NOOP("Set Watchpoint")
    WRITE_ONLY = QT_TR_NOOP("Write Only")
    READ_ONLY = QT_TR_NOOP("Read Only")
    BOTH = QT_TR_NOOP("Both")
    CHANGE_BREAKPOINT_CONDITION = QT_TR_NOOP("Add/Change condition for breakpoint")
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
    ENTER_BP_CONDITION = QT_TR_NOOP("Enter the expression for condition, for instance:\n\n"
                                    "$eax==0x523\n"
                                    "$rax>0 && ($rbp<0 || $rsp==0)\n"
                                    "printf($r10)==3")
    BP_CONDITION_FAILED = QT_TR_NOOP("Failed to set condition for address {}\n"
                                     "Check terminal for details")
    FULL_STACK = QT_TR_NOOP("Full Stack")
    COPY_RETURN_ADDRESS = QT_TR_NOOP("Copy Return Address")
    COPY_FRAME_ADDRESS = QT_TR_NOOP("Copy Frame Address")
    STACKTRACE = QT_TR_NOOP("Stacktrace")
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
    TOGGLE_BREAKPOINT = QT_TR_NOOP("Toggle Breakpoint")
    EDIT_INSTRUCTION = QT_TR_NOOP("Edit instruction")
    REPLACE_WITH_NOPS = QT_TR_NOOP("Replace instruction with NOPs")
    WHAT_ACCESSES_INSTRUCTION = QT_TR_NOOP("Find out which addresses this instruction accesses")
    TRACE_INSTRUCTION = QT_TR_NOOP("Break and trace instructions")
    DISSECT_REGION = QT_TR_NOOP("Dissect this region")
    COPY_BYTES = QT_TR_NOOP("Copy Bytes")
    COPY_OPCODE = QT_TR_NOOP("Copy Opcode")
    COPY_COMMENT = QT_TR_NOOP("Copy Comment")
    COPY_ALL = QT_TR_NOOP("Copy All")
    ENTER_TRACK_BP_EXPRESSION = QT_TR_NOOP("Enter the register expression(s) you want to track\n"
                                           "Register names must start with $\n"
                                           "Each expression must be separated with a comma\n\n"
                                           "For instance:\n"
                                           "Let's say the instruction is mov [rax+rbx],30\n"
                                           "Then you should enter $rax+$rbx\n"
                                           "So PINCE can track address [rax+rbx]\n\n"
                                           "Another example:\n"
                                           "If you enter $rax,$rbx*$rcx+4,$rbp\n"
                                           "PINCE will track down addresses [rax],[rbx*rcx+4] and [rbp]")
    ALREADY_BOOKMARKED = QT_TR_NOOP("This address has already been bookmarked")
    ENTER_BOOKMARK_COMMENT = QT_TR_NOOP("Enter the comment for bookmarked address")
    SELECT_SO_FILE = QT_TR_NOOP("Select the .so file")

    # Same applies here, keep (*.so)
    SHARED_OBJECT_TYPE = QT_TR_NOOP("Shared object library (*.so)")
    SUCCESS = QT_TR_NOOP("Success")
    FILE_INJECTED = QT_TR_NOOP("The file has been injected")
    FILE_INJECT_FAILED = QT_TR_NOOP("Failed to inject the .so file")
    ENTER_CALL_EXPRESSION = QT_TR_NOOP("Enter the expression for the function that'll be called from the inferior\n"
                                       "You can view functions list from View->Functions\n\n"
                                       "For instance:\n"
                                       'Calling printf("1234") will yield something like this\n'
                                       '↓\n'
                                       '$28 = 4\n\n'
                                       '$28 is the assigned convenience variable\n'
                                       '4 is the result\n'
                                       'You can use the assigned variable from the GDB Console')
    CALL_EXPRESSION_FAILED = QT_TR_NOOP("Failed to call the expression {}")
    INVALID_EXPRESSION = QT_TR_NOOP("Invalid expression or address")
    INVALID_ENTRY = QT_TR_NOOP("Invalid entries detected, refreshing the page")
    ADD_ENTRY = QT_TR_NOOP("Add new entry")
    DELETE = QT_TR_NOOP("Delete")
    ENTER_REGISTER_VALUE = QT_TR_NOOP("Enter the new value of register {}")
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
    OPCODE_WRITING_TO = QT_TR_NOOP("Opcodes writing to the address {}")
    OPCODE_READING_FROM = QT_TR_NOOP("Opcodes reading from the address {}")
    OPCODE_ACCESSING_TO = QT_TR_NOOP("Opcodes accessing to the address {}")
    TRACK_WATCHPOINT_FAILED = QT_TR_NOOP("Unable to track watchpoint at expression {}")
    DELETE_WATCHPOINT_FAILED = QT_TR_NOOP("Unable to delete watchpoint at expression {}")
    CLOSE = QT_TR_NOOP("Close")
    ACCESSED_BY_INSTRUCTION = QT_TR_NOOP("Addresses accessed by instruction {}")
    TRACK_BREAKPOINT_FAILED = QT_TR_NOOP("Unable to track breakpoint at expression {}")
    ACCESSED_BY = QT_TR_NOOP("Accessed by {}")
    DELETE_BREAKPOINT_FAILED = QT_TR_NOOP("Unable to delete breakpoint at expression {}")
    MAX_TRACE_COUNT_ASSERT_GT = QT_TR_NOOP("Max trace count must be greater than or equal to {}")
    PROCESSING_DATA = QT_TR_NOOP("Processing the collected data")
    SAVE_TRACE_FILE = QT_TR_NOOP("Save trace file")

    # Same applies here, keep (*.trace) and (*)
    FILE_TYPES_TRACE = QT_TR_NOOP("Trace File (*.trace);;All Files (*)")
    OPEN_TRACE_FILE = QT_TR_NOOP("Open trace file")
    EXPAND_ALL = QT_TR_NOOP("Expand All")
    COLLAPSE_ALL = QT_TR_NOOP("Collapse All")
    DEFINED = QT_TR_NOOP("DEFINED")
    DEFINED_SYMBOL = QT_TR_NOOP("This symbol is defined. You can use its body as a gdb expression. For instance:\n\n"
                                "void func(param) can be used as 'func' as a gdb expression")
    COPY_SYMBOL = QT_TR_NOOP("Copy Symbol")
    FUNCTIONS_INFO_HELPER = QT_TR_NOOP("\tHere's some useful regex tips:\n"
                                       "^quaso --> search for everything that starts with quaso\n"
                                       "[ab]cd --> search for both acd and bcd\n\n"
                                       "\tHow to interpret symbols:\n"
                                       "A symbol that looks like 'func(param)@plt' consists of 3 pieces\n"
                                       "func, func(param), func(param)@plt\n"
                                       "These 3 functions will have different addresses\n"
                                       "@plt means this function is a subroutine for the original one\n"
                                       "There can be more than one of the same function\n"
                                       "It means that the function is overloaded")
    NEW_OPCODE = QT_TR_NOOP("New opcode is {} bytes long but old opcode is only {} bytes long\n"
                            "This will cause an overflow, proceed?")
    IS_INVALID_EXPRESSION = QT_TR_NOOP("{} isn't a valid expression")
    LOG_FILE = QT_TR_NOOP("Log File of PID {}")
    LOG_CONTENTS = QT_TR_NOOP("Contents of {} (only last {} bytes are shown)")
    ON = QT_TR_NOOP("ON")
    OFF = QT_TR_NOOP("OFF")
    LOG_STATUS = QT_TR_NOOP("LOGGING: {}")
    LOG_READ_ERROR = QT_TR_NOOP("Unable to read log file at {}")
    SETTINGS_ENABLE_LOG = QT_TR_NOOP("Go to Settings->Debug to enable logging")
    INVALID_REGEX = QT_TR_NOOP("Invalid Regex")
    SEARCH_OPCODE_HELPER = QT_TR_NOOP("\tHere's some useful regex examples:\n"
                                      "call|rax --> search for opcodes that contain call or rax\n"
                                      "[re]cx --> search for both rcx and ecx\n"
                                      "Use the char \\ to escape special chars such as [\n"
                                      "\[rsp\] --> search for opcodes that contain [rsp]")
    COPY_ADDRESSES = QT_TR_NOOP("Copy Addresses")
    COPY_OFFSET = QT_TR_NOOP("Copy Offset")
    COPY_PATH = QT_TR_NOOP("Copy Path")
    START = QT_TR_NOOP("Start")
    CURRENT_SCAN_REGION = QT_TR_NOOP("Currently scanning region:")
    CANCEL = QT_TR_NOOP("Cancel")
    SCAN_FINISHED = QT_TR_NOOP("Scan finished")
    SCAN_CANCELED = QT_TR_NOOP("Scan was canceled")
    SELECT_ONE_REGION = QT_TR_NOOP("Select at least one region")
    DISSECT_CODE = QT_TR_NOOP("You need to dissect code first\n"
                              "Proceed?")
    WAITING_FOR_BREAKPOINT = QT_TR_NOOP("Waiting for breakpoint to trigger")
    TRACING_CANCELED = QT_TR_NOOP("Tracing has been canceled")
    TRACING_COMPLETED = QT_TR_NOOP("Tracing has been completed")
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
