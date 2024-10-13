from PyQt6.QtCore import QThreadPool
from GUI.Utils import guitypedefs

process_signals = guitypedefs.ProcessSignals()
setting_signals = guitypedefs.SettingSignals()

status_thread = guitypedefs.CheckInferiorStatus()
status_thread.start()

threadpool = QThreadPool()
# Placeholder number, may have to be changed in the future
threadpool.setMaxThreadCount(10)

# GDB expression cache
# TODO: Try to find a fast and non-gdb way to calculate symbols so we don't need this
# This is one of the few tricks we do to minimize examine_expression calls
# This solution might bring problems if the symbols are changing frequently
# Pressing the refresh button in the address table or attaching to a new process will clear this cache
# Currently only used in address_table_loop
exp_cache: dict[str, str] = {}

# Used by tableWidget_Disassemble in MemoryViewer
# Format -> {bookmark_address:comment}
bookmarks: dict[int, str] = {}

# Set to True when app is about to exit
exiting = False

hotkeys = guitypedefs.Hotkeys()

# The variables below are used for quick global access to settings for optimization or simplification purposes
# Initial values of these variables doesn't matter, they'll be set when apply_settings function is called
# Please don't throw every single settings variable here, only add variables that needs to be accessed frequently
update_table = False
table_update_interval = 0
freeze_interval = 0
auto_attach = ""
auto_attach_regex = False
show_memory_view_on_stop = False
instructions_per_scroll = 0
bytes_per_scroll = 0
gdb_path = ""
gdb_logging = False
