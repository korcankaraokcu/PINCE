#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>
Copyright (C) 2016-2017 Çağrı Ulaş <cagriulas@gmail.com>
Copyright (C) 2016-2017 Jakob Kreuze <jakob@memeware.net>

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
import gi

import GUI.Settings.settings as settings
from GUI.Settings.hotkeys import Hotkeys

# This fixes GTK version mismatch issues and crashes on gnome
# See #153 and #159 for more information
# This line can be deleted when GTK 4.0 properly runs on all supported systems
gi.require_version("Gtk", "3.0")

from tr.tr import TranslationConstants as tr
from tr.tr import language_list, get_locale

from PyQt6.QtGui import (
    QIcon,
    QMovie,
    QPixmap,
    QCursor,
    QKeySequence,
    QColor,
    QTextCharFormat,
    QBrush,
    QTextCursor,
    QShortcut,
    QColorConstants,
    QStandardItemModel,
    QStandardItem,
    QCloseEvent,
    QKeyEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTableWidgetItem,
    QMessageBox,
    QDialog,
    QWidget,
    QTabWidget,
    QMenu,
    QFileDialog,
    QAbstractItemView,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QCompleter,
    QLabel,
    QLineEdit,
    QComboBox,
    QDialogButtonBox,
    QCheckBox,
    QHBoxLayout,
    QPushButton,
)
from PyQt6.QtCore import (
    Qt,
    QThread,
    pyqtSignal,
    QSize,
    QByteArray,
    QSettings,
    QEvent,
    QKeyCombination,
    QTranslator,
    QItemSelectionModel,
    QTimer,
    QStringListModel,
    QRunnable,
    QObject,
    QThreadPool,
    QLocale,
    QSignalBlocker,
    QItemSelection,
)
from time import sleep, time
import os, sys, traceback, signal, re, copy, io, queue, collections, ast, pexpect, json, select

from libpince import utils, debugcore, typedefs
from libpince.libscanmem.scanmem import Scanmem
from libpince.libptrscan.ptrscan import PointerScan, FFIRange, FFIParam
from GUI.Settings.themes import get_theme
from GUI.Settings.themes import theme_list
from GUI.Utils import guiutils

from GUI.MainWindow import Ui_MainWindow as MainWindow
from GUI.SelectProcess import Ui_MainWindow as ProcessWindow
from GUI.AddAddressManuallyDialog import Ui_Dialog as ManualAddressDialog
from GUI.EditTypeDialog import Ui_Dialog as EditTypeDialog
from GUI.TrackSelectorDialog import Ui_Dialog as TrackSelectorDialog
from GUI.LoadingDialog import Ui_Dialog as LoadingDialog
from GUI.InputDialog import Ui_Dialog as InputDialog
from GUI.TextEditDialog import Ui_Dialog as TextEditDialog
from GUI.SettingsDialog import Ui_Dialog as SettingsDialog
from GUI.HandleSignalsDialog import Ui_Dialog as HandleSignalsDialog
from GUI.ConsoleWidget import Ui_Form as ConsoleWidget
from GUI.AboutWidget import Ui_TabWidget as AboutWidget

# If you are going to change the name "Ui_MainWindow_MemoryView", review GUI/Labels/RegisterLabel.py as well
from GUI.MemoryViewerWindow import Ui_MainWindow_MemoryView as MemoryViewWindow
from GUI.BookmarkWidget import Ui_Form as BookmarkWidget
from GUI.FloatRegisterWidget import Ui_TabWidget as FloatRegisterWidget
from GUI.StackTraceInfoWidget import Ui_Form as StackTraceInfoWidget
from GUI.BreakpointInfoWidget import Ui_TabWidget as BreakpointInfoWidget
from GUI.TrackWatchpointWidget import Ui_Form as TrackWatchpointWidget
from GUI.TrackBreakpointWidget import Ui_Form as TrackBreakpointWidget
from GUI.TraceInstructionsPromptDialog import Ui_Dialog as TraceInstructionsPromptDialog
from GUI.TraceInstructionsWaitWidget import Ui_Form as TraceInstructionsWaitWidget
from GUI.TraceInstructionsWindow import Ui_MainWindow as TraceInstructionsWindow
from GUI.FunctionsInfoWidget import Ui_Form as FunctionsInfoWidget
from GUI.HexEditDialog import Ui_Dialog as HexEditDialog
from GUI.EditInstructionDialog import Ui_Dialog as EditInstructionDialog
from GUI.LibpinceReferenceWidget import Ui_Form as LibpinceReferenceWidget
from GUI.LogFileWidget import Ui_Form as LogFileWidget
from GUI.SearchOpcodeWidget import Ui_Form as SearchOpcodeWidget
from GUI.MemoryRegionsWidget import Ui_Form as MemoryRegionsWidget
from GUI.DissectCodeDialog import Ui_Dialog as DissectCodeDialog
from GUI.ReferencedStringsWidget import Ui_Form as ReferencedStringsWidget
from GUI.ReferencedCallsWidget import Ui_Form as ReferencedCallsWidget
from GUI.ExamineReferrersWidget import Ui_Form as ExamineReferrersWidget
from GUI.RestoreInstructionsWidget import Ui_Form as RestoreInstructionsWidget
from GUI.PointerScanSearchDialog import Ui_Dialog as PointerScanSearchDialog
from GUI.PointerScanFilterDialog import Ui_Dialog as PointerScanFilterDialog
from GUI.PointerScanWindow import Ui_MainWindow as PointerScanWindow

from GUI.AbstractTableModels.HexModel import QHexModel
from GUI.AbstractTableModels.AsciiModel import QAsciiModel
from GUI.Validators.HexValidator import QHexValidator
from GUI.ManualAddressDialogUtils.PointerChainOffset import PointerChainOffset

from keyboard import KeyboardEvent, _pressed_events
from keyboard._nixkeyboard import to_name

if __name__ == "__main__":
    app = QApplication([])
    app.setOrganizationName("PINCE")
    app.setOrganizationDomain("github.com/korcankaraokcu/PINCE")
    app.setApplicationName("PINCE")
    QSettings.setPath(
        QSettings.Format.NativeFormat, QSettings.Scope.UserScope, utils.get_user_path(typedefs.USER_PATHS.CONFIG)
    )
    settings_instance = QSettings()
    translator = QTranslator()
    try:
        locale = settings_instance.value("General/locale", type=str)
    except SystemError:
        # We're reading the settings for the first time here
        # If there's an error due to python objects, clear settings
        settings_instance.clear()
        locale = None
    if not locale:
        locale = get_locale()
    locale_file = utils.get_script_directory() + f"/i18n/qm/{locale}.qm"
    translator.load(locale_file)
    app.installTranslator(translator)
    tr.translate()
    hotkeys = Hotkeys()  # Create the instance after translations to ensure hotkeys are translated

# represents the index of columns in instructions restore table
INSTR_ADDR_COL = 0
INSTR_AOB_COL = 1
INSTR_NAME_COL = 2

# represents the index of columns in breakpoint table
BREAK_NUM_COL = 0
BREAK_TYPE_COL = 1
BREAK_DISP_COL = 2
BREAK_ENABLED_COL = 3
BREAK_ADDR_COL = 4
BREAK_SIZE_COL = 5
BREAK_ON_HIT_COL = 6
BREAK_HIT_COUNT_COL = 7
BREAK_COND_COL = 8

# row colors for disassemble qtablewidget
PC_COLOR = QColorConstants.Blue
BOOKMARK_COLOR = QColorConstants.Cyan
BREAKPOINT_COLOR = QColorConstants.Red
REF_COLOR = QColorConstants.LightGray

# represents the index of columns in address table
FROZEN_COL = 0  # Frozen
DESC_COL = 1  # Description
ADDR_COL = 2  # Address
TYPE_COL = 3  # Type
VALUE_COL = 4  # Value

# represents the index of columns in search results table
SEARCH_TABLE_ADDRESS_COL = 0
SEARCH_TABLE_VALUE_COL = 1
SEARCH_TABLE_PREVIOUS_COL = 2

# represents the index of columns in disassemble table
DISAS_ADDR_COL = 0
DISAS_BYTES_COL = 1
DISAS_OPCODES_COL = 2
DISAS_COMMENT_COL = 3

# represents the index of columns in floating point table
FLOAT_REGISTERS_NAME_COL = 0
FLOAT_REGISTERS_VALUE_COL = 1

# represents the index of columns in stacktrace table
STACKTRACE_RETURN_ADDRESS_COL = 0
STACKTRACE_FRAME_ADDRESS_COL = 1

# represents the index of columns in stack table
STACK_POINTER_ADDRESS_COL = 0
STACK_VALUE_COL = 1
STACK_POINTS_TO_COL = 2

# represents row and column counts of Hex table
HEX_VIEW_COL_COUNT = 16
HEX_VIEW_ROW_COUNT = 42  # J-JUST A COINCIDENCE, I SWEAR!

# represents the index of columns in track watchpoint table(what accesses this address thingy)
TRACK_WATCHPOINT_COUNT_COL = 0
TRACK_WATCHPOINT_ADDR_COL = 1

# represents the index of columns in track breakpoint table(which addresses this instruction accesses thingy)
TRACK_BREAKPOINT_COUNT_COL = 0
TRACK_BREAKPOINT_ADDR_COL = 1
TRACK_BREAKPOINT_VALUE_COL = 2
TRACK_BREAKPOINT_SOURCE_COL = 3

# represents the index of columns in function info table
FUNCTIONS_INFO_ADDR_COL = 0
FUNCTIONS_INFO_SYMBOL_COL = 1

# represents the index of columns in libpince reference resources table
LIBPINCE_REFERENCE_ITEM_COL = 0
LIBPINCE_REFERENCE_VALUE_COL = 1

# represents the index of columns in search opcode table
SEARCH_OPCODE_ADDR_COL = 0
SEARCH_OPCODE_OPCODES_COL = 1

# represents the index of columns in memory regions table
MEMORY_REGIONS_ADDR_COL = 0
MEMORY_REGIONS_PERM_COL = 1
MEMORY_REGIONS_OFFSET_COL = 2
MEMORY_REGIONS_PATH_COL = 3

# represents the index of columns in dissect code table
DISSECT_CODE_ADDR_COL = 0
DISSECT_CODE_PATH_COL = 1

# represents the index of columns in referenced strings table
REF_STR_ADDR_COL = 0
REF_STR_COUNT_COL = 1
REF_STR_VAL_COL = 2

# represents the index of columns in referenced calls table
REF_CALL_ADDR_COL = 0
REF_CALL_COUNT_COL = 1

# GDB expression cache
# TODO: Try to find a fast and non-gdb way to calculate symbols so we don't need this
# This is one of the few tricks we do to minimize examine_expression calls
# This solution might bring problems if the symbols are changing frequently
# Pressing the refresh button in the address table or attaching to a new process will clear this cache
# Currently only used in address_table_loop
exp_cache = {}

# vars for communication with the non blocking threads
exiting = 0

scanmem = Scanmem(os.path.join(utils.get_libpince_directory(), "libscanmem", "libscanmem.so"))
ptrscan = PointerScan(os.path.join(utils.get_libpince_directory(), "libptrscan", "libptrscan.so"))
ptrscan.set_pointer_offset_symbol("->")

threadpool = QThreadPool()
# Placeholder number, may have to be changed in the future
threadpool.setMaxThreadCount(10)


class ProcessSignals(QObject):
    attach = pyqtSignal()
    exit = pyqtSignal()


process_signals = ProcessSignals()


class WorkerSignals(QObject):
    finished = pyqtSignal()


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()


class InterruptableWorker(QThread):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()

    def stop(self):
        self.terminate()


def except_hook(exception_type, value, tb):
    focused_widget = app.focusWidget()
    if focused_widget and exception_type == typedefs.GDBInitializeException:
        QMessageBox.information(focused_widget, tr.ERROR, tr.GDB_INIT)
    traceback.print_exception(exception_type, value, tb)


# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = except_hook

quit_prompt_active = False


def signal_handler(signal, frame):
    global quit_prompt_active
    with QSignalBlocker(app):
        if debugcore.lock_send_command.locked():
            print("\nCancelling the last GDB command")
            debugcore.cancel_last_command()
        else:
            if quit_prompt_active:
                print()  # Prints a newline so the terminal looks nicer when we quit
                debugcore.detach()
                quit()
            quit_prompt_active = True
            print("\nNo GDB command to cancel, quit PINCE? (y/n)", end="", flush=True)
            while True:
                # Using select() instead of input() because it causes the bug below
                # QBackingStore::endPaint() called with active painter
                rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
                if rlist:
                    user_input = sys.stdin.readline().strip().lower()
                    break
            if user_input.startswith("y"):
                debugcore.detach()
                quit()
            else:
                print("Quit aborted")
            quit_prompt_active = False


signal.signal(signal.SIGINT, signal_handler)


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while True:
            with debugcore.process_exited_condition:
                debugcore.process_exited_condition.wait()
            self.process_exited.emit()


# Await async output from gdb
class AwaitAsyncOutput(QThread):
    async_output_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue_active = True

    def run(self):
        async_output_queue = debugcore.gdb_async_output.register_queue()
        while self.queue_active:
            try:
                async_output = async_output_queue.get(timeout=5)
            except queue.Empty:
                pass
            else:
                self.async_output_ready.emit(async_output)
        debugcore.gdb_async_output.delete_queue(async_output_queue)

    def stop(self):
        self.queue_active = False


class CheckInferiorStatus(QThread):
    process_stopped = pyqtSignal()
    process_running = pyqtSignal()

    def run(self):
        while True:
            with debugcore.status_changed_condition:
                debugcore.status_changed_condition.wait()
            if debugcore.inferior_status == typedefs.INFERIOR_STATUS.STOPPED:
                self.process_stopped.emit()
            elif debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                self.process_running.emit()


class MainForm(QMainWindow, MainWindow):
    table_update_interval: int = 500
    freeze_interval: int = 100
    update_table: bool = True
    auto_attach: str = ""
    auto_attach_regex: bool = False

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.hotkey_to_shortcut = {}
        hotkey_to_func = {
            hotkeys.pause_hotkey: self.pause_hotkey_pressed,
            hotkeys.break_hotkey: self.break_hotkey_pressed,
            hotkeys.continue_hotkey: self.continue_hotkey_pressed,
            hotkeys.toggle_attach_hotkey: self.toggle_attach_hotkey_pressed,
            hotkeys.exact_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.EXACT),
            hotkeys.increased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.INCREASED),
            hotkeys.decreased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.DECREASED),
            hotkeys.changed_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.CHANGED),
            hotkeys.unchanged_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.UNCHANGED),
        }
        for hotkey, func in hotkey_to_func.items():
            hotkey.change_func(func)
        self.treeWidget_AddressTable.setColumnWidth(FROZEN_COL, 50)
        self.treeWidget_AddressTable.setColumnWidth(DESC_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(ADDR_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(TYPE_COL, 150)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_ADDRESS_COL, 110)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_VALUE_COL, 80)
        self.settings = QSettings()
        self.memory_view_window = MemoryViewWindowForm(self)
        self.await_exit_thread = AwaitProcessExit()
        self.auto_attach_timer = QTimer(timeout=self.auto_attach_loop)

        if not os.path.exists(self.settings.fileName()):
            self.set_default_settings()
        try:
            settings_version = self.settings.value("Misc/version", type=str)
        except Exception as e:
            print("An exception occurred while reading settings version\n", e)
            settings_version = None
        if settings_version != settings.current_settings_version:
            print("Settings version mismatch, rolling back to the default configuration")
            self.settings.clear()
            self.set_default_settings()
        try:
            self.apply_settings()
        except Exception as e:
            print("An exception occurred while loading settings, rolling back to the default configuration\n", e)
            self.settings.clear()
            self.set_default_settings()
        try:
            gdb_path = settings.gdb_path
            if os.environ.get("APPDIR"):
                gdb_path = utils.get_default_gdb_path()
            debugcore.init_gdb(gdb_path)
        except pexpect.EOF:
            InputDialogForm(self, [(tr.GDB_INIT_ERROR, None)], buttons=[QDialogButtonBox.StandardButton.Ok]).exec()
        else:
            self.apply_after_init()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.check_status_thread = CheckInferiorStatus()
        self.check_status_thread.process_stopped.connect(self.on_status_stopped)
        self.check_status_thread.process_running.connect(self.on_status_running)
        self.check_status_thread.process_stopped.connect(self.memory_view_window.process_stopped)
        self.check_status_thread.process_running.connect(self.memory_view_window.process_running)
        self.check_status_thread.start()
        self.address_table_timer = QTimer(timeout=self.address_table_loop, singleShot=True)
        self.address_table_timer.start()
        self.search_table_timer = QTimer(timeout=self.search_table_loop, singleShot=True)
        self.search_table_timer.start()
        self.freeze_timer = QTimer(timeout=self.freeze_loop, singleShot=True)
        self.freeze_timer.start()
        self.shortcut_open_file = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_open_file.activated.connect(self.pushButton_Open_clicked)
        guiutils.append_shortcut_to_tooltip(self.pushButton_Open, self.shortcut_open_file)
        self.shortcut_save_file = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save_file.activated.connect(self.pushButton_Save_clicked)
        guiutils.append_shortcut_to_tooltip(self.pushButton_Save, self.shortcut_save_file)

        # Saving the original function because super() doesn't work when we override functions like this
        self.treeWidget_AddressTable.keyPressEvent_original = self.treeWidget_AddressTable.keyPressEvent
        self.treeWidget_AddressTable.keyPressEvent = self.treeWidget_AddressTable_key_press_event
        self.treeWidget_AddressTable.contextMenuEvent = self.treeWidget_AddressTable_context_menu_event
        self.pushButton_AttachProcess.clicked.connect(self.pushButton_AttachProcess_clicked)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_clicked)
        self.pushButton_Save.clicked.connect(self.pushButton_Save_clicked)
        self.pushButton_NewFirstScan.clicked.connect(self.pushButton_NewFirstScan_clicked)
        self.pushButton_UndoScan.clicked.connect(self.pushButton_UndoScan_clicked)
        self.pushButton_NextScan.clicked.connect(self.pushButton_NextScan_clicked)
        self.scan_mode = typedefs.SCAN_MODE.NEW
        self.pushButton_NewFirstScan_clicked()
        self.comboBox_ScanScope_init()
        self.comboBox_ValueType_init()
        guiutils.fill_endianness_combobox(self.comboBox_Endianness)
        self.checkBox_Hex.stateChanged.connect(self.checkBox_Hex_stateChanged)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int"))
        self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int"))
        self.lineEdit_Scan.keyPressEvent_original = self.lineEdit_Scan.keyPressEvent
        self.lineEdit_Scan2.keyPressEvent_original = self.lineEdit_Scan2.keyPressEvent
        self.lineEdit_Scan.keyPressEvent = self.lineEdit_Scan_on_key_press_event
        self.lineEdit_Scan2.keyPressEvent = self.lineEdit_Scan2_on_key_press_event
        self.comboBox_ScanType.currentIndexChanged.connect(self.comboBox_ScanType_current_index_changed)
        self.comboBox_ScanType_current_index_changed()
        self.pushButton_Settings.clicked.connect(self.pushButton_Settings_clicked)
        self.pushButton_Console.clicked.connect(self.pushButton_Console_clicked)
        self.pushButton_Wiki.clicked.connect(self.pushButton_Wiki_clicked)
        self.pushButton_About.clicked.connect(self.pushButton_About_clicked)
        self.pushButton_AddAddressManually.clicked.connect(self.pushButton_AddAddressManually_clicked)
        self.pushButton_MemoryView.clicked.connect(self.pushButton_MemoryView_clicked)
        self.pushButton_RefreshAdressTable.clicked.connect(self.pushButton_RefreshAdressTable_clicked)
        self.pushButton_CopyToAddressTable.clicked.connect(self.copy_to_address_table)
        self.pushButton_CleanAddressTable.clicked.connect(self.clear_address_table)
        self.tableWidget_valuesearchtable.cellDoubleClicked.connect(
            self.tableWidget_valuesearchtable_cell_double_clicked
        )
        self.tableWidget_valuesearchtable.keyPressEvent_original = self.tableWidget_valuesearchtable.keyPressEvent
        self.tableWidget_valuesearchtable.keyPressEvent = self.tableWidget_valuesearchtable_key_press_event
        self.treeWidget_AddressTable.itemClicked.connect(self.treeWidget_AddressTable_item_clicked)
        self.treeWidget_AddressTable.itemDoubleClicked.connect(self.treeWidget_AddressTable_item_double_clicked)
        self.treeWidget_AddressTable.expanded.connect(self.resize_address_table)
        self.treeWidget_AddressTable.collapsed.connect(self.resize_address_table)
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_AttachProcess.setIcon(QIcon(QPixmap(icons_directory + "/monitor.png")))
        self.pushButton_Open.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        self.pushButton_Save.setIcon(QIcon(QPixmap(icons_directory + "/disk.png")))
        self.pushButton_Settings.setIcon(QIcon(QPixmap(icons_directory + "/wrench.png")))
        self.pushButton_CopyToAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/arrow_down.png")))
        self.pushButton_CleanAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/bin_closed.png")))
        self.pushButton_RefreshAdressTable.setIcon(QIcon(QPixmap(icons_directory + "/table_refresh.png")))
        self.pushButton_Console.setIcon(QIcon(QPixmap(icons_directory + "/application_xp_terminal.png")))
        self.pushButton_Wiki.setIcon(QIcon(QPixmap(icons_directory + "/book_open.png")))
        self.pushButton_About.setIcon(QIcon(QPixmap(icons_directory + "/information.png")))
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.flashAttachButton = True
        self.flashAttachButtonTimer = QTimer()
        self.flashAttachButtonTimer.timeout.connect(self.flash_attach_button)
        self.flashAttachButton_gradiantState = 0
        self.flashAttachButtonTimer.start(100)
        guiutils.center(self)

    # Please refrain from using python specific objects in settings, use json-compatible ones instead
    # Using python objects causes issues when filenames change
    def set_default_settings(self):
        self.settings.beginGroup("General")
        self.settings.setValue("auto_update_address_table", MainForm.update_table)
        self.settings.setValue("address_table_update_interval", MainForm.table_update_interval)
        self.settings.setValue("freeze_interval", MainForm.freeze_interval)
        self.settings.setValue("gdb_output_mode", json.dumps([True, True, True]))
        self.settings.setValue("auto_attach", MainForm.auto_attach)
        self.settings.setValue("auto_attach_regex", MainForm.auto_attach_regex)
        self.settings.setValue("locale", get_locale())
        self.settings.setValue("logo_path", "ozgurozbek/pince_small_transparent.png")
        self.settings.setValue("theme", "System Default")
        self.settings.endGroup()
        self.settings.beginGroup("Hotkeys")
        for hotkey in hotkeys.get_hotkeys():
            self.settings.setValue(hotkey.name, hotkey.default)
        self.settings.endGroup()
        self.settings.beginGroup("CodeInjection")
        self.settings.setValue("code_injection_method", typedefs.INJECTION_METHOD.DLOPEN)
        self.settings.endGroup()
        self.settings.beginGroup("MemoryView")
        self.settings.setValue("show_memory_view_on_stop", False)
        self.settings.setValue("instructions_per_scroll", MemoryViewWindowForm.instructions_per_scroll)
        self.settings.setValue("bytes_per_scroll", MemoryViewWindowForm.bytes_per_scroll)
        self.settings.endGroup()
        self.settings.beginGroup("Debug")
        self.settings.setValue("gdb_path", typedefs.PATHS.GDB)
        self.settings.setValue("gdb_logging", False)
        self.settings.setValue("interrupt_signal", "SIGINT")
        self.settings.setValue("handle_signals", json.dumps(settings.default_signals))
        self.settings.endGroup()
        self.settings.beginGroup("Java")
        self.settings.setValue("ignore_segfault", True)
        self.settings.endGroup()
        self.settings.beginGroup("Misc")
        self.settings.setValue("version", settings.current_settings_version)
        self.settings.endGroup()
        self.apply_settings()

    def apply_after_init(self):
        global exp_cache

        exp_cache.clear()
        settings.gdb_logging = self.settings.value("Debug/gdb_logging", type=bool)
        settings.interrupt_signal = self.settings.value("Debug/interrupt_signal", type=str)
        settings.handle_signals = json.loads(self.settings.value("Debug/handle_signals", type=str))
        java_ignore_segfault = self.settings.value("Java/ignore_segfault", type=bool)
        debugcore.set_logging(settings.gdb_logging)

        # Don't handle signals if a process isn't present, a small optimization to gain time on launch and detach
        if debugcore.currentpid != -1:
            debugcore.handle_signals(settings.handle_signals)
            # Not a great method but okayish until the implementation of the libpince engine and the java dissector
            # "jps" command could be used instead if we ever need to install openjdk
            if java_ignore_segfault and utils.get_process_name(debugcore.currentpid).startswith("java"):
                debugcore.handle_signal("SIGSEGV", False, True)
            debugcore.set_interrupt_signal(settings.interrupt_signal)  # Needs to be called after handle_signals

    def apply_settings(self):
        self.update_table = self.settings.value("General/auto_update_address_table", type=bool)
        self.table_update_interval = self.settings.value("General/address_table_update_interval", type=int)
        self.freeze_interval = self.settings.value("General/freeze_interval", type=int)
        settings.gdb_output_mode = json.loads(self.settings.value("General/gdb_output_mode", type=str))
        settings.gdb_output_mode = typedefs.gdb_output_mode(*settings.gdb_output_mode)
        self.auto_attach = self.settings.value("General/auto_attach", type=str)
        self.auto_attach_regex = self.settings.value("General/auto_attach_regex", type=bool)
        if self.auto_attach:
            self.auto_attach_timer.start(100)
        else:
            self.auto_attach_timer.stop()
        settings.locale = self.settings.value("General/locale", type=str)
        app.setWindowIcon(
            QIcon(os.path.join(utils.get_logo_directory(), self.settings.value("General/logo_path", type=str)))
        )
        app.setPalette(get_theme(self.settings.value("General/theme", type=str)))
        debugcore.set_gdb_output_mode(settings.gdb_output_mode)
        for hotkey in hotkeys.get_hotkeys():
            try:
                hotkey.change_key(self.settings.value("Hotkeys/" + hotkey.name))
            except:
                # if the hotkey cannot be applied for whatever reason, reset it to the default
                self.settings.setValue("Hotkeys/" + hotkey.name, hotkey.default)
                hotkey.change_key(hotkey.default)

        try:
            self.memory_view_window.set_dynamic_debug_hotkeys()
        except AttributeError:
            pass
        settings.code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        self.memory_view_window.show_memory_view_on_stop = self.settings.value(
            "MemoryView/show_memory_view_on_stop", type=bool
        )
        self.memory_view_window.instructions_per_scroll = self.settings.value(
            "MemoryView/instructions_per_scroll", type=int
        )
        self.memory_view_window.bytes_per_scroll = self.settings.value("MemoryView/bytes_per_scroll", type=int)
        settings.gdb_path = self.settings.value("Debug/gdb_path", type=str)
        if debugcore.gdb_initialized:
            self.apply_after_init()

    # Check if any process should be attached to automatically
    # Patterns at former positions have higher priority if regex is off
    def auto_attach_loop(self):
        if debugcore.currentpid != -1:
            return
        if self.auto_attach_regex:
            try:
                compiled_re = re.compile(self.auto_attach)
            except:
                print(f"Auto-attach failed: {self.auto_attach} isn't a valid regex")
                return
            for pid, _, name in utils.get_process_list():
                if compiled_re.search(name):
                    self.attach_to_pid(int(pid))
                    return
        else:
            for target in self.auto_attach.split(";"):
                for pid, _, name in utils.get_process_list():
                    if name.find(target) != -1:
                        self.attach_to_pid(int(pid))
                        return

    # Keyboard package has an issue with exceptions, any trigger function that throws an exception stops the event loop
    # Writing a custom event loop instead of ignoring exceptions could work as well but honestly, this looks cleaner
    # Keyboard package does not play well with Qt, do not use anything Qt related with hotkeys
    # Instead of using Qt functions, try to use their signals to prevent crashes
    @utils.ignore_exceptions
    def pause_hotkey_pressed(self):
        if not debugcore.active_trace:
            debugcore.interrupt_inferior(typedefs.STOP_REASON.PAUSE)

    @utils.ignore_exceptions
    def break_hotkey_pressed(self):
        if not debugcore.active_trace:
            debugcore.interrupt_inferior()

    @utils.ignore_exceptions
    def continue_hotkey_pressed(self):
        if not (
            debugcore.currentpid == -1
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or debugcore.active_trace
        ):
            debugcore.continue_inferior()

    @utils.ignore_exceptions
    def toggle_attach_hotkey_pressed(self):
        result = debugcore.toggle_attach()
        if not result:
            print("Unable to toggle attach")
        elif result == typedefs.TOGGLE_ATTACH.DETACHED:
            self.on_status_detached()
        else:
            # Attaching back doesn't update the status if the process is already stopped before detachment
            with debugcore.status_changed_condition:
                debugcore.status_changed_condition.notify_all()

    @utils.ignore_exceptions
    def nextscan_hotkey_pressed(self, index):
        if self.scan_mode == typedefs.SCAN_MODE.NEW:
            return
        self.comboBox_ScanType.setCurrentIndex(index)
        self.pushButton_NextScan.clicked.emit()

    def treeWidget_AddressTable_context_menu_event(self, event):
        current_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        header = self.treeWidget_AddressTable.headerItem()
        menu = QMenu()
        delete_record = menu.addAction(f"{tr.DELETE}[Del]")
        edit_menu = menu.addMenu(tr.EDIT)
        edit_desc = edit_menu.addAction(f"{header.text(DESC_COL)}[Ctrl+Enter]")
        edit_address = edit_menu.addAction(f"{header.text(ADDR_COL)}[Ctrl+Alt+Enter]")
        edit_type = edit_menu.addAction(f"{header.text(TYPE_COL)}[Alt+Enter]")
        edit_value = edit_menu.addAction(f"{header.text(VALUE_COL)}[Enter]")
        show_hex = menu.addAction(tr.SHOW_HEX)
        show_dec = menu.addAction(tr.SHOW_DEC)
        show_unsigned = menu.addAction(tr.SHOW_UNSIGNED)
        show_signed = menu.addAction(tr.SHOW_SIGNED)
        toggle_record = menu.addAction(f"{tr.TOGGLE}[Space]")
        toggle_children = menu.addAction(f"{tr.TOGGLE_CHILDREN}[Ctrl+Space]")
        freeze_menu = menu.addMenu(tr.FREEZE)
        freeze_default = freeze_menu.addAction(tr.DEFAULT)
        freeze_inc = freeze_menu.addAction(tr.INCREMENTAL)
        freeze_dec = freeze_menu.addAction(tr.DECREMENTAL)
        menu.addSeparator()
        browse_region = menu.addAction(f"{tr.BROWSE_MEMORY_REGION}[Ctrl+B]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        pointer_scanner = menu.addAction(tr.POINTER_SCANNER)
        pointer_scan = menu.addAction(tr.POINTER_SCAN)
        menu.addSeparator()
        what_writes = menu.addAction(tr.WHAT_WRITES)
        what_reads = menu.addAction(tr.WHAT_READS)
        what_accesses = menu.addAction(tr.WHAT_ACCESSES)
        menu.addSeparator()
        cut_record = menu.addAction(f"{tr.CUT}[Ctrl+X]")
        copy_record = menu.addAction(f"{tr.COPY}[Ctrl+C]")
        paste_record = menu.addAction(f"{tr.PASTE}[Ctrl+V]")
        paste_inside = menu.addAction(f"{tr.PASTE_INSIDE}[V]")
        menu.addSeparator()
        add_group = menu.addAction(tr.ADD_GROUP)
        create_group = menu.addAction(tr.CREATE_GROUP)
        if current_row is None:
            deletion_list = [
                edit_menu.menuAction(),
                show_hex,
                show_dec,
                show_unsigned,
                show_signed,
                toggle_record,
                toggle_children,
                freeze_menu.menuAction(),
                browse_region,
                disassemble,
                pointer_scan,
                what_writes,
                what_reads,
                what_accesses,
                cut_record,
                copy_record,
                paste_inside,
                delete_record,
                add_group,
            ]
            guiutils.delete_menu_entries(menu, deletion_list)
        else:
            value_type = current_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            if typedefs.VALUE_INDEX.is_integer(value_type.value_index):
                if value_type.value_repr is typedefs.VALUE_REPR.HEX:
                    guiutils.delete_menu_entries(menu, [show_unsigned, show_signed, show_hex])
                elif value_type.value_repr is typedefs.VALUE_REPR.UNSIGNED:
                    guiutils.delete_menu_entries(menu, [show_unsigned, show_dec])
                elif value_type.value_repr is typedefs.VALUE_REPR.SIGNED:
                    guiutils.delete_menu_entries(menu, [show_signed, show_dec])
                if current_row.checkState(FROZEN_COL) == Qt.CheckState.Unchecked:
                    guiutils.delete_menu_entries(menu, [freeze_menu.menuAction()])
            else:
                guiutils.delete_menu_entries(
                    menu, [show_hex, show_dec, show_unsigned, show_signed, freeze_menu.menuAction()]
                )
            if current_row.childCount() == 0:
                guiutils.delete_menu_entries(menu, [toggle_children])
            guiutils.delete_menu_entries(menu, [pointer_scanner])
            if debugcore.currentpid == -1:
                browse_region.setEnabled(False)
                disassemble.setEnabled(False)
                pointer_scan.setEnabled(False)
            if not debugcore.is_attached():
                what_writes.setEnabled(False)
                what_reads.setEnabled(False)
                what_accesses.setEnabled(False)
        font_size = self.treeWidget_AddressTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            delete_record: self.delete_records,
            edit_desc: self.treeWidget_AddressTable_edit_desc,
            edit_address: self.treeWidget_AddressTable_edit_address,
            edit_type: self.treeWidget_AddressTable_edit_type,
            edit_value: self.treeWidget_AddressTable_edit_value,
            show_hex: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.HEX),
            show_dec: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.UNSIGNED),
            show_unsigned: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.UNSIGNED),
            show_signed: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.SIGNED),
            toggle_record: self.toggle_records,
            toggle_children: lambda: self.toggle_records(True),
            freeze_default: lambda: self.change_freeze_type(typedefs.FREEZE_TYPE.DEFAULT),
            freeze_inc: lambda: self.change_freeze_type(typedefs.FREEZE_TYPE.INCREMENT),
            freeze_dec: lambda: self.change_freeze_type(typedefs.FREEZE_TYPE.DECREMENT),
            browse_region: self.browse_region_for_selected_row,
            disassemble: self.disassemble_selected_row,
            pointer_scanner: self.exec_pointer_scanner,
            pointer_scan: self.exec_pointer_scan,
            what_writes: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.WRITE_ONLY),
            what_reads: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.READ_ONLY),
            what_accesses: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.BOTH),
            cut_record: self.cut_records,
            copy_record: self.copy_records,
            paste_record: self.paste_records,
            paste_inside: lambda: self.paste_records(True),
            add_group: self.group_records,
            create_group: self.create_group,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def exec_pointer_scanner(self):
        pointer_window = PointerScanWindowForm(self)
        pointer_window.show()

    def exec_pointer_scan(self):
        selected_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not selected_row:
            return
        address = selected_row.text(ADDR_COL).strip("P->")
        pointer_window = PointerScanWindowForm(self)
        pointer_window.show()
        dialog = PointerScanSearchDialogForm(pointer_window, address)
        dialog.exec()

    def exec_track_watchpoint_widget(self, watchpoint_type):
        selected_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not selected_row:
            return
        address = selected_row.text(ADDR_COL).strip("P->")  # @todo Maybe rework address grabbing logic in the future
        address_data = selected_row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
        if isinstance(address_data, typedefs.PointerChainRequest):
            selection_dialog = TrackSelectorDialogForm(self)
            selection_dialog.exec()
            if not selection_dialog.selection:
                return
            if selection_dialog.selection == "pointer":
                address = address_data.get_base_address_as_str()
        value_type = selected_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        if typedefs.VALUE_INDEX.is_string(value_type.value_index):
            value_text = selected_row.text(VALUE_COL)
            encoding, option = typedefs.string_index_to_encoding_dict[value_type.value_index]
            byte_len = len(value_text.encode(encoding, option))
        elif value_type.value_index == typedefs.VALUE_INDEX.AOB:
            byte_len = value_type.length
        else:
            byte_len = typedefs.index_to_valuetype_dict[value_type.value_index][0]
        TrackWatchpointWidgetForm(self, address, byte_len, watchpoint_type)

    def browse_region_for_selected_row(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if row:
            self.memory_view_window.hex_dump_address(int(row.text(ADDR_COL).strip("P->"), 16))
            self.memory_view_window.show()
            self.memory_view_window.activateWindow()

    def disassemble_selected_row(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if row:
            if self.memory_view_window.disassemble_expression(
                row.text(ADDR_COL).strip("P->"), append_to_travel_history=True
            ):
                self.memory_view_window.show()
                self.memory_view_window.activateWindow()

    def change_freeze_type(self, freeze_type):
        for row in self.treeWidget_AddressTable.selectedItems():
            frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            frozen.freeze_type = freeze_type

            if freeze_type == typedefs.FREEZE_TYPE.DEFAULT:
                row.setText(FROZEN_COL, "")
                row.setForeground(FROZEN_COL, QBrush())
            elif freeze_type == typedefs.FREEZE_TYPE.INCREMENT:
                row.setText(FROZEN_COL, "▲")
                row.setForeground(FROZEN_COL, QBrush(QColor(0, 255, 0)))
            elif freeze_type == typedefs.FREEZE_TYPE.DECREMENT:
                row.setText(FROZEN_COL, "▼")
                row.setForeground(FROZEN_COL, QBrush(QColor(255, 0, 0)))

    def toggle_records(self, toggle_children=False):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if row:
            check_state = row.checkState(FROZEN_COL)
            new_state = Qt.CheckState.Checked if check_state == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setCheckState(FROZEN_COL, new_state)
                self.treeWidget_AddressTable_item_clicked(row, FROZEN_COL)
                if toggle_children:
                    for index in range(row.childCount()):
                        child = row.child(index)
                        child.setCheckState(FROZEN_COL, new_state)
                        self.treeWidget_AddressTable_item_clicked(child, FROZEN_COL)

    def cut_records(self):
        self.copy_records()
        self.delete_records()

    def copy_records(self):
        # Recursive copy
        items = self.treeWidget_AddressTable.selectedItems()

        def index_of(item):
            """Returns the index used to access the given QTreeWidgetItem
            as a list of ints."""
            result = []
            while True:
                parent = item.parent()
                if parent:
                    result.append(parent.indexOfChild(item))
                    item = parent
                else:
                    result.append(item.treeWidget().indexOfTopLevelItem(item))
                    return result[::-1]

        # First, order the items by their indices in the tree widget.
        # Store the indices for later usage.
        index_items = [(index_of(item), item) for item in items]
        index_items.sort(key=lambda x: x[0])  # sort by index

        # Now filter any selected items that is a descendant of another selected items.
        items = []
        last_index = [-1]  # any invalid list of indices are fine
        for index, item in index_items:
            if index[: len(last_index)] == last_index:
                continue  # this item is a descendant of the last item
            items.append(item)
            last_index = index

        app.clipboard().setText(repr([self.read_address_table_recursively(item) for item in items]))

    def insert_records(self, records, parent_row, insert_index):
        # parent_row should be a QTreeWidgetItem in treeWidget_AddressTable
        # records should be an iterable of valid output of read_address_table_recursively
        assert isinstance(parent_row, QTreeWidgetItem)

        rows = []
        for rec in records:
            row = QTreeWidgetItem()
            row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
            frozen = typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT)
            row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)

            # Deserialize the address_expr & value_type param
            if type(rec[1]) in [list, tuple]:
                address_expr = typedefs.PointerChainRequest(*rec[1])
            else:
                address_expr = rec[1]
            value_type = typedefs.ValueType(*rec[2])
            self.change_address_table_entries(row, rec[0], address_expr, value_type)
            self.insert_records(rec[-1], row, 0)
            rows.append(row)

        parent_row.insertChildren(insert_index, rows)
        parent_row.setExpanded(True)

    def paste_records(self, insert_inside=False):
        try:
            records = ast.literal_eval(app.clipboard().text())
        except (SyntaxError, ValueError):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return

        insert_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        root = self.treeWidget_AddressTable.invisibleRootItem()
        if not insert_row:  # this is common when the treeWidget_AddressTable is empty
            self.insert_records(records, root, self.treeWidget_AddressTable.topLevelItemCount())
        elif insert_inside:
            self.insert_records(records, insert_row, 0)
        else:
            parent = insert_row.parent() or root
            self.insert_records(records, parent, parent.indexOfChild(insert_row) + 1)
        self.update_address_table()

    def group_records(self):
        selected_items = self.treeWidget_AddressTable.selectedItems()
        if self.create_group():
            item_count = self.treeWidget_AddressTable.topLevelItemCount()
            last_item = self.treeWidget_AddressTable.topLevelItem(item_count - 1)
            for item in selected_items:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.treeWidget_AddressTable.indexOfTopLevelItem(item)
                    self.treeWidget_AddressTable.takeTopLevelItem(index)
                last_item.addChild(item)
            self.treeWidget_AddressTable.setCurrentItem(last_item)
            last_item.setExpanded(True)

    def create_group(self):
        dialog = InputDialogForm(self, [(tr.ENTER_DESCRIPTION, tr.GROUP)])
        if dialog.exec():
            desc = dialog.get_values()
            self.add_entry_to_addresstable(desc, "0x0")
            return True
        return False

    def delete_records(self):
        root = self.treeWidget_AddressTable.invisibleRootItem()
        for item in self.treeWidget_AddressTable.selectedItems():
            (item.parent() or root).removeChild(item)

    def treeWidget_AddressTable_key_press_event(self, event):
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete), self.delete_records),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
                    self.browse_region_for_selected_row,
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D), self.disassemble_selected_row),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R),
                    self.pushButton_RefreshAdressTable_clicked,
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space), self.toggle_records),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Space),
                    lambda: self.toggle_records(True),
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_X), self.cut_records),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C), self.copy_records),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V), self.paste_records),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_V), lambda: self.paste_records(True)),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_value,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.KeypadModifier, Qt.Key.Key_Enter),
                    self.treeWidget_AddressTable_edit_value,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_desc,
                ),
                (
                    QKeyCombination(
                        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return
                    ),
                    self.treeWidget_AddressTable_edit_address,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_type,
                ),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.treeWidget_AddressTable.keyPressEvent_original(event)

    def update_address_table(self):
        global exp_cache
        if debugcore.currentpid == -1 or self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        mem_handle = debugcore.memory_handle()
        basic_math_exp = re.compile(r"^[0-9a-fA-F][/*+\-0-9a-fA-FxX]+$")
        while True:
            row = it.value()
            if not row:
                break
            it += 1
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, typedefs.PointerChainRequest):
                expression = address_data.base_address
            else:
                expression = address_data
            parent = row.parent()
            if parent and expression.startswith(("+", "-")):
                expression = parent.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1) + expression
            if expression in exp_cache:
                address = exp_cache[expression]
            elif expression.startswith(("+", "-")):  # If parent has an empty address
                address = expression
            elif basic_math_exp.match(expression.replace(" ", "")):
                try:
                    address = hex(eval(expression))
                except:
                    address = debugcore.examine_expression(expression).address
                    exp_cache[expression] = address
            else:
                address = debugcore.examine_expression(expression).address
                exp_cache[expression] = address
            vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, typedefs.PointerChainRequest):
                # The original base could be a symbol so we have to save it
                # This little hack avoids the unnecessary examine_expression call
                # TODO: Consider implementing exp_cache inside libpince so we don't need this hack
                pointer_chain_req = address_data
                if address:
                    old_base = pointer_chain_req.base_address  # save the old base
                    pointer_chain_req.base_address = address
                    pointer_chain_result = debugcore.read_pointer_chain(pointer_chain_req)
                    if pointer_chain_result and pointer_chain_result.get_final_address():
                        address = pointer_chain_result.get_final_address_as_hex()
                    else:
                        address = None
                    address_data.base_address = old_base  # then set it back
                    if address:
                        row.setText(ADDR_COL, f"P->{address}")
                    else:
                        row.setText(ADDR_COL, "P->??")
                else:
                    row.setText(ADDR_COL, "P->??")
            else:
                row.setText(ADDR_COL, address or address_data)
            address = "" if not address else address
            row.setData(ADDR_COL, Qt.ItemDataRole.UserRole + 1, address)
            value = debugcore.read_memory(
                address, vt.value_index, vt.length, vt.zero_terminate, vt.value_repr, vt.endian, mem_handle=mem_handle
            )
            value = "" if value is None else str(value)
            row.setText(VALUE_COL, value)

    def scan_values(self):
        global threadpool
        if debugcore.currentpid == -1:
            return
        search_for = self.validate_search(self.lineEdit_Scan.text(), self.lineEdit_Scan2.text())
        self.QWidget_Toolbox.setEnabled(False)
        self.progressBar.setValue(0)
        self.progress_bar_timer = QTimer(timeout=self.update_progress_bar)
        self.progress_bar_timer.start(100)
        scan_thread = Worker(scanmem.send_command, search_for)
        scan_thread.signals.finished.connect(self.scan_callback)
        threadpool.start(scan_thread)

    def resize_address_table(self):
        self.treeWidget_AddressTable.resizeColumnToContents(FROZEN_COL)

    # gets the information from the dialog then adds it to addresstable
    def pushButton_AddAddressManually_clicked(self):
        manual_address_dialog = ManualAddressDialogForm(self)
        if manual_address_dialog.exec():
            desc, address_expr, vt = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(desc, address_expr, vt)
            self.update_address_table()

    def pushButton_RefreshAdressTable_clicked(self):
        global exp_cache
        exp_cache.clear()
        self.update_address_table()

    def pushButton_MemoryView_clicked(self):
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def pushButton_Wiki_clicked(self):
        utils.execute_command_as_user('python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def pushButton_About_clicked(self):
        about_widget = AboutWidgetForm(self)
        about_widget.show()
        about_widget.activateWindow()

    def pushButton_Settings_clicked(self):
        settings_dialog = SettingsDialogForm(self, self.set_default_settings)
        if settings_dialog.exec():
            self.apply_settings()

    def pushButton_Console_clicked(self):
        console_widget = ConsoleWidgetForm(self)
        console_widget.showMaximized()

    def checkBox_Hex_stateChanged(self, state):
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            # allows only things that are hex, can also start with 0x
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int_hex"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int_hex"))
        else:
            # sets it back to integers only
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int"))

    def pushButton_NewFirstScan_clicked(self):
        if debugcore.currentpid == -1:
            self.comboBox_ScanType_init()
            return
        if self.scan_mode == typedefs.SCAN_MODE.ONGOING:
            self.reset_scan()
        else:
            self.scan_mode = typedefs.SCAN_MODE.ONGOING
            self.pushButton_NewFirstScan.setText(tr.NEW_SCAN)
            self.comboBox_ValueType.setEnabled(False)
            self.pushButton_NextScan.setEnabled(True)
            search_scope = self.comboBox_ScanScope.currentData(Qt.ItemDataRole.UserRole)
            endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
            scanmem.send_command(f"option region_scan_level {search_scope}")
            scanmem.send_command(f"option endianness {endian}")
            scanmem.reset()
            self.comboBox_ScanScope.setEnabled(False)
            self.comboBox_Endianness.setEnabled(False)
            self.scan_values()
        self.comboBox_ScanType_init()

    def handle_line_edit_scan_key_press_event(self, event):
        valid_keys = [Qt.Key.Key_Return, Qt.Key.Key_Enter]
        if event.key() in valid_keys and Qt.KeyboardModifier.ControlModifier in event.modifiers():
            self.pushButton_NewFirstScan_clicked()
            return

        if event.key() in valid_keys:
            if self.scan_mode == typedefs.SCAN_MODE.ONGOING:
                self.pushButton_NextScan_clicked()
            else:
                self.pushButton_NewFirstScan_clicked()
            return

    def lineEdit_Scan_on_key_press_event(self, event):
        self.handle_line_edit_scan_key_press_event(event)
        self.lineEdit_Scan.keyPressEvent_original(event)

    def lineEdit_Scan2_on_key_press_event(self, event):
        self.handle_line_edit_scan_key_press_event(event)
        self.lineEdit_Scan2.keyPressEvent_original(event)

    def pushButton_UndoScan_clicked(self):
        global threadpool
        if debugcore.currentpid == -1:
            return
        undo_thread = Worker(scanmem.undo_scan)
        undo_thread.signals.finished.connect(self.scan_callback)
        threadpool.start(undo_thread)
        self.pushButton_UndoScan.setEnabled(False)  # we can undo once so set it to false and re-enable at next scan

    def comboBox_ScanType_current_index_changed(self):
        hidden_types = [
            typedefs.SCAN_TYPE.INCREASED,
            typedefs.SCAN_TYPE.DECREASED,
            typedefs.SCAN_TYPE.CHANGED,
            typedefs.SCAN_TYPE.UNCHANGED,
            typedefs.SCAN_TYPE.UNKNOWN,
        ]
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) in hidden_types:
            self.widget_Scan.setEnabled(False)
        else:
            self.widget_Scan.setEnabled(True)
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) == typedefs.SCAN_TYPE.BETWEEN:
            self.label_Between.setVisible(True)
            self.lineEdit_Scan2.setVisible(True)
        else:
            self.label_Between.setVisible(False)
            self.lineEdit_Scan2.setVisible(False)

    def comboBox_ScanType_init(self):
        scan_type_text = {
            typedefs.SCAN_TYPE.EXACT: tr.EXACT,
            typedefs.SCAN_TYPE.NOT: tr.NOT,
            typedefs.SCAN_TYPE.INCREASED: tr.INCREASED,
            typedefs.SCAN_TYPE.INCREASED_BY: tr.INCREASED_BY,
            typedefs.SCAN_TYPE.DECREASED: tr.DECREASED,
            typedefs.SCAN_TYPE.DECREASED_BY: tr.DECREASED_BY,
            typedefs.SCAN_TYPE.LESS: tr.LESS_THAN,
            typedefs.SCAN_TYPE.MORE: tr.MORE_THAN,
            typedefs.SCAN_TYPE.BETWEEN: tr.BETWEEN,
            typedefs.SCAN_TYPE.CHANGED: tr.CHANGED,
            typedefs.SCAN_TYPE.UNCHANGED: tr.UNCHANGED,
            typedefs.SCAN_TYPE.UNKNOWN: tr.UNKNOWN_VALUE,
        }
        current_type = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        value_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        self.comboBox_ScanType.clear()
        items = typedefs.SCAN_TYPE.get_list(self.scan_mode, value_type)
        old_index = 0
        for index, type_index in enumerate(items):
            if current_type == type_index:
                old_index = index
            self.comboBox_ScanType.addItem(scan_type_text[type_index], type_index)
        self.comboBox_ScanType.setCurrentIndex(old_index)

    def comboBox_ScanScope_init(self):
        scan_scope_text = [
            (typedefs.SCAN_SCOPE.BASIC, tr.BASIC),
            (typedefs.SCAN_SCOPE.NORMAL, tr.NORMAL),
            (typedefs.SCAN_SCOPE.FULL_RW, tr.RW),
            (typedefs.SCAN_SCOPE.FULL, tr.FULL),
        ]
        for scope, text in scan_scope_text:
            self.comboBox_ScanScope.addItem(text, scope)
        self.comboBox_ScanScope.setCurrentIndex(1)  # typedefs.SCAN_SCOPE.NORMAL

    def comboBox_ValueType_init(self):
        self.comboBox_ValueType.clear()
        for value_index, value_text in typedefs.scan_index_to_text_dict.items():
            self.comboBox_ValueType.addItem(value_text, value_index)
        self.comboBox_ValueType.setCurrentIndex(typedefs.SCAN_INDEX.INT32)
        self.comboBox_ValueType_current_index_changed()

    # :doc:
    # adds things like 0x when searching for etc, basically just makes the line valid for scanmem
    # this should cover most things, more things might be added later if need be
    def validate_search(self, search_for: str, search_for2: str):
        type_index = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        symbol_map = {
            typedefs.SCAN_TYPE.INCREASED: "+",
            typedefs.SCAN_TYPE.DECREASED: "-",
            typedefs.SCAN_TYPE.CHANGED: "!=",
            typedefs.SCAN_TYPE.UNCHANGED: "=",
            typedefs.SCAN_TYPE.UNKNOWN: "snapshot",
        }
        if type_index in symbol_map:
            return symbol_map[type_index]

        # none of these should be possible to be true at the same time
        scan_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        if scan_index >= typedefs.SCAN_INDEX.FLOAT_ANY and scan_index <= typedefs.SCAN_INDEX.FLOAT64:
            # Adjust to locale whatever the input
            if QLocale.system().decimalPoint() == ".":
                search_for = search_for.replace(",", ".")
                search_for2 = search_for2.replace(",", ".")
            else:
                search_for = search_for.replace(".", ",")
                search_for2 = search_for2.replace(".", ",")
        elif scan_index == typedefs.SCAN_INDEX.STRING:
            search_for = '" ' + search_for
        elif self.checkBox_Hex.isChecked():
            if not search_for.startswith(("0x", "-0x")):
                negative_str = "-" if search_for.startswith("-") else ""
                search_for = negative_str + "0x" + search_for.lstrip("-")
            if not search_for2.startswith(("0x", "-0x")):
                negative_str = "-" if search_for.startswith("-") else ""
                search_for2 = negative_str + "0x" + search_for2.lstrip("-")

        if type_index == typedefs.SCAN_TYPE.BETWEEN:
            return search_for + ".." + search_for2
        cmp_symbols = {
            typedefs.SCAN_TYPE.INCREASED_BY: "+",
            typedefs.SCAN_TYPE.DECREASED_BY: "-",
            typedefs.SCAN_TYPE.LESS: "<",
            typedefs.SCAN_TYPE.MORE: ">",
        }
        if type_index in cmp_symbols:
            return cmp_symbols[type_index] + " " + search_for

        if type_index == typedefs.SCAN_TYPE.NOT:
            search_for = "!= " + search_for
        return search_for

    def pushButton_NextScan_clicked(self):
        self.scan_values()
        self.pushButton_UndoScan.setEnabled(True)

    def scan_callback(self):
        self.progress_bar_timer.stop()
        self.progressBar.setValue(100)
        matches = scanmem.matches()
        self.update_match_count()
        self.tableWidget_valuesearchtable.setRowCount(0)
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = self._scan_to_length(current_type)
        mem_handle = debugcore.memory_handle()
        row = 0  # go back to using n when unknown issue gets fixed
        for n, address, offset, region_type, val, result_type in matches:
            address = "0x" + address
            result = result_type.split(" ")[0]
            if result == "unknown":  # Ignore unknown entries for now
                continue
            value_index = typedefs.scanmem_result_to_index_dict[result]
            if self.checkBox_Hex.isChecked():
                value_repr = typedefs.VALUE_REPR.HEX
            elif typedefs.VALUE_INDEX.is_integer(value_index) and result.endswith("s"):
                value_repr = typedefs.VALUE_REPR.SIGNED
            else:
                value_repr = typedefs.VALUE_REPR.UNSIGNED
            endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
            current_item = QTableWidgetItem(address)
            current_item.setData(Qt.ItemDataRole.UserRole, (value_index, value_repr, endian))
            value = str(debugcore.read_memory(address, value_index, length, True, value_repr, endian, mem_handle))
            self.tableWidget_valuesearchtable.insertRow(row)
            self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_ADDRESS_COL, current_item)
            self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_VALUE_COL, QTableWidgetItem(value))
            self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_PREVIOUS_COL, QTableWidgetItem(value))
            row += 1
            if row == 1000:
                break
        self.QWidget_Toolbox.setEnabled(True)

    def _scan_to_length(self, type_index):
        if type_index == typedefs.SCAN_INDEX.AOB:
            return self.lineEdit_Scan.text().count(" ") + 1
        if type_index == typedefs.SCAN_INDEX.STRING:
            return len(self.lineEdit_Scan.text())
        return 0

    def update_match_count(self):
        match_count = scanmem.get_match_count()
        if match_count > 1000:
            self.label_MatchCount.setText(tr.MATCH_COUNT_LIMITED.format(match_count, 1000))
        else:
            self.label_MatchCount.setText(tr.MATCH_COUNT.format(match_count))

    def tableWidget_valuesearchtable_cell_double_clicked(self, row, col):
        current_item = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL)
        value_index, value_repr, endian = current_item.data(Qt.ItemDataRole.UserRole)
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        vt = typedefs.ValueType(value_index, length, True, value_repr, endian)
        self.add_entry_to_addresstable(tr.NO_DESCRIPTION, current_item.text(), vt)
        self.update_address_table()

    def tableWidget_valuesearchtable_key_press_event(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Delete:
            # get selected rows
            selected_rows = self.tableWidget_valuesearchtable.selectedItems()
            if not selected_rows:
                return

            # get the row indexes
            rows = set()
            for item in selected_rows:
                rows.add(item.row())

            scanmem.send_command("delete {}".format(",".join([str(row) for row in rows])))

            # remove the rows from the table - removing in reverse sorted order to avoid index issues
            for row in sorted(rows, reverse=True):
                self.tableWidget_valuesearchtable.removeRow(row)
            self.update_match_count()

            return

        self.tableWidget_valuesearchtable.keyPressEvent_original(event)

    def comboBox_ValueType_current_index_changed(self):
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        scanmem_type = typedefs.scan_index_to_scanmem_dict[current_type]
        validator_str = scanmem_type  # used to get the correct validator

        # TODO this can probably be made to look nicer, though it doesn't really matter
        if "int" in validator_str:
            validator_str = "int"
            self.checkBox_Hex.setEnabled(True)
            # keep hex validator if hex is checked
            if self.checkBox_Hex.isChecked():
                validator_str = "int_hex"
        else:
            self.checkBox_Hex.setChecked(False)
            self.checkBox_Hex.setEnabled(False)
        if "float" in validator_str or validator_str == "number":
            validator_str = "float"

        self.comboBox_ScanType_init()
        self.lineEdit_Scan.setValidator(guiutils.validator_map[validator_str])
        self.lineEdit_Scan2.setValidator(guiutils.validator_map[validator_str])
        scanmem.send_command("option scan_data_type {}".format(scanmem_type))
        # according to scanmem instructions you should always do `reset` after changing type
        scanmem.reset()

    def pushButton_AttachProcess_clicked(self):
        self.processwindow = ProcessForm(self)
        self.processwindow.show()

    def pushButton_Open_clicked(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, tr.OPEN_PCT_FILE, None, tr.FILE_TYPES_PCT)
        if not file_paths:
            return
        self.clear_address_table()
        for file_path in file_paths:
            content = utils.load_file(file_path)
            if content is None:
                QMessageBox.information(self, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
                break
            self.insert_records(
                content,
                self.treeWidget_AddressTable.invisibleRootItem(),
                self.treeWidget_AddressTable.topLevelItemCount(),
            )

    def pushButton_Save_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SAVE_PCT_FILE, None, tr.FILE_TYPES_PCT)
        if not file_path:
            return
        content = [
            self.read_address_table_recursively(self.treeWidget_AddressTable.topLevelItem(i))
            for i in range(self.treeWidget_AddressTable.topLevelItemCount())
        ]
        file_path = utils.append_file_extension(file_path, "pct")
        if not utils.save_file(content, file_path):
            QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    # Returns: a bool value indicates whether the operation succeeded.
    def attach_to_pid(self, pid: int):
        attach_result = debugcore.attach(pid, settings.gdb_path)
        if attach_result == typedefs.ATTACH_RESULT.SUCCESSFUL:
            self.apply_after_init()
            scanmem.pid(pid)
            ptrscan.set_process(pid)
            self.on_new_process()
            process_signals.attach.emit()

            # TODO: This makes PINCE call on_process_stop twice when attaching
            # TODO: Signal design might have to change to something like mutexes eventually
            self.memory_view_window.on_process_stop()
            debugcore.continue_inferior()
            return True
        else:
            messages = {
                typedefs.ATTACH_RESULT.ATTACH_SELF: tr.SMARTASS,  # easter egg
                typedefs.ATTACH_RESULT.PROCESS_NOT_VALID: tr.PROCESS_NOT_VALID,
                typedefs.ATTACH_RESULT.ALREADY_DEBUGGING: tr.ALREADY_DEBUGGING,
                typedefs.ATTACH_RESULT.ALREADY_TRACED: tr.ALREADY_TRACED.format(utils.is_traced(pid)),
                typedefs.ATTACH_RESULT.PERM_DENIED: tr.PERM_DENIED,
            }
            QMessageBox.information(app.focusWidget(), tr.ERROR, messages[attach_result])
            return False

    # Returns: a bool value indicates whether the operation succeeded.
    def create_new_process(self, file_path, args, ld_preload_path):
        if debugcore.create_process(file_path, args, ld_preload_path):
            self.apply_after_init()
            self.on_new_process()
            return True
        else:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.CREATE_PROCESS_ERROR)
            self.on_inferior_exit()
            return False

    # Changes appearance whenever a new process is created or attached
    def on_new_process(self):
        name = utils.get_process_name(debugcore.currentpid)
        self.label_SelectedProcess.setText(str(debugcore.currentpid) + " - " + name)

        # enable scan GUI
        self.lineEdit_Scan.setPlaceholderText(tr.SCAN_FOR)
        self.QWidget_Toolbox.setEnabled(True)
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.pushButton_AddAddressManually.setEnabled(True)
        self.pushButton_MemoryView.setEnabled(True)

        # stop flashing attach button, timer will stop automatically on false value
        self.flashAttachButton = False

    def clear_address_table(self):
        if self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        confirm_dialog = InputDialogForm(self, [(tr.CLEAR_TABLE,)])
        if confirm_dialog.exec():
            self.treeWidget_AddressTable.clear()

    def copy_to_address_table(self):
        i = -1
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        for row in self.tableWidget_valuesearchtable.selectedItems():
            i = i + 1
            if i % 3 == 0:
                value_index, value_repr, endian = row.data(Qt.ItemDataRole.UserRole)
                vt = typedefs.ValueType(value_index, length, True, value_repr, endian)
                self.add_entry_to_addresstable(tr.NO_DESCRIPTION, row.text(), vt)
        self.update_address_table()

    def reset_scan(self):
        self.scan_mode = typedefs.SCAN_MODE.NEW
        self.pushButton_NewFirstScan.setText(tr.FIRST_SCAN)
        scanmem.reset()
        self.tableWidget_valuesearchtable.setRowCount(0)
        self.comboBox_ValueType.setEnabled(True)
        self.comboBox_ScanScope.setEnabled(True)
        self.comboBox_Endianness.setEnabled(True)
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.progressBar.setValue(0)
        self.label_MatchCount.setText(tr.MATCH_COUNT.format(0))

    def on_inferior_exit(self):
        self.pushButton_MemoryView.setEnabled(False)
        self.pushButton_AddAddressManually.setEnabled(False)
        self.QWidget_Toolbox.setEnabled(False)
        self.lineEdit_Scan.setText("")
        self.reset_scan()
        self.on_status_running()
        self.flashAttachButton = True
        self.flashAttachButtonTimer.start(100)
        self.label_SelectedProcess.setText(tr.NO_PROCESS_SELECTED)
        self.memory_view_window.setWindowTitle(tr.NO_PROCESS_SELECTED)
        gdb_path = settings.gdb_path
        if os.environ.get("APPDIR"):
            gdb_path = utils.get_default_gdb_path()
        debugcore.init_gdb(gdb_path)
        self.apply_after_init()
        process_signals.exit.emit()

    def on_status_detached(self):
        self.label_SelectedProcess.setStyleSheet("color: blue")
        self.label_InferiorStatus.setText(tr.STATUS_DETACHED)
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: blue")

    def on_status_stopped(self):
        self.label_SelectedProcess.setStyleSheet("color: red")
        self.label_InferiorStatus.setText(tr.STATUS_STOPPED)
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: red")

    def on_status_running(self):
        self.label_SelectedProcess.setStyleSheet("")
        self.label_InferiorStatus.setVisible(False)

    # closes all windows on exit
    def closeEvent(self, event):
        debugcore.detach()
        app.closeAllWindows()

    # Call update_address_table manually after this
    def add_entry_to_addresstable(self, description, address_expr, value_type=None):
        current_row = QTreeWidgetItem()
        current_row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        frozen = typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT)
        current_row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
        value_type = typedefs.ValueType() if not value_type else value_type
        self.treeWidget_AddressTable.addTopLevelItem(current_row)
        self.change_address_table_entries(current_row, description, address_expr, value_type)
        self.show()  # In case of getting called from elsewhere
        self.activateWindow()

    def treeWidget_AddressTable_item_double_clicked(self, row, column):
        action_for_column = {
            VALUE_COL: self.treeWidget_AddressTable_edit_value,
            DESC_COL: self.treeWidget_AddressTable_edit_desc,
            ADDR_COL: self.treeWidget_AddressTable_edit_address,
            TYPE_COL: self.treeWidget_AddressTable_edit_type,
        }
        action_for_column = collections.defaultdict(lambda *args: lambda: None, action_for_column)
        action_for_column[column]()

    # ----------------------------------------------------
    # QTimer loops

    def update_progress_bar(self):
        value = int(round(scanmem.get_scan_progress() * 100))
        self.progressBar.setValue(value)

    # Loop restarts itself to wait for function execution, same for the functions below
    def address_table_loop(self):
        if self.update_table and not exiting:
            try:
                self.update_address_table()
            except:
                traceback.print_exc()
        self.address_table_timer.start(self.table_update_interval)

    def search_table_loop(self):
        if not exiting:
            try:
                self.update_search_table()
            except:
                traceback.print_exc()
        self.search_table_timer.start(500)

    def freeze_loop(self):
        if not exiting:
            try:
                self.freeze()
            except:
                traceback.print_exc()
        self.freeze_timer.start(self.freeze_interval)

    # ----------------------------------------------------

    def update_search_table(self):
        if debugcore.currentpid == -1:
            return
        row_count = self.tableWidget_valuesearchtable.rowCount()
        if row_count > 0:
            length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
            mem_handle = debugcore.memory_handle()
            for row_index in range(row_count):
                address_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_ADDRESS_COL)
                previous_text = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_PREVIOUS_COL).text()
                value_index, value_repr, endian = address_item.data(Qt.ItemDataRole.UserRole)
                address = address_item.text()
                new_value = str(
                    debugcore.read_memory(
                        address, value_index, length, value_repr=value_repr, endian=endian, mem_handle=mem_handle
                    )
                )
                value_item = QTableWidgetItem(new_value)
                if new_value != previous_text:
                    value_item.setForeground(QBrush(QColor(255, 0, 0)))
                self.tableWidget_valuesearchtable.setItem(row_index, SEARCH_TABLE_VALUE_COL, value_item)

    def freeze(self):
        if debugcore.currentpid == -1:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        while it.value():
            row = it.value()
            if row.checkState(FROZEN_COL) == Qt.CheckState.Checked:
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                address = row.text(ADDR_COL).strip("P->")
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                value = frozen.value
                freeze_type = frozen.freeze_type
                if typedefs.VALUE_INDEX.is_number(vt.value_index):
                    new_value = debugcore.read_memory(address, vt.value_index, endian=vt.endian)
                    if (
                        freeze_type == typedefs.FREEZE_TYPE.INCREMENT
                        and new_value > value
                        or freeze_type == typedefs.FREEZE_TYPE.DECREMENT
                        and new_value < value
                    ):
                        frozen.value = new_value
                        debugcore.write_memory(address, vt.value_index, new_value, endian=vt.endian)
                        continue
                debugcore.write_memory(address, vt.value_index, value, vt.zero_terminate, vt.endian)
            it += 1

    def treeWidget_AddressTable_item_clicked(self, row: QTreeWidgetItem, column: int):
        if column == FROZEN_COL:
            frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            is_checked = row.checkState(FROZEN_COL) == Qt.CheckState.Checked
            is_frozen = frozen.enabled

            frozen_state_toggled = is_checked and not is_frozen or not is_checked and is_frozen
            # this helps determine whether the user clicked checkbox or the text
            # if the user clicked the text, change the freeze type

            if not frozen_state_toggled and is_checked:
                # user clicked the text, iterate through the freeze type
                if frozen.freeze_type == typedefs.FREEZE_TYPE.DECREMENT:
                    # decrement is the last freeze type
                    self.change_freeze_type(typedefs.FREEZE_TYPE.DEFAULT)
                else:
                    self.change_freeze_type(frozen.freeze_type + 1)

            if frozen_state_toggled:
                if is_checked:
                    frozen.enabled = True
                    # reapply the freeze type, to reflect the current freeze type in the UI
                    # otherwise the UI will show DEFAULT freeze type after enabling instead of the actual type
                    self.change_freeze_type(frozen.freeze_type)
                    vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                    frozen.value = utils.parse_string(row.text(VALUE_COL), vt.value_index)
                else:
                    frozen.enabled = False  # it has just been toggled off
                    self.change_freeze_type(typedefs.FREEZE_TYPE.DEFAULT)

    def treeWidget_AddressTable_change_repr(self, new_repr):
        value_type = guiutils.get_current_item(self.treeWidget_AddressTable).data(TYPE_COL, Qt.ItemDataRole.UserRole)
        value_type.value_repr = new_repr
        for row in self.treeWidget_AddressTable.selectedItems():
            row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, value_type)
            row.setText(TYPE_COL, value_type.text())
        self.update_address_table()

    def treeWidget_AddressTable_edit_value(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        value = row.text(VALUE_COL)
        value_index = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).value_index
        dialog = InputDialogForm(self, [(tr.ENTER_VALUE, value)], 0, value_index)
        if dialog.exec():
            new_value = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                address = row.text(ADDR_COL).strip("P->")
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                parsed_value = utils.parse_string(new_value, vt.value_index)
                if typedefs.VALUE_INDEX.has_length(vt.value_index) and parsed_value != None:
                    vt.length = len(parsed_value)
                    row.setText(TYPE_COL, vt.text())
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen.value = parsed_value
                debugcore.write_memory(address, vt.value_index, parsed_value, vt.zero_terminate, vt.endian)
            self.update_address_table()

    def treeWidget_AddressTable_edit_desc(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        description = row.text(DESC_COL)
        dialog = InputDialogForm(self, [(tr.ENTER_DESCRIPTION, description)])
        if dialog.exec():
            description_text = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setText(DESC_COL, description_text)

    def treeWidget_AddressTable_edit_address(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        desc, address_expr, vt = self.read_address_table_entries(row)
        manual_address_dialog = ManualAddressDialogForm(self, desc, address_expr, vt)
        manual_address_dialog.setWindowTitle(tr.EDIT_ADDRESS)
        if manual_address_dialog.exec():
            desc, address_expr, vt = manual_address_dialog.get_values()
            self.change_address_table_entries(row, desc, address_expr, vt)
            self.update_address_table()

    def treeWidget_AddressTable_edit_type(self):
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        dialog = EditTypeDialogForm(self, vt)
        if dialog.exec():
            vt = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, vt)
                row.setText(TYPE_COL, vt.text())
            self.update_address_table()

    # Changes the column values of the given row
    def change_address_table_entries(self, row, description=tr.NO_DESCRIPTION, address_expr="", vt=None):
        assert isinstance(row, QTreeWidgetItem)
        row.setText(DESC_COL, description)
        row.setData(ADDR_COL, Qt.ItemDataRole.UserRole, address_expr)
        row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, vt)
        row.setText(TYPE_COL, vt.text())

    # Returns the column values of the given row
    def read_address_table_entries(self, row, serialize=False):
        description = row.text(DESC_COL)
        if serialize:
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, typedefs.PointerChainRequest):
                address_expr = address_data.serialize()
            else:
                address_expr = address_data
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).serialize()
        else:
            address_expr = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        return description, address_expr, value_type

    # Returns the values inside the given row and all of its descendants.
    # All values except the last are the same as read_address_table_entries output.
    # Last value is an iterable of information about its direct children.
    def read_address_table_recursively(self, row):
        return self.read_address_table_entries(row, True) + (
            [self.read_address_table_recursively(row.child(i)) for i in range(row.childCount())],
        )

    # Flashing Attach Button when the process is not attached
    def flash_attach_button(self):
        if not self.flashAttachButton:
            self.flashAttachButtonTimer.stop()
            self.pushButton_AttachProcess.setStyleSheet("")
            return

        case = self.flashAttachButton_gradiantState % 32

        if case < 16:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str(case / 16) + ");}"
        else:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str((32 - case) / 16) + ");}"

        self.pushButton_AttachProcess.setStyleSheet(borderstring)
        self.flashAttachButton_gradiantState += 1
        if self.flashAttachButton_gradiantState > 768:  # 32*24
            self.flashAttachButton_gradiantState = 0


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.refresh_process_table(self.tableWidget_ProcessTable, utils.get_process_list())
        self.pushButton_Close.clicked.connect(self.close)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_clicked)
        self.pushButton_CreateProcess.clicked.connect(self.pushButton_CreateProcess_clicked)
        self.lineEdit_SearchProcess.textChanged.connect(self.generate_new_list)
        self.tableWidget_ProcessTable.itemDoubleClicked.connect(self.pushButton_Open_clicked)
        guiutils.center_to_parent(self)

    # refreshes process list
    def generate_new_list(self):
        text = self.lineEdit_SearchProcess.text()
        processlist = utils.search_processes(text)
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.pushButton_Open_clicked()
        elif event.key() == Qt.Key.Key_F1:
            self.pushButton_CreateProcess_clicked()
        else:
            return super().keyPressEvent(event)

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget, processlist):
        tablewidget.setRowCount(0)
        for pid, user, name in processlist:
            current_row = tablewidget.rowCount()
            tablewidget.insertRow(current_row)
            tablewidget.setItem(current_row, 0, QTableWidgetItem(pid))
            tablewidget.setItem(current_row, 1, QTableWidgetItem(user))
            tablewidget.setItem(current_row, 2, QTableWidgetItem(name))

    # gets the pid out of the selection to attach
    def pushButton_Open_clicked(self):
        index = self.tableWidget_ProcessTable.currentIndex()
        row_count = self.tableWidget_ProcessTable.rowCount()
        if index.row() == -1 and row_count == 1:
            # autoselect first row if there is only one row
            self.tableWidget_ProcessTable.setCurrentCell(0, 0)

        current_item = self.tableWidget_ProcessTable.item(self.tableWidget_ProcessTable.currentIndex().row(), 0)
        if current_item is None:
            QMessageBox.information(self, tr.ERROR, tr.SELECT_PROCESS)
        else:
            pid = int(current_item.text())
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            if self.parent().attach_to_pid(pid):
                self.close()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def pushButton_CreateProcess_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_BINARY)
        if file_path:
            items = [(tr.ENTER_OPTIONAL_ARGS, ""), (tr.LD_PRELOAD_OPTIONAL, "")]
            arg_dialog = InputDialogForm(self, items)
            if arg_dialog.exec():
                args, ld_preload_path = arg_dialog.get_values()
            else:
                return
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            if self.parent().create_new_process(file_path, args, ld_preload_path):
                self.close()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent, description=tr.NO_DESCRIPTION, address="0x", value_type=None):
        super().__init__(parent)
        self.setupUi(self)
        self.lineEdit_PtrStartAddress.setFixedWidth(180)
        self.lineEdit_Address.setFixedWidth(180)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(QHexValidator(99, self))
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        self.lineEdit_Description.setText(description)
        self.lineEdit_Description.setFixedWidth(180)
        self.offsetsList: list[PointerChainOffset] = []
        if not isinstance(address, typedefs.PointerChainRequest):
            self.lineEdit_Address.setText(address)
            self.widget_Pointer.hide()
        else:
            self.checkBox_IsPointer.setChecked(True)
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(address.get_base_address_as_str())
            self.create_offsets_list(address)
            self.widget_Pointer.show()
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentIndex() == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.comboBox_Endianness.currentIndexChanged.connect(self.update_value)
        self.lineEdit_Length.textChanged.connect(self.update_value)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        self.checkBox_Signed.stateChanged.connect(self.repr_changed)
        self.checkBox_ZeroTerminate.stateChanged.connect(self.update_value)
        self.checkBox_IsPointer.stateChanged.connect(self.checkBox_IsPointer_state_changed)
        self.lineEdit_PtrStartAddress.textChanged.connect(self.update_value)
        self.lineEdit_Address.textChanged.connect(self.update_value)
        self.pushButton_AddOffset.clicked.connect(lambda: self.addOffsetLayout(True))
        self.pushButton_RemoveOffset.clicked.connect(self.removeOffsetLayout)
        self.label_Value.contextMenuEvent = self.label_Value_context_menu_event
        self.update_value()
        guiutils.center_to_parent(self)

    def label_Value_context_menu_event(self, event):
        menu = QMenu()
        refresh = menu.addAction(tr.REFRESH)
        font_size = self.label_Value.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {refresh: self.update_value}
        try:
            actions[action]()
        except KeyError:
            pass

    def addOffsetLayout(self, should_update=True):
        offsetFrame = PointerChainOffset(len(self.offsetsList), self.widget_Pointer)
        self.offsetsList.append(offsetFrame)
        self.verticalLayout_Pointers.insertWidget(0, self.offsetsList[-1])
        offsetFrame.offset_changed_signal.connect(self.update_value)
        if should_update:
            self.update_value()

    def removeOffsetLayout(self):
        if len(self.offsetsList) == 1:
            return
        frame = self.offsetsList[-1]
        frame.deleteLater()
        self.verticalLayout_Pointers.removeWidget(frame)
        del self.offsetsList[-1]
        self.update_value()

    def update_deref_labels(self, pointer_chain_result: typedefs.PointerChainResult):
        if pointer_chain_result != None:
            base_deref = utils.upper_hex(hex(pointer_chain_result.pointer_chain[0]))
            self.label_BaseAddressDeref.setText(f" → {base_deref}")
            for index, offsetFrame in enumerate(self.offsetsList):
                previousDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index])
                currentDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index + 1])
                offsetText = utils.upper_hex(offsetFrame.offsetText.text())
                operationalSign = "" if offsetText.startswith("-") else "+"
                calculation = f"{previousDerefText}{operationalSign}{offsetText}"
                if index != len(self.offsetsList) - 1:
                    offsetFrame.update_deref_label(f" [{calculation}] → {currentDerefText}")
                else:
                    offsetFrame.update_deref_label(f" {calculation} = {currentDerefText}")
        else:
            self.label_BaseAddressDeref.setText(" → <font color=red>??</font>")
            for offsetFrame in self.offsetsList:
                offsetFrame.update_deref_label(" → <font color=red>??</font>")

    def caps_hex_or_error_indicator(self, address: int):
        if address == 0:
            return "<font color=red>??</font>"
        return utils.upper_hex(hex(address))

    def update_value(self):
        if self.checkBox_IsPointer.isChecked():
            hex_converted_expr = debugcore.convert_to_hex(self.lineEdit_PtrStartAddress.text())
            pointer_chain_req = typedefs.PointerChainRequest(hex_converted_expr, self.get_offsets_int_list())
            pointer_chain_result = debugcore.read_pointer_chain(pointer_chain_req)
            address = None
            if pointer_chain_result != None:
                address_text = pointer_chain_result.get_final_address_as_hex()
                address = pointer_chain_result.get_final_address()
            else:
                address_text = "??"
            self.lineEdit_Address.setText(address_text)
            self.update_deref_labels(pointer_chain_result)
        else:
            hex_converted_expr = debugcore.convert_to_hex(self.lineEdit_Address.text())
            address = debugcore.examine_expression(hex_converted_expr).address
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        address_type = self.comboBox_ValueType.currentIndex()
        length = self.lineEdit_Length.text()
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        value = debugcore.read_memory(address, address_type, length, zero_terminate, value_repr, endian)
        self.label_Value.setText("<font color=red>??</font>" if value is None else str(value))
        old_width = self.width()
        app.processEvents()
        self.adjustSize()
        self.resize(old_width, self.minimumHeight())

    def comboBox_ValueType_current_index_changed(self):
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentIndex() == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        self.update_value()

    def repr_changed(self):
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)
        self.update_value()

    def checkBox_IsPointer_state_changed(self):
        if self.checkBox_IsPointer.isChecked():
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(self.lineEdit_Address.text())
            if len(self.offsetsList) == 0:
                self.addOffsetLayout(False)
            self.widget_Pointer.show()
        else:
            self.lineEdit_Address.setText(self.lineEdit_PtrStartAddress.text())
            self.lineEdit_PtrStartAddress.setText("")
            self.lineEdit_Address.setReadOnly(False)
            self.widget_Pointer.hide()
        self.update_value()

    def reject(self):
        super().reject()

    def accept(self):
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self):
        description = self.lineEdit_Description.text()
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
        except:
            length = 0
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        value_index = self.comboBox_ValueType.currentIndex()
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        vt = typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)
        if self.checkBox_IsPointer.isChecked():
            base_expression = debugcore.convert_to_hex(self.lineEdit_PtrStartAddress.text())
            address = typedefs.PointerChainRequest(base_expression, self.get_offsets_int_list())
        else:
            address = debugcore.convert_to_hex(self.lineEdit_Address.text())
        return description, address, vt

    def get_offsets_int_list(self):
        offsetsIntList = []
        for frame in self.offsetsList:
            offsetText = frame.layout().itemAt(1).widget().text()
            try:
                offsetValue = int(offsetText, 16)
            except ValueError:
                offsetValue = 0
            offsetsIntList.append(offsetValue)
        return offsetsIntList

    def create_offsets_list(self, pointer_chain_req: typedefs.PointerChainRequest):
        if not isinstance(pointer_chain_req, typedefs.PointerChainRequest):
            raise TypeError("Passed non-PointerChainRequest type to create_offsets_list!")

        for offset in pointer_chain_req.offsets_list:
            self.addOffsetLayout(False)
            frame = self.offsetsList[-1]
            frame.layout().itemAt(1).widget().setText(hex(offset))

    def on_offset_arrow_clicked(self, offsetTextWidget, operator_func):
        offsetText = offsetTextWidget.text()
        try:
            offsetValue = int(offsetText, 16)
        except ValueError:
            offsetValue = 0
        sizeVal = typedefs.index_to_valuetype_dict[self.comboBox_ValueType.currentIndex()][0]
        offsetValue = operator_func(offsetValue, sizeVal)
        offsetTextWidget.setText(hex(offsetValue))

    def get_type_size(self):
        return typedefs.index_to_valuetype_dict[self.comboBox_ValueType.currentIndex()][0]


class EditTypeDialogForm(QDialog, EditTypeDialog):
    def __init__(self, parent, value_type=None):
        super().__init__(parent)
        self.setupUi(self)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(QHexValidator(99, self))
        self.lineEdit_Length.setFixedWidth(40)
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentIndex() == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        app.processEvents()
        self.adjustSize()
        guiutils.center_to_parent(self)

    def comboBox_ValueType_current_index_changed(self):
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentIndex() == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        app.processEvents()
        self.adjustSize()

    def repr_changed(self):
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)

    def reject(self):
        super().reject()

    def accept(self):
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self):
        value_index = self.comboBox_ValueType.currentIndex()
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
        except:
            length = 0
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        return typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)


class TrackSelectorDialogForm(QDialog, TrackSelectorDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.selection = None
        self.pushButton_Pointer.clicked.connect(lambda: self.change_selection("pointer"))
        self.pushButton_Pointed.clicked.connect(lambda: self.change_selection("pointed"))
        guiutils.center_to_parent(self)

    def change_selection(self, selection):
        self.selection = selection
        self.close()


class LoadingDialogForm(QDialog, LoadingDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags())
        self.keyPressEvent = QEvent.ignore

        # Make use of this background_thread when you spawn a LoadingDialogForm
        # Warning: overrided_func() can only return one value, so if your overridden function returns more than one
        # value, refactor your overriden function to return only one object(convert tuple to list etc.)
        # Check refresh_table method of FunctionsInfoWidgetForm for exemplary usage
        self.background_thread = self.BackgroundThread()
        self.background_thread.output_ready.connect(self.accept)
        self.pushButton_Cancel.clicked.connect(self.close)
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/LoadingDialog/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(25, 25))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        guiutils.center_to_parent(self)

    # TODO: This function only cancels the last command sent, redesign this if it's needed to cancel non-gdb functions
    def cancel_thread(self):
        debugcore.cancel_last_command()
        self.background_thread.wait()

    def exec(self):
        self.background_thread.start()
        super().exec()

    def closeEvent(self, event: QCloseEvent):
        self.cancel_thread()
        super().closeEvent(event)

    class BackgroundThread(QThread):
        output_ready = pyqtSignal(object)

        def __init__(self):
            super().__init__()

        # Unhandled exceptions in this thread freezes PINCE
        def run(self):
            try:
                output = self.overrided_func()
            except:
                traceback.print_exc()
                output = None
            self.output_ready.emit(output)

        def overrided_func(self):
            print("Override this function")
            return 0


class InputDialogForm(QDialog, InputDialog):
    # Format of item_list->[(label_str, item_data, label_alignment), ...]
    # If label_str is None, no label will be created
    # If item_data is None, no input field will be created. If it's str, a QLineEdit containing the str will be created
    # If it's a list, a QComboBox with the items in the list will be created, last item of the list should be an integer
    # that points the current index of the QComboBox, for instance: ["0", "1", 1] will create a QCombobox with the items
    # "0" and "1" then will set current index to 1 (which is the item "1")
    # label_alignment is optional
    def __init__(
        self,
        parent,
        item_list=None,
        parsed_index=-1,
        value_index=typedefs.VALUE_INDEX.INT32,
        buttons=(QDialogButtonBox.StandardButton.Ok, QDialogButtonBox.StandardButton.Cancel),
    ):
        super().__init__(parent)
        self.setupUi(self)
        for button in buttons:
            self.buttonBox.addButton(button)
        self.object_list = []
        for item in item_list:
            if item[0] is not None:
                label = QLabel(self)
                try:
                    label.setAlignment(item[2])
                except IndexError:
                    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setText(item[0])
                label.setTextInteractionFlags(
                    Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse
                )
                self.verticalLayout.addWidget(label)
            try:
                item_data = item[1]
            except IndexError:
                pass
            else:
                if item_data is not None:
                    if type(item_data) is str:
                        lineedit = QLineEdit(self)
                        lineedit.setText(item_data)
                        self.verticalLayout.addWidget(lineedit)
                        self.object_list.append(lineedit)
                    elif type(item_data) is list:
                        combobox = QComboBox(self)
                        current_index = item_data.pop()
                        combobox.addItems(item_data)
                        combobox.setCurrentIndex(current_index)
                        self.verticalLayout.addWidget(combobox)
                        self.object_list.append(combobox)
        self.adjustSize()
        self.verticalLayout.removeWidget(self.buttonBox)  # Pushing buttonBox to the end
        self.verticalLayout.addWidget(self.buttonBox)
        for widget in guiutils.get_layout_widgets(self.verticalLayout):
            if isinstance(widget, QLabel):
                continue
            widget.setFocus()  # Focus to the first input field
            break
        self.parsed_index = parsed_index
        self.value_index = value_index
        guiutils.center_to_parent(self)

    def get_text(self, item):
        try:
            string = item.text()
        except AttributeError:
            string = item.currentText()
        return string

    def get_values(self):
        return (
            self.get_text(self.object_list[0])
            if len(self.object_list) == 1
            else [self.get_text(item) for item in self.object_list]
        )

    def accept(self):
        if self.parsed_index != -1:
            item = self.object_list[self.parsed_index]
            if utils.parse_string(self.get_text(item), self.value_index) is None:
                QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                return
        super().accept()


class TextEditDialogForm(QDialog, TextEditDialog):
    def __init__(self, parent, text=""):
        super().__init__(parent)
        self.setupUi(self)
        self.textEdit.setPlainText(str(text))
        self.accept_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut.activated.connect(self.accept)
        guiutils.center_to_parent(self)

    def get_values(self):
        return self.textEdit.toPlainText()

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key.Key_Enter:
            pass
        else:
            super().keyPressEvent(QKeyEvent)


class SettingsDialogForm(QDialog, SettingsDialog):
    def __init__(self, parent, set_default_settings_func):
        super().__init__(parent)
        self.setupUi(self)
        self.settings = QSettings()
        self.set_default_settings = set_default_settings_func
        self.hotkey_to_value = {}  # Dict[str:str]-->Dict[Hotkey.name:settings_value]
        self.handle_signals_data = ""
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_GDBPath.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        locale_model = QStandardItemModel()
        for loc, name in language_list.items():
            item = QStandardItem()
            item.setData(name, Qt.ItemDataRole.DisplayRole)
            item.setData(loc, Qt.ItemDataRole.UserRole)
            locale_model.appendRow(item)
        self.comboBox_Language.setModel(locale_model)
        self.comboBox_InterruptSignal.addItem("SIGINT")
        self.comboBox_InterruptSignal.addItems([f"SIG{x}" for x in range(signal.SIGRTMIN, signal.SIGRTMAX + 1)])
        self.comboBox_InterruptSignal.setStyleSheet("combobox-popup: 0;")  # maxVisibleItems doesn't work otherwise
        self.comboBox_Theme.addItems(theme_list)
        logo_directory = utils.get_logo_directory()
        logo_list = utils.search_files(logo_directory, r"\.(png|jpg|jpeg|svg)$")
        for logo in logo_list:
            self.comboBox_Logo.addItem(QIcon(os.path.join(logo_directory, logo)), logo)
        for hotkey in hotkeys.get_hotkeys():
            self.listWidget_Functions.addItem(hotkey.desc)
        self.config_gui()

        self.listWidget_Options.currentRowChanged.connect(self.change_display)
        self.listWidget_Functions.currentRowChanged.connect(self.listWidget_Functions_current_row_changed)
        self.pushButton_ClearHotkey.clicked.connect(self.pushButton_ClearHotkey_clicked)
        self.pushButton_ResetSettings.clicked.connect(self.pushButton_ResetSettings_clicked)
        self.pushButton_GDBPath.clicked.connect(self.pushButton_GDBPath_clicked)
        self.checkBox_AutoUpdateAddressTable.stateChanged.connect(self.checkBox_AutoUpdateAddressTable_state_changed)
        self.checkBox_AutoAttachRegex.stateChanged.connect(self.checkBox_AutoAttachRegex_state_changed)
        self.comboBox_Logo.currentIndexChanged.connect(self.comboBox_Logo_current_index_changed)
        self.comboBox_Theme.currentIndexChanged.connect(self.comboBox_Theme_current_index_changed)
        self.pushButton_HandleSignals.clicked.connect(self.pushButton_HandleSignals_clicked)
        self.lineEdit_Hotkey.keyPressEvent = self.lineEdit_Hotkey_key_pressed_event
        guiutils.center_to_parent(self)

    def accept(self):
        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.settings.setValue("General/address_table_update_interval", self.spinBox_UpdateInterval.value())
        self.settings.setValue("General/freeze_interval", self.spinBox_FreezeInterval.value())
        output_mode = [
            self.checkBox_OutputModeAsync.isChecked(),
            self.checkBox_OutputModeCommand.isChecked(),
            self.checkBox_OutputModeCommandInfo.isChecked(),
        ]
        self.settings.setValue("General/gdb_output_mode", json.dumps(output_mode))
        if self.checkBox_AutoAttachRegex.isChecked():
            try:
                re.compile(self.lineEdit_AutoAttach.text())
            except:
                QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_REGEX.format(self.lineEdit_AutoAttach.text()))
                return
        self.settings.setValue("General/auto_attach", self.lineEdit_AutoAttach.text())
        self.settings.setValue("General/auto_attach_regex", self.checkBox_AutoAttachRegex.isChecked())
        new_locale = self.comboBox_Language.currentData(Qt.ItemDataRole.UserRole)
        if new_locale != settings.locale:
            QMessageBox.information(self, tr.INFO, tr.LANG_RESET)
        self.settings.setValue("General/locale", new_locale)
        self.settings.setValue("General/logo_path", self.comboBox_Logo.currentText())
        self.settings.setValue("General/theme", self.comboBox_Theme.currentText())
        for hotkey in hotkeys.get_hotkeys():
            self.settings.setValue("Hotkeys/" + hotkey.name, self.hotkey_to_value[hotkey.name])
        if self.radioButton_SimpleDLopenCall.isChecked():
            injection_method = typedefs.INJECTION_METHOD.DLOPEN
        elif self.radioButton_AdvancedInjection.isChecked():
            injection_method = typedefs.INJECTION_METHOD.ADVANCED
        self.settings.setValue("CodeInjection/code_injection_method", injection_method)
        self.settings.setValue("MemoryView/show_memory_view_on_stop", self.checkBox_ShowMemoryViewOnStop.isChecked())
        self.settings.setValue("MemoryView/instructions_per_scroll", self.spinBox_InstructionsPerScroll.value())
        self.settings.setValue("MemoryView/bytes_per_scroll", self.spinBox_BytesPerScroll.value())
        if not os.environ.get("APPDIR"):
            selected_gdb_path = self.lineEdit_GDBPath.text()
            current_gdb_path = self.settings.value("Debug/gdb_path", type=str)
            if selected_gdb_path != current_gdb_path:
                if InputDialogForm(self, [(tr.GDB_RESET,)]).exec():
                    debugcore.init_gdb(selected_gdb_path)
            self.settings.setValue("Debug/gdb_path", selected_gdb_path)
        self.settings.setValue("Debug/gdb_logging", self.checkBox_GDBLogging.isChecked())
        self.settings.setValue("Debug/interrupt_signal", self.comboBox_InterruptSignal.currentText())
        self.settings.setValue("Java/ignore_segfault", self.checkBox_JavaSegfault.isChecked())
        if self.handle_signals_data:
            self.settings.setValue("Debug/handle_signals", self.handle_signals_data)
        super().accept()

    def reject(self):
        logo_path = self.settings.value("General/logo_path", type=str)
        app.setWindowIcon(QIcon(os.path.join(utils.get_logo_directory(), logo_path)))
        theme = self.settings.value("General/theme", type=str)
        app.setPalette(get_theme(theme))
        super().reject()

    def config_gui(self):
        self.checkBox_AutoUpdateAddressTable.setChecked(
            self.settings.value("General/auto_update_address_table", type=bool)
        )
        self.spinBox_UpdateInterval.setValue(self.settings.value("General/address_table_update_interval", type=int))
        self.spinBox_FreezeInterval.setValue(self.settings.value("General/freeze_interval", type=int))
        output_mode = json.loads(self.settings.value("General/gdb_output_mode", type=str))
        output_mode = typedefs.gdb_output_mode(*output_mode)
        self.checkBox_OutputModeAsync.setChecked(output_mode.async_output)
        self.checkBox_OutputModeCommand.setChecked(output_mode.command_output)
        self.checkBox_OutputModeCommandInfo.setChecked(output_mode.command_info)
        self.lineEdit_AutoAttach.setText(self.settings.value("General/auto_attach", type=str))
        self.checkBox_AutoAttachRegex.setChecked(self.settings.value("General/auto_attach_regex", type=bool))
        current_locale = self.settings.value("General/locale", type=str)
        self.comboBox_Language.setCurrentText(language_list.get(current_locale, "en_US"))
        with QSignalBlocker(self.comboBox_Theme):
            self.comboBox_Theme.setCurrentText(self.settings.value("General/theme", type=str))
        with QSignalBlocker(self.comboBox_Logo):
            self.comboBox_Logo.setCurrentText(self.settings.value("General/logo_path", type=str))
        self.hotkey_to_value.clear()
        for hotkey in hotkeys.get_hotkeys():
            self.hotkey_to_value[hotkey.name] = self.settings.value("Hotkeys/" + hotkey.name)
        self.listWidget_Functions_current_row_changed(self.listWidget_Functions.currentRow())
        code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        if code_injection_method == typedefs.INJECTION_METHOD.DLOPEN:
            self.radioButton_SimpleDLopenCall.setChecked(True)
        elif code_injection_method == typedefs.INJECTION_METHOD.ADVANCED:
            self.radioButton_AdvancedInjection.setChecked(True)

        self.checkBox_ShowMemoryViewOnStop.setChecked(
            self.settings.value("MemoryView/show_memory_view_on_stop", type=bool)
        )
        self.spinBox_InstructionsPerScroll.setValue(self.settings.value("MemoryView/instructions_per_scroll", type=int))
        self.spinBox_BytesPerScroll.setValue(self.settings.value("MemoryView/bytes_per_scroll", type=int))
        self.lineEdit_GDBPath.setText(str(self.settings.value("Debug/gdb_path", type=str)))
        if os.environ.get("APPDIR"):
            self.label_GDBPath.setDisabled(True)
            self.label_GDBPath.setToolTip(tr.APPIMAGE_SETTING_GDB)
            self.lineEdit_GDBPath.setDisabled(True)
            self.lineEdit_GDBPath.setToolTip(tr.APPIMAGE_SETTING_GDB)
            self.pushButton_GDBPath.setDisabled(True)
            self.pushButton_GDBPath.setToolTip(tr.APPIMAGE_SETTING_GDB)
        self.checkBox_GDBLogging.setChecked(self.settings.value("Debug/gdb_logging", type=bool))
        self.comboBox_InterruptSignal.setCurrentText(self.settings.value("Debug/interrupt_signal", type=str))
        self.checkBox_JavaSegfault.setChecked(self.settings.value("Java/ignore_segfault", type=bool))

    def change_display(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def listWidget_Functions_current_row_changed(self, index):
        if index == -1:
            self.lineEdit_Hotkey.clear()
        else:
            self.lineEdit_Hotkey.setText(self.hotkey_to_value[hotkeys.get_hotkeys()[index].name])

    def pushButton_ClearHotkey_clicked(self):
        self.lineEdit_Hotkey.clear()

    def pushButton_ResetSettings_clicked(self):
        confirm_dialog = InputDialogForm(self, [(tr.RESET_DEFAULT_SETTINGS,)])
        if confirm_dialog.exec():
            self.set_default_settings()
            self.handle_signals_data = ""
            self.config_gui()

    def checkBox_AutoUpdateAddressTable_state_changed(self):
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.QWidget_UpdateInterval.setEnabled(True)
        else:
            self.QWidget_UpdateInterval.setEnabled(False)

    def checkBox_AutoAttachRegex_state_changed(self):
        if self.checkBox_AutoAttachRegex.isChecked():
            self.lineEdit_AutoAttach.setPlaceholderText(tr.MOUSE_OVER_EXAMPLES)
            self.lineEdit_AutoAttach.setToolTip(tr.AUTO_ATTACH_TOOLTIP)
        else:
            self.lineEdit_AutoAttach.setPlaceholderText(tr.SEPARATE_PROCESSES_WITH.format(";"))
            self.lineEdit_AutoAttach.setToolTip("")

    def comboBox_Logo_current_index_changed(self):
        logo_path = self.comboBox_Logo.currentText()
        app.setWindowIcon(QIcon(os.path.join(utils.get_logo_directory(), logo_path)))

    def comboBox_Theme_current_index_changed(self):
        app.setPalette(get_theme(self.comboBox_Theme.currentText()))

    def pushButton_GDBPath_clicked(self):
        current_path = self.lineEdit_GDBPath.text()
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_GDB_BINARY, os.path.dirname(current_path))
        if file_path:
            self.lineEdit_GDBPath.setText(file_path)

    def pushButton_HandleSignals_clicked(self):
        if not self.handle_signals_data:
            self.handle_signals_data = self.settings.value("Debug/handle_signals", type=str)
        signal_dialog = HandleSignalsDialogForm(self, self.handle_signals_data)
        if signal_dialog.exec():
            self.handle_signals_data = signal_dialog.get_values()

    def lineEdit_Hotkey_key_pressed_event(self, event: QKeyEvent):
        """
        Instead of relying on the QT Event, we grab input from keyboard lib directly.
        This reduces the amount of parsing from keys necessary and catches some more edge cases.

        One final caveat exists: system hotkeys or system wide defined hotkeys (xserver)
        take precedence over the keyboard lib and are not caught completely.
        """
        pressed_events: list[KeyboardEvent] = list(_pressed_events.values())
        if len(pressed_events) == 0:
            # the keypress time was so short its not recognized by keyboard lib.
            return
        hotkey_string = ""
        for ev in pressed_events:
            # replacing keys with their respective base key, e.g "!" --> "1"
            ev.name = to_name[(ev.scan_code, ())][-1]
            # keyboard does recognize meta key (win key) as alt, setting manually
            if ev.scan_code == 125 or ev.scan_code == 126:
                ev.name = "windows"
            hotkey_string += ev.name + "+"

        # remove the last plus
        hotkey_string = hotkey_string[:-1]

        # moved from old keySequenceChanged event
        self.lineEdit_Hotkey.setText(hotkey_string)
        index = self.listWidget_Functions.currentIndex().row()
        if index == -1:
            self.lineEdit_Hotkey.clear()
        else:
            self.hotkey_to_value[hotkeys.get_hotkeys()[index].name] = self.lineEdit_Hotkey.text()


class HandleSignalsDialogForm(QDialog, HandleSignalsDialog):
    def __init__(self, parent, signal_data):
        super().__init__(parent)
        self.setupUi(self)
        self.signal_data = json.loads(signal_data)
        self.tableWidget_Signals.setRowCount(len(self.signal_data))
        for index, (signal, stop, pass_to_program) in enumerate(self.signal_data):
            self.tableWidget_Signals.setItem(index, 0, QTableWidgetItem(signal))
            widget, checkbox = self.create_checkbox_widget()
            self.tableWidget_Signals.setCellWidget(index, 1, widget)
            if stop:
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)
            widget, checkbox = self.create_checkbox_widget()
            self.tableWidget_Signals.setCellWidget(index, 2, widget)
            if pass_to_program:
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.tableWidget_Signals.resizeColumnsToContents()
        guiutils.center_to_parent(self)

    def create_checkbox_widget(self):
        widget = QWidget()
        checkbox = QCheckBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget, checkbox

    def get_values(self):
        signal_data = []
        for index in range(len(self.signal_data)):
            current_signal = []
            current_signal.append(self.signal_data[index][0])
            widget = self.tableWidget_Signals.cellWidget(index, 1)
            checkbox = widget.findChild(QCheckBox)
            current_signal.append(True if checkbox.checkState() == Qt.CheckState.Checked else False)
            widget = self.tableWidget_Signals.cellWidget(index, 2)
            checkbox = widget.findChild(QCheckBox)
            current_signal.append(True if checkbox.checkState() == Qt.CheckState.Checked else False)
            signal_data.append(current_signal)
        return json.dumps(signal_data)


class ConsoleWidgetForm(QWidget, ConsoleWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.completion_model = QStringListModel()
        self.completer = QCompleter()
        self.completer.setModel(self.completion_model)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setMaxVisibleItems(8)
        self.lineEdit.setCompleter(self.completer)
        self.quit_commands = ("q", "quit", "-gdb-exit")
        self.continue_commands = ("c", "continue", "-exec-continue")
        self.input_history = [""]
        self.current_history_index = -1
        self.await_async_output_thread = AwaitAsyncOutput()
        self.await_async_output_thread.async_output_ready.connect(self.on_async_output)
        self.await_async_output_thread.start()
        self.pushButton_Send.clicked.connect(self.communicate)
        self.shortcut_send = QShortcut(QKeySequence("Return"), self)
        self.shortcut_send.activated.connect(self.communicate)
        self.shortcut_complete_command = QShortcut(QKeySequence("Tab"), self)
        self.shortcut_complete_command.activated.connect(self.complete_command)
        self.shortcut_multiline_mode = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_multiline_mode.activated.connect(self.enter_multiline_mode)
        self.lineEdit.textEdited.connect(self.finish_completion)

        # Saving the original function because super() doesn't work when we override functions like this
        self.lineEdit.keyPressEvent_original = self.lineEdit.keyPressEvent
        self.lineEdit.keyPressEvent = self.lineEdit_key_press_event
        self.reset_console_text()
        guiutils.center_to_parent(self)

    def communicate(self):
        self.current_history_index = -1
        self.input_history[-1] = ""
        console_input = self.lineEdit.text()
        last_input = self.input_history[-2] if len(self.input_history) > 1 else ""
        if console_input != last_input and console_input != "":
            self.input_history[-1] = console_input
            self.input_history.append("")
        if console_input.lower() == "/clear":
            self.lineEdit.clear()
            self.reset_console_text()
            return
        self.lineEdit.clear()
        if console_input.strip().lower() in self.quit_commands:
            console_output = tr.QUIT_SESSION_CRASH
        if console_input.strip().lower() in self.continue_commands:
            console_output = tr.CONT_SESSION_CRASH
        else:
            if self.radioButton_CLI.isChecked():
                console_output = debugcore.send_command(console_input, cli_output=True)
            else:
                console_output = debugcore.send_command(console_input)
        self.textBrowser.append("-->" + console_input)
        if console_output:
            self.textBrowser.append(console_output)
        self.scroll_to_bottom()

    def reset_console_text(self):
        self.textBrowser.clear()
        self.textBrowser.append(tr.GDB_CONSOLE_INIT)

    def scroll_to_bottom(self):
        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.textBrowser.setTextCursor(cursor)
        self.textBrowser.ensureCursorVisible()

    def enter_multiline_mode(self):
        multiline_dialog = TextEditDialogForm(self, self.lineEdit.text())
        if multiline_dialog.exec():
            self.lineEdit.setText(multiline_dialog.get_values())
            self.communicate()

    def on_async_output(self, async_output):
        self.textBrowser.append(async_output)
        self.scroll_to_bottom()

    def scroll_backwards_history(self):
        try:
            new_text = self.input_history[self.current_history_index - 1]
        except IndexError:
            return
        self.input_history[self.current_history_index] = self.lineEdit.text()
        self.current_history_index -= 1
        self.lineEdit.setText(new_text)

    def scroll_forwards_history(self):
        if self.current_history_index == -1:
            return
        self.input_history[self.current_history_index] = self.lineEdit.text()
        self.current_history_index += 1
        self.lineEdit.setText(self.input_history[self.current_history_index])

    def lineEdit_key_press_event(self, event):
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up), self.scroll_backwards_history),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down), self.scroll_forwards_history),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.lineEdit.keyPressEvent_original(event)

    def finish_completion(self):
        self.completion_model.setStringList([])

    def complete_command(self):
        if debugcore.gdb_initialized and debugcore.currentpid != -1 and self.lineEdit.text():
            self.completion_model.setStringList(debugcore.complete_command(self.lineEdit.text()))
            self.completer.complete()
        else:
            self.finish_completion()

    def closeEvent(self, event):
        self.await_async_output_thread.stop()


class AboutWidgetForm(QTabWidget, AboutWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        # This section has untranslated text since it's just a placeholder
        pince_dir = utils.get_script_directory()
        license_text = open(f"{pince_dir}/COPYING").read()
        authors_text = open(f"{pince_dir}/AUTHORS").read()
        thanks_text = open(f"{pince_dir}/THANKS").read()
        self.textBrowser_License.setPlainText(license_text)
        self.textBrowser_Contributors.append(
            "This is only a placeholder, this section may look different when the project finishes"
            + "\nIn fact, something like a demo-scene for here would look absolutely fabulous <:"
        )
        self.textBrowser_Contributors.append("\n########")
        self.textBrowser_Contributors.append("#AUTHORS#")
        self.textBrowser_Contributors.append("########\n")
        self.textBrowser_Contributors.append(authors_text)
        self.textBrowser_Contributors.append("\n#######")
        self.textBrowser_Contributors.append("#THANKS#")
        self.textBrowser_Contributors.append("#######\n")
        self.textBrowser_Contributors.append(thanks_text)
        guiutils.center_to_parent(self)


class MemoryViewWindowForm(QMainWindow, MemoryViewWindow):
    process_stopped = pyqtSignal()
    process_running = pyqtSignal()
    show_memory_view_on_stop: bool = False
    instructions_per_scroll: int = 3
    bytes_per_scroll: int = 0x40

    def set_dynamic_debug_hotkeys(self):
        self.actionBreak.setText(tr.BREAK.format(hotkeys.break_hotkey.get_active_key()))
        self.actionRun.setText(tr.RUN.format(hotkeys.continue_hotkey.get_active_key()))
        self.actionToggle_Attach.setText(tr.TOGGLE_ATTACH.format(hotkeys.toggle_attach_hotkey.get_active_key()))

    def set_debug_menu_shortcuts(self):
        self.shortcut_step = QShortcut(QKeySequence("F7"), self)
        self.shortcut_step.activated.connect(self.step_instruction)
        self.shortcut_step_over = QShortcut(QKeySequence("F8"), self)
        self.shortcut_step_over.activated.connect(self.step_over_instruction)
        self.shortcut_execute_till_return = QShortcut(QKeySequence("Shift+F8"), self)
        self.shortcut_execute_till_return.activated.connect(self.execute_till_return)
        self.shortcut_toggle_breakpoint = QShortcut(QKeySequence("F5"), self)
        self.shortcut_toggle_breakpoint.activated.connect(self.toggle_breakpoint)
        self.shortcut_set_address = QShortcut(QKeySequence("Shift+F4"), self)
        self.shortcut_set_address.activated.connect(self.set_address)

    def initialize_file_context_menu(self):
        self.actionLoad_Trace.triggered.connect(self.show_trace_window)

    def initialize_debug_context_menu(self):
        self.actionBreak.triggered.connect(debugcore.interrupt_inferior)
        self.actionRun.triggered.connect(debugcore.continue_inferior)
        self.actionToggle_Attach.triggered.connect(lambda: self.parent().toggle_attach_hotkey_pressed())
        self.actionStep.triggered.connect(self.step_instruction)
        self.actionStep_Over.triggered.connect(self.step_over_instruction)
        self.actionExecute_Till_Return.triggered.connect(self.execute_till_return)

        # Ignore the "checked" bool param as we don't make use of it
        self.actionToggle_Breakpoint.triggered.connect(lambda checked: self.toggle_breakpoint())
        self.actionSet_Address.triggered.connect(self.set_address)

    def initialize_view_context_menu(self):
        self.actionBookmarks.triggered.connect(self.actionBookmarks_triggered)
        self.actionStackTrace_Info.triggered.connect(self.actionStackTrace_Info_triggered)
        self.actionBreakpoints.triggered.connect(self.actionBreakpoints_triggered)
        self.actionFunctions.triggered.connect(self.actionFunctions_triggered)
        self.actionGDB_Log_File.triggered.connect(self.actionGDB_Log_File_triggered)
        self.actionMemory_Regions.triggered.connect(self.actionMemory_Regions_triggered)
        self.actionRestore_Instructions.triggered.connect(self.actionRestore_Instructions_triggered)
        self.actionReferenced_Strings.triggered.connect(self.actionReferenced_Strings_triggered)
        self.actionReferenced_Calls.triggered.connect(self.actionReferenced_Calls_triggered)

    def initialize_tools_context_menu(self):
        self.actionInject_so_file.triggered.connect(self.actionInject_so_file_triggered)
        self.actionCall_Function.triggered.connect(self.actionCall_Function_triggered)
        self.actionSearch_Opcode.triggered.connect(self.actionSearch_Opcode_triggered)
        self.actionDissect_Code.triggered.connect(self.actionDissect_Code_triggered)

    def initialize_help_context_menu(self):
        self.actionlibpince.triggered.connect(self.actionlibpince_triggered)

    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.updating_memoryview = False
        self.stacktrace_info_widget = StackTraceInfoWidgetForm(self)
        self.float_registers_widget = FloatRegisterWidgetForm(self)
        self.process_stopped.connect(self.on_process_stop)
        self.process_running.connect(self.on_process_running)
        self.set_debug_menu_shortcuts()
        self.set_dynamic_debug_hotkeys()
        self.initialize_file_context_menu()
        self.initialize_view_context_menu()
        self.initialize_debug_context_menu()
        self.initialize_tools_context_menu()
        self.initialize_help_context_menu()
        self.initialize_disassemble_view()
        self.initialize_register_view()
        self.initialize_stack_view()
        self.initialize_hex_view()

        self.label_HexView_Information.contextMenuEvent = self.label_HexView_Information_context_menu_event

        self.splitter_Disassemble_Registers.setStretchFactor(0, 1)
        self.splitter_MainMiddle.setStretchFactor(1, 1)
        self.widget_StackView.resize(660, self.widget_StackView.height())
        self.widget_Registers.resize(330, self.widget_Registers.height())
        guiutils.center(self)

    def initialize_register_view(self):
        self.pushButton_ShowFloatRegisters.clicked.connect(self.pushButton_ShowFloatRegisters_clicked)

    def initialize_stack_view(self):
        self.stackedWidget_StackScreens.setCurrentWidget(self.StackTrace)
        self.tableWidget_StackTrace.setColumnWidth(STACKTRACE_RETURN_ADDRESS_COL, 350)

        self.tableWidget_Stack.contextMenuEvent = self.tableWidget_Stack_context_menu_event
        self.tableWidget_StackTrace.contextMenuEvent = self.tableWidget_StackTrace_context_menu_event
        self.tableWidget_Stack.itemDoubleClicked.connect(self.tableWidget_Stack_double_click)
        self.tableWidget_StackTrace.itemDoubleClicked.connect(self.tableWidget_StackTrace_double_click)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Stack.keyPressEvent_original = self.tableWidget_Stack.keyPressEvent
        self.tableWidget_Stack.keyPressEvent = self.tableWidget_Stack_key_press_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_StackTrace.keyPressEvent_original = self.tableWidget_StackTrace.keyPressEvent
        self.tableWidget_StackTrace.keyPressEvent = self.tableWidget_StackTrace_key_press_event

    def initialize_disassemble_view(self):
        self.tableWidget_Disassemble.setColumnWidth(DISAS_ADDR_COL, 300)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_BYTES_COL, 150)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_OPCODES_COL, 400)

        self.disassemble_last_selected_address_int = 0
        self.disassemble_currently_displayed_address = "0"
        self.widget_Disassemble.wheelEvent = self.widget_Disassemble_wheel_event

        self.bDisassemblyScrolling = False  # rejects new scroll requests while scrolling
        self.tableWidget_Disassemble.wheelEvent = QEvent.ignore
        self.verticalScrollBar_Disassemble.wheelEvent = QEvent.ignore
        self.verticalScrollBar_Disassemble.sliderChange = self.disassemble_scrollbar_sliderchanged
        guiutils.center_scroll_bar(self.verticalScrollBar_Disassemble)

        # Format: [address1, address2, ...]
        self.tableWidget_Disassemble.travel_history = []

        # Format: {address1:comment1,address2:comment2, ...}
        self.tableWidget_Disassemble.bookmarks = {}

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Disassemble.keyPressEvent_original = self.tableWidget_Disassemble.keyPressEvent
        self.tableWidget_Disassemble.keyPressEvent = self.tableWidget_Disassemble_key_press_event
        self.tableWidget_Disassemble.contextMenuEvent = self.tableWidget_Disassemble_context_menu_event

        self.tableWidget_Disassemble.itemDoubleClicked.connect(self.tableWidget_Disassemble_item_double_clicked)
        self.tableWidget_Disassemble.itemSelectionChanged.connect(self.tableWidget_Disassemble_item_selection_changed)

    def initialize_hex_view(self):
        # Determines where selection starts and ends
        self.hex_selection_start = 0
        self.hex_selection_end = 0
        # Actual start and end addresses of the selection
        self.hex_selection_address_begin = 0
        self.hex_selection_address_end = 0
        self.hex_view_current_region = typedefs.tuple_region_info(0, 0, None, None)
        self.hex_model = QHexModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.ascii_model = QAsciiModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.tableView_HexView_Hex.setModel(self.hex_model)
        self.tableView_HexView_Ascii.setModel(self.ascii_model)

        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        # Saving the original function because super() doesn't work when we override functions like this
        self.widget_HexView.keyPressEvent_original = self.widget_HexView.keyPressEvent
        self.widget_HexView.keyPressEvent = self.widget_HexView_key_press_event

        self.tableView_HexView_Hex.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Ascii.contextMenuEvent = self.widget_HexView_context_menu_event

        self.bHexViewScrolling = False  # rejects new scroll requests while scrolling
        self.verticalScrollBar_HexView.wheelEvent = QEvent.ignore
        self.verticalScrollBar_HexView.sliderChange = self.hex_view_scrollbar_sliderchanged
        guiutils.center_scroll_bar(self.verticalScrollBar_HexView)

        self.tableWidget_HexView_Address.wheelEvent = QEvent.ignore
        self.tableWidget_HexView_Address.setAutoScroll(False)
        self.tableWidget_HexView_Address.setStyleSheet("QTableWidget {background-color: transparent;}")
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.tableView_HexView_Hex.selectionModel().selectionChanged.connect(self.hex_view_selection_changed)
        self.tableView_HexView_Ascii.selectionModel().selectionChanged.connect(self.hex_view_selection_changed)

        self.scrollArea_Hex.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_Hex.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.verticalHeader().setDefaultSectionSize(
            self.tableView_HexView_Hex.verticalHeader().defaultSectionSize()
        )
        self.tableWidget_HexView_Address.verticalHeader().setMaximumSectionSize(
            self.tableView_HexView_Hex.verticalHeader().maximumSectionSize()
        )

        self.hex_update_timer = QTimer(timeout=self.hex_update_loop)
        self.hex_update_timer.start(200)

    def show_trace_window(self):
        TraceInstructionsWindowForm(self, prompt_dialog=False)

    def step_instruction(self):
        if not (
            debugcore.currentpid == -1
            or debugcore.active_trace
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.step_instruction()

    def step_over_instruction(self):
        if not (
            debugcore.currentpid == -1
            or debugcore.active_trace
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.step_over_instruction()

    def execute_till_return(self):
        if not (
            debugcore.currentpid == -1
            or debugcore.active_trace
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.execute_till_return()

    def set_address(self):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        debugcore.set_convenience_variable("pc", current_address)
        self.refresh_disassemble_view()

    def edit_instruction(self):
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        bytes_aob = self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text()
        EditInstructionDialogForm(self, current_address, bytes_aob).exec()

    def nop_instruction(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        array_of_bytes = self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text()
        debugcore.nop_instruction(current_address_int, len(array_of_bytes.split()))
        self.refresh_disassemble_view()

    def toggle_breakpoint(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        if debugcore.get_breakpoints_in_range(current_address_int):
            debugcore.delete_breakpoint(current_address)
        else:
            if not debugcore.add_breakpoint(current_address):
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(current_address))
        self.refresh_disassemble_view()

    def toggle_watchpoint(self, address, length, watchpoint_type=typedefs.WATCHPOINT_TYPE.BOTH):
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(address, length)
        if not breakpoints:
            if len(debugcore.add_watchpoint(hex(address), length, watchpoint_type)) < 1:
                QMessageBox.information(self, tr.ERROR, tr.WATCHPOINT_FAILED.format(hex(address)))
        else:
            for bp in breakpoints:
                debugcore.delete_breakpoint(bp.address)
        self.refresh_hex_view()

    def label_HexView_Information_context_menu_event(self, event):
        if debugcore.currentpid == -1:
            return

        def copy_to_clipboard():
            app.clipboard().setText(self.label_HexView_Information.text())

        menu = QMenu()
        copy_label = menu.addAction(tr.COPY_CLIPBOARD)
        font_size = self.label_HexView_Information.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_label: copy_to_clipboard}
        try:
            actions[action]()
        except KeyError:
            pass

    def widget_HexView_context_menu_event(self, event):
        if debugcore.currentpid == -1:
            return
        addr = self.hex_selection_address_begin
        length = self.get_hex_selection_length()
        menu = QMenu()
        edit = menu.addAction(tr.EDIT)
        menu.addSeparator()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        add_address = menu.addAction(f"{tr.ADD_TO_ADDRESS_LIST}[Ctrl+A]")
        menu.addSeparator()
        copy_selection = menu.addAction(f"{tr.COPY}[Ctrl+C]")
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        watchpoint_menu = menu.addMenu(tr.SET_WATCHPOINT)
        watchpoint_write = watchpoint_menu.addAction(tr.WRITE_ONLY)
        watchpoint_read = watchpoint_menu.addAction(tr.READ_ONLY)
        watchpoint_both = watchpoint_menu.addAction(tr.BOTH)
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        delete_breakpoint = menu.addAction(tr.DELETE_BREAKPOINT)
        if not debugcore.get_breakpoints_in_range(addr, length):
            guiutils.delete_menu_entries(menu, [add_condition, delete_breakpoint])
        else:
            guiutils.delete_menu_entries(menu, [watchpoint_menu.menuAction()])
        font_size = self.widget_HexView.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            edit: self.exec_hex_view_edit_dialog,
            go_to: self.exec_hex_view_go_to_dialog,
            disassemble: lambda: self.disassemble_expression(hex(addr), append_to_travel_history=True),
            add_address: self.exec_hex_view_add_address_dialog,
            copy_selection: self.copy_hex_view_selection,
            refresh: self.refresh_hex_view,
            watchpoint_write: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.WRITE_ONLY),
            watchpoint_read: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.READ_ONLY),
            watchpoint_both: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.BOTH),
            add_condition: lambda: self.add_breakpoint_condition(addr, length),
            delete_breakpoint: lambda: self.toggle_watchpoint(addr, length),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def exec_hex_view_edit_dialog(self):
        if debugcore.currentpid == -1:
            return
        HexEditDialogForm(self, self.hex_selection_address_begin, self.get_hex_selection_length()).exec()
        self.refresh_hex_view()

    def exec_hex_view_go_to_dialog(self):
        if debugcore.currentpid == -1:
            return
        go_to_dialog = InputDialogForm(self, [(tr.ENTER_EXPRESSION, hex(self.hex_selection_address_begin))])
        if go_to_dialog.exec():
            expression = go_to_dialog.get_values()
            dest_address = debugcore.examine_expression(expression).address
            if not dest_address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID.format(expression))
                return
            self.hex_dump_address(int(dest_address, 16))

    def exec_hex_view_add_address_dialog(self):
        if debugcore.currentpid == -1:
            return
        vt = typedefs.ValueType(typedefs.VALUE_INDEX.AOB, self.get_hex_selection_length())
        address_dialog = ManualAddressDialogForm(self, address=hex(self.hex_selection_address_begin), value_type=vt)
        if address_dialog.exec():
            desc, address, vt = address_dialog.get_values()
            self.parent().add_entry_to_addresstable(desc, address, vt)
            self.parent().update_address_table()

    def copy_hex_view_selection(self):
        data = debugcore.hex_dump(self.hex_selection_address_begin, self.get_hex_selection_length())
        if self.focusWidget() == self.tableView_HexView_Ascii:
            display_text = utils.aob_to_str(data)
        else:
            display_text = " ".join(data)
        app.clipboard().setText(display_text)

    def hex_view_scroll_up(self):
        self.verticalScrollBar_HexView.setValue(1)

    def hex_view_scroll_down(self):
        self.verticalScrollBar_HexView.setValue(-1)

    def hex_view_scrollbar_sliderchanged(self, event):
        if self.bHexViewScrolling:
            return
        self.bHexViewScrolling = True
        maximum = self.verticalScrollBar_HexView.maximum()
        minimum = self.verticalScrollBar_HexView.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_HexView.value()
        # if midst - 10 < current_value < midst + 10:
        #    self.bHexViewScrolling = False
        #    return
        current_address = self.hex_model.current_address
        if current_value < midst:
            next_address = current_address - self.bytes_per_scroll
        else:
            next_address = current_address + self.bytes_per_scroll
        self.hex_dump_address(next_address)
        guiutils.center_scroll_bar(self.verticalScrollBar_HexView)
        self.bHexViewScrolling = False

    def disassemble_scroll_up(self):
        self.verticalScrollBar_Disassemble.setValue(1)

    def disassemble_scroll_down(self):
        self.verticalScrollBar_Disassemble.setValue(-1)

    def disassemble_scrollbar_sliderchanged(self, even):
        if self.bDisassemblyScrolling:
            return
        self.bDisassemblyScrolling = True
        maximum = self.verticalScrollBar_Disassemble.maximum()
        minimum = self.verticalScrollBar_Disassemble.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_Disassemble.value()
        # if midst - 10 < current_value < midst + 10:
        #    self.bDisassemblyScrolling = False
        #    return
        if current_value < midst:
            self.tableWidget_Disassemble_scroll("previous", self.instructions_per_scroll)
        else:
            self.tableWidget_Disassemble_scroll("next", self.instructions_per_scroll)
        guiutils.center_scroll_bar(self.verticalScrollBar_Disassemble)
        self.bDisassemblyScrolling = False

    def hex_view_selection_changed(self, selected, deselected):
        sender_selection_model: QItemSelectionModel = self.sender()
        sender_selection = sorted([(idx.row(), idx.column()) for idx in sender_selection_model.selectedIndexes()])
        first_selection = sender_selection[0]
        last_selection = sender_selection[-1]
        hex_start = self.address_to_hex_point(self.hex_selection_start)
        hex_end = self.address_to_hex_point(self.hex_selection_end)
        hex_start, hex_end = self.fix_selection_at_borders(hex_start, hex_end)
        if len(sender_selection) == 1:
            hex_start = first_selection
            hex_end = first_selection
        else:
            # Selection ends in top left
            if last_selection == hex_start:
                hex_end = first_selection
            # Selection ends in top right
            elif last_selection[0] == hex_start[0]:
                hex_end = (first_selection[0], last_selection[1])
            # Selection ends in bottom left
            elif last_selection[1] == hex_start[1]:
                hex_end = (last_selection[0], first_selection[1])
            # Selection ends in bottom right
            else:
                hex_end = last_selection
        if hex_start < hex_end:
            address_begin = hex_start
            address_end = hex_end
        else:
            address_begin = hex_end
            address_end = hex_start
        self.hex_selection_start = self.hex_point_to_address(hex_start)
        self.hex_selection_end = self.hex_point_to_address(hex_end)
        self.hex_selection_address_begin = self.hex_point_to_address(address_begin)
        self.hex_selection_address_end = self.hex_point_to_address(address_end)
        self.handle_hex_selection()

    def handle_hex_selection(self):
        hex_selection_model = self.tableView_HexView_Hex.selectionModel()
        ascii_selection_model = self.tableView_HexView_Ascii.selectionModel()
        start_point = self.address_to_hex_point(self.hex_selection_address_begin)
        end_point = self.address_to_hex_point(self.hex_selection_address_end)
        with QSignalBlocker(hex_selection_model), QSignalBlocker(ascii_selection_model):
            hex_selection_model.clearSelection()
            ascii_selection_model.clearSelection()
            self.tableWidget_HexView_Address.clearSelection()
            if start_point or end_point:
                start_point, end_point = self.fix_selection_at_borders(start_point, end_point)
                if start_point[0] == end_point[0]:
                    start = hex_selection_model.model().index(*start_point)
                    end = hex_selection_model.model().index(*end_point)
                    selection = QItemSelection(start, end)
                    hex_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                    ascii_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                else:
                    # First line
                    start = hex_selection_model.model().index(*start_point)
                    end = hex_selection_model.model().index(start_point[0], HEX_VIEW_COL_COUNT - 1)
                    selection = QItemSelection(start, end)
                    hex_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                    ascii_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                    # Middle
                    if end_point[0] - start_point[0] > 1:
                        start = hex_selection_model.model().index(start_point[0] + 1, 0)
                        end = hex_selection_model.model().index(end_point[0] - 1, HEX_VIEW_COL_COUNT - 1)
                        selection = QItemSelection(start, end)
                        hex_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                        ascii_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                    # Last line
                    start = hex_selection_model.model().index(end_point[0], 0)
                    end = hex_selection_model.model().index(*end_point)
                    selection = QItemSelection(start, end)
                    hex_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                    ascii_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
                for row in range(start_point[0], end_point[0] + 1):
                    self.tableWidget_HexView_Address.selectRow(row)
                self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tableView_HexView_Hex.update()
        self.tableView_HexView_Ascii.update()
        self.tableWidget_HexView_Address.update()

    def hex_point_to_address(self, point):
        address = self.hex_model.current_address + point[0] * HEX_VIEW_COL_COUNT + point[1]
        return utils.modulo_address(address, debugcore.inferior_arch)

    def address_to_hex_point(self, address):
        diff = address - self.hex_model.current_address
        if 0 <= diff < HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT:
            return diff // HEX_VIEW_COL_COUNT, diff % HEX_VIEW_COL_COUNT

    def get_hex_selection_length(self):
        return self.hex_selection_address_end - self.hex_selection_address_begin + 1

    def fix_selection_at_borders(self, start_point, end_point):
        if not start_point:
            start_point = (0, 0)
        if not end_point:
            end_point = (HEX_VIEW_ROW_COUNT - 1, HEX_VIEW_COL_COUNT - 1)
        return start_point, end_point

    def hex_update_loop(self):
        offset = HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT
        if debugcore.currentpid == -1 or exiting:
            updated_array = ["??"] * offset
        else:
            updated_array = debugcore.hex_dump(self.hex_model.current_address, offset)
        self.hex_model.update_loop(updated_array)
        self.ascii_model.update_loop(updated_array)

    # TODO: Consider merging HexView_Address, HexView_Hex and HexView_Ascii into one UI class
    # TODO: Move this function to that class if that happens
    # TODO: Also consider moving shared fields of HexView and HexModel to that class(such as HexModel.current_address)
    def hex_dump_address(self, int_address, offset=HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT):
        if debugcore.currentpid == -1:
            return
        int_address = utils.modulo_address(int_address, debugcore.inferior_arch)
        if not (self.hex_view_current_region.start <= int_address < self.hex_view_current_region.end):
            info = utils.get_region_info(debugcore.currentpid, int_address)
            if info:
                self.hex_view_current_region = info
                self.label_HexView_Information.setText(
                    tr.REGION_INFO.format(info.perms, hex(info.start), hex(info.end), info.file_name)
                )
            else:
                self.hex_view_current_region = typedefs.tuple_region_info(0, 0, None, None)
                self.label_HexView_Information.setText(tr.INVALID_REGION)
        self.tableWidget_HexView_Address.setRowCount(0)
        self.tableWidget_HexView_Address.setRowCount(HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT)
        for row, current_offset in enumerate(range(HEX_VIEW_ROW_COUNT)):
            row_address = hex(utils.modulo_address(int_address + current_offset * 16, debugcore.inferior_arch))
            self.tableWidget_HexView_Address.setItem(row, 0, QTableWidgetItem(utils.upper_hex(row_address)))
        tableWidget_HexView_column_size = self.tableWidget_HexView_Address.sizeHintForColumn(0) + 5
        self.tableWidget_HexView_Address.setMaximumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setMinimumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setColumnWidth(0, tableWidget_HexView_column_size)
        data_array = debugcore.hex_dump(int_address, offset)
        breakpoint_info = debugcore.get_breakpoint_info()
        self.hex_model.refresh(int_address, offset, data_array, breakpoint_info)
        self.ascii_model.refresh(int_address, offset, data_array, breakpoint_info)
        self.handle_hex_selection()

    def refresh_hex_view(self):
        if debugcore.currentpid == -1:
            return
        if self.tableWidget_HexView_Address.rowCount() == 0:
            entry_point = debugcore.find_entry_point()
            if not entry_point:
                # **Shrugs**
                entry_point = "0x00400000"
            self.hex_dump_address(int(entry_point, 16))
            self.tableView_HexView_Hex.resize_to_contents()
            self.tableView_HexView_Ascii.resize_to_contents()
        else:
            self.hex_dump_address(self.hex_model.current_address)

    # offset can also be an address as hex str
    # returns True if the given expression is disassembled correctly, False if not
    def disassemble_expression(self, expression, offset="+200", append_to_travel_history=False):
        if debugcore.currentpid == -1:
            return
        disas_data = debugcore.disassemble(expression, offset)
        if not disas_data:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.EXPRESSION_ACCESS_ERROR.format(expression))
            return False
        program_counter = debugcore.examine_expression("$pc").address
        program_counter_int = int(program_counter, 16) if program_counter else None
        row_color = {}
        breakpoint_info = debugcore.get_breakpoint_info()

        # TODO: Change this nonsense when the huge refactorization happens
        current_first_address = utils.extract_address(disas_data[0][0])  # address of first list entry
        try:
            previous_first_address = utils.extract_address(self.tableWidget_Disassemble.item(0, DISAS_ADDR_COL).text())
        except AttributeError:
            previous_first_address = current_first_address

        self.tableWidget_Disassemble.setRowCount(0)
        self.tableWidget_Disassemble.setRowCount(len(disas_data))
        jmp_dict, call_dict = debugcore.get_dissect_code_data(False, True, True)
        for row, (address_info, bytes_aob, opcode) in enumerate(disas_data):
            comment = ""
            current_address = int(utils.extract_address(address_info), 16)
            current_address_str = hex(current_address)
            jmp_ref_exists = False
            call_ref_exists = False
            try:
                jmp_referrers = jmp_dict[current_address_str]
                jmp_ref_exists = True
            except KeyError:
                pass
            try:
                call_referrers = call_dict[current_address_str]
                call_ref_exists = True
            except KeyError:
                pass
            if jmp_ref_exists or call_ref_exists:
                tooltip_text = f"{tr.REFERENCED_BY}\n"
                ref_count = 0
                if jmp_ref_exists:
                    for referrer in jmp_referrers:
                        if ref_count > 30:
                            break
                        tooltip_text += "\n" + hex(referrer) + "(" + jmp_referrers[referrer] + ")"
                        ref_count += 1
                if call_ref_exists:
                    for referrer in call_referrers:
                        if ref_count > 30:
                            break
                        tooltip_text += "\n" + hex(referrer) + "(call)"
                        ref_count += 1
                if ref_count > 30:
                    tooltip_text += "\n..."
                tooltip_text += f"\n\n{tr.SEE_REFERRERS}"
                try:
                    row_color[row].append(REF_COLOR)
                except KeyError:
                    row_color[row] = [REF_COLOR]
                real_ref_count = 0
                if jmp_ref_exists:
                    real_ref_count += len(jmp_referrers)
                if call_ref_exists:
                    real_ref_count += len(call_referrers)
                address_info = "{" + str(real_ref_count) + "}" + address_info
            if current_address == program_counter_int:
                address_info = ">>>" + address_info
                try:
                    row_color[row].append(PC_COLOR)
                except KeyError:
                    row_color[row] = [PC_COLOR]
            for bookmark_item in self.tableWidget_Disassemble.bookmarks.keys():
                if current_address == bookmark_item:
                    try:
                        row_color[row].append(BOOKMARK_COLOR)
                    except KeyError:
                        row_color[row] = [BOOKMARK_COLOR]
                    address_info = "(M)" + address_info
                    comment = self.tableWidget_Disassemble.bookmarks[bookmark_item]
                    break
            for breakpoint in breakpoint_info:
                int_breakpoint_address = int(breakpoint.address, 16)
                if current_address == int_breakpoint_address:
                    try:
                        row_color[row].append(BREAKPOINT_COLOR)
                    except KeyError:
                        row_color[row] = [BREAKPOINT_COLOR]
                    breakpoint_mark = "(B"
                    if breakpoint.enabled == "n":
                        breakpoint_mark += "-disabled"
                    else:
                        if breakpoint.disp != "keep":
                            breakpoint_mark += "-" + breakpoint.disp
                        if breakpoint.enable_count:
                            breakpoint_mark += "-" + breakpoint.enable_count
                    breakpoint_mark += ")"
                    address_info = breakpoint_mark + address_info
                    break
            if current_address == self.disassemble_last_selected_address_int:
                self.tableWidget_Disassemble.selectRow(row)
            addr_item = QTableWidgetItem(address_info)
            bytes_item = QTableWidgetItem(bytes_aob)
            opcodes_item = QTableWidgetItem(opcode)
            comment_item = QTableWidgetItem(comment)
            if jmp_ref_exists or call_ref_exists:
                addr_item.setToolTip(tooltip_text)
                bytes_item.setToolTip(tooltip_text)
                opcodes_item.setToolTip(tooltip_text)
                comment_item.setToolTip(tooltip_text)
            self.tableWidget_Disassemble.setItem(row, DISAS_ADDR_COL, addr_item)
            self.tableWidget_Disassemble.setItem(row, DISAS_BYTES_COL, bytes_item)
            self.tableWidget_Disassemble.setItem(row, DISAS_OPCODES_COL, opcodes_item)
            self.tableWidget_Disassemble.setItem(row, DISAS_COMMENT_COL, comment_item)
        jmp_dict.close()
        call_dict.close()
        self.handle_colors(row_color)

        # We append the old record to travel history as last action because we wouldn't like to see unnecessary
        # addresses in travel history if any error occurs while displaying the next location
        if append_to_travel_history:
            self.tableWidget_Disassemble.travel_history.append(previous_first_address)
        self.disassemble_currently_displayed_address = current_first_address
        return True

    def refresh_disassemble_view(self):
        if debugcore.currentpid == -1:
            return
        self.disassemble_expression(self.disassemble_currently_displayed_address)

    # Set color of a row if a specific address is encountered(e.g $pc, a bookmarked address etc.)
    def handle_colors(self, row_color):
        if debugcore.currentpid == -1:
            return
        for row in row_color:
            current_row = row_color[row]
            if PC_COLOR in current_row:
                if BREAKPOINT_COLOR in current_row:
                    color = QColorConstants.Green
                elif BOOKMARK_COLOR in current_row:
                    color = QColorConstants.Yellow
                else:
                    color = PC_COLOR
                self.set_row_color(row, color)
                continue
            if BREAKPOINT_COLOR in current_row:
                if BOOKMARK_COLOR in current_row:
                    color = QColorConstants.Magenta
                else:
                    color = BREAKPOINT_COLOR
                self.set_row_color(row, color)
                continue
            if BOOKMARK_COLOR in current_row:
                self.set_row_color(row, BOOKMARK_COLOR)
                continue
            if REF_COLOR in current_row:
                self.set_row_color(row, REF_COLOR)

    def set_row_color(self, row, color):
        if debugcore.currentpid == -1:
            return
        for col in range(self.tableWidget_Disassemble.columnCount()):
            color = QColor(color)
            color.setAlpha(96)
            self.tableWidget_Disassemble.item(row, col).setData(Qt.ItemDataRole.BackgroundRole, color)

    def on_process_stop(self):
        if debugcore.stop_reason == typedefs.STOP_REASON.PAUSE:
            self.setWindowTitle(tr.MV_PAUSED)
            return
        self.updating_memoryview = True
        time0 = time()
        self.setWindowTitle(tr.MV_DEBUGGING.format(debugcore.get_thread_info()))
        self.disassemble_expression("$pc")
        self.update_registers()
        if self.stackedWidget_StackScreens.currentWidget() == self.StackTrace:
            self.update_stacktrace()
        elif self.stackedWidget_StackScreens.currentWidget() == self.Stack:
            self.update_stack()

        # These tableWidgets are never emptied but initially both are empty, so this runs only once
        if self.tableWidget_StackTrace.rowCount() == 0:
            self.update_stacktrace()
        if self.tableWidget_Stack.rowCount() == 0:
            self.update_stack()
        self.refresh_hex_view()
        if self.show_memory_view_on_stop:
            self.showMaximized()
            self.activateWindow()
        if self.stacktrace_info_widget.isVisible():
            self.stacktrace_info_widget.update_stacktrace()
        if self.float_registers_widget.isVisible():
            self.float_registers_widget.update_registers()
        app.processEvents()
        time1 = time()
        print("UPDATED MEMORYVIEW IN:" + str(time1 - time0))
        self.updating_memoryview = False

    def on_process_running(self):
        self.setWindowTitle(tr.MV_RUNNING)

    def add_breakpoint_condition(self, int_address, length=1):
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(int_address, length)
        if breakpoints:
            condition_line_edit_text = breakpoints[0].condition
        else:
            condition_line_edit_text = ""
        items = [(tr.ENTER_BP_CONDITION, condition_line_edit_text, Qt.AlignmentFlag.AlignLeft)]
        condition_dialog = InputDialogForm(self, items)
        if condition_dialog.exec():
            condition = condition_dialog.get_values()
            for bp in breakpoints:
                addr = bp.address
                if not debugcore.modify_breakpoint(addr, typedefs.BREAKPOINT_MODIFY.CONDITION, condition):
                    QMessageBox.information(app.focusWidget(), tr.ERROR, tr.BP_CONDITION_FAILED.format(addr))

    def update_registers(self):
        if debugcore.currentpid == -1:
            return
        registers = debugcore.read_registers()
        if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            self.stackedWidget.setCurrentWidget(self.registers_64)
            self.RAX.set_value(registers["rax"])
            self.RBX.set_value(registers["rbx"])
            self.RCX.set_value(registers["rcx"])
            self.RDX.set_value(registers["rdx"])
            self.RSI.set_value(registers["rsi"])
            self.RDI.set_value(registers["rdi"])
            self.RBP.set_value(registers["rbp"])
            self.RSP.set_value(registers["rsp"])
            self.RIP.set_value(registers["rip"])
            self.R8.set_value(registers["r8"])
            self.R9.set_value(registers["r9"])
            self.R10.set_value(registers["r10"])
            self.R11.set_value(registers["r11"])
            self.R12.set_value(registers["r12"])
            self.R13.set_value(registers["r13"])
            self.R14.set_value(registers["r14"])
            self.R15.set_value(registers["r15"])
        elif debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32:
            self.stackedWidget.setCurrentWidget(self.registers_32)
            self.EAX.set_value(registers["eax"])
            self.EBX.set_value(registers["ebx"])
            self.ECX.set_value(registers["ecx"])
            self.EDX.set_value(registers["edx"])
            self.ESI.set_value(registers["esi"])
            self.EDI.set_value(registers["edi"])
            self.EBP.set_value(registers["ebp"])
            self.ESP.set_value(registers["esp"])
            self.EIP.set_value(registers["eip"])
        self.CF.set_value(registers["cf"])
        self.PF.set_value(registers["pf"])
        self.AF.set_value(registers["af"])
        self.ZF.set_value(registers["zf"])
        self.SF.set_value(registers["sf"])
        self.TF.set_value(registers["tf"])
        self.IF.set_value(registers["if"])
        self.DF.set_value(registers["df"])
        self.OF.set_value(registers["of"])
        self.CS.set_value(registers["cs"])
        self.SS.set_value(registers["ss"])
        self.DS.set_value(registers["ds"])
        self.ES.set_value(registers["es"])
        self.GS.set_value(registers["gs"])
        self.FS.set_value(registers["fs"])

    def update_stacktrace(self):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        stack_trace_info = debugcore.get_stacktrace_info()
        self.tableWidget_StackTrace.setRowCount(0)
        self.tableWidget_StackTrace.setRowCount(len(stack_trace_info))
        for row, item in enumerate(stack_trace_info):
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_RETURN_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_FRAME_ADDRESS_COL, QTableWidgetItem(item[1]))

    def set_stack_widget(self, stack_widget):
        if debugcore.currentpid == -1:
            return
        self.stackedWidget_StackScreens.setCurrentWidget(stack_widget)
        if stack_widget == self.Stack:
            self.update_stack()
        elif stack_widget == self.StackTrace:
            self.update_stacktrace()

    def tableWidget_StackTrace_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_StackTrace.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_StackTrace)
        menu = QMenu()
        switch_to_stack = menu.addAction(tr.FULL_STACK)
        menu.addSeparator()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_return = clipboard_menu.addAction(tr.COPY_RETURN_ADDRESS)
        copy_frame = clipboard_menu.addAction(tr.COPY_FRAME_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [clipboard_menu.menuAction()])
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        if debugcore.currentpid == -1:
            menu.clear()
            menu.addMenu(clipboard_menu)
        font_size = self.tableWidget_StackTrace.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            switch_to_stack: lambda: self.set_stack_widget(self.Stack),
            copy_return: lambda: copy_to_clipboard(selected_row, STACKTRACE_RETURN_ADDRESS_COL),
            copy_frame: lambda: copy_to_clipboard(selected_row, STACKTRACE_FRAME_ADDRESS_COL),
            refresh: self.update_stacktrace,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def update_stack(self):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        stack_info = debugcore.get_stack_info()
        self.tableWidget_Stack.setRowCount(0)
        self.tableWidget_Stack.setRowCount(len(stack_info))
        for row, item in enumerate(stack_info):
            self.tableWidget_Stack.setItem(row, STACK_POINTER_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Stack.setItem(row, STACK_VALUE_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Stack.setItem(row, STACK_POINTS_TO_COL, QTableWidgetItem(item[2]))
        self.tableWidget_Stack.resizeColumnToContents(STACK_POINTER_ADDRESS_COL)
        self.tableWidget_Stack.resizeColumnToContents(STACK_VALUE_COL)

    def tableWidget_Stack_key_press_event(self, event):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if selected_row == -1:
            actions = typedefs.KeyboardModifiersTupleDict(
                [(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stack)]
            )
        else:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_address(current_address_text)

            actions = typedefs.KeyboardModifiersTupleDict(
                [
                    (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stack),
                    (
                        QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                        lambda: self.disassemble_expression(current_address, append_to_travel_history=True),
                    ),
                    (
                        QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
                        lambda: self.hex_dump_address(int(current_address, 16)),
                    ),
                ]
            )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Stack.keyPressEvent_original(event)

    def tableWidget_Stack_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Stack.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if selected_row == -1:
            current_address = None
        else:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_address(current_address_text)
        menu = QMenu()
        switch_to_stacktrace = menu.addAction(tr.STACKTRACE)
        menu.addSeparator()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_address = clipboard_menu.addAction(tr.COPY_ADDRESS)
        copy_value = clipboard_menu.addAction(tr.COPY_VALUE)
        copy_points_to = clipboard_menu.addAction(tr.COPY_POINTS_TO)
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        show_in_disas = menu.addAction(f"{tr.DISASSEMBLE_VALUE_POINTER}[Ctrl+D]")
        show_in_hex = menu.addAction(f"{tr.HEXVIEW_VALUE_POINTER}[Ctrl+H]")
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [clipboard_menu.menuAction(), show_in_disas, show_in_hex])
        if debugcore.currentpid == -1:
            menu.clear()
            menu.addMenu(clipboard_menu)
        font_size = self.tableWidget_Stack.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            switch_to_stacktrace: lambda: self.set_stack_widget(self.StackTrace),
            copy_address: lambda: copy_to_clipboard(selected_row, STACK_POINTER_ADDRESS_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, STACK_VALUE_COL),
            copy_points_to: lambda: copy_to_clipboard(selected_row, STACK_POINTS_TO_COL),
            refresh: self.update_stack,
            show_in_disas: lambda: self.disassemble_expression(current_address, append_to_travel_history=True),
            show_in_hex: lambda: self.hex_dump_address(int(current_address, 16)),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_Stack_double_click(self, index):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if index.column() == STACK_POINTER_ADDRESS_COL:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_POINTER_ADDRESS_COL).text()
            current_address = utils.extract_address(current_address_text)
            self.hex_dump_address(int(current_address, 16))
        else:
            points_to_text = self.tableWidget_Stack.item(selected_row, STACK_POINTS_TO_COL).text()
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_address(current_address_text)
            if points_to_text.startswith("(str)"):
                self.hex_dump_address(int(current_address, 16))
            else:
                self.disassemble_expression(current_address, append_to_travel_history=True)

    def tableWidget_StackTrace_double_click(self, index):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_StackTrace)
        if index.column() == STACKTRACE_RETURN_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_RETURN_ADDRESS_COL).text()
            current_address = utils.extract_address(current_address_text)
            self.disassemble_expression(current_address, append_to_travel_history=True)
        if index.column() == STACKTRACE_FRAME_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_FRAME_ADDRESS_COL).text()
            current_address = utils.extract_address(current_address_text)
            self.hex_dump_address(int(current_address, 16))

    def tableWidget_StackTrace_key_press_event(self, event):
        if debugcore.currentpid == -1:
            return
        actions = typedefs.KeyboardModifiersTupleDict(
            [(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stacktrace)]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_StackTrace.keyPressEvent_original(event)

    def widget_Disassemble_wheel_event(self, event):
        if debugcore.currentpid == -1:
            return
        steps = event.angleDelta()
        if steps.y() > 0:
            self.tableWidget_Disassemble_scroll("previous", self.instructions_per_scroll)
        else:
            self.tableWidget_Disassemble_scroll("next", self.instructions_per_scroll)

    def disassemble_check_viewport(self, where, instruction_count):
        if debugcore.currentpid == -1:
            return
        current_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_row_height = self.tableWidget_Disassemble.rowViewportPosition(current_row)
        row_height = self.tableWidget_Disassemble.verticalHeader().defaultSectionSize()
        max_height = self.tableWidget_Disassemble.maximumViewportSize().height()
        # visible_height = max_height - row_height
        height = max_height - row_height * 3  # lets us see the next 2 instructions after the last visible row
        if current_row_height > max_height:
            last_visible_row = 0
            for row in range(self.tableWidget_Disassemble.rowCount()):
                if self.tableWidget_Disassemble.rowViewportPosition(row) > height:
                    break
                last_visible_row += 1
            current_address = utils.extract_address(
                self.tableWidget_Disassemble.item(current_row, DISAS_ADDR_COL).text()
            )
            new_address = debugcore.find_closest_instruction_address(current_address, "previous", last_visible_row)
            self.disassemble_expression(new_address)
        elif (where == "previous" and current_row == 0) or (where == "next" and current_row_height > height):
            self.tableWidget_Disassemble_scroll(where, instruction_count)

    def tableWidget_Disassemble_scroll(self, where, instruction_count):
        if debugcore.currentpid == -1:
            return
        current_address = self.disassemble_currently_displayed_address
        new_address = debugcore.find_closest_instruction_address(current_address, where, instruction_count)
        self.disassemble_expression(new_address)

    def widget_HexView_wheel_event(self, event):
        if debugcore.currentpid == -1:
            return
        steps = event.angleDelta()
        current_address = self.hex_model.current_address
        if steps.y() > 0:
            next_address = current_address - self.bytes_per_scroll
        else:
            next_address = current_address + self.bytes_per_scroll
        self.hex_dump_address(next_address)

    def widget_HexView_key_press_event(self, event):
        if debugcore.currentpid == -1:
            return
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G), self.exec_hex_view_go_to_dialog),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                    lambda: self.disassemble_expression(
                        hex(self.hex_selection_address_begin), append_to_travel_history=True
                    ),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_A),
                    self.exec_hex_view_add_address_dialog,
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C), self.copy_hex_view_selection),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_hex_view),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.hex_view_scroll_up),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.hex_view_scroll_down),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.widget_HexView.keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space),
                    lambda: self.follow_instruction(selected_row),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_E),
                    lambda: self.exec_examine_referrers_widget(current_address_text),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G),
                    self.exec_disassemble_go_to_dialog,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
                    lambda: self.hex_dump_address(current_address_int),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
                    lambda: self.bookmark_address(current_address_int),
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D), self.dissect_current_region),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_T),
                    self.exec_trace_instructions_dialog,
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_disassemble_view),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down),
                    lambda: self.disassemble_check_viewport("next", 1),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up),
                    lambda: self.disassemble_check_viewport("previous", 1),
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.disassemble_scroll_up),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.disassemble_scroll_down),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Disassemble.keyPressEvent_original(event)

    def tableWidget_Disassemble_item_double_clicked(self, index):
        if debugcore.currentpid == -1:
            return
        if index.column() == DISAS_COMMENT_COL:
            selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = int(utils.extract_address(current_address_text), 16)
            if current_address in self.tableWidget_Disassemble.bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def tableWidget_Disassemble_item_selection_changed(self):
        if debugcore.currentpid == -1:
            return
        try:
            selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
            selected_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            self.disassemble_last_selected_address_int = int(utils.extract_address(selected_address_text), 16)
        except (TypeError, ValueError, AttributeError):
            pass

    # Search the item in given row for location changing instructions
    # Go to the address pointed by that instruction if it contains any
    def follow_instruction(self, selected_row):
        if debugcore.currentpid == -1:
            return
        address = utils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        )
        if address:
            self.disassemble_expression(address, append_to_travel_history=True)

    def disassemble_go_back(self):
        if debugcore.currentpid == -1:
            return
        if self.tableWidget_Disassemble.travel_history:
            last_location = self.tableWidget_Disassemble.travel_history[-1]
            self.disassemble_expression(last_location)
            self.tableWidget_Disassemble.travel_history.pop()

    def tableWidget_Disassemble_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Disassemble.item(row, column).text())

        def copy_all_columns(row):
            copied_string = ""
            for column in range(self.tableWidget_Disassemble.columnCount()):
                copied_string += self.tableWidget_Disassemble.item(row, column).text() + "\t"
            app.clipboard().setText(copied_string)

        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        back = menu.addAction(tr.BACK)
        show_in_hex_view = menu.addAction(f"{tr.HEXVIEW_ADDRESS}[Ctrl+H]")
        menu.addSeparator()
        followable = utils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        )
        follow = menu.addAction(f"{tr.FOLLOW}[Space]")
        if not followable:
            guiutils.delete_menu_entries(menu, [follow])
        examine_referrers = menu.addAction(f"{tr.EXAMINE_REFERRERS}[Ctrl+E]")
        if not guiutils.contains_reference_mark(current_address_text):
            guiutils.delete_menu_entries(menu, [examine_referrers])
        bookmark = menu.addAction(f"{tr.BOOKMARK_ADDRESS}[Ctrl+B]")
        delete_bookmark = menu.addAction(tr.DELETE_BOOKMARK)
        change_comment = menu.addAction(tr.CHANGE_COMMENT)
        is_bookmarked = current_address_int in self.tableWidget_Disassemble.bookmarks
        if not is_bookmarked:
            guiutils.delete_menu_entries(menu, [delete_bookmark, change_comment])
        else:
            guiutils.delete_menu_entries(menu, [bookmark])
        go_to_bookmark = menu.addMenu(tr.GO_TO_BOOKMARK_ADDRESS)
        address_list = [hex(address) for address in self.tableWidget_Disassemble.bookmarks.keys()]
        bookmark_actions = [go_to_bookmark.addAction(item.all) for item in debugcore.examine_expressions(address_list)]
        menu.addSeparator()
        toggle_breakpoint = menu.addAction(f"{tr.TOGGLE_BREAKPOINT}[F5]")
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        if not debugcore.get_breakpoints_in_range(current_address_int):
            guiutils.delete_menu_entries(menu, [add_condition])
        menu.addSeparator()
        edit_instruction = menu.addAction(tr.EDIT_INSTRUCTION)
        nop_instruction = menu.addAction(tr.REPLACE_WITH_NOPS)
        if self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text() == "90":
            guiutils.delete_menu_entries(menu, [nop_instruction])
        menu.addSeparator()
        track_breakpoint = menu.addAction(tr.WHAT_ACCESSES_INSTRUCTION)
        trace_instructions = menu.addAction(f"{tr.TRACE_INSTRUCTION}[Ctrl+T]")
        dissect_region = menu.addAction(f"{tr.DISSECT_REGION}[Ctrl+D]")
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        if debugcore.currentpid == -1:
            menu.clear()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_address = clipboard_menu.addAction(tr.COPY_ADDRESS)
        copy_bytes = clipboard_menu.addAction(tr.COPY_BYTES)
        copy_opcode = clipboard_menu.addAction(tr.COPY_OPCODE)
        copy_comment = clipboard_menu.addAction(tr.COPY_COMMENT)
        copy_all = clipboard_menu.addAction(tr.COPY_ALL)
        font_size = self.tableWidget_Disassemble.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            go_to: self.exec_disassemble_go_to_dialog,
            back: self.disassemble_go_back,
            show_in_hex_view: lambda: self.hex_dump_address(current_address_int),
            follow: lambda: self.follow_instruction(selected_row),
            examine_referrers: lambda: self.exec_examine_referrers_widget(current_address_text),
            bookmark: lambda: self.bookmark_address(current_address_int),
            delete_bookmark: lambda: self.delete_bookmark(current_address_int),
            change_comment: lambda: self.change_bookmark_comment(current_address_int),
            toggle_breakpoint: self.toggle_breakpoint,
            add_condition: lambda: self.add_breakpoint_condition(current_address_int),
            edit_instruction: self.edit_instruction,
            nop_instruction: self.nop_instruction,
            track_breakpoint: self.exec_track_breakpoint_dialog,
            trace_instructions: self.exec_trace_instructions_dialog,
            dissect_region: self.dissect_current_region,
            refresh: self.refresh_disassemble_view,
            copy_address: lambda: copy_to_clipboard(selected_row, DISAS_ADDR_COL),
            copy_bytes: lambda: copy_to_clipboard(selected_row, DISAS_BYTES_COL),
            copy_opcode: lambda: copy_to_clipboard(selected_row, DISAS_OPCODES_COL),
            copy_comment: lambda: copy_to_clipboard(selected_row, DISAS_COMMENT_COL),
            copy_all: lambda: copy_all_columns(selected_row),
        }
        try:
            actions[action]()
        except KeyError:
            pass
        if action in bookmark_actions:
            self.disassemble_expression(utils.extract_address(action.text()), append_to_travel_history=True)

    def dissect_current_region(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        dissect_code_dialog = DissectCodeDialogForm(self, int(current_address, 16))
        dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def exec_examine_referrers_widget(self, current_address_text):
        if debugcore.currentpid == -1:
            return
        if not guiutils.contains_reference_mark(current_address_text):
            return
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        examine_referrers_widget = ExamineReferrersWidgetForm(self, current_address_int)
        examine_referrers_widget.show()

    def exec_trace_instructions_dialog(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        TraceInstructionsWindowForm(self, current_address)

    def exec_track_breakpoint_dialog(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_instruction = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        register_expression_dialog = InputDialogForm(self, [(tr.ENTER_TRACK_BP_EXPRESSION, "")])
        if register_expression_dialog.exec():
            exp = register_expression_dialog.get_values()
            TrackBreakpointWidgetForm(self, current_address, current_instruction, exp)

    def exec_disassemble_go_to_dialog(self):
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)

        go_to_dialog = InputDialogForm(self, [(tr.ENTER_EXPRESSION, current_address)])
        if go_to_dialog.exec():
            traveled_exp = go_to_dialog.get_values()
            self.disassemble_expression(traveled_exp, append_to_travel_history=True)

    def bookmark_address(self, int_address):
        if debugcore.currentpid == -1:
            return
        if int_address in self.tableWidget_Disassemble.bookmarks:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.ALREADY_BOOKMARKED)
            return
        comment_dialog = InputDialogForm(self, [(tr.ENTER_BOOKMARK_COMMENT, "")])
        if comment_dialog.exec():
            comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = comment
        self.refresh_disassemble_view()

    def change_bookmark_comment(self, int_address):
        if debugcore.currentpid == -1:
            return
        current_comment = self.tableWidget_Disassemble.bookmarks[int_address]
        comment_dialog = InputDialogForm(self, [(tr.ENTER_BOOKMARK_COMMENT, current_comment)])
        if comment_dialog.exec():
            new_comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = new_comment
        self.refresh_disassemble_view()

    def delete_bookmark(self, int_address):
        if debugcore.currentpid == -1:
            return
        if int_address in self.tableWidget_Disassemble.bookmarks:
            del self.tableWidget_Disassemble.bookmarks[int_address]
            self.refresh_disassemble_view()

    def actionBookmarks_triggered(self):
        bookmark_widget = BookmarkWidgetForm(self)
        bookmark_widget.show()
        bookmark_widget.activateWindow()

    def actionStackTrace_Info_triggered(self):
        if debugcore.currentpid == -1:
            return
        self.stacktrace_info_widget.update_stacktrace()
        guiutils.center_to_parent(self.stacktrace_info_widget)
        self.stacktrace_info_widget.show()
        self.stacktrace_info_widget.activateWindow()

    def actionBreakpoints_triggered(self):
        if debugcore.currentpid == -1:
            return
        breakpoint_widget = BreakpointInfoWidgetForm(self)
        breakpoint_widget.show()
        breakpoint_widget.activateWindow()

    def actionFunctions_triggered(self):
        if debugcore.currentpid == -1:
            return
        functions_info_widget = FunctionsInfoWidgetForm(self)
        functions_info_widget.show()

    def actionGDB_Log_File_triggered(self):
        log_file_widget = LogFileWidgetForm(self)
        log_file_widget.showMaximized()

    def actionMemory_Regions_triggered(self):
        if debugcore.currentpid == -1:
            return
        memory_regions_widget = MemoryRegionsWidgetForm(self)
        memory_regions_widget.show()

    def actionRestore_Instructions_triggered(self):
        if debugcore.currentpid == -1:
            return
        restore_instructions_widget = RestoreInstructionsWidgetForm(self)
        restore_instructions_widget.show()
        restore_instructions_widget.activateWindow()

    def actionReferenced_Strings_triggered(self):
        if debugcore.currentpid == -1:
            return
        ref_str_widget = ReferencedStringsWidgetForm(self)
        ref_str_widget.show()

    def actionReferenced_Calls_triggered(self):
        if debugcore.currentpid == -1:
            return
        ref_call_widget = ReferencedCallsWidgetForm(self)
        ref_call_widget.show()

    def actionInject_so_file_triggered(self):
        if debugcore.currentpid == -1:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_SO_FILE, "", tr.SHARED_OBJECT_TYPE)
        if file_path:
            if debugcore.inject_with_dlopen_call(file_path):
                QMessageBox.information(self, tr.SUCCESS, tr.FILE_INJECTED)
            else:
                QMessageBox.information(self, tr.ERROR, tr.FILE_INJECT_FAILED)

    def actionCall_Function_triggered(self):
        if debugcore.currentpid == -1:
            return
        call_dialog = InputDialogForm(self, [(tr.ENTER_CALL_EXPRESSION, "")])
        if call_dialog.exec():
            result = debugcore.call_function_from_inferior(call_dialog.get_values())
            if result[0]:
                QMessageBox.information(self, tr.SUCCESS, result[0] + " = " + result[1])
            else:
                QMessageBox.information(self, tr.ERROR, tr.CALL_EXPRESSION_FAILED.format(call_dialog.get_values()))

    def actionSearch_Opcode_triggered(self):
        if debugcore.currentpid == -1:
            return
        start_address = int(self.disassemble_currently_displayed_address, 16)
        end_address = start_address + 0x30000
        search_opcode_widget = SearchOpcodeWidgetForm(self, hex(start_address), hex(end_address))
        search_opcode_widget.show()

    def actionDissect_Code_triggered(self):
        if debugcore.currentpid == -1:
            return
        dissect_code_dialog = DissectCodeDialogForm(self)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def actionlibpince_triggered(self):
        libpince_widget = LibpinceReferenceWidgetForm(self)
        libpince_widget.showMaximized()

    def pushButton_ShowFloatRegisters_clicked(self):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        self.float_registers_widget.update_registers()
        guiutils.center_to_parent(self.float_registers_widget)
        self.float_registers_widget.show()
        self.float_registers_widget.activateWindow()


class BookmarkWidgetForm(QWidget, BookmarkWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget.contextMenuEvent = self.listWidget_context_menu_event
        self.listWidget.currentRowChanged.connect(self.change_display)
        self.listWidget.itemDoubleClicked.connect(self.listWidget_item_double_clicked)
        self.shortcut_delete = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete.activated.connect(self.delete_record)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        self.refresh_table()
        guiutils.center_to_parent(self)

    def refresh_table(self):
        self.listWidget.clear()
        address_list = [hex(address) for address in self.parent().tableWidget_Disassemble.bookmarks.keys()]
        if debugcore.currentpid == -1:
            self.listWidget.addItems(address_list)
        else:
            self.listWidget.addItems([item.all for item in debugcore.examine_expressions(address_list)])

    def change_display(self, row):
        current_address = utils.extract_address(self.listWidget.item(row).text())
        if debugcore.currentpid == -1:
            self.lineEdit_Info.clear()
        else:
            self.lineEdit_Info.setText(debugcore.get_address_info(current_address))
        self.lineEdit_Comment.setText(self.parent().tableWidget_Disassemble.bookmarks[int(current_address, 16)])

    def listWidget_item_double_clicked(self, item):
        self.parent().disassemble_expression(utils.extract_address(item.text()), append_to_travel_history=True)

    def exec_add_entry_dialog(self):
        entry_dialog = InputDialogForm(self, [(tr.ENTER_EXPRESSION, "")])
        if entry_dialog.exec():
            text = entry_dialog.get_values()
            address = debugcore.examine_expression(text).address
            if not address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_EXPRESSION)
                return
            self.parent().bookmark_address(int(address, 16))
            self.refresh_table()

    def exec_change_comment_dialog(self, current_address):
        self.parent().change_bookmark_comment(current_address)
        self.refresh_table()

    def listWidget_context_menu_event(self, event):
        current_item = guiutils.get_current_item(self.listWidget)
        if current_item:
            current_address = int(utils.extract_address(current_item.text()), 16)
            if current_address not in self.parent().tableWidget_Disassemble.bookmarks:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_ENTRY)
                self.refresh_table()
                return
        else:
            current_address = None
        menu = QMenu()
        add_entry = menu.addAction(tr.ADD_ENTRY)
        change_comment = menu.addAction(tr.CHANGE_COMMENT)
        delete_record = menu.addAction(f"{tr.DELETE}[Del]")
        if current_item is None:
            guiutils.delete_menu_entries(menu, [change_comment, delete_record])
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.listWidget.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            add_entry: self.exec_add_entry_dialog,
            change_comment: lambda: self.exec_change_comment_dialog(current_address),
            delete_record: self.delete_record,
            refresh: self.refresh_table,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def delete_record(self):
        current_item = guiutils.get_current_item(self.listWidget)
        if not current_item:
            return
        current_address = int(utils.extract_address(current_item.text()), 16)
        self.parent().delete_bookmark(current_address)
        self.refresh_table()


class FloatRegisterWidgetForm(QTabWidget, FloatRegisterWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_FPU.itemDoubleClicked.connect(self.set_register)
        self.tableWidget_XMM.itemDoubleClicked.connect(self.set_register)

    def update_registers(self):
        self.tableWidget_FPU.setRowCount(0)
        self.tableWidget_FPU.setRowCount(8)
        self.tableWidget_XMM.setRowCount(0)
        self.tableWidget_XMM.setRowCount(8)
        float_registers = debugcore.read_float_registers()
        for row, (st, xmm) in enumerate(zip(typedefs.REGISTERS.FLOAT.ST, typedefs.REGISTERS.FLOAT.XMM)):
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(st))
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(float_registers[st]))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(xmm))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(float_registers[xmm]))

    def set_register(self, index):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        current_row = index.row()
        if self.currentWidget() == self.FPU:
            current_table_widget = self.tableWidget_FPU
        elif self.currentWidget() == self.XMM:
            current_table_widget = self.tableWidget_XMM
        else:
            raise Exception("Current widget is invalid: " + str(self.currentWidget().objectName()))
        current_register = current_table_widget.item(current_row, FLOAT_REGISTERS_NAME_COL).text()
        current_value = current_table_widget.item(current_row, FLOAT_REGISTERS_VALUE_COL).text()
        label_text = tr.ENTER_REGISTER_VALUE.format(current_register.upper())
        register_dialog = InputDialogForm(self, [(label_text, current_value)])
        if register_dialog.exec():
            if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                return
            if self.currentWidget() == self.XMM:
                current_register += ".v4_float"
            debugcore.set_convenience_variable(current_register, register_dialog.get_values())
            self.update_registers()


class StackTraceInfoWidgetForm(QWidget, StackTraceInfoWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget_ReturnAddresses.currentRowChanged.connect(self.update_frame_info)

    def update_stacktrace(self):
        self.listWidget_ReturnAddresses.clear()
        if debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        return_addresses = debugcore.get_stack_frame_return_addresses()
        self.listWidget_ReturnAddresses.addItems(return_addresses)

    def update_frame_info(self, index):
        if debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            self.textBrowser_Info.setText(tr.PROCESS_RUNNING)
            return
        frame_info = debugcore.get_stack_frame_info(index)
        self.textBrowser_Info.setText(frame_info)


class RestoreInstructionsWidgetForm(QWidget, RestoreInstructionsWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Instructions.keyPressEvent_original = self.tableWidget_Instructions.keyPressEvent
        self.tableWidget_Instructions.keyPressEvent = self.tableWidget_Instructions_key_press_event
        self.tableWidget_Instructions.contextMenuEvent = self.tableWidget_Instructions_context_menu_event
        self.tableWidget_Instructions.itemDoubleClicked.connect(self.tableWidget_Instructions_double_clicked)
        self.refresh()
        guiutils.center_to_parent(self)

    def tableWidget_Instructions_context_menu_event(self, event):
        selected_row = guiutils.get_current_row(self.tableWidget_Instructions)
        menu = QMenu()
        restore_instruction = menu.addAction(tr.RESTORE_INSTRUCTION)
        if selected_row != -1:
            selected_address_text = self.tableWidget_Instructions.item(selected_row, INSTR_ADDR_COL).text()
            selected_address = utils.extract_address(selected_address_text)
            selected_address_int = int(selected_address, 16)
        else:
            guiutils.delete_menu_entries(menu, [restore_instruction])
            selected_address_int = None
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.tableWidget_Instructions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {restore_instruction: lambda: self.restore_instruction(selected_address_int), refresh: self.refresh}
        try:
            actions[action]()
        except KeyError:
            pass

    def restore_instruction(self, selected_address_int):
        debugcore.restore_instruction(selected_address_int)
        self.refresh_all()

    def refresh(self):
        modified_instructions = debugcore.get_modified_instructions()
        self.tableWidget_Instructions.setRowCount(len(modified_instructions))
        for row, (address, aob) in enumerate(modified_instructions.items()):
            self.tableWidget_Instructions.setItem(row, INSTR_ADDR_COL, QTableWidgetItem(hex(address)))
            self.tableWidget_Instructions.setItem(row, INSTR_AOB_COL, QTableWidgetItem(aob))
            instr_name = utils.get_opcodes(address, aob, debugcore.get_inferior_arch())
            if not instr_name:
                instr_name = "??"
            self.tableWidget_Instructions.setItem(row, INSTR_NAME_COL, QTableWidgetItem(instr_name))
        guiutils.resize_to_contents(self.tableWidget_Instructions)

    def refresh_all(self):
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def tableWidget_Instructions_key_press_event(self, event):
        actions = typedefs.KeyboardModifiersTupleDict(
            [(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh)]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Instructions.keyPressEvent_original(event)

    def tableWidget_Instructions_double_clicked(self, index):
        current_address_text = self.tableWidget_Instructions.item(index.row(), INSTR_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        self.parent().disassemble_expression(current_address, append_to_travel_history=True)


class BreakpointInfoWidgetForm(QTabWidget, BreakpointInfoWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_BreakpointInfo.contextMenuEvent = self.tableWidget_BreakpointInfo_context_menu_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_BreakpointInfo.keyPressEvent_original = self.tableWidget_BreakpointInfo.keyPressEvent
        self.tableWidget_BreakpointInfo.keyPressEvent = self.tableWidget_BreakpointInfo_key_press_event
        self.tableWidget_BreakpointInfo.itemDoubleClicked.connect(self.tableWidget_BreakpointInfo_double_clicked)
        self.refresh()
        guiutils.center_to_parent(self)

    def refresh(self):
        break_info = debugcore.get_breakpoint_info()
        self.tableWidget_BreakpointInfo.setRowCount(0)
        self.tableWidget_BreakpointInfo.setRowCount(len(break_info))
        for row, item in enumerate(break_info):
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_NUM_COL, QTableWidgetItem(item.number))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_TYPE_COL, QTableWidgetItem(item.breakpoint_type))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_DISP_COL, QTableWidgetItem(item.disp))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ENABLED_COL, QTableWidgetItem(item.enabled))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ADDR_COL, QTableWidgetItem(item.address))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_SIZE_COL, QTableWidgetItem(str(item.size)))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ON_HIT_COL, QTableWidgetItem(item.on_hit))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_HIT_COUNT_COL, QTableWidgetItem(item.hit_count))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_COND_COL, QTableWidgetItem(item.condition))
        guiutils.resize_to_contents(self.tableWidget_BreakpointInfo)
        self.textBrowser_BreakpointInfo.clear()
        self.textBrowser_BreakpointInfo.setText(debugcore.send_command("info break", cli_output=True))

    def delete_breakpoint(self, address):
        if address is not None:
            debugcore.delete_breakpoint(address)
            self.refresh_all()

    def tableWidget_BreakpointInfo_key_press_event(self, event):
        selected_row = guiutils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = utils.extract_address(current_address_text)
        else:
            current_address = None

        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete),
                    lambda: self.delete_breakpoint(current_address),
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_BreakpointInfo.keyPressEvent_original(event)

    def exec_enable_count_dialog(self, current_address):
        hit_count_dialog = InputDialogForm(self, [(tr.ENTER_HIT_COUNT.format(1), "")])
        if hit_count_dialog.exec():
            count = hit_count_dialog.get_values()
            try:
                count = int(count)
            except ValueError:
                QMessageBox.information(self, tr.ERROR, tr.HIT_COUNT_ASSERT_INT)
            else:
                if count < 1:
                    QMessageBox.information(self, tr.ERROR, tr.HIT_COUNT_ASSERT_LT.format(1))
                else:
                    debugcore.modify_breakpoint(current_address, typedefs.BREAKPOINT_MODIFY.ENABLE_COUNT, count=count)

    def tableWidget_BreakpointInfo_context_menu_event(self, event):
        selected_row = guiutils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = utils.extract_address(current_address_text)
            current_address_int = int(current_address, 16)
        else:
            current_address = None
            current_address_int = None

        menu = QMenu()
        change_condition = menu.addAction(tr.CHANGE_CONDITION)
        enable = menu.addAction(tr.ENABLE)
        disable = menu.addAction(tr.DISABLE)
        enable_once = menu.addAction(tr.DISABLE_AFTER_HIT)
        enable_count = menu.addAction(tr.DISABLE_AFTER_COUNT)
        enable_delete = menu.addAction(tr.DELETE_AFTER_HIT)
        menu.addSeparator()
        delete_breakpoint = menu.addAction(f"{tr.DELETE}[Del]")
        menu.addSeparator()
        if current_address is None:
            deletion_list = [
                change_condition,
                enable,
                disable,
                enable_once,
                enable_count,
                enable_delete,
                delete_breakpoint,
            ]
            guiutils.delete_menu_entries(menu, deletion_list)
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.tableWidget_BreakpointInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            change_condition: lambda: self.parent().add_breakpoint_condition(current_address_int),
            enable: lambda: debugcore.modify_breakpoint(current_address, typedefs.BREAKPOINT_MODIFY.ENABLE),
            disable: lambda: debugcore.modify_breakpoint(current_address, typedefs.BREAKPOINT_MODIFY.DISABLE),
            enable_once: lambda: debugcore.modify_breakpoint(current_address, typedefs.BREAKPOINT_MODIFY.ENABLE_ONCE),
            enable_count: lambda: self.exec_enable_count_dialog(current_address),
            enable_delete: lambda: debugcore.modify_breakpoint(
                current_address, typedefs.BREAKPOINT_MODIFY.ENABLE_DELETE
            ),
            delete_breakpoint: lambda: debugcore.delete_breakpoint(current_address),
            refresh: self.refresh,
        }
        try:
            actions[action]()
        except KeyError:
            pass
        if action != -1 and action is not None:
            self.refresh_all()

    def refresh_all(self):
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def tableWidget_BreakpointInfo_double_clicked(self, index):
        current_address_text = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_ADDR_COL).text()
        current_address = utils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        if index.column() == BREAK_COND_COL:
            self.parent().add_breakpoint_condition(current_address_int)
            self.refresh_all()
        else:
            current_breakpoint_type = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_TYPE_COL).text()
            if "breakpoint" in current_breakpoint_type:
                self.parent().disassemble_expression(current_address, append_to_travel_history=True)
            else:
                self.parent().hex_dump_address(current_address_int)


class TrackWatchpointWidgetForm(QWidget, TrackWatchpointWidget):
    def __init__(self, parent, address, length, watchpoint_type):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.update_timer = QTimer(timeout=self.update_list)
        self.stopped = False
        self.address = address
        self.info = {}
        self.last_selected_row = 0
        if watchpoint_type == typedefs.WATCHPOINT_TYPE.WRITE_ONLY:
            string = tr.OPCODE_WRITING_TO.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.READ_ONLY:
            string = tr.OPCODE_READING_FROM.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.BOTH:
            string = tr.OPCODE_ACCESSING_TO.format(address)
        else:
            raise Exception("Watchpoint type is invalid: " + str(watchpoint_type))
        self.setWindowTitle(string)
        guiutils.center_to_parent(self)  # Called before the QMessageBox to center its position properly
        self.breakpoints = debugcore.track_watchpoint(address, length, watchpoint_type)
        if not self.breakpoints:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_WATCHPOINT_FAILED.format(address))
            self.close()
            return
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.pushButton_Refresh.clicked.connect(self.update_list)
        self.tableWidget_Opcodes.itemDoubleClicked.connect(self.tableWidget_Opcodes_item_double_clicked)
        self.tableWidget_Opcodes.selectionModel().currentChanged.connect(self.tableWidget_Opcodes_current_changed)
        self.update_timer.start(100)
        self.show()

    def update_list(self):
        info = debugcore.get_track_watchpoint_info(self.breakpoints)
        if not info or self.info == info:
            return
        self.info = info
        self.tableWidget_Opcodes.setRowCount(0)
        self.tableWidget_Opcodes.setRowCount(len(info))
        for row, key in enumerate(info):
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_COUNT_COL, QTableWidgetItem(str(info[key][0])))
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_ADDR_COL, QTableWidgetItem(info[key][1]))
        guiutils.resize_to_contents(self.tableWidget_Opcodes)
        self.tableWidget_Opcodes.selectRow(self.last_selected_row)

    def tableWidget_Opcodes_current_changed(self, QModelIndex_current):
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

        info = self.info
        key_list = list(info)
        key = key_list[self.last_selected_row]
        self.textBrowser_Info.clear()
        for item in info[key][2]:
            self.textBrowser_Info.append(item + "=" + info[key][2][item])
        self.textBrowser_Info.append(" ")
        for item in info[key][3]:
            self.textBrowser_Info.append(item + "=" + info[key][3][item])
        self.textBrowser_Info.verticalScrollBar().setValue(self.textBrowser_Info.verticalScrollBar().minimum())
        self.textBrowser_Disassemble.setPlainText(info[key][4])

    def tableWidget_Opcodes_item_double_clicked(self, index):
        self.parent().memory_view_window.disassemble_expression(
            self.tableWidget_Opcodes.item(index.row(), TRACK_WATCHPOINT_ADDR_COL).text(), append_to_travel_history=True
        )
        self.parent().memory_view_window.show()
        self.parent().memory_view_window.activateWindow()

    def pushButton_Stop_clicked(self):
        if self.stopped:
            self.close()
            return
        if not debugcore.delete_breakpoint(self.address):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_WATCHPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)

    def closeEvent(self, event: QCloseEvent):
        self.update_timer.stop()
        if self.breakpoints:
            if not self.stopped:
                debugcore.delete_breakpoint(self.address)
            watchpoint_file = utils.get_track_watchpoint_file(debugcore.currentpid, self.breakpoints)
            if os.path.exists(watchpoint_file):
                os.remove(watchpoint_file)
        super().closeEvent(event)


class TrackBreakpointWidgetForm(QWidget, TrackBreakpointWidget):
    def __init__(self, parent, address, instruction, register_expressions):
        super().__init__(parent)
        self.setupUi(self)
        self.update_list_timer = QTimer(timeout=self.update_list)
        self.update_values_timer = QTimer(timeout=self.update_values)
        self.stopped = False
        self.address = address
        self.info = {}
        self.last_selected_row = 0
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(tr.ACCESSED_BY_INSTRUCTION.format(instruction))
        guiutils.center_to_parent(self)  # Called before the QMessageBox to center its position properly
        self.breakpoint = debugcore.track_breakpoint(address, register_expressions)
        if not self.breakpoint:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_BREAKPOINT_FAILED.format(address))
            self.close()
            return
        guiutils.fill_value_combobox(self.comboBox_ValueType)
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.tableWidget_TrackInfo.itemDoubleClicked.connect(self.tableWidget_TrackInfo_item_double_clicked)
        self.tableWidget_TrackInfo.selectionModel().currentChanged.connect(self.tableWidget_TrackInfo_current_changed)
        self.comboBox_ValueType.currentIndexChanged.connect(self.update_values)
        self.update_list_timer.start(100)
        self.update_values_timer.start(500)
        self.parent().refresh_disassemble_view()
        self.show()

    def update_list(self):
        info = debugcore.get_track_breakpoint_info(self.breakpoint)
        if not info:
            return
        if info == self.info:
            return
        self.info = info
        self.tableWidget_TrackInfo.setRowCount(0)
        for register_expression in info:
            for row, address in enumerate(info[register_expression]):
                self.tableWidget_TrackInfo.setRowCount(self.tableWidget_TrackInfo.rowCount() + 1)
                self.tableWidget_TrackInfo.setItem(
                    row, TRACK_BREAKPOINT_COUNT_COL, QTableWidgetItem(str(info[register_expression][address]))
                )
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_ADDR_COL, QTableWidgetItem(address))
                self.tableWidget_TrackInfo.setItem(
                    row, TRACK_BREAKPOINT_SOURCE_COL, QTableWidgetItem("[" + register_expression + "]")
                )
        self.update_values()

    def update_values(self):
        mem_handle = debugcore.memory_handle()
        value_type = self.comboBox_ValueType.currentIndex()
        for row in range(self.tableWidget_TrackInfo.rowCount()):
            address = self.tableWidget_TrackInfo.item(row, TRACK_BREAKPOINT_ADDR_COL).text()
            value = debugcore.read_memory(address, value_type, 10, mem_handle=mem_handle)
            value = "" if value is None else str(value)
            self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_VALUE_COL, QTableWidgetItem(value))
        guiutils.resize_to_contents(self.tableWidget_TrackInfo)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def tableWidget_TrackInfo_current_changed(self, QModelIndex_current):
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

    def tableWidget_TrackInfo_item_double_clicked(self, index):
        address = self.tableWidget_TrackInfo.item(index.row(), TRACK_BREAKPOINT_ADDR_COL).text()
        vt = typedefs.ValueType(self.comboBox_ValueType.currentIndex())
        self.parent().parent().add_entry_to_addresstable(tr.ACCESSED_BY.format(self.address), address, vt)
        self.parent().parent().update_address_table()

    def pushButton_Stop_clicked(self):
        if self.stopped:
            self.close()
            return
        if not debugcore.delete_breakpoint(self.address):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_BREAKPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)
        self.parent().refresh_disassemble_view()

    def closeEvent(self, event: QCloseEvent):
        self.update_list_timer.stop()
        self.update_values_timer.stop()
        if self.breakpoint:
            if not self.stopped:
                debugcore.delete_breakpoint(self.address)
            breakpoint_file = utils.get_track_breakpoint_file(debugcore.currentpid, self.breakpoint)
            if os.path.exists(breakpoint_file):
                os.remove(breakpoint_file)
        self.parent().refresh_disassemble_view()
        super().closeEvent(event)


class TraceInstructionsPromptDialogForm(QDialog, TraceInstructionsPromptDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)

    def get_values(self):
        max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        trigger_condition = self.lineEdit_TriggerCondition.text()
        stop_condition = self.lineEdit_StopCondition.text()
        if self.checkBox_StepOver.isChecked():
            step_mode = typedefs.STEP_MODE.STEP_OVER
        else:
            step_mode = typedefs.STEP_MODE.SINGLE_STEP
        stop_after_trace = self.checkBox_StopAfterTrace.isChecked()
        collect_registers = self.checkBox_CollectRegisters.isChecked()
        return max_trace_count, trigger_condition, stop_condition, step_mode, stop_after_trace, collect_registers

    def accept(self):
        if int(self.lineEdit_MaxTraceCount.text()) >= 1:
            super().accept()
        else:
            QMessageBox.information(self, tr.ERROR, tr.MAX_TRACE_COUNT_ASSERT_GT.format(1))


class TraceInstructionsWaitWidgetForm(QWidget, TraceInstructionsWaitWidget):
    widget_closed = pyqtSignal()

    def __init__(self, parent, address: str, tracer: debugcore.Tracer):
        super().__init__(parent)
        self.setupUi(self)
        self.status_to_text = {
            typedefs.TRACE_STATUS.IDLE: tr.WAITING_FOR_BREAKPOINT,
            typedefs.TRACE_STATUS.FINISHED: tr.TRACING_COMPLETED,
        }
        self.setWindowFlags(Qt.WindowType.Window)
        self.address = address
        self.tracer = tracer
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/TraceInstructionsWaitWidget/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(215, 100))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.pushButton_Cancel.clicked.connect(self.close)
        tracer_thread = Worker(tracer.tracer_loop)
        tracer_thread.signals.finished.connect(self.close)
        threadpool.start(tracer_thread)
        self.status_timer = QTimer()
        self.status_timer.setInterval(50)
        self.status_timer.timeout.connect(self.change_status)
        self.status_timer.start()
        guiutils.center_to_parent(self)

    def change_status(self):
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.label_StatusText.setText(f"{self.tracer.current_trace_count} / {self.tracer.max_trace_count}")
        else:
            self.label_StatusText.setText(self.status_to_text[self.tracer.trace_status])
        app.processEvents()

    def closeEvent(self, event: QCloseEvent):
        self.status_timer.stop()
        self.label_StatusText.setText(tr.TRACING_COMPLETED)
        self.pushButton_Cancel.setVisible(False)
        self.adjustSize()
        app.processEvents()
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.tracer.cancel_trace()
            while self.tracer.trace_status != typedefs.TRACE_STATUS.FINISHED:
                sleep(0.1)
                app.processEvents()
        self.widget_closed.emit()
        super().closeEvent(event)


class TraceInstructionsWindowForm(QMainWindow, TraceInstructionsWindow):
    def __init__(self, parent, address="", prompt_dialog=True):
        super().__init__(parent)
        self.setupUi(self)
        self.address = address
        self.tracer = debugcore.Tracer()
        self.treeWidget_InstructionInfo.currentItemChanged.connect(self.display_collected_data)
        self.treeWidget_InstructionInfo.itemDoubleClicked.connect(self.treeWidget_InstructionInfo_item_double_clicked)
        self.treeWidget_InstructionInfo.contextMenuEvent = self.treeWidget_InstructionInfo_context_menu_event
        self.actionOpen.triggered.connect(self.load_file)
        self.actionSave.triggered.connect(self.save_file)
        self.splitter.setStretchFactor(0, 1)
        guiutils.center_to_parent(self)
        if not prompt_dialog:
            self.showMaximized()
            return
        prompt_dialog = TraceInstructionsPromptDialogForm(self)
        if prompt_dialog.exec():
            params = (address,) + prompt_dialog.get_values()
            breakpoint = self.tracer.set_breakpoint(*params)
            if not breakpoint:
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(address))
                self.close()
                return
            self.showMaximized()
            self.wait_dialog = TraceInstructionsWaitWidgetForm(self, address, self.tracer)
            self.wait_dialog.widget_closed.connect(self.show_trace_info)
            self.wait_dialog.show()
        else:
            self.close()

    def display_collected_data(self, QTreeWidgetItem_current):
        self.textBrowser_RegisterInfo.clear()
        current_dict = QTreeWidgetItem_current.trace_data[1]
        if current_dict:
            for key in current_dict:
                self.textBrowser_RegisterInfo.append(str(key) + " = " + str(current_dict[key]))
            self.textBrowser_RegisterInfo.verticalScrollBar().setValue(
                self.textBrowser_RegisterInfo.verticalScrollBar().minimum()
            )

    def show_trace_info(self):
        self.treeWidget_InstructionInfo.setStyleSheet("QTreeWidget::item{ height: 16px; }")
        parent = QTreeWidgetItem(self.treeWidget_InstructionInfo)
        self.treeWidget_InstructionInfo.setRootIndex(self.treeWidget_InstructionInfo.indexFromItem(parent))
        trace_tree, current_root_index = copy.deepcopy(self.tracer.trace_data)
        while current_root_index is not None:
            try:
                current_index = trace_tree[current_root_index][2][0]  # Get the first child
                current_item = trace_tree[current_index][0]
                del trace_tree[current_root_index][2][0]  # Delete it
            except IndexError:  # We've depleted the children
                current_root_index = trace_tree[current_root_index][1]  # traverse upwards
                parent = parent.parent()
                continue
            child = QTreeWidgetItem(parent)
            child.trace_data = current_item
            child.setText(0, current_item[0])
            if trace_tree[current_index][2]:  # If current item has children, traverse them
                current_root_index = current_index  # traverse downwards
                parent = child
        self.treeWidget_InstructionInfo.expandAll()

    def save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SAVE_TRACE_FILE, None, tr.FILE_TYPES_TRACE)
        if file_path:
            file_path = utils.append_file_extension(file_path, "trace")
            if not utils.save_file(self.tracer.trace_data, file_path):
                QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    def load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr.OPEN_TRACE_FILE, None, tr.FILE_TYPES_TRACE)
        if file_path:
            content = utils.load_file(file_path)
            if content is None:
                QMessageBox.information(self, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
                return
            self.treeWidget_InstructionInfo.clear()
            self.tracer.trace_data = content
            self.show_trace_info()

    def treeWidget_InstructionInfo_context_menu_event(self, event):
        menu = QMenu()
        expand_all = menu.addAction(tr.EXPAND_ALL)
        collapse_all = menu.addAction(tr.COLLAPSE_ALL)
        font_size = self.treeWidget_InstructionInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            expand_all: self.treeWidget_InstructionInfo.expandAll,
            collapse_all: self.treeWidget_InstructionInfo.collapseAll,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_InstructionInfo_item_double_clicked(self, index):
        current_item = guiutils.get_current_item(self.treeWidget_InstructionInfo)
        if not current_item:
            return
        address = utils.extract_address(current_item.trace_data[0])
        if address:
            self.parent().disassemble_expression(address, append_to_travel_history=True)


class FunctionsInfoWidgetForm(QWidget, FunctionsInfoWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.textBrowser_AddressInfo.setFixedHeight(100)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_SymbolInfo.selectionModel().currentChanged.connect(self.tableWidget_SymbolInfo_current_changed)
        self.tableWidget_SymbolInfo.itemDoubleClicked.connect(self.tableWidget_SymbolInfo_item_double_clicked)
        self.tableWidget_SymbolInfo.contextMenuEvent = self.tableWidget_SymbolInfo_context_menu_event
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        guiutils.center_to_parent(self)

    def refresh_table(self):
        input_text = self.lineEdit_SearchInput.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(input_text, case_sensitive)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, gdb_input, case_sensitive):
        return debugcore.search_functions(gdb_input, case_sensitive)

    def apply_data(self, output):
        self.tableWidget_SymbolInfo.setSortingEnabled(False)
        self.tableWidget_SymbolInfo.setRowCount(0)
        self.tableWidget_SymbolInfo.setRowCount(len(output))
        defined_color = QColor(QColorConstants.Green)
        defined_color.setAlpha(96)
        for row, item in enumerate(output):
            address = item[0]
            if address:
                address_item = QTableWidgetItem(address)
            else:
                address_item = QTableWidgetItem(tr.DEFINED)
                address_item.setBackground(defined_color)
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_ADDR_COL, address_item)
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_SYMBOL_COL, QTableWidgetItem(item[1]))
        self.tableWidget_SymbolInfo.setSortingEnabled(True)
        guiutils.resize_to_contents(self.tableWidget_SymbolInfo)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current):
        self.textBrowser_AddressInfo.clear()
        current_row = QModelIndex_current.row()
        if current_row < 0:
            return
        address = self.tableWidget_SymbolInfo.item(current_row, FUNCTIONS_INFO_ADDR_COL).text()
        if utils.extract_address(address):
            symbol = self.tableWidget_SymbolInfo.item(current_row, FUNCTIONS_INFO_SYMBOL_COL).text()
            for item in utils.split_symbol(symbol):
                info = debugcore.get_symbol_info(item)
                self.textBrowser_AddressInfo.append(info)
        else:
            self.textBrowser_AddressInfo.append(tr.DEFINED_SYMBOL)

    def tableWidget_SymbolInfo_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_SymbolInfo.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_SymbolInfo)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_symbol = menu.addAction(tr.COPY_SYMBOL)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_symbol])
        font_size = self.tableWidget_SymbolInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_ADDR_COL),
            copy_symbol: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_SYMBOL_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_SymbolInfo_item_double_clicked(self, index):
        address = self.tableWidget_SymbolInfo.item(index.row(), FUNCTIONS_INFO_ADDR_COL).text()
        if address == tr.DEFINED:
            return
        self.parent().disassemble_expression(address, append_to_travel_history=True)

    def pushButton_Help_clicked(self):
        InputDialogForm(
            self,
            [(tr.FUNCTIONS_INFO_HELPER, None, Qt.AlignmentFlag.AlignLeft)],
            buttons=[QDialogButtonBox.StandardButton.Ok],
        ).exec()


class EditInstructionDialogForm(QDialog, EditInstructionDialog):
    def __init__(self, parent, address, bytes_aob):
        super().__init__(parent)
        self.setupUi(self)
        self.orig_bytes = bytes_aob
        self.lineEdit_Address.setText(address)
        self.lineEdit_Bytes.setText(bytes_aob)
        self.lineEdit_Bytes_text_edited()
        self.lineEdit_Bytes.textEdited.connect(self.lineEdit_Bytes_text_edited)
        self.lineEdit_Instruction.textEdited.connect(self.lineEdit_Instruction_text_edited)
        guiutils.center_to_parent(self)

    def set_valid(self, valid):
        if valid:
            self.is_valid = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.is_valid = False
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def lineEdit_Bytes_text_edited(self):
        bytes_aob = self.lineEdit_Bytes.text()
        if utils.parse_string(bytes_aob, typedefs.VALUE_INDEX.AOB):
            address = int(self.lineEdit_Address.text(), 0)
            instruction = utils.get_opcodes(address, bytes_aob, debugcore.inferior_arch)
            if instruction:
                self.set_valid(True)
                self.lineEdit_Instruction.setText(instruction)
                return
        self.set_valid(False)
        self.lineEdit_Instruction.setText("??")

    def lineEdit_Instruction_text_edited(self):
        instruction = self.lineEdit_Instruction.text()
        address = int(self.lineEdit_Address.text(), 0)
        result = utils.assemble(instruction, address, debugcore.inferior_arch)
        if result:
            byte_list = result[0]
            self.set_valid(True)
            bytes_str = " ".join([format(num, "02x") for num in byte_list])
            self.lineEdit_Bytes.setText(bytes_str)
        else:
            self.set_valid(False)
            self.lineEdit_Bytes.setText("??")

    def accept(self):
        if not self.is_valid:
            return

        # No need to check for validity since address is not editable and opcode is checked in text_edited
        address = int(self.lineEdit_Address.text(), 0)
        bytes_aob = self.lineEdit_Bytes.text()
        if bytes_aob != self.orig_bytes:
            new_length = len(bytes_aob.split())
            old_length = len(self.orig_bytes.split())
            if new_length < old_length:
                bytes_aob += " 90" * (old_length - new_length)  # Append NOPs if we are short on bytes
            elif new_length > old_length:
                if not InputDialogForm(self, [(tr.NEW_OPCODE.format(new_length, old_length),)]).exec():
                    return
            debugcore.modify_instruction(address, bytes_aob)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        super().accept()


class HexEditDialogForm(QDialog, HexEditDialog):
    def __init__(self, parent, address, length=20):
        super().__init__(parent)
        self.setupUi(self)
        self.lineEdit_Length.setValidator(QHexValidator(999, self))
        self.lineEdit_Address.setText(hex(address))
        self.lineEdit_Length.setText(str(length))
        self.refresh_view()
        self.lineEdit_AsciiView.selectionChanged.connect(self.lineEdit_AsciiView_selection_changed)
        guiutils.center_to_parent(self)

        # TODO: Implement this
        # self.lineEdit_HexView.selectionChanged.connect(self.lineEdit_HexView_selection_changed)
        self.lineEdit_HexView.textEdited.connect(self.lineEdit_HexView_text_edited)
        self.lineEdit_AsciiView.textEdited.connect(self.lineEdit_AsciiView_text_edited)
        self.pushButton_Refresh.pressed.connect(self.refresh_view)
        self.lineEdit_Address.textChanged.connect(self.refresh_view)
        self.lineEdit_Length.textChanged.connect(self.refresh_view)

    def lineEdit_AsciiView_selection_changed(self):
        length = len(utils.str_to_aob(self.lineEdit_AsciiView.selectedText(), "utf-8"))
        start_index = self.lineEdit_AsciiView.selectionStart()
        start_index = len(utils.str_to_aob(self.lineEdit_AsciiView.text()[0:start_index], "utf-8"))
        if start_index > 0:
            start_index += 1
        self.lineEdit_HexView.deselect()
        self.lineEdit_HexView.setSelection(start_index, length)

    def lineEdit_HexView_selection_changed(self):
        # TODO: Implement this
        print("TODO: Implement selectionChanged signal of lineEdit_HexView")
        raise NotImplementedError

    def lineEdit_HexView_text_edited(self):
        aob_string = self.lineEdit_HexView.text()
        if not utils.parse_string(aob_string, typedefs.VALUE_INDEX.AOB):
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")
            return
        aob_array = aob_string.split()
        try:
            self.lineEdit_AsciiView.setText(utils.aob_to_str(aob_array, "utf-8", replace_unprintable=False))
            self.lineEdit_HexView.setStyleSheet("")  # This should set background color back to QT default
        except ValueError:
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def lineEdit_AsciiView_text_edited(self):
        ascii_str = self.lineEdit_AsciiView.text()
        try:
            self.lineEdit_HexView.setText(utils.str_to_aob(ascii_str, "utf-8"))
            self.lineEdit_AsciiView.setStyleSheet("")
        except ValueError:
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def refresh_view(self):
        self.lineEdit_AsciiView.clear()
        self.lineEdit_HexView.clear()
        address = debugcore.examine_expression(self.lineEdit_Address.text()).address
        if not address:
            return
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
            address = int(address, 0)
        except ValueError:
            return
        aob_array = debugcore.hex_dump(address, length)
        ascii_str = utils.aob_to_str(aob_array, "utf-8", replace_unprintable=False)
        self.lineEdit_AsciiView.setText(ascii_str)
        self.lineEdit_HexView.setText(" ".join(aob_array))

    def accept(self):
        expression = self.lineEdit_Address.text()
        address = debugcore.examine_expression(expression).address
        if not address:
            QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_EXPRESSION.format(expression))
            return
        value = self.lineEdit_HexView.text()
        debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, value)
        super().accept()


# This widget will be replaced with auto-generated documentation in the future, no need to translate
class LibpinceReferenceWidgetForm(QWidget, LibpinceReferenceWidget):
    def convert_to_modules(self, module_strings):
        return [eval(item) for item in module_strings]

    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.found_count = 0
        self.current_found = 0
        self.setWindowFlags(Qt.WindowType.Window)
        self.show_typedefs()
        self.splitter.setStretchFactor(0, 1)
        self.widget_Resources.resize(700, self.widget_Resources.height())
        libpince_directory = utils.get_libpince_directory()
        self.textBrowser_TypeDefs.setText(open(libpince_directory + "/typedefs.py").read())
        source_menu_items = ["(Tagged only)", "(All)"]
        self.source_files = ["debugcore", "utils", "guiutils"]
        source_menu_items.extend(self.source_files)
        self.comboBox_SourceFile.addItems(source_menu_items)
        self.comboBox_SourceFile.setCurrentIndex(0)
        self.fill_resource_tree()
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_TextUp.setIcon(QIcon(QPixmap(icons_directory + "/bullet_arrow_up.png")))
        self.pushButton_TextDown.setIcon(QIcon(QPixmap(icons_directory + "/bullet_arrow_down.png")))
        self.comboBox_SourceFile.currentIndexChanged.connect(self.comboBox_SourceFile_current_index_changed)
        self.pushButton_ShowTypeDefs.clicked.connect(self.toggle_typedefs)
        self.lineEdit_SearchText.textChanged.connect(self.highlight_text)
        self.pushButton_TextDown.clicked.connect(self.pushButton_TextDown_clicked)
        self.pushButton_TextUp.clicked.connect(self.pushButton_TextUp_clicked)
        self.lineEdit_Search.textChanged.connect(self.comboBox_SourceFile_current_index_changed)
        self.tableWidget_ResourceTable.contextMenuEvent = self.tableWidget_ResourceTable_context_menu_event
        self.treeWidget_ResourceTree.contextMenuEvent = self.treeWidget_ResourceTree_context_menu_event
        self.treeWidget_ResourceTree.expanded.connect(self.resize_resource_tree)
        self.treeWidget_ResourceTree.collapsed.connect(self.resize_resource_tree)
        guiutils.center_to_parent(self)

    def tableWidget_ResourceTable_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_ResourceTable.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_ResourceTable)

        menu = QMenu()
        refresh = menu.addAction("Refresh")
        menu.addSeparator()
        copy_item = menu.addAction("Copy Item")
        copy_value = menu.addAction("Copy Value")
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_item, copy_value])
        font_size = self.tableWidget_ResourceTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.fill_resource_table,
            copy_item: lambda: copy_to_clipboard(selected_row, LIBPINCE_REFERENCE_ITEM_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, LIBPINCE_REFERENCE_VALUE_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_ResourceTree_context_menu_event(self, event):
        def copy_to_clipboard(column):
            current_item = guiutils.get_current_item(self.treeWidget_ResourceTree)
            if current_item:
                app.clipboard().setText(current_item.text(column))

        def expand_all():
            self.treeWidget_ResourceTree.expandAll()
            self.resize_resource_tree()

        def collapse_all():
            self.treeWidget_ResourceTree.collapseAll()
            self.resize_resource_tree()

        selected_row = guiutils.get_current_row(self.treeWidget_ResourceTree)

        menu = QMenu()
        refresh = menu.addAction("Refresh")
        menu.addSeparator()
        copy_item = menu.addAction("Copy Item")
        copy_value = menu.addAction("Copy Value")
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_item, copy_value])
        menu.addSeparator()
        expand_all_items = menu.addAction("Expand All")
        collapse_all_items = menu.addAction("Collapse All")
        font_size = self.treeWidget_ResourceTree.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.fill_resource_tree,
            copy_item: lambda: copy_to_clipboard(LIBPINCE_REFERENCE_ITEM_COL),
            copy_value: lambda: copy_to_clipboard(LIBPINCE_REFERENCE_VALUE_COL),
            expand_all_items: expand_all,
            collapse_all_items: collapse_all,
        }

        # Thanks QT, for this unexplainable, mind blowing bug of yours
        self.treeWidget_ResourceTree.blockSignals(True)
        try:
            actions[action]()
        except KeyError:
            pass
        self.treeWidget_ResourceTree.blockSignals(False)

    def comboBox_SourceFile_current_index_changed(self):
        if self.comboBox_SourceFile.currentIndex() == 0:  # (Tagged only)
            self.fill_resource_tree()
        else:
            self.fill_resource_table()

    def resize_resource_tree(self):
        self.treeWidget_ResourceTree.resizeColumnToContents(LIBPINCE_REFERENCE_ITEM_COL)

    def fill_resource_tree(self):
        self.treeWidget_ResourceTree.setStyleSheet("QTreeWidget::item{ height: 16px; }")
        self.stackedWidget_Resources.setCurrentIndex(0)
        self.treeWidget_ResourceTree.clear()
        parent = self.treeWidget_ResourceTree
        checked_source_files = self.convert_to_modules(self.source_files)
        tag_dict = utils.get_tags(checked_source_files, typedefs.tag_to_string, self.lineEdit_Search.text())
        docstring_dict = utils.get_docstrings(checked_source_files, self.lineEdit_Search.text())
        for tag in tag_dict:
            child = QTreeWidgetItem(parent)
            child.setText(0, tag)
            for item in tag_dict[tag]:
                docstring = docstring_dict.get(item)
                docstr_child = QTreeWidgetItem(child)
                docstr_child.setText(LIBPINCE_REFERENCE_ITEM_COL, item)
                docstr_child.setText(LIBPINCE_REFERENCE_VALUE_COL, str(eval(item)))
                docstr_child.setToolTip(LIBPINCE_REFERENCE_ITEM_COL, docstring)
                docstr_child.setToolTip(LIBPINCE_REFERENCE_VALUE_COL, docstring)

        # Magic and mystery
        self.treeWidget_ResourceTree.blockSignals(True)
        if self.lineEdit_Search.text():
            self.treeWidget_ResourceTree.expandAll()
        self.resize_resource_tree()
        self.treeWidget_ResourceTree.blockSignals(False)

    def fill_resource_table(self):
        self.stackedWidget_Resources.setCurrentIndex(1)
        self.tableWidget_ResourceTable.setSortingEnabled(False)
        self.tableWidget_ResourceTable.setRowCount(0)
        if self.comboBox_SourceFile.currentIndex() == 1:  # (All)
            checked_source_files = self.source_files
        else:
            checked_source_files = [self.comboBox_SourceFile.currentText()]
        checked_source_files = self.convert_to_modules(checked_source_files)
        element_dict = utils.get_docstrings(checked_source_files, self.lineEdit_Search.text())
        self.tableWidget_ResourceTable.setRowCount(len(element_dict))
        for row, item in enumerate(element_dict):
            docstring = element_dict.get(item)
            table_widget_item = QTableWidgetItem(item)
            table_widget_item_value = QTableWidgetItem(str(eval(item)))
            table_widget_item.setToolTip(docstring)
            table_widget_item_value.setToolTip(docstring)
            self.tableWidget_ResourceTable.setItem(row, LIBPINCE_REFERENCE_ITEM_COL, table_widget_item)
            self.tableWidget_ResourceTable.setItem(row, LIBPINCE_REFERENCE_VALUE_COL, table_widget_item_value)
        self.tableWidget_ResourceTable.setSortingEnabled(True)
        self.tableWidget_ResourceTable.sortByColumn(LIBPINCE_REFERENCE_ITEM_COL, Qt.SortOrder.AscendingOrder)
        guiutils.resize_to_contents(self.tableWidget_ResourceTable)

    def pushButton_TextDown_clicked(self):
        if self.found_count == 0:
            return
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)
        if self.current_found == self.found_count:
            self.current_found = 1
        else:
            self.current_found += 1
        pattern = self.lineEdit_SearchText.text()
        for x in range(self.current_found):
            self.textBrowser_TypeDefs.find(pattern)
        self.label_FoundCount.setText(str(self.current_found) + "/" + str(self.found_count))

    def pushButton_TextUp_clicked(self):
        if self.found_count == 0:
            return
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)
        if self.current_found == 1:
            self.current_found = self.found_count
        else:
            self.current_found -= 1
        pattern = self.lineEdit_SearchText.text()
        for x in range(self.current_found):
            self.textBrowser_TypeDefs.find(pattern)
        self.label_FoundCount.setText(str(self.current_found) + "/" + str(self.found_count))

    def highlight_text(self):
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)
        highlight_format = QTextCharFormat()
        color = QColor(QColorConstants.LightGray)
        color.setAlpha(96)
        highlight_format.setBackground(color)
        pattern = self.lineEdit_SearchText.text()
        found_count = 0
        while True:
            if not self.textBrowser_TypeDefs.find(pattern):
                break
            cursor = self.textBrowser_TypeDefs.textCursor()
            cursor.mergeCharFormat(highlight_format)
            found_count += 1
        self.found_count = found_count
        if found_count == 0:
            self.label_FoundCount.setText("0/0")
        else:
            self.label_FoundCount.setText("1/" + str(found_count))
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)
        self.textBrowser_TypeDefs.find(pattern)
        self.current_found = 1

    def toggle_typedefs(self):
        if self.typedefs_shown:
            self.hide_typedefs()
        else:
            self.show_typedefs()

    def hide_typedefs(self):
        self.typedefs_shown = False
        self.widget_TypeDefs.hide()
        self.pushButton_ShowTypeDefs.setText("Show typedefs")

    def show_typedefs(self):
        self.typedefs_shown = True
        self.widget_TypeDefs.show()
        self.pushButton_ShowTypeDefs.setText("Hide typedefs")


class LogFileWidgetForm(QWidget, LogFileWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.contents = ""
        self.refresh_contents()
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_contents)
        self.refresh_timer.start()
        guiutils.center_to_parent(self)

    def refresh_contents(self):
        log_path = utils.get_logging_file(debugcore.currentpid)
        self.setWindowTitle(tr.LOG_FILE.format(debugcore.currentpid))
        self.label_FilePath.setText(tr.LOG_CONTENTS.format(log_path, 20000))
        log_status = f"<font color=blue>{tr.ON}</font>" if settings.gdb_logging else f"<font color=red>{tr.OFF}</font>"
        self.label_LoggingStatus.setText(f"<b>{tr.LOG_STATUS.format(log_status)}</b>")
        try:
            log_file = open(log_path)
        except OSError:
            self.textBrowser_LogContent.clear()
            error_message = tr.LOG_READ_ERROR.format(log_path) + "\n"
            if not settings.gdb_logging:
                error_message += tr.SETTINGS_ENABLE_LOG
            self.textBrowser_LogContent.setText(error_message)
            return
        log_file.seek(0, io.SEEK_END)
        end_pos = log_file.tell()
        if end_pos > 20000:
            log_file.seek(end_pos - 20000, io.SEEK_SET)
        else:
            log_file.seek(0, io.SEEK_SET)
        contents = log_file.read().split("\n", 1)[-1]
        if contents != self.contents:
            self.contents = contents
            self.textBrowser_LogContent.clear()
            self.textBrowser_LogContent.setPlainText(contents)

            # Scrolling to bottom
            cursor = self.textBrowser_LogContent.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.textBrowser_LogContent.setTextCursor(cursor)
            self.textBrowser_LogContent.ensureCursorVisible()
        log_file.close()

    def closeEvent(self, event: QCloseEvent):
        self.refresh_timer.stop()
        super().closeEvent(event)


class SearchOpcodeWidgetForm(QWidget, SearchOpcodeWidget):
    def __init__(self, parent, start="", end=""):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.lineEdit_Start.setText(start)
        self.lineEdit_End.setText(end)
        self.tableWidget_Opcodes.setColumnWidth(SEARCH_OPCODE_ADDR_COL, 250)
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_Opcodes.itemDoubleClicked.connect(self.tableWidget_Opcodes_item_double_clicked)
        self.tableWidget_Opcodes.contextMenuEvent = self.tableWidget_Opcodes_context_menu_event
        guiutils.center_to_parent(self)

    def refresh_table(self):
        start_address = self.lineEdit_Start.text()
        end_address = self.lineEdit_End.text()
        regex = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(
            regex, start_address, end_address, case_sensitive, enable_regex
        )
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, regex, start_address, end_address, case_sensitive, enable_regex):
        return debugcore.search_opcode(regex, start_address, end_address, case_sensitive, enable_regex)

    def apply_data(self, disas_data):
        if disas_data is None:
            QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
            return
        self.tableWidget_Opcodes.setSortingEnabled(False)
        self.tableWidget_Opcodes.setRowCount(0)
        self.tableWidget_Opcodes.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            self.tableWidget_Opcodes.setItem(row, SEARCH_OPCODE_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Opcodes.setItem(row, SEARCH_OPCODE_OPCODES_COL, QTableWidgetItem(item[1]))
        self.tableWidget_Opcodes.setSortingEnabled(True)

    def pushButton_Help_clicked(self):
        InputDialogForm(
            self,
            [(tr.SEARCH_OPCODE_HELPER, None, Qt.AlignmentFlag.AlignLeft)],
            buttons=[QDialogButtonBox.StandardButton.Ok],
        ).exec()

    def tableWidget_Opcodes_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_Opcodes.item(row, SEARCH_OPCODE_ADDR_COL).text()
        self.parent().disassemble_expression(utils.extract_address(address), append_to_travel_history=True)

    def tableWidget_Opcodes_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Opcodes.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_Opcodes)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_opcode = menu.addAction(tr.COPY_OPCODE)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_opcode])
        font_size = self.tableWidget_Opcodes.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, SEARCH_OPCODE_ADDR_COL),
            copy_opcode: lambda: copy_to_clipboard(selected_row, SEARCH_OPCODE_OPCODES_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass


class MemoryRegionsWidgetForm(QWidget, MemoryRegionsWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.refresh_table()
        self.tableWidget_MemoryRegions.contextMenuEvent = self.tableWidget_MemoryRegions_context_menu_event
        self.tableWidget_MemoryRegions.itemDoubleClicked.connect(self.tableWidget_MemoryRegions_item_double_clicked)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        guiutils.center_to_parent(self)

    def refresh_table(self):
        memory_regions = utils.get_regions(debugcore.currentpid)
        self.tableWidget_MemoryRegions.setRowCount(0)
        self.tableWidget_MemoryRegions.setRowCount(len(memory_regions))
        for row, (start, end, perms, offset, _, _, path) in enumerate(memory_regions):
            address = start + "-" + end
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PERM_COL, QTableWidgetItem(perms))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_OFFSET_COL, QTableWidgetItem(offset))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PATH_COL, QTableWidgetItem(path))
        guiutils.resize_to_contents(self.tableWidget_MemoryRegions)

    def tableWidget_MemoryRegions_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_MemoryRegions.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_MemoryRegions)

        menu = QMenu()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        copy_addresses = menu.addAction(tr.COPY_ADDRESSES)
        copy_offset = menu.addAction(tr.COPY_OFFSET)
        copy_path = menu.addAction(tr.COPY_PATH)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_addresses, copy_offset, copy_path])
        font_size = self.tableWidget_MemoryRegions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.refresh_table,
            copy_addresses: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_ADDR_COL),
            copy_offset: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_OFFSET_COL),
            copy_path: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_PATH_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_MemoryRegions_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_MemoryRegions.item(row, MEMORY_REGIONS_ADDR_COL).text()
        address_int = int(address.split("-")[0], 16)
        self.parent().hex_dump_address(address_int)


class DissectCodeDialogForm(QDialog, DissectCodeDialog):
    scan_finished_signal = pyqtSignal()

    def __init__(self, parent, int_address=-1):
        super().__init__(parent)
        self.setupUi(self)
        self.init_pre_scan_gui()
        self.update_dissect_results()
        self.show_memory_regions()
        self.splitter.setStretchFactor(0, 1)
        self.pushButton_StartCancel.clicked.connect(self.pushButton_StartCancel_clicked)
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(self.refresh_dissect_status)
        if int_address != -1:
            for row in range(self.tableWidget_ExecutableMemoryRegions.rowCount()):
                item = self.tableWidget_ExecutableMemoryRegions.item(row, DISSECT_CODE_ADDR_COL).text()
                start_addr, end_addr = item.split("-")
                if int(start_addr, 16) <= int_address <= int(end_addr, 16):
                    self.tableWidget_ExecutableMemoryRegions.clearSelection()
                    self.tableWidget_ExecutableMemoryRegions.selectRow(row)
                    self.pushButton_StartCancel_clicked()
                    break
            else:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGION)
        else:
            if self.tableWidget_ExecutableMemoryRegions.rowCount() > 0:
                self.tableWidget_ExecutableMemoryRegions.selectRow(0)
        guiutils.center_to_parent(self)

    class BackgroundThread(QThread):
        output_ready = pyqtSignal()
        is_canceled = False

        def __init__(self, region_list, discard_invalid_strings):
            super().__init__()
            self.region_list = region_list
            self.discard_invalid_strings = discard_invalid_strings

        def run(self):
            debugcore.dissect_code(self.region_list, self.discard_invalid_strings)
            if not self.is_canceled:
                self.output_ready.emit()

    def init_pre_scan_gui(self):
        self.is_scanning = False
        self.is_canceled = False
        self.pushButton_StartCancel.setText(tr.START)

    def init_after_scan_gui(self):
        self.is_scanning = True
        self.label_ScanInfo.setText(tr.CURRENT_SCAN_REGION)
        self.pushButton_StartCancel.setText(tr.CANCEL)

    def refresh_dissect_status(self):
        region, region_count, range, string_count, jump_count, call_count = debugcore.get_dissect_code_status()
        if not region:
            return
        self.label_RegionInfo.setText(region)
        self.label_RegionCountInfo.setText(region_count)
        self.label_CurrentRange.setText(range)
        self.label_StringReferenceCount.setText(str(string_count))
        self.label_JumpReferenceCount.setText(str(jump_count))
        self.label_CallReferenceCount.setText(str(call_count))

    def update_dissect_results(self):
        try:
            referenced_strings, referenced_jumps, referenced_calls = debugcore.get_dissect_code_data()
        except:
            return
        self.label_StringReferenceCount.setText(str(len(referenced_strings)))
        self.label_JumpReferenceCount.setText(str(len(referenced_jumps)))
        self.label_CallReferenceCount.setText(str(len(referenced_calls)))

    def show_memory_regions(self):
        executable_regions = utils.filter_regions(debugcore.currentpid, "permissions", "..x.")
        self.region_list = []
        self.tableWidget_ExecutableMemoryRegions.setRowCount(0)
        self.tableWidget_ExecutableMemoryRegions.setRowCount(len(executable_regions))
        for row, (start, end, _, _, _, _, path) in enumerate(executable_regions):
            address = start + "-" + end
            self.region_list.append((start, end))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_PATH_COL, QTableWidgetItem(path))
        guiutils.resize_to_contents(self.tableWidget_ExecutableMemoryRegions)

    def scan_finished(self):
        self.init_pre_scan_gui()
        if not self.is_canceled:
            self.label_ScanInfo.setText(tr.SCAN_FINISHED)
        self.is_canceled = False
        self.refresh_timer.stop()
        self.refresh_dissect_status()
        self.update_dissect_results()
        self.scan_finished_signal.emit()

    def pushButton_StartCancel_clicked(self):
        if self.is_scanning:
            self.is_canceled = True
            self.background_thread.is_canceled = True
            debugcore.cancel_dissect_code()
            self.refresh_timer.stop()
            self.update_dissect_results()
            self.label_ScanInfo.setText(tr.SCAN_CANCELED)
            self.init_pre_scan_gui()
        else:
            selected_rows = self.tableWidget_ExecutableMemoryRegions.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, tr.ERROR, tr.SELECT_ONE_REGION)
                return
            selected_indexes = [selected_row.row() for selected_row in selected_rows]
            selected_regions = [self.region_list[selected_index] for selected_index in selected_indexes]
            self.background_thread = self.BackgroundThread(
                selected_regions, self.checkBox_DiscardInvalidStrings.isChecked()
            )
            self.background_thread.output_ready.connect(self.scan_finished)
            self.init_after_scan_gui()
            self.refresh_timer.start()
            self.background_thread.start()

    def closeEvent(self, event: QCloseEvent):
        debugcore.cancel_dissect_code()
        self.refresh_timer.stop()
        super().closeEvent(event)


class ReferencedStringsWidgetForm(QWidget, ReferencedStringsWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        guiutils.fill_value_combobox(self.comboBox_ValueType, typedefs.VALUE_INDEX.STRING_UTF8)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_STR_ADDR_COL, 150)
        self.tableWidget_References.setColumnWidth(REF_STR_COUNT_COL, 80)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        guiutils.center_to_parent(self)
        self.hex_len = 16 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = debugcore.get_dissect_code_data()
        str_dict_len, jmp_dict_len, call_dict_len = len(str_dict), len(jmp_dict), len(call_dict)
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        if str_dict_len == 0 and jmp_dict_len == 0 and call_dict_len == 0:
            confirm_dialog = InputDialogForm(self, [(tr.DISSECT_CODE,)])
            if confirm_dialog.exec():
                dissect_code_dialog = DissectCodeDialogForm(self)
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_STR_ADDR_COL, Qt.SortOrder.AscendingOrder)
        self.tableWidget_References.selectionModel().currentChanged.connect(self.tableWidget_References_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.tableWidget_References.itemDoubleClicked.connect(self.tableWidget_References_item_double_clicked)
        self.tableWidget_References.contextMenuEvent = self.tableWidget_References_context_menu_event
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.comboBox_ValueType.currentIndexChanged.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)

    def pad_hex(self, hex_str):
        index = hex_str.find(" ")
        if index == -1:
            self_len = 0
        else:
            self_len = len(hex_str) - index
        return "0x" + hex_str[2:].zfill(self.hex_len + self_len)

    def refresh_table(self):
        item_list = debugcore.search_referenced_strings(
            self.lineEdit_Regex.text(),
            self.comboBox_ValueType.currentIndex(),
            self.checkBox_CaseSensitive.isChecked(),
            self.checkBox_Regex.isChecked(),
        )
        if item_list is None:
            QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_STR_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_STR_COUNT_COL, table_widget_item)
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[2])
            self.tableWidget_References.setItem(row, REF_STR_VAL_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        str_dict = debugcore.get_dissect_code_data(True, False, False)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_STR_ADDR_COL).text()
        referrers = str_dict[hex(int(addr, 16))]
        addrs = [hex(address) for address in referrers]
        self.listWidget_Referrers.addItems([self.pad_hex(item.all) for item in debugcore.examine_expressions(addrs)])
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        str_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_STR_ADDR_COL).text()
        self.parent().hex_dump_address(int(address, 16))

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(utils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_value = menu.addAction(tr.COPY_VALUE)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_value])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, REF_STR_ADDR_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, REF_STR_VAL_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = guiutils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row)}
        try:
            actions[action]()
        except KeyError:
            pass


class ReferencedCallsWidgetForm(QWidget, ReferencedCallsWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_CALL_ADDR_COL, 480)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        guiutils.center_to_parent(self)
        self.hex_len = 16 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = debugcore.get_dissect_code_data()
        str_dict_len, jmp_dict_len, call_dict_len = len(str_dict), len(jmp_dict), len(call_dict)
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        if str_dict_len == 0 and jmp_dict_len == 0 and call_dict_len == 0:
            confirm_dialog = InputDialogForm(self, [(tr.DISSECT_CODE,)])
            if confirm_dialog.exec():
                dissect_code_dialog = DissectCodeDialogForm(self)
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_CALL_ADDR_COL, Qt.SortOrder.AscendingOrder)
        self.tableWidget_References.selectionModel().currentChanged.connect(self.tableWidget_References_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.tableWidget_References.itemDoubleClicked.connect(self.tableWidget_References_item_double_clicked)
        self.tableWidget_References.contextMenuEvent = self.tableWidget_References_context_menu_event
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)

    def pad_hex(self, hex_str):
        index = hex_str.find(" ")
        if index == -1:
            self_len = 0
        else:
            self_len = len(hex_str) - index
        return "0x" + hex_str[2:].zfill(self.hex_len + self_len)

    def refresh_table(self):
        item_list = debugcore.search_referenced_calls(
            self.lineEdit_Regex.text(), self.checkBox_CaseSensitive.isChecked(), self.checkBox_Regex.isChecked()
        )
        if item_list is None:
            QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_CALL_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_CALL_COUNT_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        call_dict = debugcore.get_dissect_code_data(False, False, True)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_CALL_ADDR_COL).text()
        referrers = call_dict[hex(int(utils.extract_address(addr), 16))]
        addrs = [hex(address) for address in referrers]
        self.listWidget_Referrers.addItems([self.pad_hex(item.all) for item in debugcore.examine_expressions(addrs)])
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        call_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_CALL_ADDR_COL).text()
        self.parent().disassemble_expression(utils.extract_address(address), append_to_travel_history=True)

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(utils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row, REF_CALL_ADDR_COL)}
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = guiutils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row)}
        try:
            actions[action]()
        except KeyError:
            pass


class ExamineReferrersWidgetForm(QWidget, ExamineReferrersWidget):
    def __init__(self, parent, int_address):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.splitter.setStretchFactor(0, 1)
        self.textBrowser_DisasInfo.resize(600, self.textBrowser_DisasInfo.height())
        self.referenced_hex = hex(int_address)
        self.hex_len = 16 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else 8
        self.collect_referrer_data()
        self.refresh_table()
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        self.listWidget_Referrers.selectionModel().currentChanged.connect(self.listWidget_Referrers_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        guiutils.center_to_parent(self)

    def pad_hex(self, hex_str):
        index = hex_str.find(" ")
        if index == -1:
            self_len = 0
        else:
            self_len = len(hex_str) - index
        return "0x" + hex_str[2:].zfill(self.hex_len + self_len)

    def collect_referrer_data(self):
        jmp_dict, call_dict = debugcore.get_dissect_code_data(False, True, True)
        self.referrer_data = []
        try:
            jmp_referrers = jmp_dict[self.referenced_hex]
        except KeyError:
            pass
        else:
            jmp_referrers = [hex(item) for item in jmp_referrers]
            self.referrer_data.extend([item.all for item in debugcore.examine_expressions(jmp_referrers)])
        try:
            call_referrers = call_dict[self.referenced_hex]
        except KeyError:
            pass
        else:
            call_referrers = [hex(item) for item in call_referrers]
            self.referrer_data.extend([item.all for item in debugcore.examine_expressions(call_referrers)])
        jmp_dict.close()
        call_dict.close()

    def refresh_table(self):
        searched_str = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        if enable_regex:
            try:
                if case_sensitive:
                    regex = re.compile(searched_str)
                else:
                    regex = re.compile(searched_str, re.IGNORECASE)
            except:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
                return
        self.listWidget_Referrers.setSortingEnabled(False)
        self.listWidget_Referrers.clear()
        for row, item in enumerate(self.referrer_data):
            if enable_regex:
                if not regex.search(item):
                    continue
            else:
                if case_sensitive:
                    if item.find(searched_str) == -1:
                        continue
                else:
                    if item.lower().find(searched_str.lower()) == -1:
                        continue
            self.listWidget_Referrers.addItem(item)
        self.listWidget_Referrers.setSortingEnabled(True)
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)

    def listWidget_Referrers_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.textBrowser_DisasInfo.clear()
        disas_data = debugcore.disassemble(
            utils.extract_address(self.listWidget_Referrers.item(QModelIndex_current.row()).text()), "+200"
        )
        for address_info, _, opcode in disas_data:
            self.textBrowser_DisasInfo.append(address_info + opcode)
        cursor = self.textBrowser_DisasInfo.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_DisasInfo.setTextCursor(cursor)
        self.textBrowser_DisasInfo.ensureCursorVisible()

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(utils.extract_address(item.text()), append_to_travel_history=True)

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = guiutils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row)}
        try:
            actions[action]()
        except KeyError:
            pass


class PointerScanSearchDialogForm(QDialog, PointerScanSearchDialog):
    def __init__(self, parent, address) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.lineEdit_Address.setText(address)
        self.lineEdit_Path.setText(os.getcwd() + f"/{utils.get_process_name(debugcore.currentpid)}.scandata")
        self.pushButton_PathBrowse.clicked.connect(self.pushButton_PathBrowse_clicked)
        self.scan_button: QPushButton | None = self.buttonBox.addButton(tr.SCAN, QDialogButtonBox.ButtonRole.ActionRole)
        if self.scan_button:
            self.scan_button.clicked.connect(self.scan_button_clicked)
        self.ptrscan_thread: InterruptableWorker | None = None

    def pushButton_PathBrowse_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path = utils.append_file_extension(file_path, "scandata")
            self.lineEdit_Path.setText(file_path)

    def reject(self) -> None:
        if self.ptrscan_thread:
            self.ptrscan_thread.stop()
        return super().reject()

    def scan_button_clicked(self) -> None:
        if debugcore.currentpid == -1 or self.scan_button == None:
            return
        self.scan_button.setText(tr.SCANNING)
        self.scan_button.setEnabled(False)
        self.pushButton_PathBrowse.setEnabled(False)
        params: FFIParam = FFIParam()
        try:
            addr_val = int(self.lineEdit_Address.text(), 16)
        except ValueError:
            addr_val = 0
        params.addr(addr_val)
        params.depth(self.spinBox_Depth.value())
        params.srange(FFIRange(self.spinBox_ScanRangeStart.value(), self.spinBox_ScanRangeEnd.value()))
        lrange_start: int = self.spinBox_ScanLRangeStart.value()
        lrange_end: int = self.spinBox_ScanLRangeEnd.value()
        if lrange_start == 0 and lrange_end == 0:
            lrange_val = None
        else:
            lrange_val = FFIRange(lrange_start, lrange_end)
        params.lrange(lrange_val)
        params.node(utils.return_optional_int(self.spinBox_Node.value()))
        try:
            last_val = int(self.lineEdit_Last.text(), 16)
        except ValueError:
            last_val = None
        params.last(last_val)
        params.max(utils.return_optional_int(self.spinBox_Max.value()))
        params.cycle(self.checkBox_Cycle.isChecked())
        ptrscan.set_modules(ptrscan.list_modules_pince())  # TODO: maybe cache this and let user refresh with a button
        ptrscan.create_pointer_map()  # TODO: maybe cache this and let user refresh with a button
        ptrmap_file_path = self.lineEdit_Path.text()
        if os.path.isfile(ptrmap_file_path):
            os.remove(ptrmap_file_path)
        self.ptrscan_thread = InterruptableWorker(ptrscan.scan_pointer_chain, params, ptrmap_file_path)
        self.ptrscan_thread.signals.finished.connect(self.ptrscan_callback)
        self.ptrscan_thread.start()

    def ptrscan_callback(self) -> None:
        self.accept()


class PointerScanFilterDialogForm(QDialog, PointerScanFilterDialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.pushButton_File1Browse.clicked.connect(self.pushButton_File1Browse_clicked)
        self.pushButton_File2Browse.clicked.connect(self.pushButton_File2Browse_clicked)
        self.filter_button: QPushButton | None = self.buttonBox.addButton(
            tr.FILTER, QDialogButtonBox.ButtonRole.ActionRole
        )
        if self.filter_button:
            self.filter_button.clicked.connect(self.filter_button_clicked)
            self.filter_button.setEnabled(False)
        self.filter_result: list[str] | None = None

    def browse_scandata_file(self, file_path_field: QLineEdit) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path_field.setText(file_path)
            self.check_filterable_state()

    def check_filterable_state(self) -> None:
        if self.lineEdit_File1Path.text() != "" and self.lineEdit_File2Path.text() != "" and self.filter_button:
            self.filter_button.setEnabled(True)

    def pushButton_File1Browse_clicked(self) -> None:
        self.browse_scandata_file(self.lineEdit_File1Path)

    def pushButton_File2Browse_clicked(self) -> None:
        self.browse_scandata_file(self.lineEdit_File2Path)

    def filter_button_clicked(self) -> None:
        if self.lineEdit_File1Path.text() == "" or self.lineEdit_File2Path.text() == "" or self.filter_button == None:
            return
        self.filter_button.setEnabled(False)
        self.filter_button.setText(tr.FILTERING)
        lines: list[str]
        with open(self.lineEdit_File1Path.text()) as file:
            lines = file.read().split(os.linesep)
        with open(self.lineEdit_File2Path.text()) as file:
            lines.extend(file.read().split(os.linesep))
        counts = collections.Counter(lines)
        self.filter_result = list(set([line for line in lines if counts[line] > 1 and line != ""]))
        self.accept()

    def get_filter_result(self) -> list[str] | None:
        return self.filter_result


class PointerScanWindowForm(QMainWindow, PointerScanWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.tableWidget_ScanResult.hide()
        process_signals.attach.connect(self.on_process_changed)
        process_signals.exit.connect(self.on_process_changed)
        self.pushButton_Clear.pressed.connect(self.pushButton_Clear_pressed)
        self.pushButton_Sort.pressed.connect(self.pushButton_Sort_pressed)
        self.actionOpen.triggered.connect(self.actionOpen_triggered)
        self.actionSaveAs.triggered.connect(self.actionSaveAs_triggered)
        self.actionScan.triggered.connect(self.scan_triggered)
        self.actionFilter.triggered.connect(self.filter_triggered)
        if debugcore.currentpid == -1:
            self.actionScan.setEnabled(False)
        guiutils.center_to_parent(self)

    def on_process_changed(self) -> None:
        val: bool = False if debugcore.currentpid == -1 else True
        self.actionScan.setEnabled(val)

    def pushButton_Clear_pressed(self) -> None:
        self.textEdit.clear()

    def pushButton_Sort_pressed(self) -> None:
        text: str = self.textEdit.toPlainText()
        if text == "":
            return
        text_list: list[str] = text.split(os.linesep)
        # Sometimes files will have ending newlines.
        # We want to get rid of them otherwise they'll be at top.
        if text_list[-1] == "":
            del text_list[-1]
        text_list.sort()
        self.textEdit.setText(os.linesep.join(text_list))

    def actionOpen_triggered(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            self.textEdit.clear()
            with open(file_path) as file:
                self.textEdit.setText(file.read())

    def actionSaveAs_triggered(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path = utils.append_file_extension(file_path, "scandata")
            with open(file_path, "w") as file:
                file.write(self.textEdit.toPlainText())

    def scan_triggered(self) -> None:
        dialog = PointerScanSearchDialogForm(self, "0x0")
        dialog.exec()

    def filter_triggered(self) -> None:
        dialog = PointerScanFilterDialogForm(self)
        if dialog.exec():
            filter_result: list[str] | None = dialog.get_filter_result()
            if filter_result == None:
                return
            self.textEdit.clear()
            self.textEdit.setText(os.linesep.join(filter_result))


def handle_exit():
    global exiting
    exiting = 1


if __name__ == "__main__":
    app.aboutToQuit.connect(handle_exit)
    window = MainForm()
    window.show()
    sys.exit(app.exec())
