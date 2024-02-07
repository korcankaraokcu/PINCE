import libpince.typedefs as typedefs

current_settings_version = "32"  # Increase version by one if you change settings


locale: str = ""
# Unused, will be re-added in the future
code_injection_method: int = 0

gdb_path: str = typedefs.PATHS.GDB
gdb_output_mode: tuple = (True, True, True)
gdb_logging: bool = False
interrupt_signal: str
handle_signals: list = []
# Due to community feedback, these signals are disabled by default: SIGUSR1, SIGUSR2, SIGPWR, SIGXCPU, SIGXFSZ, SIGSYS
default_signals = [
    ["SIGHUP", True, True], ["SIGINT", True, False], ["SIGQUIT", True, True], ["SIGILL", True, True],
    ["SIGTRAP", True, False], ["SIGABRT", True, True], ["SIGEMT", True, True], ["SIGFPE", True, True],
    ["SIGKILL", True, True], ["SIGBUS", True, True], ["SIGSEGV", True, True], ["SIGSYS", False, True],
    ["SIGPIPE", True, True], ["SIGALRM", False, True], ["SIGTERM", True, True], ["SIGURG", False, True],
    ["SIGSTOP", True, True], ["SIGTSTP", True, True], ["SIGCONT", True, True], ["SIGCHLD", False, True],
    ["SIGTTIN", True, True], ["SIGTTOU", True, True], ["SIGIO", False, True], ["SIGXCPU", False, True],
    ["SIGXFSZ", False, True], ["SIGVTALRM", False, True], ["SIGPROF", False, True], ["SIGWINCH", False, True],
    ["SIGLOST", True, True], ["SIGUSR1", False, True], ["SIGUSR2", False, True], ["SIGPWR", False, True],
    ["SIGPOLL", False, True], ["SIGWIND", True, True], ["SIGPHONE", True, True], ["SIGWAITING", False, True],
    ["SIGLWP", False, True], ["SIGDANGER", True, True], ["SIGGRANT", True, True], ["SIGRETRACT", True, True],
    ["SIGMSG", True, True], ["SIGSOUND", True, True], ["SIGSAK", True, True], ["SIGPRIO", False, True],
    ["SIGCANCEL", False, True], ["SIGINFO", True, True], ["EXC_BAD_ACCESS", True, True],
    ["EXC_BAD_INSTRUCTION", True, True], ["EXC_ARITHMETIC", True, True], ["EXC_EMULATION", True, True],
    ["EXC_SOFTWARE", True, True], ["EXC_BREAKPOINT", True, True], ["SIGLIBRT", False, True],
    #
    ['SIG32', True, True],
    ['SIG33', True, True], ['SIG34', True, True], ['SIG35', True, True], ['SIG36', True, True], ['SIG37', True, True],
    ['SIG38', True, True], ['SIG39', True, True], ['SIG40', True, True], ['SIG41', True, True], ['SIG42', True, True],
    ['SIG43', True, True], ['SIG44', True, True], ['SIG45', True, True], ['SIG46', True, True], ['SIG47', True, True],
    ['SIG48', True, True], ['SIG49', True, True], ['SIG50', True, True], ['SIG51', True, True], ['SIG52', True, True],
    ['SIG53', True, True], ['SIG54', True, True], ['SIG55', True, True], ['SIG56', True, True], ['SIG57', True, True],
    ['SIG58', True, True], ['SIG59', True, True], ['SIG60', True, True], ['SIG61', True, True], ['SIG62', True, True],
    ['SIG63', True, True], ['SIG64', True, True], ['SIG65', True, True], ['SIG66', True, True], ['SIG67', True, True],
    ['SIG68', True, True], ['SIG69', True, True], ['SIG70', True, True], ['SIG71', True, True], ['SIG72', True, True],
    ['SIG73', True, True], ['SIG74', True, True], ['SIG75', True, True], ['SIG76', True, True], ['SIG77', True, True],
    ['SIG78', True, True], ['SIG79', True, True], ['SIG80', True, True], ['SIG81', True, True], ['SIG82', True, True],
    ['SIG83', True, True], ['SIG84', True, True], ['SIG85', True, True], ['SIG86', True, True], ['SIG87', True, True],
    ['SIG88', True, True], ['SIG89', True, True], ['SIG90', True, True], ['SIG91', True, True], ['SIG92', True, True],
    ['SIG93', True, True], ['SIG94', True, True], ['SIG95', True, True], ['SIG96', True, True], ['SIG97', True, True],
    ['SIG98', True, True], ['SIG99', True, True], ['SIG100', True, True], ['SIG101', True, True],
    ['SIG102', True, True], ['SIG103', True, True], ['SIG104', True, True], ['SIG105', True, True],
    ['SIG106', True, True], ['SIG107', True, True], ['SIG108', True, True], ['SIG109', True, True],
    ['SIG110', True, True], ['SIG111', True, True], ['SIG112', True, True], ['SIG113', True, True],
    ['SIG114', True, True], ['SIG115', True, True], ['SIG116', True, True], ['SIG117', True, True],
    ['SIG118', True, True], ['SIG119', True, True], ['SIG120', True, True], ['SIG121', True, True],
    ['SIG122', True, True], ['SIG123', True, True], ['SIG124', True, True], ['SIG125', True, True],
    ['SIG126', True, True], ['SIG127', True, True]]
