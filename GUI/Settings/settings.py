import libpince.typedefs as typedefs

current_settings_version = "34"  # Increase version by one if you change settings

# Unused, will be re-added in the future
code_injection_method: int = 0

gdb_path: str = typedefs.PATHS.GDB
gdb_output_mode: tuple = (True, True, True)
locale: str = "en_US"
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
    ["EXC_SOFTWARE", True, True], ["EXC_BREAKPOINT", True, True], ["SIGLIBRT", False, True]
]
for x in range(32, 128):  # Add signals SIG32-SIG127
  default_signals.append([f"SIG{x}", True, True])