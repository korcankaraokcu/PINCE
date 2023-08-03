from PyQt6.QtCore import QObject, QT_TR_NOOP


class TranslationConstants(QObject):
    @staticmethod
    def translate():
        for key, value in vars(TranslationConstants).items():
            if not key.startswith("__") and isinstance(value, str):
                setattr(TranslationConstants, key, TranslationConstants.tr(value))
    _translate = QT_TR_NOOP
    PAUSE_HOTKEY = _translate("Pause the process")
    BREAK_HOTKEY = _translate("Break the process")
    CONTINUE_HOTKEY = _translate("Continue the process")
    TOGGLE_ATTACH_HOTKEY = _translate("Toggle attach/detach")
    EXACT_SCAN_HOTKEY = _translate("Next Scan - Exact")
    INC_SCAN_HOTKEY = _translate("Next Scan - Increased")
    DEC_SCAN_HOTKEY = _translate("Next Scan - Decreased")
    CHANGED_SCAN_HOTKEY = _translate("Next Scan - Changed")
    UNCHANGED_SCAN_HOTKEY = _translate("Next Scan - Unchanged")
    ERROR = _translate("Error")
    GDB_INIT = _translate("GDB isn't initialized yet")
    GDB_INIT_ERROR = _translate("Unable to initialize GDB\n"
                                "You might want to reinstall GDB or use the system GDB\n"
                                "To change the current GDB path, check Settings->Debug")
    EDIT = _translate("Edit")
    SHOW_HEX = _translate("Show as hexadecimal")
    SHOW_DEC = _translate("Show as decimal")
    SHOW_UNSIGNED = _translate("Show as unsigned")
    SHOW_SIGNED = _translate("Show as signed")
    TOGGLE_RECORDS = _translate("Toggle selected records")
    FREEZE = _translate("Freeze")
    DEFAULT = _translate("Default")
    INCREMENTAL = _translate("Incremental")
    DECREMENTAL = _translate("Decremental")
    BROWSE_MEMORY_REGION = _translate("Browse this memory region")
    DISASSEMBLE_ADDRESS = _translate("Disassemble this address")
    CUT_RECORDS = _translate("Cut selected records")
    COPY_RECORDS = _translate("Copy selected records")
    CUT_RECORDS_RECURSIVE = _translate("Cut selected records (recursive)")
    COPY_RECORDS_RECURSIVE = _translate("Copy selected records (recursive)")
    PASTE_BEFORE = _translate("Paste selected records before")
    PASTE_AFTER = _translate("Paste selected records after")
    PASTE_INSIDE = _translate("Paste selected records inside")
    DELETE_RECORDS = _translate("Delete selected records")
    WHAT_WRITES = _translate("Find out what writes to this address")
    WHAT_READS = _translate("Find out what reads this address")
    WHAT_ACCESSES = _translate("Find out what accesses this address")
    INVALID_CLIPBOARD = _translate("Invalid clipboard content")
    NEW_SCAN = _translate("New Scan")
    MATCH_COUNT_LIMITED = _translate("Match count: {} ({} shown)")
    MATCH_COUNT = _translate("Match count: {}")
    NO_DESCRIPTION = _translate("No Description")
    OPEN_PCT_FILE = _translate("Open PCT file(s)")

    # Keep (*.pct) and (*) while translating, it doesn't matter where it stays within the sentence
    # For instance, you can keep (*) in the beginning of the sentence for right-to-left languages like arabic
    # All entries are separated by ;; Please try to respect the original order of the file types
    FILE_TYPES_PCT = _translate("PINCE Cheat Table (*.pct);;All files (*)")
    CLEAR_TABLE = _translate("Clear address table?")
    FILE_LOAD_ERROR = _translate("File {} is inaccessible or contains invalid content")
    SAVE_PCT_FILE = _translate("Save PCT file")
    FILE_SAVE_ERROR = _translate("Cannot save to file")
    SMARTASS = _translate("Nice try, smartass")
    PROCESS_NOT_VALID = _translate("Selected process is not valid")
    ALREADY_DEBUGGING = _translate("You're debugging this process already")
    ALREADY_TRACED = _translate("That process is already being traced by {}, could not attach to the process")
    PERM_DENIED = _translate("Permission denied, could not attach to the process")
    CREATE_PROCESS_ERROR = _translate("An error occurred while trying to create process")
    SCAN_FOR = _translate("Scan for")
    FIRST_SCAN = _translate("First Scan")
    NO_PROCESS_SELECTED = _translate("No Process Selected")
    STATUS_DETACHED = _translate("[detached]")
    STATUS_STOPPED = _translate("[stopped]")
    ENTER_VALUE = _translate("Enter the new value")
    ENTER_DESCRIPTION = _translate("Enter the new description")
    EDIT_ADDRESS = _translate("Edit Address")
    SELECT_PROCESS = _translate("Please select a process first")
    SELECT_BINARY = _translate("Select the target binary")
    ENTER_OPTIONAL_ARGS = _translate("Enter the optional arguments")
    LD_PRELOAD_OPTIONAL = _translate("LD_PRELOAD .so path (optional)")
    REFRESH = _translate("Refresh")
    LENGTH_NOT_VALID = _translate("Length is not valid")
    LENGTH_GT = _translate("Length must be greater than 0")
    PARSE_ERROR = _translate("Can't parse the input")
    UPDATE_ASSERT_INT = _translate("Update interval must be an int")
    FREEZE_ASSERT_INT = _translate("Freeze interval must be an int")
    INSTRUCTION_ASSERT_INT = _translate("Instruction count must be an int")
    INSTRUCTION_ASSERT_LT = _translate("Instruction count cannot be lower than {}")
    INTERVAL_ASSERT_NEGATIVE = _translate("Interval cannot be a negative number")
    ASKING_FOR_TROUBLE = _translate("You are asking for it, aren't you?")
    UPDATE_ASSERT_GT = _translate("Update interval should be bigger than {} ms\n"
                                  "Setting update interval less than {} ms may cause slowdown\n"
                                  "Proceed?")
    IS_INVALID_REGEX = _translate("{} isn't a valid regex")
    GDB_RESET = _translate("You have changed the GDB path, reset GDB now?")
    RESET_DEFAULT_SETTINGS = _translate("This will reset to the default settings\n"
                                        "Proceed?")
    MOUSE_OVER_EXAMPLES = _translate("Mouse over on this text for examples")
    AUTO_ATTACH_TOOLTIP = _translate("asdf|qwer --> search for asdf or qwer\n"
                                     "[as]df --> search for both adf and sdf\n"
                                     "Use the char \\ to escape special chars such as [\n"
                                     "\[asdf\] --> search for opcodes that contain [asdf]")
    SEPARATE_PROCESSES_WITH = _translate("Separate processes with {}")
    SELECT_GDB_BINARY = _translate("Select the gdb binary")
    QUIT_SESSION_CRASH = _translate("Quitting current session will crash PINCE")
    CONT_SESSION_CRASH = _translate("Use global hotkeys or the commands 'interrupt' and 'c&' to stop/run the inferior")
    GDB_CONSOLE_INIT = _translate(
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
    BREAK = _translate("Break[{}]")
    RUN = _translate("Run[{}]")
    TOGGLE_ATTACH = _translate("Toggle Attach[{}]")
    BREAKPOINT_FAILED = _translate("Failed to set breakpoint at address {}")
    ENTER_WATCHPOINT_LENGTH = _translate("Enter the watchpoint length in size of bytes")
    PARSE_ERROR_INT = _translate("{} can't be parsed as an integer")
    BREAKPOINT_ASSERT_LT = _translate("Breakpoint length can't be lower than {}")
    WATCHPOINT_FAILED = _translate("Failed to set watchpoint at address {}")
    COPY_CLIPBOARD = _translate("Copy to Clipboard")
    GO_TO_EXPRESSION = _translate("Go to expression")
    ADD_TO_ADDRESS_LIST = _translate("Add this address to address list")
    SET_WATCHPOINT = _translate("Set Watchpoint")
    WRITE_ONLY = _translate("Write Only")
    READ_ONLY = _translate("Read Only")
    BOTH = _translate("Both")
    CHANGE_BREAKPOINT_CONDITION = _translate("Add/Change condition for breakpoint")
    DELETE_BREAKPOINT = _translate("Delete Breakpoint")
    ENTER_EXPRESSION = _translate("Enter the expression")
    INVALID = _translate("{} is invalid")
    REGION_INFO = _translate("Protection:{} | Base:{}-{} | Module:{}")
    INVALID_REGION = _translate("Invalid Region")
    EXPRESSION_ACCESS_ERROR = _translate("Cannot access memory at expression {}")
    REFERENCED_BY = _translate("Referenced by:")
    SEE_REFERRERS = _translate("Press 'Ctrl+E' to see a detailed list of referrers")
    MV_PAUSED = _translate("Memory Viewer - Paused")
    MV_DEBUGGING = _translate("Memory Viewer - Currently debugging {}")
    MV_RUNNING = _translate("Memory Viewer - Running")
    ENTER_BP_CONDITION = _translate("Enter the expression for condition, for instance:\n\n"
                                    "$eax==0x523\n"
                                    "$rax>0 && ($rbp<0 || $rsp==0)\n"
                                    "printf($r10)==3")
    BP_CONDITION_FAILED = _translate("Failed to set condition for address {}\n"
                                     "Check terminal for details")
    FULL_STACK = _translate("Full Stack")
    COPY_RETURN_ADDRESS = _translate("Copy Return Address")
    COPY_FRAME_ADDRESS = _translate("Copy Frame Address")
    STACKTRACE = _translate("Stacktrace")
    COPY_ADDRESS = _translate("Copy Address")
    COPY_VALUE = _translate("Copy Value")
    COPY_POINTS_TO = _translate("Copy Points to")
    DISASSEMBLE_VALUE_POINTER = _translate("Disassemble 'value' pointer address")
    HEXVIEW_VALUE_POINTER = _translate("Show 'value' pointer in HexView")
    BACK = _translate("Back")
    HEXVIEW_ADDRESS = _translate("Show this address in HexView")
    FOLLOW = _translate("Follow")
    EXAMINE_REFERRERS = _translate("Examine Referrers")
    BOOKMARK_ADDRESS = _translate("Bookmark this address")
    DELETE_BOOKMARK = _translate("Delete this bookmark")
    CHANGE_COMMENT = _translate("Change comment")
    GO_TO_BOOKMARK_ADDRESS = _translate("Go to bookmarked address")
    TOGGLE_BREAKPOINT = _translate("Toggle Breakpoint")
    EDIT_INSTRUCTION = _translate("Edit instruction")
    REPLACE_WITH_NOPS = _translate("Replace instruction with NOPs")
    WHAT_ACCESSES_INSTRUCTION = _translate("Find out which addresses this instruction accesses")
    TRACE_INSTRUCTION = _translate("Break and trace instructions")
    DISSECT_REGION = _translate("Dissect this region")
    COPY_BYTES = _translate("Copy Bytes")
    COPY_OPCODE = _translate("Copy Opcode")
    COPY_COMMENT = _translate("Copy Comment")
    COPY_ALL = _translate("Copy All")
    ENTER_TRACK_BP_EXPRESSION = _translate("Enter the register expression(s) you want to track\n"
                                           "Register names must start with $\n"
                                           "Each expression must be separated with a comma\n\n"
                                           "For instance:\n"
                                           "Let's say the instruction is mov [rax+rbx],30\n"
                                           "Then you should enter $rax+$rbx\n"
                                           "So PINCE can track address [rax+rbx]\n\n"
                                           "Another example:\n"
                                           "If you enter $rax,$rbx*$rcx+4,$rbp\n"
                                           "PINCE will track down addresses [rax],[rbx*rcx+4] and [rbp]")
    ALREADY_BOOKMARKED = _translate("This address has already been bookmarked")
    ENTER_BOOKMARK_COMMENT = _translate("Enter the comment for bookmarked address")
    SELECT_SO_FILE = _translate("Select the .so file")

    # Same applies here, keep (*.so)
    SHARED_OBJECT_TYPE = _translate("Shared object library (*.so)")
    SUCCESS = _translate("Success")
    FILE_INJECTED = _translate("The file has been injected")
    FILE_INJECT_FAILED = _translate("Failed to inject the .so file")
    ENTER_CALL_EXPRESSION = _translate("Enter the expression for the function that'll be called from the inferior\n"
                                       "You can view functions list from View->Functions\n\n"
                                       "For instance:\n"
                                       'Calling printf("1234") will yield something like this\n'
                                       '↓\n'
                                       '$28 = 4\n\n'
                                       '$28 is the assigned convenience variable\n'
                                       '4 is the result\n'
                                       'You can use the assigned variable from the GDB Console')
    CALL_EXPRESSION_FAILED = _translate("Failed to call the expression {}")
    INVALID_EXPRESSION = _translate("Invalid expression or address")
    INVALID_ENTRY = _translate("Invalid entries detected, refreshing the page")
    ADD_ENTRY = _translate("Add new entry")
    DELETE = _translate("Delete")
    ENTER_REGISTER_VALUE = _translate("Enter the new value of register {}")
    RESTORE_INSTRUCTION = _translate("Restore this instruction")
    ENTER_HIT_COUNT = _translate("Enter the hit count({} or higher)")
    HIT_COUNT_ASSERT_INT = _translate("Hit count must be an integer")
    HIT_COUNT_ASSERT_LT = _translate("Hit count can't be lower than {}")
    CHANGE_CONDITION = _translate("Change condition")
    ENABLE = _translate("Enable")
    DISABLE = _translate("Disable")
    DISABLE_AFTER_HIT = _translate("Disable after hit")
    DISABLE_AFTER_COUNT = _translate("Disable after X hits")
    DELETE_AFTER_HIT = _translate("Delete after hit")
    OPCODE_WRITING_TO = _translate("Opcodes writing to the address {}")
    OPCODE_READING_FROM = _translate("Opcodes reading from the address {}")
    OPCODE_ACCESSING_TO = _translate("Opcodes accessing to the address {}")
    TRACK_WATCHPOINT_FAILED = _translate("Unable to track watchpoint at expression {}")
    DELETE_WATCHPOINT_FAILED = _translate("Unable to delete watchpoint at expression {}")
    CLOSE = _translate("Close")
    ACCESSED_BY_INSTRUCTION = _translate("Addresses accessed by instruction {}")
    TRACK_BREAKPOINT_FAILED = _translate("Unable to track breakpoint at expression {}")
    ACCESSED_BY = _translate("Accessed by {}")
    DELETE_BREAKPOINT_FAILED = _translate("Unable to delete breakpoint at expression {}")
    MAX_TRACE_COUNT_ASSERT_GT = _translate("Max trace count must be greater than or equal to {}")
    PROCESSING_DATA = _translate("Processing the collected data")
    SAVE_TRACE_FILE = _translate("Save trace file")

    # Same applies here, keep (*.trace) and (*)
    FILE_TYPES_TRACE = _translate("Trace File (*.trace);;All Files (*)")
    OPEN_TRACE_FILE = _translate("Open trace file")
    EXPAND_ALL = _translate("Expand All")
    COLLAPSE_ALL = _translate("Collapse All")
    DEFINED = _translate("DEFINED")
    DEFINED_SYMBOL = _translate("This symbol is defined. You can use its body as a gdb expression. For instance:\n\n"
                                "void func(param) can be used as 'func' as a gdb expression")
    COPY_SYMBOL = _translate("Copy Symbol")
    FUNCTIONS_INFO_HELPER = _translate("\tHere's some useful regex tips:\n"
                                       "^quaso --> search for everything that starts with quaso\n"
                                       "[ab]cd --> search for both acd and bcd\n\n"
                                       "\tHow to interpret symbols:\n"
                                       "A symbol that looks like 'func(param)@plt' consists of 3 pieces\n"
                                       "func, func(param), func(param)@plt\n"
                                       "These 3 functions will have different addresses\n"
                                       "@plt means this function is a subroutine for the original one\n"
                                       "There can be more than one of the same function\n"
                                       "It means that the function is overloaded")
    NEW_OPCODE = _translate("New opcode is {} bytes long but old opcode is only {} bytes long\n"
                            "This will cause an overflow, proceed?")
    IS_INVALID_EXPRESSION = _translate("{} isn't a valid expression")
    LOG_FILE = _translate("Log File of PID {}")
    LOG_CONTENTS = _translate("Contents of {} (only last {} bytes are shown)")
    ON = _translate("ON")
    OFF = _translate("OFF")
    LOG_STATUS = _translate("LOGGING: {}")
    LOG_READ_ERROR = _translate("Unable to read log file at {}")
    SETTINGS_ENABLE_LOG = _translate("Go to Settings->Debug to enable logging")
    INVALID_REGEX = _translate("Invalid Regex")
    SEARCH_OPCODE_HELPER = _translate("\tHere's some useful regex examples:\n"
                                      "call|rax --> search for opcodes that contain call or rax\n"
                                      "[re]cx --> search for both rcx and ecx\n"
                                      "Use the char \\ to escape special chars such as [\n"
                                      "\[rsp\] --> search for opcodes that contain [rsp]")
    COPY_ADDRESSES = _translate("Copy Addresses")
    COPY_OFFSET = _translate("Copy Offset")
    COPY_PATH = _translate("Copy Path")
    START = _translate("Start")
    CURRENT_SCAN_REGION = _translate("Currently scanning region:")
    CANCEL = _translate("Cancel")
    SCAN_FINISHED = _translate("Scan finished")
    SCAN_CANCELED = _translate("Scan was canceled")
    SELECT_ONE_REGION = _translate("Select at least one region")
    DISSECT_CODE = _translate("You need to dissect code first\n"
                              "Proceed?")
    WAITING_FOR_BREAKPOINT = _translate("Waiting for breakpoint to trigger")
    TRACING_CANCELED = _translate("Tracing has been canceled")
    TRACING_COMPLETED = _translate("Tracing has been completed")
    EXACT = _translate("Exact")
    INCREASED = _translate("Increased")
    INCREASED_BY = _translate("Increased by")
    DECREASED = _translate("Decreased")
    DECREASED_BY = _translate("Decreased by")
    LESS_THAN = _translate("Less Than")
    MORE_THAN = _translate("More Than")
    BETWEEN = _translate("Between")
    CHANGED = _translate("Changed")
    UNCHANGED = _translate("Unchanged")
    UNKNOWN_VALUE = _translate("Unknown Value")
    BASIC = _translate("Basic")
    NORMAL = _translate("Normal")
    RW = _translate("Read+Write")
    FULL = _translate("Full")
