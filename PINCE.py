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

# This fixes GTK version mismatch issues and crashes on gnome
# See #153 and #159 for more information
# This line can be deleted when GTK 4.0 properly runs on all supported systems
gi.require_version('Gtk', '3.0')

from typing import Final

from PyQt6.QtGui import QIcon, QMovie, QPixmap, QCursor, QKeySequence, QColor, QTextCharFormat, QBrush, QTextCursor, \
    QKeyEvent, QRegularExpressionValidator, QShortcut, QColorConstants
from PyQt6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QWidget, QTabWidget, \
    QMenu, QFileDialog, QAbstractItemView, QTreeWidgetItem, QTreeWidgetItemIterator, QCompleter, QLabel, QLineEdit, \
    QComboBox, QDialogButtonBox, QCheckBox, QHBoxLayout, QPushButton, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray, QSettings, QEvent, QKeyCombination, \
    QItemSelectionModel, QTimer, QModelIndex, QStringListModel, QRegularExpression, QRunnable, QThreadPool, \
    QTranslator, QLocale, pyqtSlot
from time import sleep, time
import os, sys, traceback, signal, re, copy, io, queue, collections, ast, pexpect

from libpince import GuiUtils, SysUtils, GDB_Engine, type_defs
from libpince.libscanmem.scanmem import Scanmem
from tr.tr import TranslationConstants as tr

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

# If you are going to change the name "Ui_MainWindow_MemoryView", review GUI/CustomLabels/RegisterLabel.py as well
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

from GUI.CustomAbstractTableModels.HexModel import QHexModel
from GUI.CustomAbstractTableModels.AsciiModel import QAsciiModel
from GUI.CustomValidators.HexValidator import QHexValidator

from keyboard import add_hotkey, remove_hotkey
from operator import add as opAdd, sub as opSub

# TODO: Carry all settings related things to their own script if possible
language_list = [
    ("English", "en_US"),
    ("Italiano", "it_IT"),
    ("简体中文", "zh_CN")
]

def get_locale():
    system_locale = QLocale.system().name()
    for _, locale in language_list:
        if system_locale == locale:
            return locale
    return language_list[0][1]

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setOrganizationName("PINCE")
    app.setOrganizationDomain("github.com/korcankaraokcu/PINCE")
    app.setApplicationName("PINCE")
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope,
                      SysUtils.get_user_path(type_defs.USER_PATHS.CONFIG_PATH))
    settings = QSettings()
    translator = QTranslator()
    locale = settings.value("General/locale", type=str)
    if not locale:
        locale = get_locale()
    translator.load(f'i18n/qm/{locale}.qm')
    app.installTranslator(translator)
    tr.translate()

instances = []  # Holds temporary instances that will be deleted later on

# settings
current_settings_version = "25"  # Increase version by one if you change settings
update_table = bool
table_update_interval = int
freeze_interval = int
gdb_output_mode = tuple
auto_attach_list = str
auto_attach_regex = bool
locale = str
logo_path = str


class Hotkeys:
    class Hotkey:
        def __init__(self, name="", desc="", default="", func=None, custom="", handle=None):
            self.name = name
            self.desc = desc
            self.default = default
            self.func = func
            self.custom = custom
            if default == "" or func is None:
                self.handle = handle
            else:
                self.handle = add_hotkey(default, func)

        def change_key(self, custom):
            if self.handle is not None:
                remove_hotkey(self.handle)
                self.handle = None
            self.custom = custom
            if custom == '':
                return
            self.handle = add_hotkey(custom.lower(), self.func)

        def change_func(self, func):
            self.func = func
            if self.handle is not None:
                remove_hotkey(self.handle)
            if self.custom != "":
                self.handle = add_hotkey(self.custom, func)
            elif self.default != "":
                self.handle = add_hotkey(self.default, func)

        def get_active_key(self):
            if self.custom == "":
                return self.default
            return self.custom

    pause_hotkey = Hotkey("pause_hotkey", tr.PAUSE_HOTKEY, "F1")
    break_hotkey = Hotkey("break_hotkey", tr.BREAK_HOTKEY, "F2")
    continue_hotkey = Hotkey("continue_hotkey", tr.CONTINUE_HOTKEY, "F3")
    toggle_attach_hotkey = Hotkey("toggle_attach_hotkey", tr.TOGGLE_ATTACH_HOTKEY, "Shift+F10")
    exact_scan_hotkey = Hotkey("exact_scan_hotkey", tr.EXACT_SCAN_HOTKEY, "")
    increased_scan_hotkey = Hotkey("increased_scan_hotkey", tr.INC_SCAN_HOTKEY, "")
    decreased_scan_hotkey = Hotkey("decreased_scan_hotkey", tr.DEC_SCAN_HOTKEY, "")
    changed_scan_hotkey = Hotkey("changed_scan_hotkey", tr.CHANGED_SCAN_HOTKEY, "")
    unchanged_scan_hotkey = Hotkey("unchanged_scan_hotkey", tr.UNCHANGED_SCAN_HOTKEY, "")

    @staticmethod
    def get_hotkeys():
        return Hotkeys.pause_hotkey, Hotkeys.break_hotkey, Hotkeys.continue_hotkey, Hotkeys.toggle_attach_hotkey, \
            Hotkeys.exact_scan_hotkey, Hotkeys.increased_scan_hotkey, Hotkeys.decreased_scan_hotkey, \
            Hotkeys.changed_scan_hotkey, Hotkeys.unchanged_scan_hotkey


code_injection_method = int
bring_disassemble_to_front = bool
instructions_per_scroll = int
gdb_path = str
gdb_logging = bool

ignored_signals = str
signal_list = ["SIGUSR1", "SIGPWR", "SIGXCPU", "SIGSEGV"]

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

# used for automatically updating the values in the saved address tree widget
# see UpdateAddressTableThread
saved_addresses_changed_list = list()

# vars for communication/storage with the non blocking threads
exiting = 0
progress_running = 0

threadpool = QThreadPool()
# Placeholder number, may have to be changed in the future
threadpool.setMaxThreadCount(10)


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        self.fn(*self.args, **self.kwargs)


def except_hook(exception_type, value, tb):
    focused_widget = app.focusWidget()
    if focused_widget and exception_type == type_defs.GDBInitializeException:
        QMessageBox.information(focused_widget, tr.ERROR, tr.GDB_INIT)
    traceback.print_exception(exception_type, value, tb)


# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = except_hook


def signal_handler(signal, frame):
    GDB_Engine.cancel_last_command()
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, signal_handler)


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while True:
            with GDB_Engine.process_exited_condition:
                GDB_Engine.process_exited_condition.wait()
            self.process_exited.emit()


# Await async output from gdb
class AwaitAsyncOutput(QThread):
    async_output_ready = pyqtSignal(str)

    def __init__(self):
        super(AwaitAsyncOutput, self).__init__()
        self.queue_active = True

    def run(self):
        async_output_queue = GDB_Engine.gdb_async_output.register_queue()
        while self.queue_active:
            try:
                async_output = async_output_queue.get(timeout=5)
            except queue.Empty:
                pass
            else:
                self.async_output_ready.emit(async_output)
        GDB_Engine.gdb_async_output.delete_queue(async_output_queue)

    def stop(self):
        self.queue_active = False


class CheckInferiorStatus(QThread):
    process_stopped = pyqtSignal()
    process_running = pyqtSignal()

    def run(self):
        while True:
            with GDB_Engine.status_changed_condition:
                GDB_Engine.status_changed_condition.wait()
            if GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
                self.process_stopped.emit()
            elif GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_RUNNING:
                self.process_running.emit()


class MainForm(QMainWindow, MainWindow):
    def __init__(self):
        """
            Declare regular expressions for hexadecimal and decimal input
            to be used in checkBox_Hex_stateChanged (or anywhere else that
            they are needed).
        """
        self.qRegExp_hex: Final[QRegularExpression] = QRegularExpression("(0x)?[A-Fa-f0-9]*$")
        self.qRegExp_dec: Final[QRegularExpression] = QRegularExpression("-?[0-9]*")

        super().__init__()
        self.setupUi(self)
        self.hotkey_to_shortcut = {}
        hotkey_to_func = {
            Hotkeys.pause_hotkey: self.pause_hotkey_pressed,
            Hotkeys.break_hotkey: self.break_hotkey_pressed,
            Hotkeys.continue_hotkey: self.continue_hotkey_pressed,
            Hotkeys.toggle_attach_hotkey: self.toggle_attach_hotkey_pressed,
            Hotkeys.exact_scan_hotkey: lambda: self.nextscan_hotkey_pressed(type_defs.SCAN_TYPE.EXACT),
            Hotkeys.increased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(type_defs.SCAN_TYPE.INCREASED),
            Hotkeys.decreased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(type_defs.SCAN_TYPE.DECREASED),
            Hotkeys.changed_scan_hotkey: lambda: self.nextscan_hotkey_pressed(type_defs.SCAN_TYPE.CHANGED),
            Hotkeys.unchanged_scan_hotkey: lambda: self.nextscan_hotkey_pressed(type_defs.SCAN_TYPE.UNCHANGED)
        }
        for hotkey, func in hotkey_to_func.items():
            hotkey.change_func(func)
        GuiUtils.center(self)
        self.treeWidget_AddressTable.setColumnWidth(FROZEN_COL, 50)
        self.treeWidget_AddressTable.setColumnWidth(DESC_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(ADDR_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(TYPE_COL, 150)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_ADDRESS_COL, 110)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_VALUE_COL, 80)
        self.settings = QSettings()
        if not SysUtils.is_path_valid(self.settings.fileName()):
            self.set_default_settings()
        try:
            settings_version = self.settings.value("Misc/version", type=str)
        except Exception as e:
            print("An exception occurred while reading settings version\n", e)
            settings_version = None
        if settings_version != current_settings_version:
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
            GDB_Engine.init_gdb(gdb_path)
        except pexpect.EOF:
            InputDialogForm(item_list=[(tr.GDB_INIT_ERROR, None)], buttons=[QDialogButtonBox.StandardButton.Ok]).exec()
        else:
            self.apply_after_init()

        # This should be changed, only works if you use the current directory
        # Fails if you for example install it to some place like bin
        libscanmem_path = os.path.join(os.getcwd(), "libpince", "libscanmem", "libscanmem.so")
        self.backend = Scanmem(libscanmem_path)
        self.memory_view_window = MemoryViewWindowForm(self)
        self.about_widget = AboutWidgetForm()
        self.await_exit_thread = AwaitProcessExit()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.check_status_thread = CheckInferiorStatus()
        self.check_status_thread.process_stopped.connect(self.on_status_stopped)
        self.check_status_thread.process_running.connect(self.on_status_running)
        self.check_status_thread.process_stopped.connect(self.memory_view_window.process_stopped)
        self.check_status_thread.process_running.connect(self.memory_view_window.process_running)
        self.check_status_thread.start()
        self.update_address_table_thread = Worker(self.update_address_table_loop)
        self.update_search_table_thread = Worker(self.update_search_table_loop)
        self.freeze_thread = Worker(self.freeze_loop)
        global threadpool
        threadpool.start(self.update_address_table_thread)
        threadpool.start(self.update_search_table_thread)
        threadpool.start(self.freeze_thread)
        self.shortcut_open_file = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_open_file.activated.connect(self.pushButton_Open_clicked)
        GuiUtils.append_shortcut_to_tooltip(self.pushButton_Open, self.shortcut_open_file)
        self.shortcut_save_file = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save_file.activated.connect(self.pushButton_Save_clicked)
        GuiUtils.append_shortcut_to_tooltip(self.pushButton_Save, self.shortcut_save_file)

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
        self.scan_mode = type_defs.SCAN_MODE.NEW
        self.pushButton_NewFirstScan_clicked()
        self.comboBox_ScanScope_init()
        self.comboBox_ValueType_init()
        self.checkBox_Hex.stateChanged.connect(self.checkBox_Hex_stateChanged)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_Scan.setValidator(
            QRegularExpressionValidator(QRegularExpression("-?[0-9]*"), parent=self.lineEdit_Scan))
        self.lineEdit_Scan2.setValidator(
            QRegularExpressionValidator(QRegularExpression("-?[0-9]*"), parent=self.lineEdit_Scan2))
        self.comboBox_ScanType.currentIndexChanged.connect(self.comboBox_ScanType_current_index_changed)
        self.comboBox_ScanType_current_index_changed()
        self.pushButton_Settings.clicked.connect(self.pushButton_Settings_clicked)
        self.pushButton_Console.clicked.connect(self.pushButton_Console_clicked)
        self.pushButton_Wiki.clicked.connect(self.pushButton_Wiki_clicked)
        self.pushButton_About.clicked.connect(self.pushButton_About_clicked)
        self.pushButton_AddAddressManually.clicked.connect(self.pushButton_AddAddressManually_clicked)
        self.pushButton_MemoryView.clicked.connect(self.pushButton_MemoryView_clicked)
        self.pushButton_RefreshAdressTable.clicked.connect(self.update_address_table)
        self.pushButton_CopyToAddressTable.clicked.connect(self.copy_to_address_table)
        self.pushButton_CleanAddressTable.clicked.connect(self.delete_address_table_contents)
        self.tableWidget_valuesearchtable.cellDoubleClicked.connect(
            self.tableWidget_valuesearchtable_cell_double_clicked)
        self.treeWidget_AddressTable.itemClicked.connect(self.treeWidget_AddressTable_item_clicked)
        self.treeWidget_AddressTable.itemDoubleClicked.connect(self.treeWidget_AddressTable_item_double_clicked)
        self.treeWidget_AddressTable.expanded.connect(self.resize_address_table)
        self.treeWidget_AddressTable.collapsed.connect(self.resize_address_table)
        icons_directory = GuiUtils.get_icons_directory()
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
        self.auto_attach()

    def set_default_settings(self):
        self.settings.beginGroup("General")
        self.settings.setValue("auto_update_address_table", True)
        self.settings.setValue("address_table_update_interval", 500)
        self.settings.setValue("freeze_interval", 100)
        self.settings.setValue("gdb_output_mode", type_defs.gdb_output_mode(True, True, True))
        self.settings.setValue("auto_attach_list", "")
        self.settings.setValue("auto_attach_regex", False)
        self.settings.setValue("locale", get_locale())
        self.settings.setValue("logo_path", "ozgurozbek/pince_small_transparent.png")
        self.settings.endGroup()
        self.settings.beginGroup("Hotkeys")
        for hotkey in Hotkeys.get_hotkeys():
            self.settings.setValue(hotkey.name, hotkey.default)
        self.settings.endGroup()
        self.settings.beginGroup("CodeInjection")
        self.settings.setValue("code_injection_method", type_defs.INJECTION_METHOD.SIMPLE_DLOPEN_CALL)
        self.settings.endGroup()
        self.settings.beginGroup("Disassemble")
        self.settings.setValue("bring_disassemble_to_front", False)
        self.settings.setValue("instructions_per_scroll", 2)
        self.settings.endGroup()
        self.settings.beginGroup("Debug")
        self.settings.setValue("gdb_path", type_defs.PATHS.GDB_PATH)
        self.settings.setValue("gdb_logging", False)
        self.settings.setValue("ignored_signals", "1,1,1,0")
        self.settings.endGroup()
        self.settings.beginGroup("Misc")
        self.settings.setValue("version", current_settings_version)
        self.settings.endGroup()
        self.apply_settings()

    def apply_after_init(self):
        global gdb_logging
        global ignored_signals

        gdb_logging = self.settings.value("Debug/gdb_logging", type=bool)
        ignored_signals = self.settings.value("Debug/ignored_signals", type=str)
        GDB_Engine.set_logging(gdb_logging)
        for index, ignore_status in enumerate(ignored_signals.split(",")):
            if ignore_status == "1":
                GDB_Engine.ignore_signal(signal_list[index])
            else:
                GDB_Engine.unignore_signal(signal_list[index])

    def apply_settings(self):
        global update_table
        global table_update_interval
        global gdb_output_mode
        global auto_attach_list
        global auto_attach_regex
        global locale
        global logo_path
        global code_injection_method
        global bring_disassemble_to_front
        global instructions_per_scroll
        global gdb_path
        global freeze_interval

        update_table = self.settings.value("General/auto_update_address_table", type=bool)
        table_update_interval = self.settings.value("General/address_table_update_interval", type=int)
        freeze_interval = self.settings.value("General/freeze_interval", type=int)
        gdb_output_mode = self.settings.value("General/gdb_output_mode", type=tuple)
        auto_attach_list = self.settings.value("General/auto_attach_list", type=str)
        auto_attach_regex = self.settings.value("General/auto_attach_regex", type=bool)
        locale = self.settings.value("General/locale", type=str)
        logo_path = self.settings.value("General/logo_path", type=str)
        app.setWindowIcon(QIcon(os.path.join(SysUtils.get_logo_directory(), logo_path)))
        GDB_Engine.set_gdb_output_mode(gdb_output_mode)
        for hotkey in Hotkeys.get_hotkeys():
            hotkey.change_key(self.settings.value("Hotkeys/" + hotkey.name))
        try:
            self.memory_view_window.set_dynamic_debug_hotkeys()
        except AttributeError:
            pass
        code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        bring_disassemble_to_front = self.settings.value("Disassemble/bring_disassemble_to_front", type=bool)
        instructions_per_scroll = self.settings.value("Disassemble/instructions_per_scroll", type=int)
        gdb_path = self.settings.value("Debug/gdb_path", type=str)
        if GDB_Engine.gdb_initialized:
            self.apply_after_init()

    # Check if any process should be attached to automatically
    # Patterns at former positions have higher priority if regex is off
    def auto_attach(self):
        if not auto_attach_list:
            return
        if auto_attach_regex:
            try:
                compiled_re = re.compile(auto_attach_list)
            except:
                print("Auto-attach failed: " + auto_attach_list + " isn't a valid regex")
                return
            for pid, _, name in SysUtils.get_process_list():
                if compiled_re.search(name):
                    self.attach_to_pid(pid)
                    self.flashAttachButton = False
                    return
        else:
            for target in auto_attach_list.split(";"):
                for pid, _, name in SysUtils.get_process_list():
                    if name.find(target) != -1:
                        self.attach_to_pid(pid)
                        self.flashAttachButton = False
                        return

    # Keyboard package has an issue with exceptions, any trigger function that throws an exception stops the event loop
    # Writing a custom event loop instead of ignoring exceptions could work as well but honestly, this looks cleaner
    # Keyboard package does not play well with Qt, do not use anything Qt related with hotkeys
    # Instead of using Qt functions, try to use their signals to prevent crashes
    @SysUtils.ignore_exceptions
    def pause_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior(type_defs.STOP_REASON.PAUSE)

    @SysUtils.ignore_exceptions
    def break_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior()

    @SysUtils.ignore_exceptions
    def continue_hotkey_pressed(self):
        GDB_Engine.continue_inferior()

    @SysUtils.ignore_exceptions
    def toggle_attach_hotkey_pressed(self):
        result = GDB_Engine.toggle_attach()
        if not result:
            print("Unable to toggle attach")
        elif result == type_defs.TOGGLE_ATTACH.DETACHED:
            self.on_status_detached()

    @SysUtils.ignore_exceptions
    def nextscan_hotkey_pressed(self, index):
        if self.scan_mode == type_defs.SCAN_MODE.NEW:
            return
        self.comboBox_ScanType.setCurrentIndex(index)
        self.pushButton_NextScan.clicked.emit()

    def treeWidget_AddressTable_context_menu_event(self, event):
        if self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        current_row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        header = self.treeWidget_AddressTable.headerItem()
        menu = QMenu()
        edit_menu = menu.addMenu(tr.EDIT)
        edit_desc = edit_menu.addAction(f"{header.text(DESC_COL)}[Ctrl+Enter]")
        edit_address = edit_menu.addAction(f"{header.text(ADDR_COL)}[Ctrl+Alt+Enter]")
        edit_type = edit_menu.addAction(f"{header.text(TYPE_COL)}[Alt+Enter]")
        edit_value = edit_menu.addAction(f"{header.text(VALUE_COL)}[Enter]")
        show_hex = menu.addAction(tr.SHOW_HEX)
        show_dec = menu.addAction(tr.SHOW_DEC)
        show_unsigned = menu.addAction(tr.SHOW_UNSIGNED)
        show_signed = menu.addAction(tr.SHOW_SIGNED)
        toggle_record = menu.addAction(f"{tr.TOGGLE_RECORDS}[Space]")
        freeze_menu = menu.addMenu(tr.FREEZE)
        freeze_default = freeze_menu.addAction(tr.DEFAULT)
        freeze_inc = freeze_menu.addAction(tr.INCREMENTAL)
        freeze_dec = freeze_menu.addAction(tr.DECREMENTAL)
        menu.addSeparator()
        browse_region = menu.addAction(f"{tr.BROWSE_MEMORY_REGION}[Ctrl+B]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        cut_record = menu.addAction(f"{tr.CUT_RECORDS}[Ctrl+X]")
        copy_record = menu.addAction(f"{tr.COPY_RECORDS}[Ctrl+C]")
        cut_record_recursively = menu.addAction(f"{tr.CUT_RECORDS_RECURSIVE}[X]")
        copy_record_recursively = menu.addAction(f"{tr.COPY_RECORDS_RECURSIVE}[C]")
        paste_record_before = menu.addAction(f"{tr.PASTE_BEFORE}[Ctrl+V]")
        paste_record_after = menu.addAction(f"{tr.PASTE_AFTER}[V]")
        paste_record_inside = menu.addAction(f"{tr.PASTE_INSIDE}[I]")
        delete_record = menu.addAction(f"{tr.DELETE_RECORDS}[Del]")
        menu.addSeparator()
        what_writes = menu.addAction(tr.WHAT_WRITES)
        what_reads = menu.addAction(tr.WHAT_READS)
        what_accesses = menu.addAction(tr.WHAT_ACCESSES)
        if current_row is None:
            deletion_list = [edit_menu.menuAction(), show_hex, show_dec, show_unsigned, show_signed, toggle_record,
                             freeze_menu.menuAction(), browse_region, disassemble, what_writes, what_reads,
                             what_accesses]
            GuiUtils.delete_menu_entries(menu, deletion_list)
        else:
            value_type = current_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            if type_defs.VALUE_INDEX.is_integer(value_type.value_index):
                if value_type.value_repr is type_defs.VALUE_REPR.HEX:
                    GuiUtils.delete_menu_entries(menu, [show_unsigned, show_signed, show_hex])
                elif value_type.value_repr is type_defs.VALUE_REPR.UNSIGNED:
                    GuiUtils.delete_menu_entries(menu, [show_unsigned, show_dec])
                elif value_type.value_repr is type_defs.VALUE_REPR.SIGNED:
                    GuiUtils.delete_menu_entries(menu, [show_signed, show_dec])
                if current_row.checkState(FROZEN_COL) == Qt.CheckState.Unchecked:
                    GuiUtils.delete_menu_entries(menu, [freeze_menu.menuAction()])
            else:
                GuiUtils.delete_menu_entries(menu, [show_hex, show_dec, show_unsigned, show_signed,
                                                    freeze_menu.menuAction()])
        font_size = self.treeWidget_AddressTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            edit_desc: self.treeWidget_AddressTable_edit_desc,
            edit_address: self.treeWidget_AddressTable_edit_address,
            edit_type: self.treeWidget_AddressTable_edit_type,
            edit_value: self.treeWidget_AddressTable_edit_value,
            show_hex: lambda: self.treeWidget_AddressTable_change_repr(type_defs.VALUE_REPR.HEX),
            show_dec: lambda: self.treeWidget_AddressTable_change_repr(type_defs.VALUE_REPR.UNSIGNED),
            show_unsigned: lambda: self.treeWidget_AddressTable_change_repr(type_defs.VALUE_REPR.UNSIGNED),
            show_signed: lambda: self.treeWidget_AddressTable_change_repr(type_defs.VALUE_REPR.SIGNED),
            toggle_record: self.toggle_selected_records,
            freeze_default: lambda: self.change_freeze_type(type_defs.FREEZE_TYPE.DEFAULT),
            freeze_inc: lambda: self.change_freeze_type(type_defs.FREEZE_TYPE.INCREMENT),
            freeze_dec: lambda: self.change_freeze_type(type_defs.FREEZE_TYPE.DECREMENT),
            browse_region: self.browse_region_for_selected_row,
            disassemble: self.disassemble_selected_row,
            cut_record: self.cut_selected_records,
            copy_record: self.copy_selected_records,
            cut_record_recursively: self.cut_selected_records_recursively,
            copy_record_recursively: self.copy_selected_records_recursively,
            paste_record_before: lambda: self.paste_records(insert_after=False),
            paste_record_after: lambda: self.paste_records(insert_after=True),
            paste_record_inside: lambda: self.paste_records(insert_inside=True),
            delete_record: self.delete_selected_records,
            what_writes: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.WRITE_ONLY),
            what_reads: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.READ_ONLY),
            what_accesses: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.BOTH)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def exec_track_watchpoint_widget(self, watchpoint_type):
        selected_row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if not selected_row:
            return
        address = selected_row.text(ADDR_COL).strip("P->")  # @todo Maybe rework address grabbing logic in the future
        address_data = selected_row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
        if isinstance(address_data, type_defs.PointerType):
            selection_dialog = TrackSelectorDialogForm()
            selection_dialog.exec()
            if not selection_dialog.selection:
                return
            if selection_dialog.selection == "pointer":
                address = address_data.get_base_address()
        value_type = selected_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        if type_defs.VALUE_INDEX.is_string(value_type.value_index):
            value_text = selected_row.text(VALUE_COL)
            encoding, option = type_defs.string_index_to_encoding_dict[value_type.value_index]
            byte_len = len(value_text.encode(encoding, option))
        elif value_type.value_index == type_defs.VALUE_INDEX.INDEX_AOB:
            byte_len = value_type.length
        else:
            byte_len = type_defs.index_to_valuetype_dict[value_type.value_index][0]
        TrackWatchpointWidgetForm(address, byte_len, watchpoint_type, self).show()

    def browse_region_for_selected_row(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if row:
            self.memory_view_window.hex_dump_address(int(row.text(ADDR_COL).strip("P->"), 16))
            self.memory_view_window.show()
            self.memory_view_window.activateWindow()

    def disassemble_selected_row(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if row:
            if self.memory_view_window.disassemble_expression(row.text(ADDR_COL).strip("P->"),
                                                              append_to_travel_history=True):
                self.memory_view_window.show()
                self.memory_view_window.activateWindow()

    def change_freeze_type(self, freeze_type):
        for row in self.treeWidget_AddressTable.selectedItems():
            frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            frozen.freeze_type = freeze_type

            # TODO: Create a QWidget subclass with signals so freeze type can be changed by clicking on the cell
            if freeze_type == type_defs.FREEZE_TYPE.DEFAULT:
                row.setText(FROZEN_COL, "")
                row.setForeground(FROZEN_COL, QBrush())
            elif freeze_type == type_defs.FREEZE_TYPE.INCREMENT:
                row.setText(FROZEN_COL, "▲")
                row.setForeground(FROZEN_COL, QBrush(QColor(0, 255, 0)))
            elif freeze_type == type_defs.FREEZE_TYPE.DECREMENT:
                row.setText(FROZEN_COL, "▼")
                row.setForeground(FROZEN_COL, QBrush(QColor(255, 0, 0)))

    def toggle_selected_records(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if row:
            check_state = row.checkState(FROZEN_COL)
            new_check_state = Qt.CheckState.Checked if check_state == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setCheckState(FROZEN_COL, new_check_state)
                self.treeWidget_AddressTable_item_clicked(row, FROZEN_COL)

    def cut_selected_records(self):
        # Flat cut, does not preserve structure
        self.copy_selected_records()
        self.delete_selected_records()

    def copy_selected_records(self):
        # Flat copy, does not preserve structure
        app.clipboard().setText(repr([self.read_address_table_entries(selected_row, True) + ((),) for selected_row in
                                      self.treeWidget_AddressTable.selectedItems()]))
        # each element in the list has no children

    def cut_selected_records_recursively(self):
        self.copy_selected_records_recursively()
        self.delete_selected_records()

    def copy_selected_records_recursively(self):
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
            if index[:len(last_index)] == last_index:
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
            frozen = type_defs.Frozen("", type_defs.FREEZE_TYPE.DEFAULT)
            row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)

            # Deserialize the address_expr & value_type param
            if type(rec[1]) in [list, tuple]:
                address_expr = type_defs.PointerType(*rec[1])
            else:
                address_expr = rec[1]
            value_type = type_defs.ValueType(*rec[2])
            self.change_address_table_entries(row, rec[0], address_expr, value_type)
            self.insert_records(rec[-1], row, 0)
            rows.append(row)

        parent_row.insertChildren(insert_index, rows)

    def paste_records(self, insert_after=None, insert_inside=False):
        try:
            records = ast.literal_eval(app.clipboard().text())
        except (SyntaxError, ValueError):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return

        insert_row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        root = self.treeWidget_AddressTable.invisibleRootItem()
        if not insert_row:  # this is common when the treeWidget_AddressTable is empty
            self.insert_records(records, root, self.treeWidget_AddressTable.topLevelItemCount())
        elif insert_inside:
            self.insert_records(records, insert_row, 0)
        else:
            parent = insert_row.parent() or root
            self.insert_records(records, parent, parent.indexOfChild(insert_row) + insert_after)
        self.update_address_table()

    def delete_selected_records(self):
        root = self.treeWidget_AddressTable.invisibleRootItem()
        for item in self.treeWidget_AddressTable.selectedItems():
            (item.parent() or root).removeChild(item)

    def treeWidget_AddressTable_key_press_event(self, event):
        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete), self.delete_selected_records),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B), self.browse_region_for_selected_row),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D), self.disassemble_selected_row),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_address_table),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space), self.toggle_selected_records),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_X), self.cut_selected_records),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C), self.copy_selected_records),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_X), self.cut_selected_records_recursively),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_C), self.copy_selected_records_recursively),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V),
             lambda: self.paste_records(insert_after=False)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_V),
             lambda: self.paste_records(insert_after=True)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_I),
             lambda: self.paste_records(insert_inside=True)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return),
             self.treeWidget_AddressTable_edit_value),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Return),
             self.treeWidget_AddressTable_edit_desc),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return),
             self.treeWidget_AddressTable_edit_address),
            (
            QKeyCombination(Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return), self.treeWidget_AddressTable_edit_type)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.treeWidget_AddressTable.keyPressEvent_original(event)

    def update_address_table(self):
        if GDB_Engine.currentpid == -1 or self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        mem_handle = GDB_Engine.memory_handle()
        rows = []
        address_list = []
        examine_indices = []
        examine_list = []
        index = 0
        while True:
            row = it.value()
            if not row:
                break
            it += 1
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, type_defs.PointerType):
                address = address_data.base_address
            else:
                address = address_data
            # Simple addresses first, examine_expression takes much longer time, especially for larger tables
            try:
                int(address, 0)
            except (ValueError, TypeError):
                examine_list.append(address)
                examine_indices.append(index)
            address_list.append(address)
            rows.append(row)
            index += 1
        examine_list = [item.address for item in GDB_Engine.examine_expressions(examine_list)]
        for index, address in enumerate(examine_list):
            address_list[examine_indices[index]] = address
        for index, row in enumerate(rows):
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            current_address = address_list[index]
            if isinstance(address_data, type_defs.PointerType):
                # The original base could be a symbol so we have to save it
                # This little hack makes it possible to call examine_expressions only once
                if current_address:
                    old_base = address_data.base_address  # save the old base
                    address_data.base_address = current_address
                    address = GDB_Engine.read_pointer(address_data)
                    address_data.base_address = old_base  # then set it back
                    if address:
                        row.setText(ADDR_COL, f'P->{hex(address)}')
                    else:
                        row.setText(ADDR_COL, 'P->??')
                else:
                    # We already know that base address is an invalid symbol, skip the read_pointer call
                    address = None
                    row.setText(ADDR_COL, 'P->??')
            else:
                address = current_address
                row.setText(ADDR_COL, address or address_data)
            signed = True if value_type.value_repr == type_defs.VALUE_REPR.SIGNED else False
            value = GDB_Engine.read_memory(address, value_type.value_index, value_type.length,
                                           value_type.zero_terminate, signed, mem_handle=mem_handle)
            if value is None:
                value = ""
            elif value_type.value_repr == type_defs.VALUE_REPR.HEX:
                value = hex(value)
            else:
                value = str(value)
            row.setText(VALUE_COL, value)

    def resize_address_table(self):
        self.treeWidget_AddressTable.resizeColumnToContents(FROZEN_COL)

    # gets the information from the dialog then adds it to addresstable
    def pushButton_AddAddressManually_clicked(self):
        manual_address_dialog = ManualAddressDialogForm()
        if manual_address_dialog.exec():
            desc, address_expr, value_index, length, zero_terminate = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(desc, address_expr, value_index, length, zero_terminate)

    def pushButton_MemoryView_clicked(self):
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def pushButton_Wiki_clicked(self):
        SysUtils.execute_command_as_user('python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def pushButton_About_clicked(self):
        self.about_widget.show()
        self.about_widget.activateWindow()

    def pushButton_Settings_clicked(self):
        settings_dialog = SettingsDialogForm(self.set_default_settings)
        if settings_dialog.exec():
            self.apply_settings()

    def pushButton_Console_clicked(self):
        console_widget = ConsoleWidgetForm()
        console_widget.showMaximized()

    def checkBox_Hex_stateChanged(self, state):
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            # allows only things that are hex, can also start with 0x
            self.lineEdit_Scan.setValidator(QRegularExpressionValidator(self.qRegExp_hex, parent=self.lineEdit_Scan))
            self.lineEdit_Scan2.setValidator(QRegularExpressionValidator(self.qRegExp_hex, parent=self.lineEdit_Scan2))
        else:
            # sets it back to integers only
            self.lineEdit_Scan.setValidator(QRegularExpressionValidator(self.qRegExp_dec, parent=self.lineEdit_Scan))
            self.lineEdit_Scan2.setValidator(QRegularExpressionValidator(self.qRegExp_dec, parent=self.lineEdit_Scan2))

    # TODO add a damn keybind for this...
    def pushButton_NewFirstScan_clicked(self):
        if GDB_Engine.currentpid == -1:
            self.comboBox_ScanType_init()
            return
        if self.scan_mode == type_defs.SCAN_MODE.ONGOING:
            self.reset_scan()
        else:
            self.scan_mode = type_defs.SCAN_MODE.ONGOING
            self.pushButton_NewFirstScan.setText(tr.NEW_SCAN)
            self.comboBox_ValueType.setEnabled(False)
            self.pushButton_NextScan.setEnabled(True)
            self.pushButton_UndoScan.setEnabled(True)
            search_scope = self.comboBox_ScanScope.currentData(Qt.ItemDataRole.UserRole)
            self.backend.send_command("option region_scan_level " + str(search_scope))
            self.backend.reset()
            self.comboBox_ScanScope.setEnabled(False)
            self.pushButton_NextScan_clicked()  # makes code a little simpler to just implement everything in nextscan
        self.comboBox_ScanType_init()

    def pushButton_UndoScan_clicked(self):
        self.pushButton_NextScan_clicked("undo")

    def comboBox_ScanType_current_index_changed(self):
        hidden_types = [type_defs.SCAN_TYPE.INCREASED, type_defs.SCAN_TYPE.DECREASED, type_defs.SCAN_TYPE.CHANGED,
                        type_defs.SCAN_TYPE.UNCHANGED, type_defs.SCAN_TYPE.UNKNOWN]
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) in hidden_types:
            self.widget_Scan.setEnabled(False)
        else:
            self.widget_Scan.setEnabled(True)
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) == type_defs.SCAN_TYPE.BETWEEN:
            self.label_Between.setVisible(True)
            self.lineEdit_Scan2.setVisible(True)
        else:
            self.label_Between.setVisible(False)
            self.lineEdit_Scan2.setVisible(False)

    def comboBox_ScanType_init(self):
        scan_type_text = {
            type_defs.SCAN_TYPE.EXACT: tr.EXACT,
            type_defs.SCAN_TYPE.INCREASED: tr.INCREASED,
            type_defs.SCAN_TYPE.INCREASED_BY: tr.INCREASED_BY,
            type_defs.SCAN_TYPE.DECREASED: tr.DECREASED,
            type_defs.SCAN_TYPE.DECREASED_BY: tr.DECREASED_BY,
            type_defs.SCAN_TYPE.LESS: tr.LESS_THAN,
            type_defs.SCAN_TYPE.MORE: tr.MORE_THAN,
            type_defs.SCAN_TYPE.BETWEEN: tr.BETWEEN,
            type_defs.SCAN_TYPE.CHANGED: tr.CHANGED,
            type_defs.SCAN_TYPE.UNCHANGED: tr.UNCHANGED,
            type_defs.SCAN_TYPE.UNKNOWN: tr.UNKNOWN_VALUE
        }
        current_type = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        self.comboBox_ScanType.clear()
        items = type_defs.SCAN_TYPE.get_list(self.scan_mode)
        old_index = 0
        for index, type_index in enumerate(items):
            if current_type == type_index:
                old_index = index
            self.comboBox_ScanType.addItem(scan_type_text[type_index], type_index)
        self.comboBox_ScanType.setCurrentIndex(old_index)

    def comboBox_ScanScope_init(self):
        scan_scope_text = [
            (type_defs.SCAN_SCOPE.BASIC, tr.BASIC),
            (type_defs.SCAN_SCOPE.NORMAL, tr.NORMAL),
            (type_defs.SCAN_SCOPE.FULL_RW, tr.RW),
            (type_defs.SCAN_SCOPE.FULL, tr.FULL)
        ]
        for scope, text in scan_scope_text:
            self.comboBox_ScanScope.addItem(text, scope)
        self.comboBox_ScanScope.setCurrentIndex(1)  # type_defs.SCAN_SCOPE.NORMAL

    def comboBox_ValueType_init(self):
        self.comboBox_ValueType.clear()
        for value_index, value_text in type_defs.scan_index_to_text_dict.items():
            self.comboBox_ValueType.addItem(value_text, value_index)
        self.comboBox_ValueType.setCurrentIndex(type_defs.SCAN_INDEX.INDEX_INT32)
        self.comboBox_ValueType_current_index_changed()

    # :doc:
    # adds things like 0x when searching for etc, basically just makes the line valid for scanmem
    # this should cover most things, more things might be added later if need be
    def validate_search(self, search_for, search_for2):
        type_index = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        symbol_map = {
            type_defs.SCAN_TYPE.INCREASED: "+",
            type_defs.SCAN_TYPE.DECREASED: "-",
            type_defs.SCAN_TYPE.CHANGED: "!=",
            type_defs.SCAN_TYPE.UNCHANGED: "=",
            type_defs.SCAN_TYPE.UNKNOWN: "snapshot"
        }
        if type_index in symbol_map:
            return symbol_map[type_index]

        # none of these should be possible to be true at the same time
        scan_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        if scan_index == type_defs.SCAN_INDEX.INDEX_FLOAT32 or scan_index == type_defs.SCAN_INDEX.INDEX_FLOAT64:
            # this is odd, since when searching for floats from command line it uses `.` and not `,`
            search_for = search_for.replace(".", ",")
            search_for2 = search_for2.replace(".", ",")
        elif scan_index == type_defs.SCAN_INDEX.INDEX_STRING:
            search_for = "\" " + search_for
        elif self.checkBox_Hex.isChecked():
            if not search_for.startswith("0x"):
                search_for = "0x" + search_for
            if not search_for2.startswith("0x"):
                search_for2 = "0x" + search_for2
        if type_index == type_defs.SCAN_TYPE.BETWEEN:
            return search_for + ".." + search_for2
        cmp_symbols = {
            type_defs.SCAN_TYPE.INCREASED_BY: "+",
            type_defs.SCAN_TYPE.DECREASED_BY: "-",
            type_defs.SCAN_TYPE.LESS: "<",
            type_defs.SCAN_TYPE.MORE: ">"
        }
        if type_index in cmp_symbols:
            return cmp_symbols[type_index] + " " + search_for
        return search_for

    def pushButton_NextScan_clicked(self, search_for=None):
        if GDB_Engine.currentpid == -1:
            return
        global progress_running
        if not search_for:
            search_for = self.validate_search(self.lineEdit_Scan.text(), self.lineEdit_Scan2.text())

        # ProgressBar
        global threadpool
        threadpool.start(Worker(self.update_progress_bar))
        if search_for == "undo":
            self.backend.undo_scan()
        else:
            self.backend.send_command(search_for)
        matches = self.backend.matches()
        progress_running = 0
        match_count = self.backend.get_match_count()
        if match_count > 10000:
            self.label_MatchCount.setText(tr.MATCH_COUNT_LIMITED.format(match_count, 10000))
        else:
            self.label_MatchCount.setText(tr.MATCH_COUNT.format(match_count))
        self.tableWidget_valuesearchtable.setRowCount(0)
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = self._scan_to_length(current_type)
        mem_handle = GDB_Engine.memory_handle()
        for n, address, offset, region_type, val, result_type in matches:
            n = int(n)
            address = "0x" + address
            current_item = QTableWidgetItem(address)
            result = result_type.split(" ")[0]
            value_index = type_defs.scanmem_result_to_index_dict[result]
            signed = False
            if type_defs.VALUE_INDEX.is_integer(value_index) and result.endswith("s"):
                signed = True
            current_item.setData(Qt.ItemDataRole.UserRole, (value_index, signed))
            value = str(GDB_Engine.read_memory(address, value_index, length, signed=signed, mem_handle=mem_handle))
            self.tableWidget_valuesearchtable.insertRow(self.tableWidget_valuesearchtable.rowCount())
            self.tableWidget_valuesearchtable.setItem(n, SEARCH_TABLE_ADDRESS_COL, current_item)
            self.tableWidget_valuesearchtable.setItem(n, SEARCH_TABLE_VALUE_COL, QTableWidgetItem(value))
            self.tableWidget_valuesearchtable.setItem(n, SEARCH_TABLE_PREVIOUS_COL, QTableWidgetItem(value))
            if n == 10000:
                break

    def _scan_to_length(self, type_index):
        if type_index == type_defs.SCAN_INDEX.INDEX_AOB:
            return self.lineEdit_Scan.text().count(" ") + 1
        if type_index == type_defs.SCAN_INDEX.INDEX_STRING:
            return len(self.lineEdit_Scan.text())
        return 0

    def tableWidget_valuesearchtable_cell_double_clicked(self, row, col):
        current_item = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL)
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        self.add_entry_to_addresstable(tr.NO_DESCRIPTION, current_item.text(),
                                       current_item.data(Qt.ItemDataRole.UserRole)[0], length)

    def comboBox_ValueType_current_index_changed(self):
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        validator_map = {
            "int": QRegularExpressionValidator(QRegularExpression("-?[0-9]*"), parent=self.lineEdit_Scan),  # integers
            "float": QRegularExpressionValidator(QRegularExpression("-?[0-9]+[.,]?[0-9]*")),
            # floats, should work fine with the small amount of testing I did
            "bytearray": QRegularExpressionValidator(QRegularExpression("^(([A-Fa-f0-9?]{2} +)+)$"),
                                                     parent=self.lineEdit_Scan),
            # array of bytes
            "string": None
        }
        scanmem_type = type_defs.scan_index_to_scanmem_dict[current_type]
        validator_str = scanmem_type  # used to get the correct validator

        # TODO this can probably be made to look nicer, though it doesn't really matter
        if "int" in validator_str:
            validator_str = "int"
            self.checkBox_Hex.setEnabled(True)
        else:
            self.checkBox_Hex.setChecked(False)
            self.checkBox_Hex.setEnabled(False)
        if "float" in validator_str or validator_str == "number":
            validator_str = "float"

        self.lineEdit_Scan.setValidator(validator_map[validator_str])
        self.lineEdit_Scan2.setValidator(validator_map[validator_str])
        self.backend.send_command("option scan_data_type {}".format(scanmem_type))
        # according to scanmem instructions you should always do `reset` after changing type
        self.backend.reset()

    def pushButton_AttachProcess_clicked(self):
        self.processwindow = ProcessForm(self)
        self.processwindow.show()

    def pushButton_Open_clicked(self):
        pct_file_path = SysUtils.get_user_path(type_defs.USER_PATHS.CHEAT_TABLES_PATH)
        file_paths = QFileDialog.getOpenFileNames(self, tr.OPEN_PCT_FILE, pct_file_path, tr.FILE_TYPES_PCT)[0]
        if not file_paths:
            return
        if self.treeWidget_AddressTable.topLevelItemCount() > 0:
            if InputDialogForm(item_list=[(tr.CLEAR_TABLE,)]).exec():
                self.treeWidget_AddressTable.clear()

        for file_path in file_paths:
            content = SysUtils.load_file(file_path)
            if content is None:
                QMessageBox.information(self, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
                break
            self.insert_records(content, self.treeWidget_AddressTable.invisibleRootItem(),
                                self.treeWidget_AddressTable.topLevelItemCount())

    def pushButton_Save_clicked(self):
        pct_file_path = SysUtils.get_user_path(type_defs.USER_PATHS.CHEAT_TABLES_PATH)
        file_path = QFileDialog.getSaveFileName(self, tr.SAVE_PCT_FILE, pct_file_path, tr.FILE_TYPES_PCT)[0]
        if not file_path:
            return
        content = [self.read_address_table_recursively(self.treeWidget_AddressTable.topLevelItem(i))
                   for i in range(self.treeWidget_AddressTable.topLevelItemCount())]
        file_path = SysUtils.append_file_extension(file_path, "pct")
        if not SysUtils.save_file(content, file_path):
            QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    # Returns: a bool value indicates whether the operation succeeded.
    def attach_to_pid(self, pid):
        attach_result = GDB_Engine.attach(pid, gdb_path)
        if attach_result == type_defs.ATTACH_RESULT.ATTACH_SUCCESSFUL:
            self.apply_after_init()
            self.backend.pid(pid)
            self.on_new_process()

            # TODO: This makes PINCE call on_process_stop twice when attaching
            # TODO: Signal design might have to change to something like mutexes eventually
            self.memory_view_window.on_process_stop()
            GDB_Engine.continue_inferior()
            return True
        else:
            messages = {
                type_defs.ATTACH_RESULT.ATTACH_SELF: tr.SMARTASS,  # easter egg
                type_defs.ATTACH_RESULT.PROCESS_NOT_VALID: tr.PROCESS_NOT_VALID,
                type_defs.ATTACH_RESULT.ALREADY_DEBUGGING: tr.ALREADY_DEBUGGING,
                type_defs.ATTACH_RESULT.ALREADY_TRACED: tr.ALREADY_TRACED.format(SysUtils.is_traced(pid)),
                type_defs.ATTACH_RESULT.PERM_DENIED: tr.PERM_DENIED
            }
            QMessageBox.information(app.focusWidget(), tr.ERROR, messages[attach_result])
            return False

    # Returns: a bool value indicates whether the operation succeeded.
    def create_new_process(self, file_path, args, ld_preload_path):
        if GDB_Engine.create_process(file_path, args, ld_preload_path):
            self.apply_after_init()
            self.on_new_process()
            return True
        else:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.CREATE_PROCESS_ERROR)
            self.on_inferior_exit()
            return False

    # Changes appearance whenever a new process is created or attached
    def on_new_process(self):
        name = SysUtils.get_process_name(GDB_Engine.currentpid)
        self.label_SelectedProcess.setText(str(GDB_Engine.currentpid) + " - " + name)

        # enable scan GUI
        self.lineEdit_Scan.setPlaceholderText(tr.SCAN_FOR)
        self.QWidget_Toolbox.setEnabled(True)
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.pushButton_AddAddressManually.setEnabled(True)
        self.pushButton_MemoryView.setEnabled(True)

        # stop flashing attach button, timer will stop automatically on false value
        self.flashAttachButton = False

    def delete_address_table_contents(self):
        if self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        confirm_dialog = InputDialogForm(item_list=[(tr.CLEAR_TABLE,)])
        if confirm_dialog.exec():
            self.treeWidget_AddressTable.clear()

    def copy_to_address_table(self):
        i = -1
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        for row in self.tableWidget_valuesearchtable.selectedItems():
            i = i + 1
            if i % 3 == 0:
                self.add_entry_to_addresstable("", row.text(), row.data(Qt.ItemDataRole.UserRole)[0], length)

    def reset_scan(self):
        self.scan_mode = type_defs.SCAN_MODE.NEW
        self.pushButton_NewFirstScan.setText(tr.FIRST_SCAN)
        self.backend.reset()
        self.tableWidget_valuesearchtable.setRowCount(0)
        self.comboBox_ValueType.setEnabled(True)
        self.comboBox_ScanScope.setEnabled(True)
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
        GDB_Engine.init_gdb(gdb_path)
        self.apply_after_init()
        self.flashAttachButton = True
        self.flashAttachButtonTimer.start(100)
        self.label_SelectedProcess.setText(tr.NO_PROCESS_SELECTED)

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
        GDB_Engine.detach()
        app.closeAllWindows()

    def add_entry_to_addresstable(self, description, address_expr, value_index, length=0, zero_terminate=True):
        current_row = QTreeWidgetItem()
        current_row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        frozen = type_defs.Frozen("", type_defs.FREEZE_TYPE.DEFAULT)
        current_row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
        value_type = type_defs.ValueType(value_index, length, zero_terminate)
        self.treeWidget_AddressTable.addTopLevelItem(current_row)
        self.change_address_table_entries(current_row, description, address_expr, value_type)
        self.show()  # In case of getting called from elsewhere
        self.activateWindow()

    def treeWidget_AddressTable_item_double_clicked(self, row, column):
        action_for_column = {
            VALUE_COL: self.treeWidget_AddressTable_edit_value,
            DESC_COL: self.treeWidget_AddressTable_edit_desc,
            ADDR_COL: self.treeWidget_AddressTable_edit_address,
            TYPE_COL: self.treeWidget_AddressTable_edit_type
        }
        action_for_column = collections.defaultdict(lambda *args: lambda: None, action_for_column)
        action_for_column[column]()

    # ----------------------------------------------------
    # Async Functions

    def update_progress_bar(self):
        global progress_running
        global exiting
        self.progressBar.setValue(0)
        progress_running = 1
        while progress_running == 1 and exiting == 0:
            sleep(0.1)
            value = int(round(self.backend.get_scan_progress() * 100))
            self.progressBar.setValue(value)

    def update_address_table_loop(self):
        while exiting == 0:
            sleep(table_update_interval / 1000)
            if update_table:
                try:
                    self.update_address_table()
                except:
                    traceback.print_exc()

    def update_search_table_loop(self):
        while exiting == 0:
            sleep(0.5)
            try:
                self.update_search_table()
            except:
                traceback.print_exc()

    def freeze_loop(self):
        while exiting == 0:
            sleep(freeze_interval / 1000)
            try:
                self.freeze()
            except:
                traceback.print_exc()

    # ----------------------------------------------------

    def update_search_table(self):
        if GDB_Engine.currentpid == -1:
            return
        row_count = self.tableWidget_valuesearchtable.rowCount()
        if row_count > 0:
            length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
            mem_handle = GDB_Engine.memory_handle()
            for row_index in range(row_count):
                address_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_ADDRESS_COL)
                previous_text = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_PREVIOUS_COL).text()
                value_index, signed = address_item.data(Qt.ItemDataRole.UserRole)
                address = address_item.text()
                new_value = str(GDB_Engine.read_memory(address, value_index, length, signed=signed,
                                                       mem_handle=mem_handle))
                value_item = QTableWidgetItem(new_value)
                if new_value != previous_text:
                    value_item.setForeground(QBrush(QColor(255, 0, 0)))
                self.tableWidget_valuesearchtable.setItem(row_index, SEARCH_TABLE_VALUE_COL, value_item)

    def freeze(self):
        if GDB_Engine.currentpid == -1:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        while it.value():
            row = it.value()
            if row.checkState(FROZEN_COL) == Qt.CheckState.Checked:
                value_index = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).value_index
                address = row.text(ADDR_COL).strip("P->")
                frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                value = frozen.value
                freeze_type = frozen.freeze_type
                if type_defs.VALUE_INDEX.is_integer(value_index):
                    new_value = GDB_Engine.read_memory(address, value_index)
                    if freeze_type == type_defs.FREEZE_TYPE.INCREMENT and new_value > int(value, 0) or \
                            freeze_type == type_defs.FREEZE_TYPE.DECREMENT and new_value < int(value, 0):
                        frozen.value = str(new_value)
                        GDB_Engine.write_memory(address, value_index, frozen.value)
                        continue
                GDB_Engine.write_memory(address, value_index, value)
            it += 1

    def treeWidget_AddressTable_item_clicked(self, row, column):
        if column == FROZEN_COL:
            if row.checkState(FROZEN_COL) == Qt.CheckState.Checked:
                frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen.value = row.text(VALUE_COL)
            else:
                row.setText(FROZEN_COL, "")
                row.setForeground(FROZEN_COL, QBrush())

    def treeWidget_AddressTable_change_repr(self, new_repr):
        value_type = GuiUtils.get_current_item(self.treeWidget_AddressTable).data(TYPE_COL, Qt.ItemDataRole.UserRole)
        value_type.value_repr = new_repr
        for row in self.treeWidget_AddressTable.selectedItems():
            row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, value_type)
            row.setText(TYPE_COL, value_type.text())
        self.update_address_table()

    def treeWidget_AddressTable_edit_value(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        value = row.text(VALUE_COL)
        value_index = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).value_index
        dialog = InputDialogForm(item_list=[(tr.ENTER_VALUE, value)], parsed_index=0, value_index=value_index)
        if dialog.exec():
            new_value = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                address = row.text(ADDR_COL).strip("P->")
                value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                if type_defs.VALUE_INDEX.has_length(value_type.value_index):
                    unknown_type = SysUtils.parse_string(new_value, value_type.value_index)
                    if unknown_type is not None:
                        value_type.length = len(unknown_type)
                        row.setText(TYPE_COL, value_type.text())
                frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen.value = new_value
                row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
                GDB_Engine.write_memory(address, value_type.value_index, new_value)
            self.update_address_table()

    def treeWidget_AddressTable_edit_desc(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        description = row.text(DESC_COL)
        dialog = InputDialogForm(item_list=[(tr.ENTER_DESCRIPTION, description)])
        if dialog.exec():
            description_text = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setText(DESC_COL, description_text)

    def treeWidget_AddressTable_edit_address(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        desc, address_expr, value_type = self.read_address_table_entries(row)
        manual_address_dialog = ManualAddressDialogForm(description=desc, address=address_expr,
                                                        index=value_type.value_index, length=value_type.length,
                                                        zero_terminate=value_type.zero_terminate)
        manual_address_dialog.setWindowTitle(tr.EDIT_ADDRESS)
        if manual_address_dialog.exec():
            desc, address_expr, value_index, length, zero_terminate = manual_address_dialog.get_values()
            value_type = type_defs.ValueType(value_index, length, zero_terminate, value_type.value_repr)
            self.change_address_table_entries(row, desc, address_expr, value_type)

    def treeWidget_AddressTable_edit_type(self):
        row = GuiUtils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        dialog = EditTypeDialogForm(index=value_type.value_index, length=value_type.length,
                                    zero_terminate=value_type.zero_terminate)
        if dialog.exec():
            value_index, length, zero_terminate = dialog.get_values()
            value_type = type_defs.ValueType(value_index, length, zero_terminate, value_type.value_repr)
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, value_type)
                row.setText(TYPE_COL, value_type.text())
            self.update_address_table()

    # Changes the column values of the given row
    def change_address_table_entries(self, row, description=tr.NO_DESCRIPTION, address_expr="", value_type=None):
        if isinstance(address_expr, type_defs.PointerType):
            address = GDB_Engine.read_pointer(address_expr)
            address_text = f'P->{hex(address)}' if address != None else 'P->??'
        else:
            # Simple addresses first, examine_expression takes much longer time, especially for larger tables
            try:
                address = int(address_expr, 0)
                address_text = hex(address)
            except (ValueError, TypeError):
                address = GDB_Engine.examine_expression(address_expr).address
                address_text = address
        value = ''
        if address:
            value = GDB_Engine.read_memory(address, value_type.value_index, value_type.length,
                                           value_type.zero_terminate)

        assert isinstance(row, QTreeWidgetItem)
        row.setText(DESC_COL, description)
        row.setData(ADDR_COL, Qt.ItemDataRole.UserRole, address_expr)
        row.setText(ADDR_COL, address_text)
        row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, value_type)
        row.setText(TYPE_COL, value_type.text())
        row.setText(VALUE_COL, "" if value is None else str(value))

    # Returns the column values of the given row
    def read_address_table_entries(self, row, serialize=False):
        description = row.text(DESC_COL)
        if serialize:
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, type_defs.PointerType):
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
        return self.read_address_table_entries(row, True) + \
               ([self.read_address_table_recursively(row.child(i)) for i in range(row.childCount())],)
    
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
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_to_parent(self)
        self.refresh_process_table(self.tableWidget_ProcessTable, SysUtils.get_process_list())
        self.pushButton_Close.clicked.connect(self.close)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_clicked)
        self.pushButton_CreateProcess.clicked.connect(self.pushButton_CreateProcess_clicked)
        self.lineEdit_SearchProcess.textChanged.connect(self.generate_new_list)
        self.tableWidget_ProcessTable.itemDoubleClicked.connect(self.pushButton_Open_clicked)

    # refreshes process list
    def generate_new_list(self):
        text = self.lineEdit_SearchProcess.text()
        processlist = SysUtils.search_processes(text)
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            # closes the window whenever ESC key is pressed
            self.close()
        elif e.key() == Qt.Key.Key_Return:
            self.pushButton_Open_clicked()
        elif e.key() == Qt.Key.Key_F1:
            self.pushButton_CreateProcess_clicked()
        elif e.key() == Qt.Key.Key_Down or e.key() == Qt.Key.Key_Up:
            self.tableWidget_ProcessTable.keyPressEvent(QKeyEvent(QEvent.KeyPress, e.key(), Qt.NoModifier))

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
        file_path = QFileDialog.getOpenFileName(self, tr.SELECT_BINARY)[0]
        if file_path:
            items = [(tr.ENTER_OPTIONAL_ARGS, ""), (tr.LD_PRELOAD_OPTIONAL, "")]
            arg_dialog = InputDialogForm(item_list=items)
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
    def __init__(self, parent=None, description=tr.NO_DESCRIPTION, address="0x",
                 index=type_defs.VALUE_INDEX.INDEX_INT32, length=10, zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.adjustSize()
        self.setMinimumWidth(300)
        self.setFixedHeight(self.height())
        self.lineEdit_length.setValidator(QHexValidator(999, self))
        GuiUtils.fill_value_combobox(self.comboBox_ValueType, index)
        self.lineEdit_description.setText(description)
        self.offsetsList = []
        if not isinstance(address, type_defs.PointerType):
            self.lineEdit_address.setText(address)
            self.widget_Pointer.hide()
        else:
            self.checkBox_IsPointer.setChecked(True)
            self.lineEdit_address.setEnabled(False)
            self.lineEdit_PtrStartAddress.setText(address.get_base_address())
            self.create_offsets_list(address)
            self.widget_Pointer.show()
        if type_defs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.label_length.show()
            self.lineEdit_length.show()
            try:
                length = str(length)
            except:
                length = "10"
            self.lineEdit_length.setText(length)
            self.checkBox_zeroterminate.show()
            self.checkBox_zeroterminate.setChecked(zero_terminate)
        elif self.comboBox_ValueType.currentIndex() == type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_length.show()
            self.lineEdit_length.show()
            try:
                length = str(length)
            except:
                length = "10"
            self.lineEdit_length.setText(length)
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_zeroterminate.hide()
        self.setFixedSize(self.layout().sizeHint())
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_length.textChanged.connect(self.update_value_of_address)
        self.checkBox_zeroterminate.stateChanged.connect(self.update_value_of_address)
        self.checkBox_IsPointer.stateChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_PtrStartAddress.textChanged.connect(self.update_value_of_address)
        self.lineEdit_address.textChanged.connect(self.update_value_of_address)
        self.addOffsetButton.clicked.connect(lambda: self.addOffsetLayout(True))
        self.removeOffsetButton.clicked.connect(self.removeOffsetLayout)
        self.label_valueofaddress.contextMenuEvent = self.label_valueofaddress_context_menu_event
        self.update_value_of_address()

    def label_valueofaddress_context_menu_event(self, event):
        menu = QMenu()
        refresh = menu.addAction(tr.REFRESH)
        font_size = self.label_valueofaddress.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.update_value_of_address
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def addOffsetLayout(self, should_update=True):
        offsetFrame = QFrame(self.widget_Pointer)
        offsetLayout = QHBoxLayout(offsetFrame)
        offsetLayout.setContentsMargins(0, 3, 0, 3)
        offsetFrame.setLayout(offsetLayout)
        buttonLeft = QPushButton("<", offsetFrame)
        buttonLeft.setFixedSize(70, 30)
        offsetLayout.addWidget(buttonLeft)
        offsetText = QLineEdit(offsetFrame)
        offsetText.setFixedSize(70, 30)
        offsetText.setText(hex(0))
        offsetText.textChanged.connect(self.update_value_of_address)
        offsetLayout.addWidget(offsetText)
        buttonRight = QPushButton(">", offsetFrame)
        buttonRight.setFixedSize(70, 30)
        offsetLayout.addWidget(buttonRight)
        buttonLeft.clicked.connect(lambda: self.on_offset_arrow_clicked(offsetText, opSub))
        buttonRight.clicked.connect(lambda: self.on_offset_arrow_clicked(offsetText, opAdd))

        self.offsetsList.append(offsetFrame)
        self.verticalLayout_Pointers.insertWidget(0, self.offsetsList[-1])
        if should_update:
            app.processEvents()  # @todo should probably change this once we can properly resize right after creation
            self.setFixedSize(self.layout().sizeHint())
            self.update_value_of_address()

    def removeOffsetLayout(self):
        if len(self.offsetsList) == 0:
            return
        frame = self.offsetsList[-1]
        frame.deleteLater()
        self.verticalLayout_Pointers.removeWidget(frame)
        del self.offsetsList[-1]
        app.processEvents()  # @todo should probably change this once we can properly resize right after delete
        self.setFixedSize(self.layout().sizeHint())
        self.update_value_of_address()

    def update_value_of_address(self):
        if self.checkBox_IsPointer.isChecked():
            pointer_type = type_defs.PointerType(self.lineEdit_PtrStartAddress.text(), self.get_offsets_int_list())
            address = GDB_Engine.read_pointer(pointer_type)
            if address != None:
                address_text = hex(address)
            else:
                address_text = "??"
            self.lineEdit_address.setText(address_text)
        else:
            address = GDB_Engine.examine_expression(self.lineEdit_address.text()).address
        if not address:
            self.label_valueofaddress.setText("<font color=red>??</font>")
            return

        address_type = self.comboBox_ValueType.currentIndex()
        if address_type == type_defs.VALUE_INDEX.INDEX_AOB:
            length = self.lineEdit_length.text()
            value = GDB_Engine.read_memory(address, address_type, length)
        elif type_defs.VALUE_INDEX.is_string(address_type):
            length = self.lineEdit_length.text()
            is_zeroterminate = self.checkBox_zeroterminate.isChecked()
            value = GDB_Engine.read_memory(address, address_type, length, is_zeroterminate)
        else:
            value = GDB_Engine.read_memory(address, address_type)
        self.label_valueofaddress.setText("<font color=red>??</font>" if value is None else str(value))

    def comboBox_ValueType_current_index_changed(self):
        if type_defs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() == type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_zeroterminate.hide()
        if self.checkBox_IsPointer.isChecked():
            self.lineEdit_address.setEnabled(False)
            if self.lineEdit_PtrStartAddress.text() == "":
                self.lineEdit_PtrStartAddress.setText(self.lineEdit_address.text())
            self.widget_Pointer.show()
        else:
            self.lineEdit_address.setEnabled(True)
            self.widget_Pointer.hide()
        self.setFixedSize(self.layout().sizeHint())
        self.update_value_of_address()

    def reject(self):
        super(ManualAddressDialogForm, self).reject()

    def accept(self):
        if self.label_length.isVisible():
            length = self.lineEdit_length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super(ManualAddressDialogForm, self).accept()

    def get_values(self):
        description = self.lineEdit_description.text()
        address = self.lineEdit_address.text()
        length = self.lineEdit_length.text()
        try:
            length = int(length, 0)
        except:
            length = 0
        zero_terminate = False
        if self.checkBox_zeroterminate.isChecked():
            zero_terminate = True
        value_index = self.comboBox_ValueType.currentIndex()
        if self.checkBox_IsPointer.isChecked():
            address = type_defs.PointerType(self.lineEdit_PtrStartAddress.text(), self.get_offsets_int_list())
        return description, address, value_index, length, zero_terminate

    def get_offsets_int_list(self):
        offsetsIntList = []
        for frame in self.offsetsList:
            layout = frame.layout()
            offsetText = layout.itemAt(1).widget().text()
            try:
                offsetValue = int(offsetText, 16)
            except ValueError:
                offsetValue = 0
            offsetsIntList.append(offsetValue)
        return offsetsIntList

    def create_offsets_list(self, address):
        if not isinstance(address, type_defs.PointerType):
            raise TypeError("Passed non-pointer type to create_offsets_list!")

        for offset in address.offsets_list:
            self.addOffsetLayout(False)
            frame = self.offsetsList[-1]
            layout = frame.layout()
            offsetText = layout.itemAt(1).widget().setText(hex(offset))

    def on_offset_arrow_clicked(self, offsetTextWidget, operator_func):
        offsetText = offsetTextWidget.text()
        try:
            offsetValue = int(offsetText, 16)
        except ValueError:
            offsetValue = 0
        sizeVal = type_defs.index_to_valuetype_dict[self.comboBox_ValueType.currentIndex()][0]
        offsetValue = operator_func(offsetValue, sizeVal)
        offsetTextWidget.setText(hex(offsetValue))


class EditTypeDialogForm(QDialog, EditTypeDialog):
    def __init__(self, parent=None, index=type_defs.VALUE_INDEX.INDEX_INT32, length=10, zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setMaximumSize(100, 100)
        self.lineEdit_Length.setValidator(QHexValidator(999, self))
        GuiUtils.fill_value_combobox(self.comboBox_ValueType, index)
        if type_defs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.label_Length.show()
            self.lineEdit_Length.show()
            try:
                length = str(length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(zero_terminate)
        elif self.comboBox_ValueType.currentIndex() == type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_Length.show()
            self.lineEdit_Length.show()
            try:
                length = str(length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.label_Length.hide()
            self.lineEdit_Length.hide()
            self.checkBox_ZeroTerminate.hide()
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)

    def comboBox_ValueType_current_index_changed(self):
        if type_defs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.label_Length.show()
            self.lineEdit_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentIndex() == type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_Length.show()
            self.lineEdit_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.label_Length.hide()
            self.lineEdit_Length.hide()
            self.checkBox_ZeroTerminate.hide()

    def reject(self):
        super(EditTypeDialogForm, self).reject()

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
        super(EditTypeDialogForm, self).accept()

    def get_values(self):
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
        except:
            length = 0
        zero_terminate = False
        if self.checkBox_ZeroTerminate.isChecked():
            zero_terminate = True
        address_type = self.comboBox_ValueType.currentIndex()
        return address_type, length, zero_terminate


class TrackSelectorDialogForm(QDialog, TrackSelectorDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.selection = None
        self.pushButton_Pointer.clicked.connect(lambda: self.change_selection("pointer"))
        self.pushButton_Pointed.clicked.connect(lambda: self.change_selection("pointed"))

    def change_selection(self, selection):
        self.selection = selection
        self.close()


class LoadingDialogForm(QDialog, LoadingDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        if parent:
            GuiUtils.center_to_parent(self)
        self.keyPressEvent = QEvent.ignore

        # Make use of this background_thread when you spawn a LoadingDialogForm
        # Warning: overrided_func() can only return one value, so if your overridden function returns more than one
        # value, refactor your overriden function to return only one object(convert tuple to list etc.)
        # Check refresh_table method of FunctionsInfoWidgetForm for exemplary usage
        self.background_thread = self.BackgroundThread()
        self.background_thread.output_ready.connect(self.accept)
        self.pushButton_Cancel.clicked.connect(self.cancel_thread)
        media_directory = SysUtils.get_media_directory()
        self.movie = QMovie(media_directory + "/LoadingDialog/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(25, 25))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()

    # This function only cancels the last command sent
    # Override this if you want to do dangerous stuff like, God forbid, background_thread.terminate()
    def cancel_thread(self):
        GDB_Engine.cancel_last_command()

    def exec(self):
        self.background_thread.start()
        super(LoadingDialogForm, self).exec()

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
    def __init__(self, parent=None, item_list=None, parsed_index=-1, value_index=type_defs.VALUE_INDEX.INDEX_INT32,
                 buttons=(QDialogButtonBox.StandardButton.Ok, QDialogButtonBox.StandardButton.Cancel)):
        super().__init__(parent=parent)
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
                    Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.TextSelectableByMouse)
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
        for widget in GuiUtils.get_layout_widgets(self.verticalLayout):
            if isinstance(widget, QLabel):
                continue
            widget.setFocus()  # Focus to the first input field
            break
        self.parsed_index = parsed_index
        self.value_index = value_index

    def get_text(self, item):
        try:
            string = item.text()
        except AttributeError:
            string = item.currentText()
        return string

    def get_values(self):
        return self.get_text(self.object_list[0]) if len(self.object_list) == 1 else [self.get_text(item) for item in
                                                                                      self.object_list]

    def accept(self):
        if self.parsed_index != -1:
            item = self.object_list[self.parsed_index]
            if SysUtils.parse_string(self.get_text(item), self.value_index) is None:
                QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                return
        super(InputDialogForm, self).accept()


class TextEditDialogForm(QDialog, TextEditDialog):
    def __init__(self, parent=None, text=""):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.textEdit.setPlainText(str(text))
        self.accept_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut.activated.connect(self.accept)

    def get_values(self):
        return self.textEdit.toPlainText()

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key.Key_Enter:
            pass
        else:
            super(TextEditDialogForm, self).keyPressEvent(QKeyEvent)


class SettingsDialogForm(QDialog, SettingsDialog):
    def __init__(self, set_default_settings_func, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.settings = QSettings()
        self.set_default_settings = set_default_settings_func
        self.hotkey_to_value = {}  # Dict[str:str]-->Dict[Hotkey.name:settings_value]
        self.listWidget_Options.currentRowChanged.connect(self.change_display)
        icons_directory = GuiUtils.get_icons_directory()
        self.pushButton_GDBPath.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        self.listWidget_Functions.currentRowChanged.connect(self.listWidget_Functions_current_row_changed)
        self.keySequenceEdit_Hotkey.keySequenceChanged.connect(self.keySequenceEdit_Hotkey_key_sequence_changed)
        self.pushButton_ClearHotkey.clicked.connect(self.pushButton_ClearHotkey_clicked)
        self.pushButton_ResetSettings.clicked.connect(self.pushButton_ResetSettings_clicked)
        self.pushButton_GDBPath.clicked.connect(self.pushButton_GDBPath_clicked)
        self.checkBox_AutoUpdateAddressTable.stateChanged.connect(self.checkBox_AutoUpdateAddressTable_state_changed)
        self.checkBox_AutoAttachRegex.stateChanged.connect(self.checkBox_AutoAttachRegex_state_changed)
        self.checkBox_AutoAttachRegex_state_changed()
        self.pushButton_HandleSignals.clicked.connect(self.pushButton_HandleSignals_clicked)
        self.handle_signals_data = None
        self.config_gui()

    def accept(self):
        try:
            current_table_update_interval = int(self.lineEdit_UpdateInterval.text())
        except:
            QMessageBox.information(self, tr.ERROR, tr.UPDATE_ASSERT_INT)
            return
        try:
            current_freeze_interval = int(self.lineEdit_FreezeInterval.text())
        except:
            QMessageBox.information(self, tr.ERROR, tr.FREEZE_ASSERT_INT)
            return
        try:
            current_instructions_shown = int(self.lineEdit_InstructionsPerScroll.text())
        except:
            QMessageBox.information(self, tr.ERROR, tr.INSTRUCTION_ASSERT_INT)
            return
        if current_instructions_shown < 1:
            QMessageBox.information(self, tr.ERROR, tr.INSTRUCTION_ASSERT_LT.format(1))
            return
        if not self.checkBox_AutoUpdateAddressTable.isChecked():
            pass
        elif current_table_update_interval < 0 or current_freeze_interval < 0:
            QMessageBox.information(self, tr.ERROR, tr.INTERVAL_ASSERT_NEGATIVE)
            return
        elif current_table_update_interval == 0 or current_freeze_interval == 0:
            if not InputDialogForm(item_list=[(tr.ASKING_FOR_TROUBLE,)]).exec():  # Easter egg
                return
        elif current_table_update_interval < 100:
            if not InputDialogForm(item_list=[(tr.UPDATE_ASSERT_GT.format(100),)]).exec():
                return

        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.settings.setValue("General/address_table_update_interval", current_table_update_interval)
        self.settings.setValue("General/freeze_interval", current_freeze_interval)
        current_gdb_output_mode = type_defs.gdb_output_mode(self.checkBox_OutputModeAsync.isChecked(),
                                                            self.checkBox_OutputModeCommand.isChecked(),
                                                            self.checkBox_OutputModeCommandInfo.isChecked())
        self.settings.setValue("General/gdb_output_mode", current_gdb_output_mode)
        if self.checkBox_AutoAttachRegex.isChecked():
            try:
                re.compile(self.lineEdit_AutoAttachList.text())
            except:
                QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_REGEX.format(self.lineEdit_AutoAttachList.text()))
                return
        self.settings.setValue("General/auto_attach_list", self.lineEdit_AutoAttachList.text())
        self.settings.setValue("General/auto_attach_regex", self.checkBox_AutoAttachRegex.isChecked())
        new_locale = language_list[self.comboBox_Language.currentIndex()][1]
        self.settings.setValue("General/locale", new_locale)
        if locale != new_locale:
            QMessageBox.information(self, tr.INFO, tr.LANG_RESET)
        self.settings.setValue("General/logo_path", self.comboBox_Logo.currentText())
        for hotkey in Hotkeys.get_hotkeys():
            self.settings.setValue("Hotkeys/" + hotkey.name, self.hotkey_to_value[hotkey.name])
        if self.radioButton_SimpleDLopenCall.isChecked():
            injection_method = type_defs.INJECTION_METHOD.SIMPLE_DLOPEN_CALL
        elif self.radioButton_AdvancedInjection.isChecked():
            injection_method = type_defs.INJECTION_METHOD.ADVANCED_INJECTION
        self.settings.setValue("CodeInjection/code_injection_method", injection_method)
        self.settings.setValue("Disassemble/bring_disassemble_to_front",
                               self.checkBox_BringDisassembleToFront.isChecked())
        self.settings.setValue("Disassemble/instructions_per_scroll", current_instructions_shown)
        selected_gdb_path = self.lineEdit_GDBPath.text()
        current_gdb_path = self.settings.value("Debug/gdb_path", type=str)
        if selected_gdb_path != current_gdb_path:
            if InputDialogForm(item_list=[(tr.GDB_RESET,)]).exec():
                GDB_Engine.init_gdb(selected_gdb_path)
        self.settings.setValue("Debug/gdb_path", selected_gdb_path)
        self.settings.setValue("Debug/gdb_logging", self.checkBox_GDBLogging.isChecked())
        if self.handle_signals_data is not None:
            self.settings.setValue("Debug/ignored_signals", ",".join(self.handle_signals_data))
        super(SettingsDialogForm, self).accept()

    def config_gui(self):
        self.checkBox_AutoUpdateAddressTable.setChecked(
            self.settings.value("General/auto_update_address_table", type=bool))
        self.lineEdit_UpdateInterval.setText(
            str(self.settings.value("General/address_table_update_interval", type=int)))
        self.lineEdit_FreezeInterval.setText(str(self.settings.value("General/freeze_interval", type=int)))
        self.checkBox_OutputModeAsync.setChecked(self.settings.value("General/gdb_output_mode").async_output)
        self.checkBox_OutputModeCommand.setChecked(self.settings.value("General/gdb_output_mode").command_output)
        self.checkBox_OutputModeCommandInfo.setChecked(self.settings.value("General/gdb_output_mode").command_info)
        self.lineEdit_AutoAttachList.setText(self.settings.value("General/auto_attach_list", type=str))
        self.checkBox_AutoAttachRegex.setChecked(self.settings.value("General/auto_attach_regex", type=bool))
        self.comboBox_Language.clear()
        cur_loc = self.settings.value("General/locale", type=str)
        for lang, loc in language_list:
            self.comboBox_Language.addItem(lang)
            if loc == cur_loc:
                self.comboBox_Language.setCurrentIndex(self.comboBox_Language.count()-1)
        logo_directory = SysUtils.get_logo_directory()
        logo_list = SysUtils.search_files(logo_directory, "\.(png|jpg|jpeg|svg)$")
        self.comboBox_Logo.clear()
        for logo in logo_list:
            self.comboBox_Logo.addItem(QIcon(os.path.join(logo_directory, logo)), logo)
        self.comboBox_Logo.setCurrentIndex(logo_list.index(self.settings.value("General/logo_path", type=str)))
        self.listWidget_Functions.clear()
        self.hotkey_to_value.clear()
        for hotkey in Hotkeys.get_hotkeys():
            self.listWidget_Functions.addItem(hotkey.desc)
            self.hotkey_to_value[hotkey.name] = self.settings.value("Hotkeys/" + hotkey.name)
        injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        if injection_method == type_defs.INJECTION_METHOD.SIMPLE_DLOPEN_CALL:
            self.radioButton_SimpleDLopenCall.setChecked(True)
        elif injection_method == type_defs.INJECTION_METHOD.ADVANCED_INJECTION:
            self.radioButton_AdvancedInjection.setChecked(True)
        self.checkBox_BringDisassembleToFront.setChecked(
            self.settings.value("Disassemble/bring_disassemble_to_front", type=bool))
        self.lineEdit_InstructionsPerScroll.setText(
            str(self.settings.value("Disassemble/instructions_per_scroll", type=int)))
        self.lineEdit_GDBPath.setText(str(self.settings.value("Debug/gdb_path", type=str)))
        self.checkBox_GDBLogging.setChecked(self.settings.value("Debug/gdb_logging", type=bool))

    def change_display(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def listWidget_Functions_current_row_changed(self, index):
        if index == -1:
            self.keySequenceEdit_Hotkey.clear()
        else:
            self.keySequenceEdit_Hotkey.setKeySequence(self.hotkey_to_value[Hotkeys.get_hotkeys()[index].name])

    def keySequenceEdit_Hotkey_key_sequence_changed(self):
        index = self.listWidget_Functions.currentIndex().row()
        if index == -1:
            self.keySequenceEdit_Hotkey.clear()
        else:
            self.hotkey_to_value[Hotkeys.get_hotkeys()[index].name] = self.keySequenceEdit_Hotkey.keySequence().toString()

    def pushButton_ClearHotkey_clicked(self):
        self.keySequenceEdit_Hotkey.clear()

    def pushButton_ResetSettings_clicked(self):
        confirm_dialog = InputDialogForm(item_list=[(tr.RESET_DEFAULT_SETTINGS,)])
        if confirm_dialog.exec():
            self.set_default_settings()
            self.handle_signals_data = None
            self.config_gui()

    def checkBox_AutoUpdateAddressTable_state_changed(self):
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.QWidget_UpdateInterval.setEnabled(True)
        else:
            self.QWidget_UpdateInterval.setEnabled(False)

    def checkBox_AutoAttachRegex_state_changed(self):
        if self.checkBox_AutoAttachRegex.isChecked():
            self.lineEdit_AutoAttachList.setPlaceholderText(tr.MOUSE_OVER_EXAMPLES)
            self.lineEdit_AutoAttachList.setToolTip(tr.AUTO_ATTACH_TOOLTIP)
        else:
            self.lineEdit_AutoAttachList.setPlaceholderText(tr.SEPARATE_PROCESSES_WITH.format(";"))
            self.lineEdit_AutoAttachList.setToolTip("")

    def pushButton_GDBPath_clicked(self):
        current_path = self.lineEdit_GDBPath.text()
        file_path = QFileDialog.getOpenFileName(self, tr.SELECT_GDB_BINARY, os.path.dirname(current_path))[0]
        if file_path:
            self.lineEdit_GDBPath.setText(file_path)

    def pushButton_HandleSignals_clicked(self):
        if self.handle_signals_data is None:
            self.handle_signals_data = self.settings.value("Debug/ignored_signals", type=str).split(",")
        signal_dialog = HandleSignalsDialogForm(self.handle_signals_data)
        if signal_dialog.exec():
            self.handle_signals_data = signal_dialog.get_values()


class HandleSignalsDialogForm(QDialog, HandleSignalsDialog):
    def __init__(self, signal_data, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.tableWidget_Signals.setRowCount(len(signal_list))
        for index, state in enumerate(signal_data):
            self.tableWidget_Signals.setItem(index, 0, QTableWidgetItem(signal_list[index]))
            widget = QWidget()
            checkbox = QCheckBox()
            layout = QHBoxLayout(widget)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.tableWidget_Signals.setCellWidget(index, 1, widget)
            if state == "1":
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

    def get_values(self):
        final_state = []
        for index in range(len(signal_list)):
            widget = self.tableWidget_Signals.cellWidget(index, 1)
            checkbox = widget.findChild(QCheckBox)
            if checkbox.checkState() == Qt.CheckState.Checked:
                final_state.append("1")
            else:
                final_state.append("0")
        return final_state


class ConsoleWidgetForm(QWidget, ConsoleWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        global instances
        instances.append(self)
        GuiUtils.center(self)
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
                console_output = GDB_Engine.send_command(console_input, cli_output=True)
            else:
                console_output = GDB_Engine.send_command(console_input)
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
        multiline_dialog = TextEditDialogForm(text=self.lineEdit.text())
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
        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up), self.scroll_backwards_history),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down), self.scroll_forwards_history)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.lineEdit.keyPressEvent_original(event)

    def finish_completion(self):
        self.completion_model.setStringList([])

    def complete_command(self):
        if GDB_Engine.gdb_initialized and GDB_Engine.currentpid != -1 and self.lineEdit.text():
            self.completion_model.setStringList(GDB_Engine.complete_command(self.lineEdit.text()))
            self.completer.complete()
        else:
            self.finish_completion()

    def closeEvent(self, QCloseEvent):
        self.await_async_output_thread.stop()
        global instances
        instances.remove(self)


class AboutWidgetForm(QTabWidget, AboutWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)

        # This section has untranslated text since it's just a placeholder
        license_text = open("COPYING").read()
        authors_text = open("AUTHORS").read()
        thanks_text = open("THANKS").read()
        self.textBrowser_License.setPlainText(license_text)
        self.textBrowser_Contributors.append(
            "This is only a placeholder, this section may look different when the project finishes" +
            "\nIn fact, something like a demo-scene for here would look absolutely fabulous <:")
        self.textBrowser_Contributors.append("\n########")
        self.textBrowser_Contributors.append("#AUTHORS#")
        self.textBrowser_Contributors.append("########\n")
        self.textBrowser_Contributors.append(authors_text)
        self.textBrowser_Contributors.append("\n#######")
        self.textBrowser_Contributors.append("#THANKS#")
        self.textBrowser_Contributors.append("#######\n")
        self.textBrowser_Contributors.append(thanks_text)


class MemoryViewWindowForm(QMainWindow, MemoryViewWindow):
    process_stopped = pyqtSignal()
    process_running = pyqtSignal()

    def set_dynamic_debug_hotkeys(self):
        self.actionBreak.setText(tr.BREAK.format(Hotkeys.break_hotkey.get_active_key()))
        self.actionRun.setText(tr.RUN.format(Hotkeys.continue_hotkey.get_active_key()))
        self.actionToggle_Attach.setText(tr.TOGGLE_ATTACH.format(Hotkeys.toggle_attach_hotkey.get_active_key()))

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
        self.actionBreak.triggered.connect(GDB_Engine.interrupt_inferior)
        self.actionRun.triggered.connect(GDB_Engine.continue_inferior)
        self.actionToggle_Attach.triggered.connect(self.parent().toggle_attach_hotkey_pressed)
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

    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        GuiUtils.center(self)
        self.updating_memoryview = False
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

        GuiUtils.center_scroll_bar(self.verticalScrollBar_Disassemble)

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
        self.hex_view_last_selected_address_int = 0
        self.hex_view_current_region = type_defs.tuple_region_info(0, 0, None, None)
        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        
        # Saving the original function because super() doesn't work when we override functions like this
        self.widget_HexView.keyPressEvent_original = self.widget_HexView.keyPressEvent
        self.widget_HexView.keyPressEvent = self.widget_HexView_key_press_event

        self.tableView_HexView_Hex.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Ascii.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Hex.doubleClicked.connect(self.exec_hex_view_edit_dialog)
        self.tableView_HexView_Ascii.doubleClicked.connect(self.exec_hex_view_edit_dialog)

        # Ignoring the event sends it directly to the parent, which is widget_HexView
        self.tableView_HexView_Hex.keyPressEvent = QEvent.ignore
        self.tableView_HexView_Ascii.keyPressEvent = QEvent.ignore

        self.bHexViewScrolling = False  # rejects new scroll requests while scrolling
        self.verticalScrollBar_HexView.wheelEvent = QEvent.ignore

        self.verticalScrollBar_HexView.sliderChange = self.hex_view_scrollbar_sliderchanged

        self.tableWidget_HexView_Address.wheelEvent = QEvent.ignore
        self.tableWidget_HexView_Address.setAutoScroll(False)
        self.tableWidget_HexView_Address.setStyleSheet("QTableWidget {background-color: transparent;}")
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.hex_model = QHexModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.ascii_model = QAsciiModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.tableView_HexView_Hex.setModel(self.hex_model)
        self.tableView_HexView_Ascii.setModel(self.ascii_model)

        self.tableView_HexView_Hex.selectionModel().currentChanged.connect(self.on_hex_view_current_changed)
        self.tableView_HexView_Ascii.selectionModel().currentChanged.connect(self.on_ascii_view_current_changed)

        self.scrollArea_Hex.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_Hex.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.verticalHeader().setDefaultSectionSize(
            self.tableView_HexView_Hex.verticalHeader().defaultSectionSize())

        GuiUtils.center_scroll_bar(self.verticalScrollBar_HexView)

    def show_trace_window(self):
        if GDB_Engine.currentpid == -1:
            return
        TraceInstructionsWindowForm(prompt_dialog=False)

    def step_instruction(self):
        if GDB_Engine.currentpid == -1:
            return
        if self.updating_memoryview:
            return
        GDB_Engine.step_instruction()

    def step_over_instruction(self):
        if GDB_Engine.currentpid == -1:
            return
        if self.updating_memoryview:
            return
        GDB_Engine.step_over_instruction()

    def execute_till_return(self):
        if GDB_Engine.currentpid == -1:
            return
        if self.updating_memoryview:
            return
        GDB_Engine.execute_till_return()

    def set_address(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        GDB_Engine.set_convenience_variable("pc", current_address)
        self.refresh_disassemble_view()

    def edit_instruction(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        bytes_aob = self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text()
        EditInstructionDialogForm(current_address, bytes_aob, self).exec()

    def nop_instruction(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        array_of_bytes = self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text()
        GDB_Engine.nop_instruction(current_address_int, len(array_of_bytes.split()))
        self.refresh_disassemble_view()

    def toggle_breakpoint(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        if GDB_Engine.check_address_in_breakpoints(current_address_int):
            GDB_Engine.delete_breakpoint(current_address)
        else:
            if not GDB_Engine.add_breakpoint(current_address):
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(current_address))
        self.refresh_disassemble_view()

    def toggle_watchpoint(self, address, watchpoint_type=type_defs.WATCHPOINT_TYPE.BOTH):
        if GDB_Engine.currentpid == -1:
            return
        if GDB_Engine.check_address_in_breakpoints(address):
            GDB_Engine.delete_breakpoint(hex(address))
        else:
            watchpoint_dialog = InputDialogForm(item_list=[(tr.ENTER_WATCHPOINT_LENGTH, "")])
            if watchpoint_dialog.exec():
                user_input = watchpoint_dialog.get_values()
                user_input_int = SysUtils.parse_string(user_input, type_defs.VALUE_INDEX.INDEX_INT32)
                if user_input_int is None:
                    QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR_INT.format(user_input))
                    return
                if user_input_int < 1:
                    QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_ASSERT_LT.format(1))
                    return
                if len(GDB_Engine.add_watchpoint(hex(address), user_input_int, watchpoint_type)) < 1:
                    QMessageBox.information(self, tr.ERROR, tr.WATCHPOINT_FAILED.format(hex(address)))
        self.refresh_hex_view()

    def label_HexView_Information_context_menu_event(self, event):
        if GDB_Engine.currentpid == -1:
            return

        def copy_to_clipboard():
            app.clipboard().setText(self.label_HexView_Information.text())

        menu = QMenu()
        copy_label = menu.addAction(tr.COPY_CLIPBOARD)
        font_size = self.label_HexView_Information.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_label: copy_to_clipboard
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def widget_HexView_context_menu_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        selected_address = self.tableView_HexView_Hex.get_selected_address()
        menu = QMenu()
        edit = menu.addAction(tr.EDIT)
        menu.addSeparator()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        add_address = menu.addAction(f"{tr.ADD_TO_ADDRESS_LIST}[Ctrl+A]")
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        watchpoint_menu = menu.addMenu(tr.SET_WATCHPOINT)
        watchpoint_write = watchpoint_menu.addAction(tr.WRITE_ONLY)
        watchpoint_read = watchpoint_menu.addAction(tr.READ_ONLY)
        watchpoint_both = watchpoint_menu.addAction(tr.BOTH)
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        delete_breakpoint = menu.addAction(tr.DELETE_BREAKPOINT)
        if not GDB_Engine.check_address_in_breakpoints(selected_address):
            GuiUtils.delete_menu_entries(menu, [add_condition, delete_breakpoint])
        else:
            GuiUtils.delete_menu_entries(menu, [watchpoint_menu.menuAction()])
        font_size = self.widget_HexView.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            edit: self.exec_hex_view_edit_dialog,
            go_to: self.exec_hex_view_go_to_dialog,
            disassemble: lambda: self.disassemble_expression(hex(selected_address), append_to_travel_history=True),
            add_address: self.exec_hex_view_add_address_dialog,
            refresh: self.refresh_hex_view,
            watchpoint_write: lambda: self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.WRITE_ONLY),
            watchpoint_read: lambda: self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.READ_ONLY),
            watchpoint_both: lambda: self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.BOTH),
            add_condition: lambda: self.add_breakpoint_condition(selected_address),
            delete_breakpoint: lambda: self.toggle_watchpoint(selected_address)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def exec_hex_view_edit_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_address = self.tableView_HexView_Hex.get_selected_address()
        HexEditDialogForm(hex(selected_address)).exec()
        self.refresh_hex_view()

    def exec_hex_view_go_to_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        current_address = hex(self.tableView_HexView_Hex.get_selected_address())
        go_to_dialog = InputDialogForm(item_list=[(tr.ENTER_EXPRESSION, current_address)])
        if go_to_dialog.exec():
            expression = go_to_dialog.get_values()
            dest_address = GDB_Engine.examine_expression(expression).address
            if not dest_address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID.format(expression))
                return
            self.hex_dump_address(int(dest_address, 16))

    def exec_hex_view_add_address_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_address = self.tableView_HexView_Hex.get_selected_address()
        manual_address_dialog = ManualAddressDialogForm(address=hex(selected_address),
                                                        index=type_defs.VALUE_INDEX.INDEX_AOB)
        if manual_address_dialog.exec():
            desc, address_expr, value_index, length, zero_terminate = manual_address_dialog.get_values()
            self.parent().add_entry_to_addresstable(desc, address_expr, value_index, length, zero_terminate)

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
            next_address = current_address - 0x40
        else:
            next_address = current_address + 0x40
        self.hex_dump_address(next_address)
        GuiUtils.center_scroll_bar(self.verticalScrollBar_HexView)
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
            self.tableWidget_Disassemble_scroll("previous", instructions_per_scroll)
        else:
            self.tableWidget_Disassemble_scroll("next", instructions_per_scroll)
        GuiUtils.center_scroll_bar(self.verticalScrollBar_Disassemble)
        self.bDisassemblyScrolling = False

    def on_hex_view_current_changed(self, QModelIndex_current):
        if GDB_Engine.currentpid == -1:
            return
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView_HexView_Ascii.selectionModel().setCurrentIndex(QModelIndex_current,
                                                                      QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.tableWidget_HexView_Address.selectRow(QModelIndex_current.row())
        self.hex_view_last_selected_address_int = self.tableView_HexView_Hex.get_selected_address()
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

    def on_ascii_view_current_changed(self, QModelIndex_current):
        if GDB_Engine.currentpid == -1:
            return
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tableView_HexView_Hex.selectionModel().setCurrentIndex(QModelIndex_current,
                                                                    QItemSelectionModel.SelectionFlag.ClearAndSelect)
        self.tableWidget_HexView_Address.selectRow(QModelIndex_current.row())
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

    # TODO: Consider merging HexView_Address, HexView_Hex and HexView_Ascii into one UI class
    # TODO: Move this function to that class if that happens
    # TODO: Also consider moving shared fields of HexView and HexModel to that class(such as HexModel.current_address)
    def hex_dump_address(self, int_address, offset=HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT):
        if GDB_Engine.currentpid == -1:
            return
        int_address = SysUtils.modulo_address(int_address, GDB_Engine.inferior_arch)
        if not (self.hex_view_current_region.start <= int_address < self.hex_view_current_region.end):
            info = SysUtils.get_region_info(GDB_Engine.currentpid, int_address)
            if info:
                self.hex_view_current_region = info
                self.label_HexView_Information.setText(tr.REGION_INFO.format(
                    info.perms, hex(info.start), hex(info.end), info.file_name))
            else:
                self.hex_view_current_region = type_defs.tuple_region_info(0, 0, None, None)
                self.label_HexView_Information.setText(tr.INVALID_REGION)
        self.tableWidget_HexView_Address.setRowCount(0)
        self.tableWidget_HexView_Address.setRowCount(HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT)
        for row, current_offset in enumerate(range(HEX_VIEW_ROW_COUNT)):
            row_address = hex(SysUtils.modulo_address(int_address + current_offset * 16, GDB_Engine.inferior_arch))
            self.tableWidget_HexView_Address.setItem(row, 0, QTableWidgetItem(row_address))
        tableWidget_HexView_column_size = self.tableWidget_HexView_Address.sizeHintForColumn(0) + 5
        self.tableWidget_HexView_Address.setMaximumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setMinimumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setColumnWidth(0, tableWidget_HexView_column_size)
        data_array = GDB_Engine.hex_dump(int_address, offset)
        breakpoint_info = GDB_Engine.get_breakpoint_info()
        self.hex_model.refresh(int_address, offset, data_array, breakpoint_info)
        self.ascii_model.refresh(int_address, offset, data_array, breakpoint_info)
        for index in range(offset):
            current_address = SysUtils.modulo_address(self.hex_model.current_address + index, GDB_Engine.inferior_arch)
            if current_address == self.hex_view_last_selected_address_int:
                row_index = int(index / HEX_VIEW_COL_COUNT)
                model_index = QModelIndex(self.hex_model.index(row_index, index % HEX_VIEW_COL_COUNT))
                self.tableView_HexView_Hex.selectionModel().setCurrentIndex(model_index,
                                                                            QItemSelectionModel.SelectionFlag.ClearAndSelect)
                self.tableView_HexView_Ascii.selectionModel().setCurrentIndex(model_index,
                                                                              QItemSelectionModel.SelectionFlag.ClearAndSelect)
                self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
                self.tableWidget_HexView_Address.selectRow(row_index)
                self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
                break
        else:
            self.tableView_HexView_Hex.clearSelection()
            self.tableView_HexView_Ascii.clearSelection()

    def refresh_hex_view(self):
        if GDB_Engine.currentpid == -1:
            return
        if self.tableWidget_HexView_Address.rowCount() == 0:
            entry_point = GDB_Engine.find_entry_point()
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
        if GDB_Engine.currentpid == -1:
            return
        disas_data = GDB_Engine.disassemble(expression, offset)
        if not disas_data:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.EXPRESSION_ACCESS_ERROR.format(expression))
            return False
        program_counter = GDB_Engine.examine_expression("$pc").address
        program_counter_int = int(program_counter, 16) if program_counter else None
        row_color = {}
        breakpoint_info = GDB_Engine.get_breakpoint_info()

        # TODO: Change this nonsense when the huge refactorization happens
        current_first_address = SysUtils.extract_address(disas_data[0][0])  # address of first list entry
        try:
            previous_first_address = SysUtils.extract_address(
                self.tableWidget_Disassemble.item(0, DISAS_ADDR_COL).text())
        except AttributeError:
            previous_first_address = current_first_address

        self.tableWidget_Disassemble.setRowCount(0)
        self.tableWidget_Disassemble.setRowCount(len(disas_data))
        jmp_dict, call_dict = GDB_Engine.get_dissect_code_data(False, True, True)
        for row, (address_info, bytes_aob, opcode) in enumerate(disas_data):
            comment = ""
            current_address = int(SysUtils.extract_address(address_info), 16)
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
        if GDB_Engine.currentpid == -1:
            return
        self.disassemble_expression(self.disassemble_currently_displayed_address)

    # Set color of a row if a specific address is encountered(e.g $pc, a bookmarked address etc.)
    def handle_colors(self, row_color):
        if GDB_Engine.currentpid == -1:
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
        if GDB_Engine.currentpid == -1:
            return
        for col in range(self.tableWidget_Disassemble.columnCount()):
            color = QColor(color)
            color.setAlpha(96)
            self.tableWidget_Disassemble.item(row, col).setData(Qt.ItemDataRole.BackgroundRole, color)

    def on_process_stop(self):
        if GDB_Engine.stop_reason == type_defs.STOP_REASON.PAUSE:
            self.setWindowTitle(tr.MV_PAUSED)
            return
        self.updating_memoryview = True
        time0 = time()
        self.setWindowTitle(tr.MV_DEBUGGING.format(GDB_Engine.get_thread_info()))
        self.disassemble_expression("$pc")
        self.update_registers()
        if self.stackedWidget_StackScreens.currentWidget() == self.StackTrace:
            self.update_stacktrace()
        elif self.stackedWidget_StackScreens.currentWidget() == self.Stack:
            self.update_stack()
        self.refresh_hex_view()
        if bring_disassemble_to_front:
            self.showMaximized()
            self.activateWindow()
        try:
            if self.stacktrace_info_widget.isVisible():
                self.stacktrace_info_widget.update_stacktrace()
        except AttributeError:
            pass
        try:
            if self.float_registers_widget.isVisible():
                self.float_registers_widget.update_registers()
        except AttributeError:
            pass
        app.processEvents()
        time1 = time()
        print("UPDATED MEMORYVIEW IN:" + str(time1 - time0))
        self.updating_memoryview = False

    def on_process_running(self):
        self.setWindowTitle(tr.MV_RUNNING)

    def add_breakpoint_condition(self, int_address):
        if GDB_Engine.currentpid == -1:
            return
        breakpoint = GDB_Engine.check_address_in_breakpoints(int_address)
        if breakpoint:
            condition_line_edit_text = breakpoint.condition
        else:
            condition_line_edit_text = ""
        condition_dialog = InputDialogForm(
            item_list=[(tr.ENTER_BP_CONDITION, condition_line_edit_text, Qt.AlignmentFlag.AlignLeft)])
        if condition_dialog.exec():
            condition = condition_dialog.get_values()
            if not GDB_Engine.modify_breakpoint(hex(int_address), type_defs.BREAKPOINT_MODIFY.CONDITION,
                                                condition=condition):
                QMessageBox.information(app.focusWidget(), tr.ERROR, tr.BP_CONDITION_FAILED.format(hex(int_address)))

    def update_registers(self):
        if GDB_Engine.currentpid == -1:
            return
        registers = GDB_Engine.read_registers()
        if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64:
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
        elif GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_32:
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
        if GDB_Engine.currentpid == -1:
            return
        stack_trace_info = GDB_Engine.get_stacktrace_info()
        self.tableWidget_StackTrace.setRowCount(0)
        self.tableWidget_StackTrace.setRowCount(len(stack_trace_info))
        for row, item in enumerate(stack_trace_info):
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_RETURN_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_FRAME_ADDRESS_COL, QTableWidgetItem(item[1]))

    def set_stack_widget(self, stack_widget):
        if GDB_Engine.currentpid == -1:
            return
        self.stackedWidget_StackScreens.setCurrentWidget(stack_widget)
        if stack_widget == self.Stack:
            self.update_stack()
        elif stack_widget == self.StackTrace:
            self.update_stacktrace()

    def tableWidget_StackTrace_context_menu_event(self, event):
        if GDB_Engine.currentpid == -1:
            return

        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_StackTrace.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_StackTrace)

        menu = QMenu()
        switch_to_stack = menu.addAction(tr.FULL_STACK)
        menu.addSeparator()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_return = clipboard_menu.addAction(tr.COPY_RETURN_ADDRESS)
        copy_frame = clipboard_menu.addAction(tr.COPY_FRAME_ADDRESS)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [clipboard_menu.menuAction()])
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.tableWidget_StackTrace.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            switch_to_stack: lambda: self.set_stack_widget(self.Stack),
            copy_return: lambda: copy_to_clipboard(selected_row, STACKTRACE_RETURN_ADDRESS_COL),
            copy_frame: lambda: copy_to_clipboard(selected_row, STACKTRACE_FRAME_ADDRESS_COL),
            refresh: self.update_stacktrace
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def update_stack(self):
        if GDB_Engine.currentpid == -1:
            return
        stack_info = GDB_Engine.get_stack_info()
        self.tableWidget_Stack.setRowCount(0)
        self.tableWidget_Stack.setRowCount(len(stack_info))
        for row, item in enumerate(stack_info):
            self.tableWidget_Stack.setItem(row, STACK_POINTER_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Stack.setItem(row, STACK_VALUE_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Stack.setItem(row, STACK_POINTS_TO_COL, QTableWidgetItem(item[2]))
        self.tableWidget_Stack.resizeColumnToContents(STACK_POINTER_ADDRESS_COL)
        self.tableWidget_Stack.resizeColumnToContents(STACK_VALUE_COL)

    def tableWidget_Stack_key_press_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Stack)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stack),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
             lambda: self.disassemble_expression(current_address, append_to_travel_history=True)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
             lambda: self.hex_dump_address(int(current_address, 16)))
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Stack.keyPressEvent_original(event)

    def tableWidget_Stack_context_menu_event(self, event):
        if GDB_Engine.currentpid == -1:
            return

        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Stack.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_Stack)
        current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

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
            GuiUtils.delete_menu_entries(menu, [clipboard_menu.menuAction(), show_in_disas, show_in_hex])
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
            show_in_hex: lambda: self.hex_dump_address(int(current_address, 16))
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_Stack_double_click(self, index):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Stack)
        if index.column() == STACK_POINTER_ADDRESS_COL:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_POINTER_ADDRESS_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            self.hex_dump_address(int(current_address, 16))
        else:
            points_to_text = self.tableWidget_Stack.item(selected_row, STACK_POINTS_TO_COL).text()
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            if points_to_text.startswith("(str)"):
                self.hex_dump_address(int(current_address, 16))
            else:
                self.disassemble_expression(current_address, append_to_travel_history=True)

    def tableWidget_StackTrace_double_click(self, index):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_StackTrace)
        if index.column() == STACKTRACE_RETURN_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_RETURN_ADDRESS_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            self.disassemble_expression(current_address, append_to_travel_history=True)
        if index.column() == STACKTRACE_FRAME_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_FRAME_ADDRESS_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            self.hex_dump_address(int(current_address, 16))

    def tableWidget_StackTrace_key_press_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stacktrace)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_StackTrace.keyPressEvent_original(event)

    def widget_Disassemble_wheel_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        steps = event.angleDelta()
        if steps.y() > 0:
            self.tableWidget_Disassemble_scroll("previous", instructions_per_scroll)
        else:
            self.tableWidget_Disassemble_scroll("next", instructions_per_scroll)

    def disassemble_check_viewport(self, where, instruction_count):
        if GDB_Engine.currentpid == -1:
            return
        current_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
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
            current_address = SysUtils.extract_address(
                self.tableWidget_Disassemble.item(current_row, DISAS_ADDR_COL).text())
            new_address = GDB_Engine.find_closest_instruction_address(current_address, "previous", last_visible_row)
            self.disassemble_expression(new_address)
        elif (where == "previous" and current_row == 0) or (where == "next" and current_row_height > height):
            self.tableWidget_Disassemble_scroll(where, instruction_count)

    def tableWidget_Disassemble_scroll(self, where, instruction_count):
        if GDB_Engine.currentpid == -1:
            return
        current_address = self.disassemble_currently_displayed_address
        new_address = GDB_Engine.find_closest_instruction_address(current_address, where, instruction_count)
        self.disassemble_expression(new_address)

    def widget_HexView_wheel_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        steps = event.angleDelta()
        current_address = self.hex_model.current_address
        if steps.y() > 0:
            next_address = current_address - 0x40
        else:
            next_address = current_address + 0x40
        self.hex_dump_address(next_address)

    def widget_HexView_key_press_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        selected_address = self.tableView_HexView_Hex.get_selected_address()

        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G), self.exec_hex_view_go_to_dialog),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
             lambda: self.disassemble_expression(hex(selected_address), append_to_travel_history=True)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_A), self.exec_hex_view_add_address_dialog),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_hex_view),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.hex_view_scroll_up),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.hex_view_scroll_down),
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.widget_HexView.keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space),
             lambda: self.follow_instruction(selected_row)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_E),
             lambda: self.exec_examine_referrers_widget(current_address_text)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G), self.exec_disassemble_go_to_dialog),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
             lambda: self.hex_dump_address(current_address_int)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
             lambda: self.bookmark_address(current_address_int)),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D), self.dissect_current_region),
            (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_T), self.exec_trace_instructions_dialog),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_disassemble_view),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down),
             lambda: self.disassemble_check_viewport("next", 1)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up),
             lambda: self.disassemble_check_viewport("previous", 1)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.disassemble_scroll_up),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.disassemble_scroll_down)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Disassemble.keyPressEvent_original(event)

    def tableWidget_Disassemble_item_double_clicked(self, index):
        if GDB_Engine.currentpid == -1:
            return
        if index.column() == DISAS_COMMENT_COL:
            selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = int(SysUtils.extract_address(current_address_text), 16)
            if current_address in self.tableWidget_Disassemble.bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def tableWidget_Disassemble_item_selection_changed(self):
        if GDB_Engine.currentpid == -1:
            return
        try:
            selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
            selected_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            self.disassemble_last_selected_address_int = int(SysUtils.extract_address(selected_address_text), 16)
        except (TypeError, ValueError, AttributeError):
            pass

    # Search the item in given row for location changing instructions
    # Go to the address pointed by that instruction if it contains any
    def follow_instruction(self, selected_row):
        if GDB_Engine.currentpid == -1:
            return
        address = SysUtils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text())
        if address:
            self.disassemble_expression(address, append_to_travel_history=True)

    def disassemble_go_back(self):
        if GDB_Engine.currentpid == -1:
            return
        if self.tableWidget_Disassemble.travel_history:
            last_location = self.tableWidget_Disassemble.travel_history[-1]
            self.disassemble_expression(last_location)
            self.tableWidget_Disassemble.travel_history.pop()

    def tableWidget_Disassemble_context_menu_event(self, event):
        if GDB_Engine.currentpid == -1:
            return

        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Disassemble.item(row, column).text())

        def copy_all_columns(row):
            copied_string = ""
            for column in range(self.tableWidget_Disassemble.columnCount()):
                copied_string += self.tableWidget_Disassemble.item(row, column).text() + "\t"
            app.clipboard().setText(copied_string)

        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        back = menu.addAction(tr.BACK)
        show_in_hex_view = menu.addAction(f"{tr.HEXVIEW_ADDRESS}[Ctrl+H]")
        menu.addSeparator()
        followable = SysUtils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text())
        follow = menu.addAction(f"{tr.FOLLOW}[Space]")
        if not followable:
            GuiUtils.delete_menu_entries(menu, [follow])
        examine_referrers = menu.addAction(f"{tr.EXAMINE_REFERRERS}[Ctrl+E]")
        if not GuiUtils.contains_reference_mark(current_address_text):
            GuiUtils.delete_menu_entries(menu, [examine_referrers])
        bookmark = menu.addAction(f"{tr.BOOKMARK_ADDRESS}[Ctrl+B]")
        delete_bookmark = menu.addAction(tr.DELETE_BOOKMARK)
        change_comment = menu.addAction(tr.CHANGE_COMMENT)
        is_bookmarked = current_address_int in self.tableWidget_Disassemble.bookmarks
        if not is_bookmarked:
            GuiUtils.delete_menu_entries(menu, [delete_bookmark, change_comment])
        else:
            GuiUtils.delete_menu_entries(menu, [bookmark])
        go_to_bookmark = menu.addMenu(tr.GO_TO_BOOKMARK_ADDRESS)
        address_list = [hex(address) for address in self.tableWidget_Disassemble.bookmarks.keys()]
        bookmark_actions = [go_to_bookmark.addAction(item.all) for item in GDB_Engine.examine_expressions(address_list)]
        menu.addSeparator()
        toggle_breakpoint = menu.addAction(f"{tr.TOGGLE_BREAKPOINT}[F5]")
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        if not GDB_Engine.check_address_in_breakpoints(current_address_int):
            GuiUtils.delete_menu_entries(menu, [add_condition])
        menu.addSeparator()
        edit_instruction = menu.addAction(tr.EDIT_INSTRUCTION)
        nop_instruction = menu.addAction(tr.REPLACE_WITH_NOPS)
        if self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text() == '90':
            GuiUtils.delete_menu_entries(menu, [nop_instruction])
        menu.addSeparator()
        track_breakpoint = menu.addAction(tr.WHAT_ACCESSES_INSTRUCTION)
        trace_instructions = menu.addAction(f"{tr.TRACE_INSTRUCTION}[Ctrl+T]")
        dissect_region = menu.addAction(f"{tr.DISSECT_REGION}[Ctrl+D]")
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
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
            copy_all: lambda: copy_all_columns(selected_row)
        }
        try:
            actions[action]()
        except KeyError:
            pass
        if action in bookmark_actions:
            self.disassemble_expression(SysUtils.extract_address(action.text()), append_to_travel_history=True)

    def dissect_current_region(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        dissect_code_dialog = DissectCodeDialogForm(int_address=int(current_address, 16))
        dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def exec_examine_referrers_widget(self, current_address_text):
        if GDB_Engine.currentpid == -1:
            return
        if not GuiUtils.contains_reference_mark(current_address_text):
            return
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        examine_referrers_widget = ExamineReferrersWidgetForm(current_address_int, self)
        examine_referrers_widget.show()

    def exec_trace_instructions_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        TraceInstructionsWindowForm(current_address, parent=self)

    def exec_track_breakpoint_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_instruction = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        register_expression_dialog = InputDialogForm(item_list=[(tr.ENTER_TRACK_BP_EXPRESSION, "")])
        if register_expression_dialog.exec():
            exp = register_expression_dialog.get_values()
            track_breakpoint_widget = TrackBreakpointWidgetForm(current_address, current_instruction, exp, self)
            track_breakpoint_widget.show()

    def exec_disassemble_go_to_dialog(self):
        if GDB_Engine.currentpid == -1:
            return
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        go_to_dialog = InputDialogForm(item_list=[(tr.ENTER_EXPRESSION, current_address)])
        if go_to_dialog.exec():
            traveled_exp = go_to_dialog.get_values()
            self.disassemble_expression(traveled_exp, append_to_travel_history=True)

    def bookmark_address(self, int_address):
        if GDB_Engine.currentpid == -1:
            return
        if int_address in self.tableWidget_Disassemble.bookmarks:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.ALREADY_BOOKMARKED)
            return
        comment_dialog = InputDialogForm(item_list=[(tr.ENTER_BOOKMARK_COMMENT, "")])
        if comment_dialog.exec():
            comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = comment
        self.refresh_disassemble_view()

    def change_bookmark_comment(self, int_address):
        if GDB_Engine.currentpid == -1:
            return
        current_comment = self.tableWidget_Disassemble.bookmarks[int_address]
        comment_dialog = InputDialogForm(item_list=[(tr.ENTER_BOOKMARK_COMMENT, current_comment)])
        if comment_dialog.exec():
            new_comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = new_comment
        self.refresh_disassemble_view()

    def delete_bookmark(self, int_address):
        if GDB_Engine.currentpid == -1:
            return
        if int_address in self.tableWidget_Disassemble.bookmarks:
            del self.tableWidget_Disassemble.bookmarks[int_address]
            self.refresh_disassemble_view()

    def actionBookmarks_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        bookmark_widget = BookmarkWidgetForm(self)
        bookmark_widget.show()
        bookmark_widget.activateWindow()

    def actionStackTrace_Info_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        self.stacktrace_info_widget = StackTraceInfoWidgetForm()
        self.stacktrace_info_widget.show()

    def actionBreakpoints_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        breakpoint_widget = BreakpointInfoWidgetForm(self)
        breakpoint_widget.show()
        breakpoint_widget.activateWindow()

    def actionFunctions_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        functions_info_widget = FunctionsInfoWidgetForm(self)
        functions_info_widget.show()

    def actionGDB_Log_File_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        log_file_widget = LogFileWidgetForm()
        log_file_widget.showMaximized()

    def actionMemory_Regions_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        memory_regions_widget = MemoryRegionsWidgetForm(self)
        memory_regions_widget.show()

    def actionRestore_Instructions_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        restore_instructions_widget = RestoreInstructionsWidgetForm(self)
        restore_instructions_widget.show()

    def actionReferenced_Strings_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        ref_str_widget = ReferencedStringsWidgetForm(self)
        ref_str_widget.show()

    def actionReferenced_Calls_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        ref_call_widget = ReferencedCallsWidgetForm(self)
        ref_call_widget.show()

    def actionInject_so_file_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        file_path = QFileDialog.getOpenFileName(self, tr.SELECT_SO_FILE, "", tr.SHARED_OBJECT_TYPE)[0]
        if file_path:
            if GDB_Engine.inject_with_dlopen_call(file_path):
                QMessageBox.information(self, tr.SUCCESS, tr.FILE_INJECTED)
            else:
                QMessageBox.information(self, tr.ERROR, tr.FILE_INJECT_FAILED)

    def actionCall_Function_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        call_dialog = InputDialogForm(item_list=[(tr.ENTER_CALL_EXPRESSION, "")])
        if call_dialog.exec():
            result = GDB_Engine.call_function_from_inferior(call_dialog.get_values())
            if result[0]:
                QMessageBox.information(self, tr.SUCCESS, result[0] + " = " + result[1])
            else:
                QMessageBox.information(self, tr.ERROR, tr.CALL_EXPRESSION_FAILED.format(call_dialog.get_values()))

    def actionSearch_Opcode_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        start_address = int(self.disassemble_currently_displayed_address, 16)
        end_address = start_address + 0x30000
        search_opcode_widget = SearchOpcodeWidgetForm(hex(start_address), hex(end_address), self)
        search_opcode_widget.show()

    def actionDissect_Code_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        self.dissect_code_dialog = DissectCodeDialogForm()
        self.dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def actionlibpince_triggered(self):
        if GDB_Engine.currentpid == -1:
            return
        libpince_widget = LibpinceReferenceWidgetForm(is_window=True)
        libpince_widget.showMaximized()

    def pushButton_ShowFloatRegisters_clicked(self):
        if GDB_Engine.currentpid == -1:
            return
        self.float_registers_widget = FloatRegisterWidgetForm()
        self.float_registers_widget.show()
        GuiUtils.center_to_window(self.float_registers_widget, self.widget_Registers)


class BookmarkWidgetForm(QWidget, BookmarkWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget.contextMenuEvent = self.listWidget_context_menu_event
        self.listWidget.currentRowChanged.connect(self.change_display)
        self.listWidget.itemDoubleClicked.connect(self.listWidget_item_double_clicked)
        self.shortcut_delete = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete.activated.connect(self.delete_record)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        self.refresh_table()

    def refresh_table(self):
        self.listWidget.clear()
        address_list = [hex(address) for address in self.parent().tableWidget_Disassemble.bookmarks.keys()]
        self.listWidget.addItems([item.all for item in GDB_Engine.examine_expressions(address_list)])

    def change_display(self, row):
        current_address = SysUtils.extract_address(self.listWidget.item(row).text())
        self.lineEdit_Info.setText(GDB_Engine.get_address_info(current_address))
        self.lineEdit_Comment.setText(self.parent().tableWidget_Disassemble.bookmarks[int(current_address, 16)])

    def listWidget_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def exec_add_entry_dialog(self):
        entry_dialog = InputDialogForm(item_list=[(tr.ENTER_EXPRESSION, "")])
        if entry_dialog.exec():
            text = entry_dialog.get_values()
            address = GDB_Engine.examine_expression(text).address
            if not address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_EXPRESSION)
                return
            self.parent().bookmark_address(int(address, 16))
            self.refresh_table()

    def exec_change_comment_dialog(self, current_address):
        self.parent().change_bookmark_comment(current_address)
        self.refresh_table()

    def listWidget_context_menu_event(self, event):
        current_item = GuiUtils.get_current_item(self.listWidget)
        if current_item:
            current_address = int(SysUtils.extract_address(current_item.text()), 16)
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
            GuiUtils.delete_menu_entries(menu, [change_comment, delete_record])
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.listWidget.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            add_entry: self.exec_add_entry_dialog,
            change_comment: lambda: self.exec_change_comment_dialog(current_address),
            delete_record: self.delete_record,
            refresh: self.refresh_table
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def delete_record(self):
        current_item = GuiUtils.get_current_item(self.listWidget)
        if not current_item:
            return
        current_address = int(SysUtils.extract_address(current_item.text()), 16)
        self.parent().delete_bookmark(current_address)
        self.refresh_table()

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class FloatRegisterWidgetForm(QTabWidget, FloatRegisterWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.update_registers()
        self.tableWidget_FPU.itemDoubleClicked.connect(self.set_register)
        self.tableWidget_XMM.itemDoubleClicked.connect(self.set_register)

    def update_registers(self):
        self.tableWidget_FPU.setRowCount(0)
        self.tableWidget_FPU.setRowCount(8)
        self.tableWidget_XMM.setRowCount(0)
        self.tableWidget_XMM.setRowCount(8)
        float_registers = GDB_Engine.read_float_registers()
        for row, (st, xmm) in enumerate(zip(type_defs.REGISTERS.FLOAT.ST, type_defs.REGISTERS.FLOAT.XMM)):
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(st))
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(float_registers[st]))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(xmm))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(float_registers[xmm]))

    def set_register(self, index):
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
        register_dialog = InputDialogForm(item_list=[(label_text, current_value)])
        if register_dialog.exec():
            if self.currentWidget() == self.XMM:
                current_register += ".v4_float"
            GDB_Engine.set_convenience_variable(current_register, register_dialog.get_values())
            self.update_registers()


class StackTraceInfoWidgetForm(QWidget, StackTraceInfoWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget_ReturnAddresses.currentRowChanged.connect(self.update_frame_info)
        self.update_stacktrace()

    def update_stacktrace(self):
        self.listWidget_ReturnAddresses.clear()
        return_addresses = GDB_Engine.get_stack_frame_return_addresses()
        self.listWidget_ReturnAddresses.addItems(return_addresses)

    def update_frame_info(self, index):
        frame_info = GDB_Engine.get_stack_frame_info(index)
        self.textBrowser_Info.setText(frame_info)


class RestoreInstructionsWidgetForm(QWidget, RestoreInstructionsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Instructions.keyPressEvent_original = self.tableWidget_Instructions.keyPressEvent
        self.tableWidget_Instructions.keyPressEvent = self.tableWidget_Instructions_key_press_event
        self.tableWidget_Instructions.contextMenuEvent = self.tableWidget_Instructions_context_menu_event
        self.tableWidget_Instructions.itemDoubleClicked.connect(self.tableWidget_Instructions_double_clicked)
        self.refresh()

    def tableWidget_Instructions_context_menu_event(self, event):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Instructions)
        menu = QMenu()
        restore_instruction = menu.addAction(tr.RESTORE_INSTRUCTION)
        if selected_row != -1:
            selected_address_text = self.tableWidget_Instructions.item(selected_row, INSTR_ADDR_COL).text()
            selected_address = SysUtils.extract_address(selected_address_text)
            selected_address_int = int(selected_address, 16)
        else:
            GuiUtils.delete_menu_entries(menu, [restore_instruction])
            selected_address_int = None
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.tableWidget_Instructions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            restore_instruction: lambda: self.restore_instruction(selected_address_int),
            refresh: self.refresh
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def restore_instruction(self, selected_address_int):
        GDB_Engine.restore_instruction(selected_address_int)
        self.refresh_all()

    def refresh(self):
        modified_instructions = GDB_Engine.get_modified_instructions()
        self.tableWidget_Instructions.setRowCount(len(modified_instructions))
        for row, (address, aob) in enumerate(modified_instructions.items()):
            self.tableWidget_Instructions.setItem(row, INSTR_ADDR_COL, QTableWidgetItem(hex(address)))
            self.tableWidget_Instructions.setItem(row, INSTR_AOB_COL, QTableWidgetItem(aob))
            instr_name = SysUtils.get_opcodes(address, aob, GDB_Engine.get_inferior_arch())
            if not instr_name:
                instr_name = "??"
            self.tableWidget_Instructions.setItem(row, INSTR_NAME_COL, QTableWidgetItem(instr_name))
        GuiUtils.resize_to_contents(self.tableWidget_Instructions)

    def refresh_all(self):
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def tableWidget_Instructions_key_press_event(self, event):
        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Instructions.keyPressEvent_original(event)

    def tableWidget_Instructions_double_clicked(self, index):
        current_address_text = self.tableWidget_Instructions.item(index.row(), INSTR_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        self.parent().disassemble_expression(current_address, append_to_travel_history=True)

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class BreakpointInfoWidgetForm(QTabWidget, BreakpointInfoWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_BreakpointInfo.contextMenuEvent = self.tableWidget_BreakpointInfo_context_menu_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_BreakpointInfo.keyPressEvent_original = self.tableWidget_BreakpointInfo.keyPressEvent
        self.tableWidget_BreakpointInfo.keyPressEvent = self.tableWidget_BreakpointInfo_key_press_event
        self.tableWidget_BreakpointInfo.itemDoubleClicked.connect(self.tableWidget_BreakpointInfo_double_clicked)
        self.refresh()

    def refresh(self):
        break_info = GDB_Engine.get_breakpoint_info()
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
        GuiUtils.resize_to_contents(self.tableWidget_BreakpointInfo)
        self.textBrowser_BreakpointInfo.clear()
        self.textBrowser_BreakpointInfo.setText(GDB_Engine.send_command("info break", cli_output=True))

    def delete_breakpoint(self, address):
        if address is not None:
            GDB_Engine.delete_breakpoint(address)
            self.refresh_all()

    def tableWidget_BreakpointInfo_key_press_event(self, event):
        selected_row = GuiUtils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
        else:
            current_address = None

        actions = type_defs.KeyboardModifiersTupleDict([
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete),
             lambda: self.delete_breakpoint(current_address)),
            (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh)
        ])
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_BreakpointInfo.keyPressEvent_original(event)

    def exec_enable_count_dialog(self, current_address):
        hit_count_dialog = InputDialogForm(item_list=[(tr.ENTER_HIT_COUNT.format(1), "")])
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
                    GDB_Engine.modify_breakpoint(current_address, type_defs.BREAKPOINT_MODIFY.ENABLE_COUNT,
                                                 count=count)

    def tableWidget_BreakpointInfo_context_menu_event(self, event):
        selected_row = GuiUtils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
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
            deletion_list = [change_condition, enable, disable, enable_once, enable_count, enable_delete,
                             delete_breakpoint]
            GuiUtils.delete_menu_entries(menu, deletion_list)
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.tableWidget_BreakpointInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            change_condition: lambda: self.parent().add_breakpoint_condition(current_address_int),
            enable: lambda: GDB_Engine.modify_breakpoint(current_address, type_defs.BREAKPOINT_MODIFY.ENABLE),
            disable: lambda: GDB_Engine.modify_breakpoint(current_address, type_defs.BREAKPOINT_MODIFY.DISABLE),
            enable_once: lambda: GDB_Engine.modify_breakpoint(current_address, type_defs.BREAKPOINT_MODIFY.ENABLE_ONCE),
            enable_count: lambda: self.exec_enable_count_dialog(current_address),
            enable_delete: lambda: GDB_Engine.modify_breakpoint(current_address,
                                                                type_defs.BREAKPOINT_MODIFY.ENABLE_DELETE),
            delete_breakpoint: lambda: GDB_Engine.delete_breakpoint(current_address),
            refresh: self.refresh
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
        current_address = SysUtils.extract_address(current_address_text)
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

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class TrackWatchpointWidgetForm(QWidget, TrackWatchpointWidget):
    def __init__(self, address, length, watchpoint_type, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.update_timer = QTimer()
        if watchpoint_type == type_defs.WATCHPOINT_TYPE.WRITE_ONLY:
            string = tr.OPCODE_WRITING_TO.format(address)
        elif watchpoint_type == type_defs.WATCHPOINT_TYPE.READ_ONLY:
            string = tr.OPCODE_READING_FROM.format(address)
        elif watchpoint_type == type_defs.WATCHPOINT_TYPE.BOTH:
            string = tr.OPCODE_ACCESSING_TO.format(address)
        else:
            raise Exception("Watchpoint type is invalid: " + str(watchpoint_type))
        self.setWindowTitle(string)
        breakpoints = GDB_Engine.track_watchpoint(address, length, watchpoint_type)
        if not breakpoints:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_WATCHPOINT_FAILED.format(address))
            return
        self.address = address
        self.breakpoints = breakpoints
        self.info = {}
        self.last_selected_row = 0
        self.stopped = False
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.pushButton_Refresh.clicked.connect(self.update_list)
        self.tableWidget_Opcodes.itemDoubleClicked.connect(self.tableWidget_Opcodes_item_double_clicked)
        self.tableWidget_Opcodes.selectionModel().currentChanged.connect(self.tableWidget_Opcodes_current_changed)
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_list)
        self.update_timer.start()

    def update_list(self):
        info = GDB_Engine.get_track_watchpoint_info(self.breakpoints)
        if not info or self.info == info:
            return
        self.info = info
        self.tableWidget_Opcodes.setRowCount(0)
        self.tableWidget_Opcodes.setRowCount(len(info))
        for row, key in enumerate(info):
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_COUNT_COL, QTableWidgetItem(str(info[key][0])))
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_ADDR_COL, QTableWidgetItem(info[key][1]))
        GuiUtils.resize_to_contents(self.tableWidget_Opcodes)
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
            self.tableWidget_Opcodes.item(index.row(), TRACK_WATCHPOINT_ADDR_COL).text(),
            append_to_travel_history=True)
        self.parent().memory_view_window.show()
        self.parent().memory_view_window.activateWindow()

    def pushButton_Stop_clicked(self):
        if self.stopped:
            self.close()
            return
        if not GDB_Engine.delete_breakpoint(self.address):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_WATCHPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)

    def closeEvent(self, QCloseEvent):
        global instances
        self.update_timer.stop()
        if not self.stopped:
            GDB_Engine.delete_breakpoint(self.address)
        self.deleteLater()
        instances.remove(self)


class TrackBreakpointWidgetForm(QWidget, TrackBreakpointWidget):
    def __init__(self, address, instruction, register_expressions, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        self.setWindowFlags(Qt.WindowType.Window)
        GuiUtils.center_to_parent(self)
        self.setWindowTitle(tr.ACCESSED_BY_INSTRUCTION.format(instruction))
        breakpoint = GDB_Engine.track_breakpoint(address, register_expressions)
        if not breakpoint:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_BREAKPOINT_FAILED.format(address))
            return
        self.address = address
        self.breakpoint = breakpoint
        self.info = {}
        self.last_selected_row = 0
        self.stopped = False
        GuiUtils.fill_value_combobox(self.comboBox_ValueType)
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.tableWidget_TrackInfo.itemDoubleClicked.connect(self.tableWidget_TrackInfo_item_double_clicked)
        self.tableWidget_TrackInfo.selectionModel().currentChanged.connect(self.tableWidget_TrackInfo_current_changed)
        self.comboBox_ValueType.currentIndexChanged.connect(self.update_values)
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_list)
        self.update_timer.start()
        self.parent().process_stopped.connect(self.update_values)
        self.parent().refresh_disassemble_view()

    def update_list(self):
        info = GDB_Engine.get_track_breakpoint_info(self.breakpoint)
        if not info:
            return
        if info == self.info:
            return
        self.info = info
        self.tableWidget_TrackInfo.setRowCount(0)
        for register_expression in info:
            for row, address in enumerate(info[register_expression]):
                self.tableWidget_TrackInfo.setRowCount(self.tableWidget_TrackInfo.rowCount() + 1)
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_COUNT_COL,
                                                   QTableWidgetItem(str(info[register_expression][address])))
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_ADDR_COL, QTableWidgetItem(address))
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_SOURCE_COL,
                                                   QTableWidgetItem("[" + register_expression + "]"))
        GuiUtils.resize_to_contents(self.tableWidget_TrackInfo)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def update_values(self):
        mem_handle = GDB_Engine.memory_handle()
        value_type = self.comboBox_ValueType.currentIndex()
        for row in range(self.tableWidget_TrackInfo.rowCount()):
            address = self.tableWidget_TrackInfo.item(row, TRACK_BREAKPOINT_ADDR_COL).text()
            value = GDB_Engine.read_memory(address, value_type, 10, mem_handle=mem_handle)
            value = "" if value is None else str(value)
            self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_VALUE_COL, QTableWidgetItem(value))
        GuiUtils.resize_to_contents(self.tableWidget_TrackInfo)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def tableWidget_TrackInfo_current_changed(self, QModelIndex_current):
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

    def tableWidget_TrackInfo_item_double_clicked(self, index):
        address = self.tableWidget_TrackInfo.item(index.row(), TRACK_BREAKPOINT_ADDR_COL).text()
        self.parent().parent().add_entry_to_addresstable(tr.ACCESSED_BY.format(self.address), address,
                                                         self.comboBox_ValueType.currentIndex(), 10, True)

    def pushButton_Stop_clicked(self):
        if self.stopped:
            self.close()
            return
        if not GDB_Engine.delete_breakpoint(self.address):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_BREAKPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)
        self.parent().refresh_disassemble_view()

    def closeEvent(self, QCloseEvent):
        global instances
        self.update_timer.stop()
        if not self.stopped:
            GDB_Engine.delete_breakpoint(self.address)
        self.parent().refresh_disassemble_view()
        self.deleteLater()
        instances.remove(self)


class TraceInstructionsPromptDialogForm(QDialog, TraceInstructionsPromptDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

    def get_values(self):
        max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        trigger_condition = self.lineEdit_TriggerCondition.text()
        stop_condition = self.lineEdit_StopCondition.text()
        if self.checkBox_StepOver.isChecked():
            step_mode = type_defs.STEP_MODE.STEP_OVER
        else:
            step_mode = type_defs.STEP_MODE.SINGLE_STEP
        stop_after_trace = self.checkBox_StopAfterTrace.isChecked()
        collect_general_registers = self.checkBox_GeneralRegisters.isChecked()
        collect_flag_registers = self.checkBox_FlagRegisters.isChecked()
        collect_segment_registers = self.checkBox_SegmentRegisters.isChecked()
        collect_float_registers = self.checkBox_FloatRegisters.isChecked()
        return (max_trace_count, trigger_condition, stop_condition, step_mode, stop_after_trace,
                collect_general_registers, collect_flag_registers, collect_segment_registers, collect_float_registers)

    def accept(self):
        if int(self.lineEdit_MaxTraceCount.text()) >= 1:
            super(TraceInstructionsPromptDialogForm, self).accept()
        else:
            QMessageBox.information(self, tr.ERROR, tr.MAX_TRACE_COUNT_ASSERT_GT.format(1))


class TraceInstructionsWaitWidgetForm(QWidget, TraceInstructionsWaitWidget):
    widget_closed = pyqtSignal()

    def __init__(self, address, breakpoint, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.status_to_text = {
            type_defs.TRACE_STATUS.STATUS_IDLE: tr.WAITING_FOR_BREAKPOINT,
            type_defs.TRACE_STATUS.STATUS_CANCELED: tr.TRACING_CANCELED,
            type_defs.TRACE_STATUS.STATUS_PROCESSING: tr.PROCESSING_DATA,
            type_defs.TRACE_STATUS.STATUS_FINISHED: tr.TRACING_COMPLETED
        }
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        GuiUtils.center(self)
        self.address = address
        self.breakpoint = breakpoint
        media_directory = SysUtils.get_media_directory()
        self.movie = QMovie(media_directory + "/TraceInstructionsWaitWidget/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(215, 100))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.pushButton_Cancel.clicked.connect(self.close)
        self.status_timer = QTimer()
        self.status_timer.setInterval(30)
        self.status_timer.timeout.connect(self.change_status)
        self.status_timer.start()

    def change_status(self):
        status_info = GDB_Engine.get_trace_instructions_status(self.breakpoint)
        if status_info[0] == type_defs.TRACE_STATUS.STATUS_FINISHED or \
                status_info[0] == type_defs.TRACE_STATUS.STATUS_PROCESSING:
            self.close()
            return
        if status_info[0] == type_defs.TRACE_STATUS.STATUS_TRACING:
            self.label_StatusText.setText(status_info[1])
        else:
            self.label_StatusText.setText(self.status_to_text[status_info[0]])
        app.processEvents()

    def closeEvent(self, QCloseEvent):
        self.status_timer.stop()
        self.label_StatusText.setText(tr.PROCESSING_DATA)
        self.pushButton_Cancel.setVisible(False)
        self.adjustSize()
        app.processEvents()
        status_info = GDB_Engine.get_trace_instructions_status(self.breakpoint)
        if status_info[0] == type_defs.TRACE_STATUS.STATUS_TRACING or \
                status_info[0] == type_defs.TRACE_STATUS.STATUS_PROCESSING:
            GDB_Engine.cancel_trace_instructions(self.breakpoint)
            while GDB_Engine.get_trace_instructions_status(self.breakpoint)[0] \
                    != type_defs.TRACE_STATUS.STATUS_FINISHED:
                sleep(0.1)
                app.processEvents()
        GDB_Engine.delete_breakpoint(self.address)
        self.widget_closed.emit()


class TraceInstructionsWindowForm(QMainWindow, TraceInstructionsWindow):
    def __init__(self, address="", prompt_dialog=True, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.address = address
        self.trace_data = None
        self.treeWidget_InstructionInfo.currentItemChanged.connect(self.display_collected_data)
        self.treeWidget_InstructionInfo.itemDoubleClicked.connect(self.treeWidget_InstructionInfo_item_double_clicked)
        self.treeWidget_InstructionInfo.contextMenuEvent = self.treeWidget_InstructionInfo_context_menu_event
        self.actionOpen.triggered.connect(self.load_file)
        self.actionSave.triggered.connect(self.save_file)
        self.splitter.setStretchFactor(0, 1)
        if not prompt_dialog:
            return
        prompt_dialog = TraceInstructionsPromptDialogForm()
        if prompt_dialog.exec():
            params = (address,) + prompt_dialog.get_values()
            breakpoint = GDB_Engine.trace_instructions(*params)
            if not breakpoint:
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(address))
                self.close()
                return
            self.showMaximized()
            self.breakpoint = breakpoint
            self.wait_dialog = TraceInstructionsWaitWidgetForm(address, breakpoint, self)
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
                self.textBrowser_RegisterInfo.verticalScrollBar().minimum())

    def show_trace_info(self, trace_data=None):
        self.treeWidget_InstructionInfo.setStyleSheet("QTreeWidget::item{ height: 16px; }")
        parent = QTreeWidgetItem(self.treeWidget_InstructionInfo)
        self.treeWidget_InstructionInfo.setRootIndex(self.treeWidget_InstructionInfo.indexFromItem(parent))
        if trace_data:
            trace_tree, current_root_index = trace_data
        else:
            trace_data = GDB_Engine.get_trace_instructions_info(self.breakpoint)
            if trace_data:
                trace_tree, current_root_index = trace_data
            else:
                return
        self.trace_data = copy.deepcopy(trace_data)
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
        trace_file_path = SysUtils.get_user_path(type_defs.USER_PATHS.TRACE_INSTRUCTIONS_PATH)
        file_path = QFileDialog.getSaveFileName(self, tr.SAVE_TRACE_FILE, trace_file_path, tr.FILE_TYPES_TRACE)[0]
        if file_path:
            file_path = SysUtils.append_file_extension(file_path, "trace")
            if not SysUtils.save_file(self.trace_data, file_path):
                QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    def load_file(self):
        trace_file_path = SysUtils.get_user_path(type_defs.USER_PATHS.TRACE_INSTRUCTIONS_PATH)
        file_path = QFileDialog.getOpenFileName(self, tr.OPEN_TRACE_FILE, trace_file_path, tr.FILE_TYPES_TRACE)[0]
        if file_path:
            content = SysUtils.load_file(file_path)
            if content is None:
                QMessageBox.information(self, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
                return
            self.treeWidget_InstructionInfo.clear()
            self.show_trace_info(content)

    def treeWidget_InstructionInfo_context_menu_event(self, event):
        menu = QMenu()
        expand_all = menu.addAction(tr.EXPAND_ALL)
        collapse_all = menu.addAction(tr.COLLAPSE_ALL)
        font_size = self.treeWidget_InstructionInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            expand_all: self.treeWidget_InstructionInfo.expandAll,
            collapse_all: self.treeWidget_InstructionInfo.collapseAll
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_InstructionInfo_item_double_clicked(self, index):
        current_item = GuiUtils.get_current_item(self.treeWidget_InstructionInfo)
        if not current_item:
            return
        address = SysUtils.extract_address(current_item.trace_data[0])
        if address:
            self.parent().disassemble_expression(address, append_to_travel_history=True)

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class FunctionsInfoWidgetForm(QWidget, FunctionsInfoWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.textBrowser_AddressInfo.setFixedHeight(100)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_SymbolInfo.selectionModel().currentChanged.connect(self.tableWidget_SymbolInfo_current_changed)
        self.tableWidget_SymbolInfo.itemDoubleClicked.connect(self.tableWidget_SymbolInfo_item_double_clicked)
        self.tableWidget_SymbolInfo.contextMenuEvent = self.tableWidget_SymbolInfo_context_menu_event
        icons_directory = GuiUtils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)

    def refresh_table(self):
        input_text = self.lineEdit_SearchInput.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(input_text, case_sensitive)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, gdb_input, case_sensitive):
        return GDB_Engine.search_functions(gdb_input, case_sensitive)

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
        GuiUtils.resize_to_contents(self.tableWidget_SymbolInfo)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current):
        self.textBrowser_AddressInfo.clear()
        address = self.tableWidget_SymbolInfo.item(QModelIndex_current.row(), FUNCTIONS_INFO_ADDR_COL).text()
        if SysUtils.extract_address(address):
            symbol = self.tableWidget_SymbolInfo.item(QModelIndex_current.row(), FUNCTIONS_INFO_SYMBOL_COL).text()
            for item in SysUtils.split_symbol(symbol):
                info = GDB_Engine.get_symbol_info(item)
                self.textBrowser_AddressInfo.append(info)
        else:
            self.textBrowser_AddressInfo.append(tr.DEFINED_SYMBOL)

    def tableWidget_SymbolInfo_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_SymbolInfo.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_SymbolInfo)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_symbol = menu.addAction(tr.COPY_SYMBOL)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_symbol])
        font_size = self.tableWidget_SymbolInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_ADDR_COL),
            copy_symbol: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_SYMBOL_COL)
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
        InputDialogForm(item_list=[(tr.FUNCTIONS_INFO_HELPER, None, Qt.AlignmentFlag.AlignLeft)],
                        buttons=[QDialogButtonBox.StandardButton.Ok]).exec()

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class EditInstructionDialogForm(QDialog, EditInstructionDialog):
    def __init__(self, address, bytes_aob, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.orig_bytes = bytes_aob
        self.lineEdit_Address.setText(address)
        self.lineEdit_Bytes.setText(bytes_aob)
        self.lineEdit_Bytes_text_edited()
        self.lineEdit_Bytes.textEdited.connect(self.lineEdit_Bytes_text_edited)
        self.lineEdit_Instruction.textEdited.connect(self.lineEdit_Instruction_text_edited)

    def set_valid(self, valid):
        if valid:
            self.is_valid = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.is_valid = False
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def lineEdit_Bytes_text_edited(self):
        bytes_aob = self.lineEdit_Bytes.text()
        if SysUtils.parse_string(bytes_aob, type_defs.VALUE_INDEX.INDEX_AOB):
            address = int(self.lineEdit_Address.text(), 0)
            instruction = SysUtils.get_opcodes(address, bytes_aob, GDB_Engine.inferior_arch)
            if instruction:
                self.set_valid(True)
                self.lineEdit_Instruction.setText(instruction)
                return
        self.set_valid(False)
        self.lineEdit_Instruction.setText("??")

    def lineEdit_Instruction_text_edited(self):
        instruction = self.lineEdit_Instruction.text()
        address = int(self.lineEdit_Address.text(), 0)
        result = SysUtils.assemble(instruction, address, GDB_Engine.inferior_arch)
        if result:
            byte_list = result[0]
            self.set_valid(True)
            bytes_str = " ".join([format(num, '02x') for num in byte_list])
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
                bytes_aob += " 90"*(old_length-new_length)  # Append NOPs if we are short on bytes
            elif new_length > old_length:
                if not InputDialogForm(item_list=[(tr.NEW_OPCODE.format(new_length, old_length),)]).exec():
                    return
            GDB_Engine.modify_instruction(address, bytes_aob)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        super(EditInstructionDialogForm, self).accept()


class HexEditDialogForm(QDialog, HexEditDialog):
    def __init__(self, address, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.lineEdit_Length.setValidator(QHexValidator(999, self))
        self.lineEdit_Address.setText(address)
        self.lineEdit_Length.setText("20")
        self.refresh_view()
        self.lineEdit_AsciiView.selectionChanged.connect(self.lineEdit_AsciiView_selection_changed)

        # TODO: Implement this
        # self.lineEdit_HexView.selectionChanged.connect(self.lineEdit_HexView_selection_changed)
        self.lineEdit_HexView.textEdited.connect(self.lineEdit_HexView_text_edited)
        self.lineEdit_AsciiView.textEdited.connect(self.lineEdit_AsciiView_text_edited)
        self.pushButton_Refresh.pressed.connect(self.refresh_view)
        self.lineEdit_Address.textChanged.connect(self.refresh_view)
        self.lineEdit_Length.textChanged.connect(self.refresh_view)

    def lineEdit_AsciiView_selection_changed(self):
        length = len(SysUtils.str_to_aob(self.lineEdit_AsciiView.selectedText(), "utf-8"))
        start_index = self.lineEdit_AsciiView.selectionStart()
        start_index = len(SysUtils.str_to_aob(self.lineEdit_AsciiView.text()[0:start_index], "utf-8"))
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
        if not SysUtils.parse_string(aob_string, type_defs.VALUE_INDEX.INDEX_AOB):
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")
            return
        aob_array = aob_string.split()
        try:
            self.lineEdit_AsciiView.setText(SysUtils.aob_to_str(aob_array, "utf-8"))
            self.lineEdit_HexView.setStyleSheet("")  # This should set background color back to QT default
        except ValueError:
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def lineEdit_AsciiView_text_edited(self):
        ascii_str = self.lineEdit_AsciiView.text()
        try:
            self.lineEdit_HexView.setText(SysUtils.str_to_aob(ascii_str, "utf-8"))
            self.lineEdit_AsciiView.setStyleSheet("")
        except ValueError:
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def refresh_view(self):
        self.lineEdit_AsciiView.clear()
        self.lineEdit_HexView.clear()
        address = GDB_Engine.examine_expression(self.lineEdit_Address.text()).address
        if not address:
            return
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
            address = int(address, 0)
        except ValueError:
            return
        aob_array = GDB_Engine.hex_dump(address, length)
        ascii_str = SysUtils.aob_to_str(aob_array, "utf-8")
        self.lineEdit_AsciiView.setText(ascii_str)
        self.lineEdit_HexView.setText(" ".join(aob_array))

    def accept(self):
        expression = self.lineEdit_Address.text()
        address = GDB_Engine.examine_expression(expression).address
        if not address:
            QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_EXPRESSION.format(expression))
            return
        value = self.lineEdit_HexView.text()
        GDB_Engine.write_memory(address, type_defs.VALUE_INDEX.INDEX_AOB, value)
        super(HexEditDialogForm, self).accept()


# This widget will be replaced with auto-generated documentation in the future, no need to translate
class LibpinceReferenceWidgetForm(QWidget, LibpinceReferenceWidget):
    def convert_to_modules(self, module_strings):
        return [eval(item) for item in module_strings]

    def __init__(self, is_window=False, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.found_count = 0
        self.current_found = 0
        global instances
        instances.append(self)
        if is_window:
            GuiUtils.center(self)
            self.setWindowFlags(Qt.WindowType.Window)
        self.show_type_defs()
        self.splitter.setStretchFactor(0, 1)
        self.widget_Resources.resize(700, self.widget_Resources.height())
        libpince_directory = SysUtils.get_libpince_directory()
        self.textBrowser_TypeDefs.setText(open(libpince_directory + "/type_defs.py").read())
        source_menu_items = ["(Tagged only)", "(All)"]
        self.libpince_source_files = ["GDB_Engine", "SysUtils", "GuiUtils"]
        source_menu_items.extend(self.libpince_source_files)
        self.comboBox_SourceFile.addItems(source_menu_items)
        self.comboBox_SourceFile.setCurrentIndex(0)
        self.fill_resource_tree()
        icons_directory = GuiUtils.get_icons_directory()
        self.pushButton_TextUp.setIcon(QIcon(QPixmap(icons_directory + "/bullet_arrow_up.png")))
        self.pushButton_TextDown.setIcon(QIcon(QPixmap(icons_directory + "/bullet_arrow_down.png")))
        self.comboBox_SourceFile.currentIndexChanged.connect(self.comboBox_SourceFile_current_index_changed)
        self.pushButton_ShowTypeDefs.clicked.connect(self.toggle_type_defs)
        self.lineEdit_SearchText.textChanged.connect(self.highlight_text)
        self.pushButton_TextDown.clicked.connect(self.pushButton_TextDown_clicked)
        self.pushButton_TextUp.clicked.connect(self.pushButton_TextUp_clicked)
        self.lineEdit_Search.textChanged.connect(self.comboBox_SourceFile_current_index_changed)
        self.tableWidget_ResourceTable.contextMenuEvent = self.tableWidget_ResourceTable_context_menu_event
        self.treeWidget_ResourceTree.contextMenuEvent = self.treeWidget_ResourceTree_context_menu_event
        self.treeWidget_ResourceTree.expanded.connect(self.resize_resource_tree)
        self.treeWidget_ResourceTree.collapsed.connect(self.resize_resource_tree)

    def tableWidget_ResourceTable_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_ResourceTable.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_ResourceTable)

        menu = QMenu()
        refresh = menu.addAction("Refresh")
        menu.addSeparator()
        copy_item = menu.addAction("Copy Item")
        copy_value = menu.addAction("Copy Value")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_item, copy_value])
        font_size = self.tableWidget_ResourceTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.fill_resource_table,
            copy_item: lambda: copy_to_clipboard(selected_row, LIBPINCE_REFERENCE_ITEM_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, LIBPINCE_REFERENCE_VALUE_COL)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_ResourceTree_context_menu_event(self, event):
        def copy_to_clipboard(column):
            current_item = GuiUtils.get_current_item(self.treeWidget_ResourceTree)
            if current_item:
                app.clipboard().setText(current_item.text(column))

        def expand_all():
            self.treeWidget_ResourceTree.expandAll()
            self.resize_resource_tree()

        def collapse_all():
            self.treeWidget_ResourceTree.collapseAll()
            self.resize_resource_tree()

        selected_row = GuiUtils.get_current_row(self.treeWidget_ResourceTree)

        menu = QMenu()
        refresh = menu.addAction("Refresh")
        menu.addSeparator()
        copy_item = menu.addAction("Copy Item")
        copy_value = menu.addAction("Copy Value")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_item, copy_value])
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
            collapse_all_items: collapse_all
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
        checked_source_files = self.convert_to_modules(self.libpince_source_files)
        tag_dict = SysUtils.get_tags(checked_source_files, type_defs.tag_to_string, self.lineEdit_Search.text())
        docstring_dict = SysUtils.get_docstrings(checked_source_files, self.lineEdit_Search.text())
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
            checked_source_files = self.libpince_source_files
        else:
            checked_source_files = [self.comboBox_SourceFile.currentText()]
        checked_source_files = self.convert_to_modules(checked_source_files)
        element_dict = SysUtils.get_docstrings(checked_source_files, self.lineEdit_Search.text())
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
        GuiUtils.resize_to_contents(self.tableWidget_ResourceTable)

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

    def toggle_type_defs(self):
        if self.type_defs_shown:
            self.hide_type_defs()
        else:
            self.show_type_defs()

    def hide_type_defs(self):
        self.type_defs_shown = False
        self.widget_TypeDefs.hide()
        self.pushButton_ShowTypeDefs.setText("Show type_defs")

    def show_type_defs(self):
        self.type_defs_shown = True
        self.widget_TypeDefs.show()
        self.pushButton_ShowTypeDefs.setText("Hide type_defs")

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class LogFileWidgetForm(QWidget, LogFileWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        global instances
        instances.append(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.contents = ""
        self.refresh_contents()
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_contents)
        self.refresh_timer.start()

    def refresh_contents(self):
        log_path = SysUtils.get_logging_file(GDB_Engine.currentpid)
        self.setWindowTitle(tr.LOG_FILE.format(GDB_Engine.currentpid))
        self.label_FilePath.setText(tr.LOG_CONTENTS.format(log_path, 20000))
        logging_status = f"<font color=blue>{tr.ON}</font>" if gdb_logging else f"<font color=red>{tr.OFF}</font>"
        self.label_LoggingStatus.setText(f"<b>{tr.LOG_STATUS.format(logging_status)}</b>")
        try:
            log_file = open(log_path)
        except OSError:
            self.textBrowser_LogContent.clear()
            error_message = tr.LOG_READ_ERROR.format(log_path) + "\n"
            if not gdb_logging:
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

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)
        self.refresh_timer.stop()


class SearchOpcodeWidgetForm(QWidget, SearchOpcodeWidget):
    def __init__(self, start="", end="", parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.lineEdit_Start.setText(start)
        self.lineEdit_End.setText(end)
        self.tableWidget_Opcodes.setColumnWidth(SEARCH_OPCODE_ADDR_COL, 250)
        icons_directory = GuiUtils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_Opcodes.itemDoubleClicked.connect(self.tableWidget_Opcodes_item_double_clicked)
        self.tableWidget_Opcodes.contextMenuEvent = self.tableWidget_Opcodes_context_menu_event

    def refresh_table(self):
        start_address = self.lineEdit_Start.text()
        end_address = self.lineEdit_End.text()
        regex = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(regex, start_address, end_address,
                                                                          case_sensitive, enable_regex)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, regex, start_address, end_address, case_sensitive, enable_regex):
        return GDB_Engine.search_opcode(regex, start_address, end_address, case_sensitive, enable_regex)

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
        InputDialogForm(item_list=[(tr.SEARCH_OPCODE_HELPER, None, Qt.AlignmentFlag.AlignLeft)],
                        buttons=[QDialogButtonBox.StandardButton.Ok]).exec()

    def tableWidget_Opcodes_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_Opcodes.item(row, SEARCH_OPCODE_ADDR_COL).text()
        self.parent().disassemble_expression(SysUtils.extract_address(address), append_to_travel_history=True)

    def tableWidget_Opcodes_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_Opcodes.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_Opcodes)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_opcode = menu.addAction(tr.COPY_OPCODE)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_opcode])
        font_size = self.tableWidget_Opcodes.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, SEARCH_OPCODE_ADDR_COL),
            copy_opcode: lambda: copy_to_clipboard(selected_row, SEARCH_OPCODE_OPCODES_COL)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class MemoryRegionsWidgetForm(QWidget, MemoryRegionsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.refresh_table()
        self.tableWidget_MemoryRegions.contextMenuEvent = self.tableWidget_MemoryRegions_context_menu_event
        self.tableWidget_MemoryRegions.itemDoubleClicked.connect(self.tableWidget_MemoryRegions_item_double_clicked)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)

    def refresh_table(self):
        memory_regions = SysUtils.get_regions(GDB_Engine.currentpid)
        self.tableWidget_MemoryRegions.setRowCount(0)
        self.tableWidget_MemoryRegions.setRowCount(len(memory_regions))
        for row, (start, end, perms, offset, _, _, path) in enumerate(memory_regions):
            address = start+"-"+end
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PERM_COL, QTableWidgetItem(perms))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_OFFSET_COL, QTableWidgetItem(offset))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PATH_COL, QTableWidgetItem(path))
        GuiUtils.resize_to_contents(self.tableWidget_MemoryRegions)

    def tableWidget_MemoryRegions_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_MemoryRegions.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_MemoryRegions)

        menu = QMenu()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        copy_addresses = menu.addAction(tr.COPY_ADDRESSES)
        copy_offset = menu.addAction(tr.COPY_OFFSET)
        copy_path = menu.addAction(tr.COPY_PATH)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_addresses, copy_offset, copy_path])
        font_size = self.tableWidget_MemoryRegions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.refresh_table,
            copy_addresses: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_ADDR_COL),
            copy_offset: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_OFFSET_COL),
            copy_path: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_PATH_COL)
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

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class DissectCodeDialogForm(QDialog, DissectCodeDialog):
    scan_finished_signal = pyqtSignal()

    def __init__(self, parent=None, int_address=-1):
        super().__init__(parent=parent)
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

    class BackgroundThread(QThread):
        output_ready = pyqtSignal()
        is_canceled = False

        def __init__(self, region_list, discard_invalid_strings):
            super().__init__()
            self.region_list = region_list
            self.discard_invalid_strings = discard_invalid_strings

        def run(self):
            GDB_Engine.dissect_code(self.region_list, self.discard_invalid_strings)
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
        region, region_count, range, string_count, jump_count, call_count = GDB_Engine.get_dissect_code_status()
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
            referenced_strings, referenced_jumps, referenced_calls = GDB_Engine.get_dissect_code_data()
        except:
            return
        self.label_StringReferenceCount.setText(str(len(referenced_strings)))
        self.label_JumpReferenceCount.setText(str(len(referenced_jumps)))
        self.label_CallReferenceCount.setText(str(len(referenced_calls)))

    def show_memory_regions(self):
        executable_regions = SysUtils.filter_regions(GDB_Engine.currentpid, "permissions", "..x.")
        self.region_list = []
        self.tableWidget_ExecutableMemoryRegions.setRowCount(0)
        self.tableWidget_ExecutableMemoryRegions.setRowCount(len(executable_regions))
        for row, (start, end, _, _, _, _, path) in enumerate(executable_regions):
            address = start+"-"+end
            self.region_list.append((start, end))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_PATH_COL, QTableWidgetItem(path))
        GuiUtils.resize_to_contents(self.tableWidget_ExecutableMemoryRegions)

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
            GDB_Engine.cancel_dissect_code()
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
            self.background_thread = self.BackgroundThread(selected_regions,
                                                           self.checkBox_DiscardInvalidStrings.isChecked())
            self.background_thread.output_ready.connect(self.scan_finished)
            self.init_after_scan_gui()
            self.refresh_timer.start()
            self.background_thread.start()

    def closeEvent(self, QCloseEvent):
        GDB_Engine.cancel_dissect_code()
        self.refresh_timer.stop()


class ReferencedStringsWidgetForm(QWidget, ReferencedStringsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        GuiUtils.fill_value_combobox(self.comboBox_ValueType, type_defs.VALUE_INDEX.INDEX_STRING_UTF8)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center_to_parent(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_STR_ADDR_COL, 150)
        self.tableWidget_References.setColumnWidth(REF_STR_COUNT_COL, 80)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = GDB_Engine.get_dissect_code_data()
        str_dict_len, jmp_dict_len, call_dict_len = len(str_dict), len(jmp_dict), len(call_dict)
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        if str_dict_len == 0 and jmp_dict_len == 0 and call_dict_len == 0:
            confirm_dialog = InputDialogForm(item_list=[(tr.DISSECT_CODE,)])
            if confirm_dialog.exec():
                dissect_code_dialog = DissectCodeDialogForm()
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
        return '0x' + hex_str[2:].zfill(self.hex_len + self_len)

    def refresh_table(self):
        item_list = GDB_Engine.search_referenced_strings(self.lineEdit_Regex.text(),
                                                         self.comboBox_ValueType.currentIndex(),
                                                         self.checkBox_CaseSensitive.isChecked(),
                                                         self.checkBox_Regex.isChecked())
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
        str_dict = GDB_Engine.get_dissect_code_data(True, False, False)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_STR_ADDR_COL).text()
        referrers = str_dict[hex(int(addr, 16))]
        addrs = [hex(address) for address in referrers]
        self.listWidget_Referrers.addItems([self.pad_hex(item.all) for item in GDB_Engine.examine_expressions(addrs)])
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        str_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_STR_ADDR_COL).text()
        self.parent().hex_dump_address(int(address, 16))

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_value = menu.addAction(tr.COPY_VALUE)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_value])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, REF_STR_ADDR_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, REF_STR_VAL_COL)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class ReferencedCallsWidgetForm(QWidget, ReferencedCallsWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center_to_parent(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_CALL_ADDR_COL, 480)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = GDB_Engine.get_dissect_code_data()
        str_dict_len, jmp_dict_len, call_dict_len = len(str_dict), len(jmp_dict), len(call_dict)
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        if str_dict_len == 0 and jmp_dict_len == 0 and call_dict_len == 0:
            confirm_dialog = InputDialogForm(item_list=[(tr.DISSECT_CODE,)])
            if confirm_dialog.exec():
                dissect_code_dialog = DissectCodeDialogForm()
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
        return '0x' + hex_str[2:].zfill(self.hex_len + self_len)

    def refresh_table(self):
        item_list = GDB_Engine.search_referenced_calls(self.lineEdit_Regex.text(),
                                                       self.checkBox_CaseSensitive.isChecked(),
                                                       self.checkBox_Regex.isChecked())
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
        call_dict = GDB_Engine.get_dissect_code_data(False, False, True)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_CALL_ADDR_COL).text()
        referrers = call_dict[hex(int(SysUtils.extract_address(addr), 16))]
        addrs = [hex(address) for address in referrers]
        self.listWidget_Referrers.addItems([self.pad_hex(item.all) for item in GDB_Engine.examine_expressions(addrs)])
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        call_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_CALL_ADDR_COL).text()
        self.parent().disassemble_expression(SysUtils.extract_address(address), append_to_travel_history=True)

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, REF_CALL_ADDR_COL)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class ExamineReferrersWidgetForm(QWidget, ExamineReferrersWidget):
    def __init__(self, int_address, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center_to_parent(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.splitter.setStretchFactor(0, 1)
        self.textBrowser_DisasInfo.resize(600, self.textBrowser_DisasInfo.height())
        self.referenced_hex = hex(int_address)
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        self.collect_referrer_data()
        self.refresh_table()
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        self.listWidget_Referrers.selectionModel().currentChanged.connect(self.listWidget_Referrers_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
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
        return '0x' + hex_str[2:].zfill(self.hex_len + self_len)

    def collect_referrer_data(self):
        jmp_dict, call_dict = GDB_Engine.get_dissect_code_data(False, True, True)
        self.referrer_data = []
        try:
            jmp_referrers = jmp_dict[self.referenced_hex]
        except KeyError:
            pass
        else:
            jmp_referrers = [hex(item) for item in jmp_referrers]
            self.referrer_data.extend([item.all for item in GDB_Engine.examine_expressions(jmp_referrers)])
        try:
            call_referrers = call_dict[self.referenced_hex]
        except KeyError:
            pass
        else:
            call_referrers = [hex(item) for item in call_referrers]
            self.referrer_data.extend([item.all for item in GDB_Engine.examine_expressions(call_referrers)])
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
        disas_data = GDB_Engine.disassemble(
            SysUtils.extract_address(self.listWidget_Referrers.item(QModelIndex_current.row()).text()), "+200")
        for address_info, _, opcode in disas_data:
            self.textBrowser_DisasInfo.append(address_info + opcode)
        cursor = self.textBrowser_DisasInfo.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_DisasInfo.setTextCursor(cursor)
        self.textBrowser_DisasInfo.ensureCursorVisible()

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


def handle_exit():
    global exiting
    exiting = 1


if __name__ == "__main__":
    app.aboutToQuit.connect(handle_exit)
    window = MainForm()
    window.show()
    sys.exit(app.exec())
