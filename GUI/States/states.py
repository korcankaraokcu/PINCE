from PyQt6.QtCore import QThreadPool
from GUI.Utils import guitypedefs

process_signals = guitypedefs.ProcessSignals()

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
exp_cache = {}

# Set to True when app is about to exit
exiting = False
