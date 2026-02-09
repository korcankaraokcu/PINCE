import logging

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from GUI.States import states
from GUI.Settings import themes
from tr.tr import get_locale
from libpince import debugcore, utils, typedefs
import json, os

current_settings_version = "36"  # Increase version by one if you change settings

# Due to community feedback, these signals are disabled by default: SIGUSR1, SIGUSR2, SIGPWR, SIGXCPU, SIGXFSZ, SIGSYS
default_signals = [
    ["SIGHUP", True, True],
    ["SIGINT", True, False],
    ["SIGQUIT", True, True],
    ["SIGILL", True, True],
    ["SIGTRAP", True, False],
    ["SIGABRT", True, True],
    ["SIGEMT", True, True],
    ["SIGFPE", True, True],
    ["SIGKILL", True, True],
    ["SIGBUS", True, True],
    ["SIGSEGV", True, True],
    ["SIGSYS", False, True],
    ["SIGPIPE", True, True],
    ["SIGALRM", False, True],
    ["SIGTERM", True, True],
    ["SIGURG", False, True],
    ["SIGSTOP", True, True],
    ["SIGTSTP", True, True],
    ["SIGCONT", True, True],
    ["SIGCHLD", False, True],
    ["SIGTTIN", True, True],
    ["SIGTTOU", True, True],
    ["SIGIO", False, True],
    ["SIGXCPU", False, True],
    ["SIGXFSZ", False, True],
    ["SIGVTALRM", False, True],
    ["SIGPROF", False, True],
    ["SIGWINCH", False, True],
    ["SIGLOST", True, True],
    ["SIGUSR1", False, True],
    ["SIGUSR2", False, True],
    ["SIGPWR", False, True],
    ["SIGPOLL", False, True],
    ["SIGWIND", True, True],
    ["SIGPHONE", True, True],
    ["SIGWAITING", False, True],
    ["SIGLWP", False, True],
    ["SIGDANGER", True, True],
    ["SIGGRANT", True, True],
    ["SIGRETRACT", True, True],
    ["SIGMSG", True, True],
    ["SIGSOUND", True, True],
    ["SIGSAK", True, True],
    ["SIGPRIO", False, True],
    ["SIGCANCEL", False, True],
    ["SIGINFO", True, True],
    ["EXC_BAD_ACCESS", True, True],
    ["EXC_BAD_INSTRUCTION", True, True],
    ["EXC_ARITHMETIC", True, True],
    ["EXC_EMULATION", True, True],
    ["EXC_SOFTWARE", True, True],
    ["EXC_BREAKPOINT", True, True],
    ["SIGLIBRT", False, True],
]
for x in range(32, 128):  # Add signals SIG32-SIG127
    default_signals.append([f"SIG{x}", True, True])

logger = logging.getLogger(__name__)

def init_settings():
    settings = QSettings()
    if not os.path.exists(settings.fileName()):
        set_default_settings()
    try:
        settings_version = settings.value("Misc/version", type=str)
    except Exception:
        logger.exception("An exception occurred while reading settings version")
        settings_version = None
    if settings_version != current_settings_version:
        logger.warning("Settings version mismatch, rolling back to the default configuration")
        settings.clear()
        set_default_settings()
    try:
        apply_settings()
    except Exception:
        logger.exception("An exception occurred while loading settings, rolling back to the default configuration")
        settings.clear()
        set_default_settings()


# Please refrain from using python specific objects in settings, use json-compatible ones instead
# Using python objects causes issues when filenames change
def set_default_settings():
    settings = QSettings()
    settings.beginGroup("General")
    settings.setValue("auto_update_address_table", True)
    settings.setValue("address_table_update_interval", 500)
    settings.setValue("freeze_interval", 100)
    settings.setValue("gdb_output_mode", json.dumps([True, True, True]))
    settings.setValue("auto_attach", "")
    settings.setValue("auto_attach_regex", False)
    settings.setValue("locale", get_locale())
    settings.setValue("logo_path", "ozgurozbek/pince_small_transparent.png")
    settings.setValue("theme", themes.Themes.DEFAULT.value)
    settings.endGroup()
    settings.beginGroup("Hotkeys")
    for hotkey in states.hotkeys.get_hotkeys():
        settings.setValue(hotkey.name, hotkey.default)
    settings.endGroup()
    settings.beginGroup("CodeInjection")
    settings.setValue("code_injection_method", typedefs.INJECTION_METHOD.DLOPEN)
    settings.endGroup()
    settings.beginGroup("MemoryView")
    settings.setValue("show_memory_view_on_stop", False)
    settings.setValue("instructions_per_scroll", 3)
    settings.setValue("bytes_per_scroll", 0x40)
    settings.endGroup()
    settings.beginGroup("Debug")
    settings.setValue("gdb_path", typedefs.PATHS.GDB)
    settings.setValue("gdb_logging", False)
    settings.setValue("interrupt_signal", "SIGINT")
    settings.setValue("handle_signals", json.dumps(default_signals))
    settings.endGroup()
    settings.beginGroup("Java")
    settings.setValue("ignore_segfault", True)
    settings.endGroup()
    settings.beginGroup("Misc")
    settings.setValue("version", current_settings_version)
    settings.endGroup()
    apply_settings()


def apply_settings():
    settings = QSettings()
    states.update_table = settings.value("General/auto_update_address_table", type=bool)
    states.table_update_interval = settings.value("General/address_table_update_interval", type=int)
    states.freeze_interval = settings.value("General/freeze_interval", type=int)
    gdb_output_mode = json.loads(settings.value("General/gdb_output_mode", type=str))
    gdb_output_mode = typedefs.gdb_output_mode(*gdb_output_mode)
    states.auto_attach = settings.value("General/auto_attach", type=str)
    states.auto_attach_regex = settings.value("General/auto_attach_regex", type=bool)
    QApplication.setWindowIcon(
        QIcon(os.path.join(utils.get_logo_directory(), settings.value("General/logo_path", type=str)))
    )
    QApplication.setPalette(themes.get_theme(settings.value("General/theme", type=str)))
    debugcore.set_gdb_output_mode(gdb_output_mode)
    for hotkey in states.hotkeys.get_hotkeys():
        try:
            hotkey.change_key(settings.value("Hotkeys/" + hotkey.name))
        except:
            # if the hotkey cannot be applied for whatever reason, reset it to the default
            settings.setValue("Hotkeys/" + hotkey.name, hotkey.default)
            hotkey.change_key(hotkey.default)
    states.show_memory_view_on_stop = settings.value("MemoryView/show_memory_view_on_stop", type=bool)
    states.instructions_per_scroll = settings.value("MemoryView/instructions_per_scroll", type=int)
    states.bytes_per_scroll = settings.value("MemoryView/bytes_per_scroll", type=int)
    states.gdb_path = settings.value("Debug/gdb_path", type=str)
    if debugcore.gdb_initialized:
        apply_after_init()
    states.setting_signals.changed.emit()


def apply_after_init():
    settings = QSettings()
    states.exp_cache.clear()
    states.gdb_logging = settings.value("Debug/gdb_logging", type=bool)
    interrupt_signal = settings.value("Debug/interrupt_signal", type=str)
    handle_signals = json.loads(settings.value("Debug/handle_signals", type=str))
    java_ignore_segfault = settings.value("Java/ignore_segfault", type=bool)
    debugcore.set_logging(states.gdb_logging)

    # Don't handle signals if a process isn't present, a small optimization to gain time on launch and detach
    if debugcore.currentpid != -1:
        debugcore.handle_signals(handle_signals)
        # Not a great method but okayish until the implementation of the libpince engine and the java dissector
        # "jps" command could be used instead if we ever need to install openjdk
        if java_ignore_segfault and utils.get_process_name(debugcore.currentpid).startswith("java"):
            debugcore.handle_signal("SIGSEGV", False, True)
        debugcore.set_interrupt_signal(interrupt_signal)  # Needs to be called after handle_signals
