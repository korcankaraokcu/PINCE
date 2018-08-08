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
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QCursor, QKeySequence, QColor, QTextCharFormat, QBrush, QTextCursor, \
    QIntValidator
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QWidget, \
    QShortcut, QKeySequenceEdit, QTabWidget, QMenu, QFileDialog, QAbstractItemView, QToolTip, QTreeWidgetItem, \
    QTreeWidgetItemIterator, QCompleter, QLabel, QLineEdit, QComboBox, QDialogButtonBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray, QSettings, QCoreApplication, QEvent, \
    QItemSelectionModel, QTimer, QModelIndex, QStringListModel
from time import sleep, time
import os, sys, traceback, signal, re, copy, io, queue, collections, ast, functools

from libPINCE import GuiUtils, SysUtils, GDB_Engine, type_defs

from GUI.MainWindow import Ui_MainWindow as MainWindow
from GUI.SelectProcess import Ui_MainWindow as ProcessWindow
from GUI.AddAddressManuallyDialog import Ui_Dialog as ManualAddressDialog
from GUI.EditTypeDialog import Ui_Dialog as EditTypeDialog
from GUI.LoadingDialog import Ui_Dialog as LoadingDialog
from GUI.InputDialog import Ui_Dialog as InputDialog
from GUI.TextEditDialog import Ui_Dialog as TextEditDialog
from GUI.SettingsDialog import Ui_Dialog as SettingsDialog
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
from GUI.LibPINCEReferenceWidget import Ui_Form as LibPINCEReferenceWidget
from GUI.LogFileWidget import Ui_Form as LogFileWidget
from GUI.SearchOpcodeWidget import Ui_Form as SearchOpcodeWidget
from GUI.MemoryRegionsWidget import Ui_Form as MemoryRegionsWidget
from GUI.DissectCodeDialog import Ui_Dialog as DissectCodeDialog
from GUI.ReferencedStringsWidget import Ui_Form as ReferencedStringsWidget
from GUI.ReferencedCallsWidget import Ui_Form as ReferencedCallsWidget
from GUI.ExamineReferrersWidget import Ui_Form as ExamineReferrersWidget

from GUI.CustomAbstractTableModels.HexModel import QHexModel
from GUI.CustomAbstractTableModels.AsciiModel import QAsciiModel

selfpid = os.getpid()
instances = []  # Holds temporary instances that will be deleted later on

# settings
current_settings_version = "master-10"  # Increase version by one if you change settings. Format: branch_name-version
update_table = bool
table_update_interval = float
show_messagebox_on_exception = bool
show_messagebox_on_toggle_attach = bool
gdb_output_mode = int
global_hotkeys = collections.OrderedDict(
    [("pause_hotkey", str), ("break_hotkey", str), ("continue_hotkey", str), ("toggle_attach_hotkey", str)])
code_injection_method = int
bring_disassemble_to_front = bool
instructions_per_scroll = int
gdb_path = str

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

# row colours for disassemble qtablewidget
PC_COLOUR = Qt.blue
BOOKMARK_COLOUR = Qt.cyan
DEFAULT_COLOUR = Qt.white
BREAKPOINT_COLOUR = Qt.red
REF_COLOUR = Qt.lightGray

# represents the index of columns in address table
FROZEN_COL = 0  # Frozen
DESC_COL = 1  # Description
ADDR_COL = 2  # Address
TYPE_COL = 3  # Type
VALUE_COL = 4  # Value

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

# represents the index of columns in libPINCE reference resources table
LIBPINCE_REFERENCE_ITEM_COL = 0
LIBPINCE_REFERENCE_VALUE_COL = 1

# represents the index of columns in search opcode table
SEARCH_OPCODE_ADDR_COL = 0
SEARCH_OPCODE_OPCODES_COL = 1

# represents the index of columns in memory regions table
MEMORY_REGIONS_ADDR_COL = 0
MEMORY_REGIONS_PERM_COL = 1
MEMORY_REGIONS_SIZE_COL = 2
MEMORY_REGIONS_PATH_COL = 3
MEMORY_REGIONS_RSS_COL = 4
MEMORY_REGIONS_PSS_COL = 5
MEMORY_REGIONS_SHRCLN_COL = 6
MEMORY_REGIONS_SHRDRTY_COL = 7
MEMORY_REGIONS_PRIVCLN_COL = 8
MEMORY_REGIONS_PRIVDRTY_COL = 9
MEMORY_REGIONS_REF_COL = 10
MEMORY_REGIONS_ANON_COL = 11
MEMORY_REGIONS_SWAP_COL = 12

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


def except_hook(exception_type, value, tb):
    if show_messagebox_on_exception:
        focused_widget = QApplication.focusWidget()
        if focused_widget:
            if exception_type == type_defs.GDBInitializeException:
                QMessageBox.information(focused_widget, "Error", "GDB isn't initialized yet")
            elif exception_type == type_defs.InferiorRunningException:
                error_dialog = InputDialogForm(item_list=[(
                    "Process is running" + "\nPress " + global_hotkeys["break_hotkey"] + " to stop process" +
                    "\n\nGo to settings->General to disable this dialog",)], buttons=[QDialogButtonBox.Ok])
                error_dialog.exec_()
    traceback.print_exception(exception_type, value, tb)


# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = except_hook


def signal_handler(signal, frame):
    GDB_Engine.cancel_last_command()
    raise KeyboardInterrupt


signal.signal(signal.SIGINT, signal_handler)


# A decorator for selection control
def requires_selection(attribute_name, single):
    def real_decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            attribute = getattr(self, attribute_name)
            selected_rows = attribute.selectionModel().selectedRows()
            if ((len(selected_rows) == 1) if single else selected_rows):
                func(self, *args, **kwargs)

        return wrapper

    return real_decorator


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
            if GDB_Engine.inferior_status is type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
                self.process_stopped.emit()
            else:
                self.process_running.emit()


class UpdateAddressTableThread(QThread):
    update_table_signal = pyqtSignal()

    def run(self):
        while True:
            while not update_table:
                sleep(0.1)
            if GDB_Engine.inferior_status is type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
                self.update_table_signal.emit()
            sleep(table_update_interval)


# the mainwindow
class MainForm(QMainWindow, MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.treeWidget_AddressTable.setColumnWidth(FROZEN_COL, 50)
        self.treeWidget_AddressTable.setColumnWidth(DESC_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(ADDR_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(TYPE_COL, 150)
        QCoreApplication.setOrganizationName("PINCE")
        QCoreApplication.setOrganizationDomain("github.com/korcankaraokcu/PINCE")
        QCoreApplication.setApplicationName("PINCE")
        QSettings.setPath(QSettings.NativeFormat, QSettings.UserScope,
                          SysUtils.get_user_path(type_defs.USER_PATHS.CONFIG_PATH))
        self.settings = QSettings()
        if not SysUtils.is_path_valid(self.settings.fileName()):
            self.set_default_settings()
        try:
            self.apply_settings()
        except Exception as e:
            print("An exception occurred while trying to load settings, rolling back to the default configuration\n", e)
            self.settings.clear()
            self.set_default_settings()
        try:
            settings_version = self.settings.value("Misc/version", type=str)
        except TypeError:
            settings_version = None
        if settings_version != current_settings_version:
            self.settings.clear()
            self.set_default_settings()
        GDB_Engine.init_gdb(gdb_path=gdb_path)
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
        self.update_address_table_thread = UpdateAddressTableThread()
        self.update_address_table_thread.update_table_signal.connect(self.update_address_table_manually)
        self.update_address_table_thread.start()
        for key, value in list(global_hotkeys.items()):
            setattr(self, key, QShortcut(QKeySequence(value), self))
            current_hotkey = getattr(self, key)
            current_hotkey.activated.connect(getattr(self, key + "_pressed"))
            current_hotkey.setContext(Qt.ApplicationShortcut)

        # Saving the original function because super() doesn't work when we override functions like this
        self.treeWidget_AddressTable.keyPressEvent_original = self.treeWidget_AddressTable.keyPressEvent
        self.treeWidget_AddressTable.keyPressEvent = self.treeWidget_AddressTable_key_press_event
        self.treeWidget_AddressTable.contextMenuEvent = self.treeWidget_AddressTable_context_menu_event
        self.pushButton_AttachProcess.clicked.connect(self.pushButton_AttachProcess_clicked)
        self.pushButton_NewFirstScan.clicked.connect(self.pushButton_NewFirstScan_clicked)
        self.pushButton_NextScan.clicked.connect(self.pushButton_NextScan_clicked)
        self.pushButton_Settings.clicked.connect(self.pushButton_Settings_clicked)
        self.pushButton_Console.clicked.connect(self.pushButton_Console_clicked)
        self.pushButton_Wiki.clicked.connect(self.pushButton_Wiki_clicked)
        self.pushButton_About.clicked.connect(self.pushButton_About_clicked)
        self.pushButton_AddAddressManually.clicked.connect(self.pushButton_AddAddressManually_clicked)
        self.pushButton_MemoryView.clicked.connect(self.pushButton_MemoryView_clicked)
        self.pushButton_RefreshAdressTable.clicked.connect(self.update_address_table_manually)
        self.pushButton_CleanAddressTable.clicked.connect(self.delete_address_table_contents)
        self.treeWidget_AddressTable.itemDoubleClicked.connect(self.treeWidget_AddressTable_item_double_clicked)
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

    def set_default_settings(self):
        self.settings.beginGroup("General")
        self.settings.setValue("auto_update_address_table", False)
        self.settings.setValue("address_table_update_interval", 0.5)
        self.settings.setValue("show_messagebox_on_exception", True)
        self.settings.setValue("show_messagebox_on_toggle_attach", True)
        self.settings.setValue("gdb_output_mode", type_defs.GDB_OUTPUT_MODE.UNMUTED)
        self.settings.endGroup()
        self.settings.beginGroup("Hotkeys")
        self.settings.setValue("pause_hotkey", "F1")
        self.settings.setValue("break_hotkey", "F2")
        self.settings.setValue("continue_hotkey", "F3")
        self.settings.setValue("toggle_attach_hotkey", "Shift+F10")
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
        self.settings.endGroup()
        self.settings.beginGroup("Misc")
        self.settings.setValue("version", current_settings_version)
        self.settings.endGroup()
        self.apply_settings()

    def apply_settings(self):
        global update_table
        global table_update_interval
        global show_messagebox_on_exception
        global show_messagebox_on_toggle_attach
        global gdb_output_mode
        global global_hotkeys
        global code_injection_method
        global bring_disassemble_to_front
        global instructions_per_scroll
        global gdb_path
        update_table = self.settings.value("General/auto_update_address_table", type=bool)
        table_update_interval = self.settings.value("General/address_table_update_interval", type=float)
        show_messagebox_on_exception = self.settings.value("General/show_messagebox_on_exception", type=bool)
        show_messagebox_on_toggle_attach = self.settings.value("General/show_messagebox_on_toggle_attach", type=bool)
        gdb_output_mode = self.settings.value("General/gdb_output_mode", type=int)
        GDB_Engine.set_gdb_output_mode(gdb_output_mode)
        for key, value in list(global_hotkeys.items()):
            value = self.settings.value("Hotkeys/" + key)
            global_hotkeys[key] = value
            try:
                current_hotkey = getattr(self, key)
            except AttributeError:
                pass
            else:
                current_hotkey.setKey(QKeySequence(value))
        try:
            self.memory_view_window.set_dynamic_debug_hotkeys()
        except AttributeError:
            pass
        code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        bring_disassemble_to_front = self.settings.value("Disassemble/bring_disassemble_to_front", type=bool)
        instructions_per_scroll = self.settings.value("Disassemble/instructions_per_scroll", type=int)
        gdb_path = self.settings.value("Debug/gdb_path", type=str)

    # These "_pressed" event functions are automatically connected in MainForm.__init__ within a for loop
    # These functions are used to declare stuff that'll be done when a global hotkey is triggered
    def pause_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior(type_defs.STOP_REASON.PAUSE)

    def break_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior()

    def continue_hotkey_pressed(self):
        GDB_Engine.continue_inferior()

    def toggle_attach_hotkey_pressed(self):
        if GDB_Engine.toggle_attach() is type_defs.TOGGLE_ATTACH.DETACHED:
            self.on_status_detached()
            dialog_text = "GDB is detached from the process"
        else:
            dialog_text = "GDB is attached back to the process"
        if show_messagebox_on_toggle_attach:
            dialog = InputDialogForm(item_list=[(
                dialog_text + "\n\nGo to settings->General to disable this dialog",)], buttons=[QDialogButtonBox.Ok])
            dialog.exec_()

    def treeWidget_AddressTable_context_menu_event(self, event):
        current_row = self.treeWidget_AddressTable.currentItem()
        menu = QMenu()
        edit_menu = menu.addMenu("Edit")
        edit_desc = edit_menu.addAction("Description[Ctrl+Enter]")
        edit_address = edit_menu.addAction("Address[Ctrl+Alt+Enter]")
        edit_type = edit_menu.addAction("Type[Alt+Enter]")
        edit_value = edit_menu.addAction("Value[Enter]")
        # TODO: Implement toggling of records
        toggle_record = menu.addAction("Toggle selected records[Space] (not implemented yet)")
        menu.addSeparator()
        browse_region = menu.addAction("Browse this memory region[Ctrl+B]")
        disassemble = menu.addAction("Disassemble this address[Ctrl+D]")
        menu.addSeparator()
        cut_record = menu.addAction("Cut selected records[Ctrl+X]")
        copy_record = menu.addAction("Copy selected records[Ctrl+C]")
        paste_record_before = menu.addAction("Paste selected records before[Ctrl+V]")
        paste_record_after = menu.addAction("Paste selected records after[V]")
        paste_record_inside = menu.addAction("Paste selected records inside[I]")
        delete_record = menu.addAction("Delete selected records[Del]")
        menu.addSeparator()
        what_writes = menu.addAction("Find out what writes to this address")
        what_reads = menu.addAction("Find out what reads this address")
        what_accesses = menu.addAction("Find out what accesses this address")
        if current_row == None:
            deletion_list = [edit_menu.menuAction(), toggle_record, browse_region, disassemble, what_writes, what_reads,
                             what_accesses]
            GuiUtils.delete_menu_entries(menu, deletion_list)
        font_size = self.treeWidget_AddressTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            edit_desc: self.treeWidget_AddressTable_edit_desc,
            edit_address: self.treeWidget_AddressTable_edit_address,
            edit_type: self.treeWidget_AddressTable_edit_type,
            edit_value: self.treeWidget_AddressTable_edit_value,
            toggle_record: self.toggle_selected_records,
            browse_region: self.browse_region_for_selected_row,
            disassemble: self.disassemble_selected_row,
            cut_record: self.cut_selected_records,
            copy_record: self.copy_selected_records,
            paste_record_before: lambda: self.paste_records(insert_after = False),
            paste_record_after: lambda: self.paste_records(insert_after = True),
            paste_record_inside: lambda: self.paste_records(insert_inside = True),
            delete_record: self.delete_selected_records,
            what_writes: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.WRITE_ONLY),
            what_reads: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.READ_ONLY),
            what_accesses: lambda: self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.BOTH)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    @requires_selection("treeWidget_AddressTable", single=True)
    def exec_track_watchpoint_widget(self, watchpoint_type):
        selected_row = self.treeWidget_AddressTable.currentItem()
        address = selected_row.text(ADDR_COL).text()
        value_type_text = selected_row.text(TYPE_COL).text()
        index, length, zero_terminate, byte_len = GuiUtils.text_to_valuetype(value_type_text)
        if byte_len == -1:
            value_text = selected_row.text(VALUE_COL).text()
            encoding, option = type_defs.string_index_to_encoding_dict[index]
            byte_len = len(value_text.encode(encoding, option))
        TrackWatchpointWidgetForm(address, byte_len, watchpoint_type, self).show()

    @requires_selection("treeWidget_AddressTable", single=True)
    def browse_region_for_selected_row(self):
        row = self.treeWidget_AddressTable.currentItem()
        self.memory_view_window.hex_dump_address(int(row.text(ADDR_COL), 16))
        self.memory_view_window.show()
        self.memory_view_window.activateWindow()

    @requires_selection("treeWidget_AddressTable", single=True)
    def disassemble_selected_row(self):
        row = self.treeWidget_AddressTable.currentItem()
        self.memory_view_window.disassemble_expression(
            row.text(ADDR_COL), append_to_travel_history=True)
        self.memory_view_window.show()
        self.memory_view_window.activateWindow()

    @requires_selection("treeWidget_AddressTable", single=False)
    def toggle_selected_records(self):
        row = self.treeWidget_AddressTable.currentItem()
        check_state = row.checkState(FROZEN_COL)
        new_check_state = Qt.Checked if check_state == Qt.Unchecked else Qt.Unchecked
        for row in self.treeWidget_AddressTable.selectedItems():
            row.setCheckState(FROZEN_COL, new_check_state)

    def cut_selected_records(self):
        # Flat cut, does not preserve structure
        self.copy_selected_records()
        self.delete_selected_records()

    def copy_selected_records(self):
        # Flat copy, does not preserve structure
        QApplication.clipboard().setText(repr(
            [self.read_address_table_entries(selected_row)
             for selected_row in self.treeWidget_AddressTable.selectedItems()]
        ))

    def insert_records(self, records, parent_row, insert_index):
        # parent_row should be a QTreeWidgetItem in treeWidget_AddressTable
        # records should be a list of list of strings
        assert isinstance(parent_row, QTreeWidgetItem)

        records = [QTreeWidgetItem(("",) + x) for x in records]
        for rec in records: rec.setCheckState(FROZEN_COL, Qt.Unchecked)

        parent_row.insertChildren(insert_index, records)

    def paste_records(self, insert_after = None, insert_inside = False):
        try:
            records = ast.literal_eval(QApplication.clipboard().text())
            if not isinstance(records, list) or \
                    any(not isinstance(row, tuple) or len(row) != 3 for row in records):
                raise ValueError()
        except (SyntaxError, ValueError):
            QMessageBox.information(self, "Error", "Invalid clipboard content")
            return

        insert_row = self.treeWidget_AddressTable.currentItem()
        root = self.treeWidget_AddressTable.invisibleRootItem()
        if not insert_row: # this is common when the treeWidget_AddressTable is empty
            self.insert_records(records, root, self.treeWidget_AddressTable.topLevelItemCount())
        elif insert_inside:
            self.insert_records(records, insert_row, 0) 
        else:
            parent = insert_row.parent() or root
            self.insert_records(records, parent, parent.indexOfChild(insert_row) + insert_after)
        self.update_address_table_manually()

    def delete_selected_records(self):
        root = self.treeWidget_AddressTable.invisibleRootItem()
        for item in self.treeWidget_AddressTable.selectedItems():
            (item.parent() or root).removeChild(item)

    def treeWidget_AddressTable_key_press_event(self, event):
        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.NoModifier, Qt.Key_Delete), self.delete_selected_records),
            ((Qt.ControlModifier, Qt.Key_B), self.browse_region_for_selected_row),
            ((Qt.ControlModifier, Qt.Key_D), self.disassemble_selected_row),
            ((Qt.NoModifier, Qt.Key_R), self.update_address_table_manually),
            ((Qt.NoModifier, Qt.Key_Space), self.toggle_selected_records),
            ((Qt.ControlModifier, Qt.Key_X), self.cut_selected_records),
            ((Qt.ControlModifier, Qt.Key_C), self.copy_selected_records),
            ((Qt.ControlModifier, Qt.Key_V), lambda: self.paste_records(insert_after = False)),
            ((Qt.NoModifier, Qt.Key_V), lambda: self.paste_records(insert_after = True)),
            ((Qt.NoModifier, Qt.Key_I), lambda: self.paste_records(insert_inside = True)),
            ((Qt.NoModifier, Qt.Key_Return), self.treeWidget_AddressTable_edit_value),
            ((Qt.ControlModifier, Qt.Key_Return), self.treeWidget_AddressTable_edit_desc),
            ((Qt.ControlModifier | Qt.AltModifier, Qt.Key_Return), self.treeWidget_AddressTable_edit_address),
            ((Qt.AltModifier, Qt.Key_Return), self.treeWidget_AddressTable_edit_type)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.treeWidget_AddressTable.keyPressEvent_original(event)

    def update_address_table_manually(self):
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        table_contents = []
        rows = []
        while True:
            row = it.value()
            if not row: break
            it += 1

            address = row.text(ADDR_COL)
            index, length, zero_terminate, byte_len = GuiUtils.text_to_valuetype(row.text(TYPE_COL))
            table_contents.append((address, index, length, zero_terminate))
            rows.append(row)

        new_table_contents = GDB_Engine.read_multiple_addresses(table_contents)
        for row, item in zip(rows, new_table_contents):
            row.setText(VALUE_COL, str(item))

    # gets the information from the dialog then adds it to addresstable
    def pushButton_AddAddressManually_clicked(self):
        manual_address_dialog = ManualAddressDialogForm()
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, zero_terminate = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(description=description, address=address, typeofaddress=typeofaddress,
                                           length=length, zero_terminate=zero_terminate)

    def pushButton_MemoryView_clicked(self):
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def pushButton_Wiki_clicked(self):
        SysUtils.execute_shell_command_as_user('python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def pushButton_About_clicked(self):
        self.about_widget.show()
        self.about_widget.activateWindow()

    def pushButton_Settings_clicked(self):
        settings_dialog = SettingsDialogForm(self.set_default_settings)
        if settings_dialog.exec_():
            self.apply_settings()

    def pushButton_Console_clicked(self):
        console_widget = ConsoleWidgetForm()
        console_widget.showMaximized()

    def pushButton_NewFirstScan_clicked(self):
        QMessageBox.information(self, "Error", "Memory searching isn't implemented yet" +
                                "\nUse GameConqueror for now" +
                                "\nUse GDB Console to detach&attach PINCE(at top right)")
        print("Exception test")
        x = 0 / 0
        if self.pushButton_NewFirstScan.text() == "First Scan":
            self.pushButton_NextScan.setEnabled(True)
            self.pushButton_UndoScan.setEnabled(True)
            self.pushButton_NewFirstScan.setText("New Scan")
            return
        if self.pushButton_NewFirstScan.text() == "New Scan":
            self.pushButton_NextScan.setEnabled(False)
            self.pushButton_UndoScan.setEnabled(False)
            self.pushButton_NewFirstScan.setText("First Scan")

    def pushButton_NextScan_clicked(self):
        # GDB_Engine.send_command('interrupt\nx _start\nc &')  # test
        GDB_Engine.send_command("x/100x _start")
        # t = Thread(target=GDB_Engine.test)  # test
        # t2=Thread(target=test2)
        # t.start()
        # t2.start()
        if self.tableWidget_valuesearchtable.rowCount() <= 0:
            return

    # shows the process select window
    def pushButton_AttachProcess_clicked(self):
        self.processwindow = ProcessForm(self)
        self.processwindow.show()

    def delete_address_table_contents(self):
        confirm_dialog = InputDialogForm(item_list=[("This will clear the contents of address table\nProceed?",)])
        if confirm_dialog.exec_():
            self.treeWidget_AddressTable.clear()

    def on_inferior_exit(self):
        if GDB_Engine.currentpid == -1:
            self.on_status_running()
            GDB_Engine.init_gdb(gdb_path=gdb_path)
            self.label_SelectedProcess.setText("No Process Selected")

    def on_status_detached(self):
        self.label_SelectedProcess.setStyleSheet("color: blue")
        self.label_InferiorStatus.setText("[detached]")
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: blue")

    def on_status_stopped(self):
        self.label_SelectedProcess.setStyleSheet("color: red")
        self.label_InferiorStatus.setText("[stopped]")
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: red")
        self.update_address_table_manually()

    def on_status_running(self):
        self.label_SelectedProcess.setStyleSheet("")
        self.label_InferiorStatus.setVisible(False)

    # closes all windows on exit
    def closeEvent(self, event):
        GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    def add_entry_to_addresstable(self, description, address, typeofaddress, length=0, zero_terminate=True):
        currentrow = QTreeWidgetItem()
        currentrow.setCheckState(FROZEN_COL, Qt.Unchecked)
        typeofaddress_text = GuiUtils.valuetype_to_text(typeofaddress, length, zero_terminate)

        # this line lets us take symbols as parameters, pretty rad isn't it?
        address_text = GDB_Engine.convert_symbol_to_address(address)
        if address_text:
            address = address_text
        self.treeWidget_AddressTable.addTopLevelItem(currentrow)
        value = GDB_Engine.read_single_address(address, typeofaddress, length, zero_terminate)
        self.change_address_table_entries(row=currentrow, description=description, address=address,
                                          typeofaddress=typeofaddress_text, value=str(value))
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

    @requires_selection("treeWidget_AddressTable", single=False)
    def treeWidget_AddressTable_edit_value(self):
        row = self.treeWidget_AddressTable.currentItem()
        value = row.text(VALUE_COL)
        value_index = GuiUtils.text_to_valuetype(
            row.text(TYPE_COL))[0]
        label_text = "Enter the new value"
        if type_defs.VALUE_INDEX.is_string(value_index):
            label_text += "\nPINCE doesn't automatically insert a null terminated string at the end" \
                          "\nCopy-paste this character(\0) if you need to insert it at somewhere"
        dialog = InputDialogForm(item_list=[(label_text, value)], parsed_index=0, value_index=value_index)
        if dialog.exec_():
            table_contents = []
            value_text = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                address = row.text(ADDR_COL)
                value_type = row.text(TYPE_COL)
                value_index = GuiUtils.text_to_valuetype(value_type)[0]
                if type_defs.VALUE_INDEX.is_string(value_index) or value_index == type_defs.VALUE_INDEX.INDEX_AOB:
                    unknown_type = SysUtils.parse_string(value_text, value_index)
                    if unknown_type is not None:
                        length = len(unknown_type)
                        row.setText(TYPE_COL, GuiUtils.change_text_length(value_type, length))
                table_contents.append((address, value_index))
            GDB_Engine.set_multiple_addresses(table_contents, value_text)
            self.update_address_table_manually()

    @requires_selection("treeWidget_AddressTable", single=False)
    def treeWidget_AddressTable_edit_desc(self):
        row = self.treeWidget_AddressTable.currentItem()
        description = row.text(DESC_COL)
        dialog = InputDialogForm(item_list=[("Enter the new description", description)])
        if dialog.exec_():
            description_text = dialog.get_values()
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setText(DESC_COL, description_text)

    @requires_selection("treeWidget_AddressTable", single=False)
    def treeWidget_AddressTable_edit_address(self):
        row = self.treeWidget_AddressTable.currentItem()
        description, address, value_type = self.read_address_table_entries(row=row)
        index, length, zero_terminate, byte_len = GuiUtils.text_to_valuetype(value_type)
        manual_address_dialog = ManualAddressDialogForm(description=description, address=address, index=index,
                                                        length=length, zero_terminate=zero_terminate)
        manual_address_dialog.setWindowTitle("Edit Address")
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, zero_terminate = manual_address_dialog.get_values()
            typeofaddress_text = GuiUtils.valuetype_to_text(value_index=typeofaddress, length=length,
                                                            zero_terminate=zero_terminate)
            address_text = GDB_Engine.convert_symbol_to_address(address)
            if address_text:
                address = address_text
            value = GDB_Engine.read_single_address(address=address, value_index=typeofaddress,
                                                   length=length, zero_terminate=zero_terminate)
            self.change_address_table_entries(row=row, description=description, address=address,
                                              typeofaddress=typeofaddress_text, value=str(value))

    @requires_selection("treeWidget_AddressTable", single=False)
    def treeWidget_AddressTable_edit_type(self):
        row = self.treeWidget_AddressTable.currentItem()
        value_type = row.text(TYPE_COL)
        value_index, length, zero_terminate = GuiUtils.text_to_valuetype(value_type)[0:3]
        dialog = EditTypeDialogForm(index=value_index, length=length, zero_terminate=zero_terminate)
        if dialog.exec_():
            params = dialog.get_values()
            type_text = GuiUtils.valuetype_to_text(*params)
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setText(TYPE_COL, type_text)
            self.update_address_table_manually()

    # Changes the column values of the given row
    def change_address_table_entries(self, row, description="", address="", typeofaddress="", value=""):
        assert isinstance(row, QTreeWidgetItem)
        row.setText(DESC_COL, description)
        row.setText(ADDR_COL, address)
        row.setText(TYPE_COL, typeofaddress)
        row.setText(VALUE_COL, value)

    # Returns the column values of the given row
    def read_address_table_entries(self, row):
        description = row.text(DESC_COL)
        address = row.text(ADDR_COL)
        value_type = row.text(TYPE_COL)
        return description, address, value_type


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_to_parent(self)
        processlist = SysUtils.get_process_list()
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)
        self.pushButton_Close.clicked.connect(self.pushButton_Close_clicked)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_clicked)
        self.pushButton_CreateProcess.clicked.connect(self.pushButton_CreateProcess_clicked)
        self.lineEdit_SearchProcess.textChanged.connect(self.generate_new_list)
        self.tableWidget_ProcessTable.itemDoubleClicked.connect(self.pushButton_Open_clicked)

    # refreshes process list
    def generate_new_list(self):
        text = self.lineEdit_SearchProcess.text()
        processlist = SysUtils.search_in_processes_by_name(text)
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            # closes the window whenever ESC key is pressed
            self.close()
        elif e.key() == Qt.Key_Return:
            self.pushButton_Open_clicked()
        elif e.key() == Qt.Key_F1:
            self.pushButton_CreateProcess_clicked()

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget, processlist):
        tablewidget.setRowCount(0)
        tablewidget.setRowCount(len(processlist))
        for i, row in enumerate(processlist):
            tablewidget.setItem(i, 0, QTableWidgetItem(str(row.pid)))

            # For psutil compatibility with different versions
            try:
                tablewidget.setItem(i, 1, QTableWidgetItem(row.username()))
            except TypeError:
                tablewidget.setItem(i, 1, QTableWidgetItem(row.username))
            tablewidget.setItem(i, 2, QTableWidgetItem(row.name()))

    # self-explanatory
    def pushButton_Close_clicked(self):
        self.close()

    # gets the pid out of the selection to attach
    def pushButton_Open_clicked(self):
        currentitem = self.tableWidget_ProcessTable.item(self.tableWidget_ProcessTable.currentIndex().row(), 0)
        if currentitem is None:
            QMessageBox.information(self, "Error", "Please select a process first")
        else:
            pid = int(currentitem.text())
            if pid == selfpid:
                QMessageBox.information(self, "Error", "What the fuck are you trying to do?")  # planned easter egg
                return
            self.setCursor(QCursor(Qt.WaitCursor))
            attach_result = GDB_Engine.attach(pid, gdb_path=gdb_path)
            if attach_result[0] == type_defs.ATTACH_RESULT.ATTACH_SUCCESSFUL:
                p = SysUtils.get_process_information(GDB_Engine.currentpid)
                self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
                self.enable_scan_gui()
                self.close()
            else:
                QMessageBox.information(self, "Error", attach_result[1])
            self.setCursor(QCursor(Qt.ArrowCursor))

    def pushButton_CreateProcess_clicked(self):
        file_path = QFileDialog.getOpenFileName(self, "Select the target binary")[0]
        if file_path:
            items = [("Enter the optional arguments", ""), ("LD_PRELOAD .so path (optional)", "")]
            arg_dialog = InputDialogForm(item_list=items)
            if arg_dialog.exec_():
                args, ld_preload_path = arg_dialog.get_values()
            else:
                return
            self.setCursor(QCursor(Qt.WaitCursor))
            if GDB_Engine.create_process(file_path, args, ld_preload_path, gdb_path):
                p = SysUtils.get_process_information(GDB_Engine.currentpid)
                self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
                self.enable_scan_gui()
                self.close()
            else:
                QMessageBox.information(self, "Error", "An error occurred while trying to create process")
                self.parent().on_inferior_exit()
            self.setCursor(QCursor(Qt.ArrowCursor))

    def enable_scan_gui(self):
        self.parent().QWidget_Toolbox.setEnabled(True)
        self.parent().pushButton_NextScan.setEnabled(False)
        self.parent().pushButton_UndoScan.setEnabled(False)


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent=None, description="No Description", address="0x",
                 index=type_defs.VALUE_INDEX.INDEX_4BYTES, length=10, zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.adjustSize()
        self.setMinimumWidth(300)
        self.setFixedHeight(self.height())
        self.lineEdit_length.setValidator(QIntValidator(0, 200, self))
        GuiUtils.fill_value_combobox(self.comboBox_ValueType, index)
        self.lineEdit_description.setText(description)
        self.lineEdit_address.setText(address)
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
        elif self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_AOB:
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
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_length.textChanged.connect(self.update_value_of_address)
        self.checkBox_zeroterminate.stateChanged.connect(self.update_value_of_address)
        self.lineEdit_address.textChanged.connect(self.update_value_of_address)
        self.label_valueofaddress.contextMenuEvent = self.label_valueofaddress_context_menu_event
        self.update_value_of_address()

    def label_valueofaddress_context_menu_event(self, event):
        menu = QMenu()
        refresh = menu.addAction("Refresh")
        font_size = self.label_valueofaddress.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            refresh: self.update_value_of_address
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def update_value_of_address(self):
        address = self.lineEdit_address.text()
        address_type = self.comboBox_ValueType.currentIndex()
        if address_type is type_defs.VALUE_INDEX.INDEX_AOB:
            length = self.lineEdit_length.text()
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type, length))
        elif type_defs.VALUE_INDEX.is_string(address_type):
            length = self.lineEdit_length.text()
            is_zeroterminate = self.checkBox_zeroterminate.isChecked()
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type, length, is_zeroterminate))
        else:
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type))

    def comboBox_ValueType_current_index_changed(self):
        if type_defs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentIndex()):
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_zeroterminate.hide()
        self.update_value_of_address()

    def reject(self):
        super(ManualAddressDialogForm, self).reject()

    def accept(self):
        if self.label_length.isVisible():
            length = self.lineEdit_length.text()
            try:
                length = int(length)
            except:
                QMessageBox.information(self, "Error", "Length is not valid")
                return
            if length < 0:
                QMessageBox.information(self, "Error", "Length cannot be smaller than 0")
                return
        super(ManualAddressDialogForm, self).accept()

    def get_values(self):
        description = self.lineEdit_description.text()
        address = self.lineEdit_address.text()
        length = self.lineEdit_length.text()
        try:
            length = int(length)
        except:
            length = 0
        zero_terminate = False
        if self.checkBox_zeroterminate.isChecked():
            zero_terminate = True
        typeofaddress = self.comboBox_ValueType.currentIndex()
        return description, address, typeofaddress, length, zero_terminate


class EditTypeDialogForm(QDialog, EditTypeDialog):
    def __init__(self, parent=None, index=type_defs.VALUE_INDEX.INDEX_4BYTES, length=10, zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setMaximumSize(100, 100)
        self.lineEdit_Length.setValidator(QIntValidator(0, 200, self))
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
        elif self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_AOB:
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
        elif self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_AOB:
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
                length = int(length)
            except:
                QMessageBox.information(self, "Error", "Length is not valid")
                return
            if length < 0:
                QMessageBox.information(self, "Error", "Length cannot be smaller than 0")
                return
        super(EditTypeDialogForm, self).accept()

    def get_values(self):
        length = self.lineEdit_Length.text()
        try:
            length = int(length)
        except:
            length = 0
        zero_terminate = False
        if self.checkBox_ZeroTerminate.isChecked():
            zero_terminate = True
        typeofaddress = self.comboBox_ValueType.currentIndex()
        return typeofaddress, length, zero_terminate


class LoadingDialogForm(QDialog, LoadingDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
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
        pince_directory = SysUtils.get_current_script_directory()
        self.movie = QMovie(pince_directory + "/media/LoadingDialog/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(25, 25))
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()

    # This function only cancels the last command sent
    # Override this if you want to do dangerous stuff like, God forbid, background_thread.terminate()
    def cancel_thread(self):
        GDB_Engine.cancel_last_command()

    def exec_(self):
        self.background_thread.start()
        super(LoadingDialogForm, self).exec_()

    class BackgroundThread(QThread):
        output_ready = pyqtSignal(object)

        def __init__(self):
            super().__init__()

        def run(self):
            output = self.overrided_func()
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
    def __init__(self, parent=None, item_list=None, parsed_index=-1, value_index=type_defs.VALUE_INDEX.INDEX_4BYTES,
                 buttons=(QDialogButtonBox.Ok, QDialogButtonBox.Cancel)):
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
                    label.setAlignment(Qt.AlignCenter)
                label.setText(item[0])
                label.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.TextSelectableByMouse)
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
                QMessageBox.information(self, "Error", "Can't parse the input")
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
        if QKeyEvent.key() == Qt.Key_Enter:
            pass
        else:
            super(TextEditDialogForm, self).keyPressEvent(QKeyEvent)

    def accept(self):
        super(TextEditDialogForm, self).accept()


class SettingsDialogForm(QDialog, SettingsDialog):
    def __init__(self, set_default_settings_func, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.set_default_settings = set_default_settings_func

        # Yet another retarded hack, thanks to pyuic5 not supporting QKeySequenceEdit
        self.keySequenceEdit = QKeySequenceEdit()
        self.verticalLayout_Hotkey.addWidget(self.keySequenceEdit)
        self.comboBox_GDBOutputMode.addItems(type_defs.gdb_output_mode_to_text.values())
        self.listWidget_Options.currentRowChanged.connect(self.change_display)
        icons_directory = GuiUtils.get_icons_directory()
        self.pushButton_GDBPath.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        self.listWidget_Functions.currentRowChanged.connect(self.listWidget_Functions_current_row_changed)
        self.keySequenceEdit.keySequenceChanged.connect(self.keySequenceEdit_key_sequence_changed)
        self.pushButton_ClearHotkey.clicked.connect(self.pushButton_ClearHotkey_clicked)
        self.pushButton_ResetSettings.clicked.connect(self.pushButton_ResetSettings_clicked)
        self.pushButton_GDBPath.clicked.connect(self.pushButton_GDBPath_clicked)
        self.checkBox_AutoUpdateAddressTable.stateChanged.connect(self.checkBox_AutoUpdateAddressTable_state_changed)
        self.config_gui()

    def accept(self):
        try:
            current_table_update_interval = float(self.lineEdit_UpdateInterval.text())
        except:
            QMessageBox.information(self, "Error", "Update interval must be a float")
            return
        try:
            current_instructions_shown = int(self.lineEdit_InstructionsPerScroll.text())
        except:
            QMessageBox.information(self, "Error", "Instruction count must be an integer")
            return
        if current_instructions_shown < 1:
            QMessageBox.information(self, "Error", "Instruction count cannot be lower than 1" +
                                    "\nIt would be silly anyway, wouldn't it?")
            return
        if not self.checkBox_AutoUpdateAddressTable.isChecked():
            pass
        elif current_table_update_interval < 0:
            QMessageBox.information(self, "Error", "Update interval cannot be a negative number")
            return
        elif current_table_update_interval == 0:

            # Easter egg #2
            if not InputDialogForm(item_list=[("You are asking for it, aren't you?",)]).exec_():
                return
        elif current_table_update_interval < 0.1:
            if not InputDialogForm(item_list=[("Update interval should be bigger than 0.1 seconds" +
                                               "\nSetting update interval less than 0.1 seconds may cause slowdown"
                                               "\nProceed?",)]).exec_():
                return
        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.settings.setValue("General/address_table_update_interval", current_table_update_interval)
        self.settings.setValue("General/show_messagebox_on_exception", self.checkBox_MessageBoxOnException.isChecked())
        self.settings.setValue("General/show_messagebox_on_toggle_attach",
                               self.checkBox_MessageBoxOnToggleAttach.isChecked())
        self.settings.setValue("General/gdb_output_mode", self.comboBox_GDBOutputMode.currentIndex())
        for key, value in list(global_hotkeys.items()):
            self.settings.setValue("Hotkeys/" + key, getattr(self, key))
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
            if InputDialogForm(item_list=[("You have changed the GDB path, reset GDB now?",)]).exec_():
                GDB_Engine.init_gdb(gdb_path=selected_gdb_path)
        self.settings.setValue("Debug/gdb_path", selected_gdb_path)
        super(SettingsDialogForm, self).accept()

    def config_gui(self):
        self.settings = QSettings()
        self.checkBox_AutoUpdateAddressTable.setChecked(
            self.settings.value("General/auto_update_address_table", type=bool))
        self.lineEdit_UpdateInterval.setText(
            str(self.settings.value("General/address_table_update_interval", type=float)))
        self.checkBox_MessageBoxOnException.setChecked(
            self.settings.value("General/show_messagebox_on_exception", type=bool))
        self.checkBox_MessageBoxOnToggleAttach.setChecked(
            self.settings.value("General/show_messagebox_on_toggle_attach", type=bool))
        self.comboBox_GDBOutputMode.setCurrentIndex(self.settings.value("General/gdb_output_mode", type=int))
        self.listWidget_Functions.clear()
        self.listWidget_Functions.addItems(
            ["Pause the process", "Break the process", "Continue the process", "Toggle attach/detach"])
        for key, value in list(global_hotkeys.items()):
            setattr(self, key, self.settings.value("Hotkeys/" + key))
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

    def change_display(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def listWidget_Functions_current_row_changed(self, index):
        if index is -1:
            self.keySequenceEdit.clear()
        else:
            self.keySequenceEdit.setKeySequence(getattr(self, list(global_hotkeys.items())[index][0]))

    def keySequenceEdit_key_sequence_changed(self):
        current_index = self.listWidget_Functions.currentIndex().row()
        if current_index is -1:
            self.keySequenceEdit.clear()
        else:
            setattr(self, list(global_hotkeys.items())[current_index][0], self.keySequenceEdit.keySequence().toString())

    def pushButton_ClearHotkey_clicked(self):
        self.keySequenceEdit.clear()

    def pushButton_ResetSettings_clicked(self):
        confirm_dialog = InputDialogForm(item_list=[("This will reset to the default settings\nProceed?",)])
        if confirm_dialog.exec_():
            self.set_default_settings()
            self.config_gui()

    def checkBox_AutoUpdateAddressTable_state_changed(self):
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.QWidget_UpdateInterval.setEnabled(True)
        else:
            self.QWidget_UpdateInterval.setEnabled(False)

    def pushButton_GDBPath_clicked(self):
        current_path = self.lineEdit_GDBPath.text()
        file_path = QFileDialog.getOpenFileName(self, "Select the gdb binary", os.path.dirname(current_path))[0]
        if file_path:
            self.lineEdit_GDBPath.setText(file_path)


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
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setMaxVisibleItems(8)
        self.lineEdit.setCompleter(self.completer)
        self.quit_commands = ("q", "quit", "-gdb-exit")
        self.input_history = [""]
        self.current_history_index = -1
        self.await_async_output_thread = AwaitAsyncOutput()
        self.await_async_output_thread.async_output_ready.connect(self.on_async_output)
        self.await_async_output_thread.start()
        self.pushButton_Send.clicked.connect(self.communicate)
        self.pushButton_SendCtrl.clicked.connect(lambda: self.communicate(control=True))
        self.shortcut_send = QShortcut(QKeySequence("Return"), self)
        self.shortcut_send.activated.connect(self.communicate)
        self.shortcut_complete_command = QShortcut(QKeySequence("Tab"), self)
        self.shortcut_complete_command.activated.connect(self.complete_command)
        self.shortcut_send_ctrl = QShortcut(QKeySequence("Ctrl+C"), self)
        self.shortcut_send_ctrl.activated.connect(lambda: self.communicate(control=True))
        self.shortcut_multiline_mode = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_multiline_mode.activated.connect(self.enter_multiline_mode)
        self.lineEdit.textEdited.connect(self.finish_completion)

        # Saving the original function because super() doesn't work when we override functions like this
        self.lineEdit.keyPressEvent_original = self.lineEdit.keyPressEvent
        self.lineEdit.keyPressEvent = self.lineEdit_key_press_event
        self.reset_console_text()

    def communicate(self, control=False):
        if control:
            console_input = "/Ctrl+C"
        else:
            console_input = self.lineEdit.text()
            self.input_history.insert(-1, console_input)
            self.current_history_index = -1
        if console_input.lower() == "/clear":
            self.reset_console_text()
            return
        elif console_input.strip().lower() in self.quit_commands:
            console_output = "pls don't"
        else:
            if not control:
                if self.radioButton_CLI.isChecked():
                    console_output = GDB_Engine.send_command(console_input, cli_output=True)
                else:
                    console_output = GDB_Engine.send_command(console_input)
                if not console_output:
                    if GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_RUNNING:
                        console_output = "Inferior is running"
            else:
                GDB_Engine.interrupt_inferior()
                console_output = ""
        self.textBrowser.append("-->" + console_input)
        if console_output:
            self.textBrowser.append(console_output)
        self.lineEdit.clear()
        self.scroll_to_bottom()

    def reset_console_text(self):
        self.textBrowser.clear()
        self.textBrowser.append("Hotkeys:")
        self.textBrowser.append("----------------------------")
        self.textBrowser.append("Send=Enter                 |")
        self.textBrowser.append("Send ctrl+c=Ctrl+C         |")
        self.textBrowser.append("Multi-line mode=Ctrl+Enter |")
        self.textBrowser.append("Complete command=Tab       |")
        self.textBrowser.append("----------------------------")
        self.textBrowser.append("Commands:")
        self.textBrowser.append("----------------------------------------------------------")
        self.textBrowser.append("/clear: Clear the console                                |")
        self.textBrowser.append("phase-out: Detach from the current process               |")
        self.textBrowser.append("phase-in: Attach back to the previously detached process |")
        self.textBrowser.append(
            "---------------------------------------------------------------------------------------------------")
        self.textBrowser.append(
            "pince-init-so-file so_file_path: Initializes 'lib' variable                                       |")
        self.textBrowser.append(
            "pince-get-so-file-information: Get information about current lib                                  |")
        self.textBrowser.append(
            "pince-execute-from-so-file lib.func(params): Execute a function from lib                          |")
        self.textBrowser.append(
            "# Check https://github.com/korcankaraokcu/PINCE/wiki#extending-pince-with-so-files for an example |")
        self.textBrowser.append(
            "# CLI output mode doesn't work very well with .so extensions, use MI output mode instead          |")
        self.textBrowser.append(
            "---------------------------------------------------------------------------------------------------")
        self.textBrowser.append("You can change the output mode from bottom right")
        self.textBrowser.append("Note: Changing output mode only affects commands sent. Any other " +
                                "output coming from external sources(e.g async output) will be shown in MI format")

    def scroll_to_bottom(self):
        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.textBrowser.setTextCursor(cursor)
        self.textBrowser.ensureCursorVisible()

    def enter_multiline_mode(self):
        multiline_dialog = TextEditDialogForm(text=self.lineEdit.text())
        if multiline_dialog.exec_():
            self.lineEdit.setText(multiline_dialog.get_values())
            self.communicate()

    def on_async_output(self, async_output):
        self.textBrowser.append(async_output)
        self.scroll_to_bottom()

    def scroll_backwards_history(self):
        try:
            self.lineEdit.setText(self.input_history[self.current_history_index - 1])
            self.current_history_index += -1
        except IndexError:
            pass

    def scroll_forwards_history(self):
        if self.current_history_index == -1:
            return
        self.lineEdit.setText(self.input_history[self.current_history_index + 1])
        self.current_history_index += 1

    def lineEdit_key_press_event(self, event):
        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.NoModifier, Qt.Key_Up), self.scroll_backwards_history),
            ((Qt.NoModifier, Qt.Key_Down), self.scroll_forwards_history)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.lineEdit.keyPressEvent_original(event)

    def finish_completion(self):
        self.completion_model.setStringList([])

    def complete_command(self):
        if GDB_Engine.gdb_initialized and GDB_Engine.currentpid != -1 and self.lineEdit.text() and \
                GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
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
        self.actionBreak.setText("Break[" + global_hotkeys["break_hotkey"] + "]")
        self.actionRun.setText("Run[" + global_hotkeys["continue_hotkey"] + "]")
        self.actionToggle_Attach.setText("Toggle Attach[" + global_hotkeys["toggle_attach_hotkey"] + "]")

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
        self.actionToggle_Breakpoint.triggered.connect(self.toggle_breakpoint)
        self.actionSet_Address.triggered.connect(self.set_address)

    def initialize_view_context_menu(self):
        self.actionBookmarks.triggered.connect(self.actionBookmarks_triggered)
        self.actionStackTrace_Info.triggered.connect(self.actionStackTrace_Info_triggered)
        self.actionBreakpoints.triggered.connect(self.actionBreakpoints_triggered)
        self.actionFunctions.triggered.connect(self.actionFunctions_triggered)
        self.actionGDB_Log_File.triggered.connect(self.actionGDB_Log_File_triggered)
        self.actionMemory_Regions.triggered.connect(self.actionMemory_Regions_triggered)
        self.actionReferenced_Strings.triggered.connect(self.actionReferenced_Strings_triggered)
        self.actionReferenced_Calls.triggered.connect(self.actionReferenced_Calls_triggered)

    def initialize_tools_context_menu(self):
        self.actionInject_so_file.triggered.connect(self.actionInject_so_file_triggered)
        self.actionCall_Function.triggered.connect(self.actionCall_Function_triggered)
        self.actionSearch_Opcode.triggered.connect(self.actionSearch_Opcode_triggered)
        self.actionDissect_Code.triggered.connect(self.actionDissect_Code_triggered)

    def initialize_help_context_menu(self):
        self.actionLibPINCE.triggered.connect(self.actionLibPINCE_triggered)

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
        self.widget_StackView.resize(420, self.widget_StackView.height())  # blaze it
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

        self.tableWidget_Disassemble.wheelEvent = QEvent.ignore
        self.verticalScrollBar_Disassemble.wheelEvent = QEvent.ignore

        GuiUtils.center_scroll_bar(self.verticalScrollBar_Disassemble)
        self.verticalScrollBar_Disassemble.mouseReleaseEvent = self.verticalScrollBar_Disassemble_mouse_release_event

        self.disassemble_scroll_bar_timer = QTimer()
        self.disassemble_scroll_bar_timer.setInterval(100)
        self.disassemble_scroll_bar_timer.timeout.connect(self.check_disassemble_scrollbar)
        self.disassemble_scroll_bar_timer.start()

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
        self.hex_view_currently_displayed_address = 0
        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        self.tableView_HexView_Hex.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Ascii.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Hex.doubleClicked.connect(self.exec_hex_view_edit_dialog)
        self.tableView_HexView_Ascii.doubleClicked.connect(self.exec_hex_view_edit_dialog)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableView_HexView_Hex.keyPressEvent_original = self.tableView_HexView_Hex.keyPressEvent
        self.tableView_HexView_Hex.keyPressEvent = self.widget_HexView_key_press_event
        self.tableView_HexView_Ascii.keyPressEvent = self.widget_HexView_key_press_event

        self.verticalScrollBar_HexView.wheelEvent = QEvent.ignore
        self.tableWidget_HexView_Address.wheelEvent = QEvent.ignore
        self.scrollArea_Hex.keyPressEvent = QEvent.ignore
        self.tableWidget_HexView_Address.setAutoScroll(False)
        self.tableWidget_HexView_Address.setStyleSheet("QTableWidget {background-color: transparent;}")
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.NoSelection)

        self.hex_model = QHexModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.ascii_model = QAsciiModel(HEX_VIEW_ROW_COUNT, HEX_VIEW_COL_COUNT)
        self.tableView_HexView_Hex.setModel(self.hex_model)
        self.tableView_HexView_Ascii.setModel(self.ascii_model)

        self.tableView_HexView_Hex.selectionModel().currentChanged.connect(self.on_hex_view_current_changed)
        self.tableView_HexView_Ascii.selectionModel().currentChanged.connect(self.on_ascii_view_current_changed)

        self.scrollArea_Hex.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea_Hex.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.verticalHeader().setDefaultSectionSize(
            self.tableView_HexView_Hex.verticalHeader().defaultSectionSize())

        GuiUtils.center_scroll_bar(self.verticalScrollBar_HexView)
        self.hex_view_scroll_bar_timer = QTimer()
        self.hex_view_scroll_bar_timer.setInterval(100)
        self.hex_view_scroll_bar_timer.timeout.connect(self.check_hex_view_scrollbar)
        self.hex_view_scroll_bar_timer.start()
        self.verticalScrollBar_HexView.mouseReleaseEvent = self.verticalScrollBar_HexView_mouse_release_event

    def show_trace_window(self):
        trace_instructions_window = TraceInstructionsWindowForm(prompt_dialog=False)
        trace_instructions_window.showMaximized()

    def step_instruction(self):
        if self.updating_memoryview:
            return
        GDB_Engine.step_instruction()

    def step_over_instruction(self):
        if self.updating_memoryview:
            return
        GDB_Engine.step_over_instruction()

    def execute_till_return(self):
        if self.updating_memoryview:
            return
        GDB_Engine.execute_till_return()

    def set_address(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        GDB_Engine.set_convenience_variable("pc", current_address)
        self.refresh_disassemble_view()

    def toggle_breakpoint(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        if GDB_Engine.check_address_in_breakpoints(current_address_int):
            GDB_Engine.delete_breakpoint(current_address)
        else:
            if not GDB_Engine.add_breakpoint(current_address):
                QMessageBox.information(self, "Error", "Failed to set breakpoint at address " + current_address)
        self.refresh_disassemble_view()

    def toggle_watchpoint(self, address, watchpoint_type=type_defs.WATCHPOINT_TYPE.BOTH):
        if GDB_Engine.check_address_in_breakpoints(address):
            GDB_Engine.delete_breakpoint(hex(address))
        else:
            watchpoint_dialog = InputDialogForm(item_list=[("Enter the watchpoint length in size of bytes", "")])
            if watchpoint_dialog.exec_():
                user_input = watchpoint_dialog.get_values()
                user_input_int = SysUtils.parse_string(user_input, type_defs.VALUE_INDEX.INDEX_4BYTES)
                if user_input_int is None:
                    QMessageBox.information(self, "Error", user_input + " can't be parsed as an integer")
                    return
                if user_input_int < 1:
                    QMessageBox.information(self, "Error", "Breakpoint length can't be lower than 1")
                    return
                if len(GDB_Engine.add_watchpoint(hex(address), user_input_int, watchpoint_type)) < 1:
                    QMessageBox.information(self, "Error", "Failed to set watchpoint at address " + hex(address))
        self.refresh_hex_view()

    def label_HexView_Information_context_menu_event(self, event):
        def copy_to_clipboard():
            QApplication.clipboard().setText(self.label_HexView_Information.text())

        menu = QMenu()
        copy_label = menu.addAction("Copy to Clipboard")
        font_size = self.label_HexView_Information.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            copy_label: copy_to_clipboard
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def widget_HexView_context_menu_event(self, event):
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        menu = QMenu()
        edit = menu.addAction("Edit")
        menu.addSeparator()
        go_to = menu.addAction("Go to expression[Ctrl+G]")
        disassemble = menu.addAction("Disassemble this address[Ctrl+D]")
        menu.addSeparator()
        add_address = menu.addAction("Add this address to address list[Ctrl+A]")
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        watchpoint_menu = menu.addMenu("Set Watchpoint")
        watchpoint_write = watchpoint_menu.addAction("Write Only")
        watchpoint_read = watchpoint_menu.addAction("Read Only")
        watchpoint_both = watchpoint_menu.addAction("Both")
        add_condition = menu.addAction("Add/Change condition for breakpoint")
        delete_breakpoint = menu.addAction("Delete Breakpoint")
        if not GDB_Engine.check_address_in_breakpoints(selected_address):
            GuiUtils.delete_menu_entries(menu, [add_condition, delete_breakpoint])
        else:
            GuiUtils.delete_menu_entries(menu, [watchpoint_menu.menuAction()])
        font_size = self.widget_HexView.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            edit: self.exec_hex_view_edit_dialog,
            go_to: self.exec_hex_view_go_to_dialog,
            disassemble: lambda: self.disassemble_expression(hex(selected_address), append_to_travel_history=True),
            add_address: self.exec_hex_view_add_address_dialog,
            refresh: lambda: self.hex_dump_address(self.hex_view_currently_displayed_address),
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
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        HexEditDialogForm(hex(selected_address)).exec_()
        self.refresh_hex_view()

    def exec_hex_view_go_to_dialog(self):
        current_address = hex(self.hex_view_currently_displayed_address)
        go_to_dialog = InputDialogForm(item_list=[("Enter the expression", current_address)])
        if go_to_dialog.exec_():
            expression = go_to_dialog.get_values()
            dest_address = GDB_Engine.convert_symbol_to_address(expression)
            if dest_address is "":
                QMessageBox.information(self, "Error", "Cannot access memory at expression " + expression)
                return
            self.hex_dump_address(int(dest_address, 16))

    def exec_hex_view_add_address_dialog(self):
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        manual_address_dialog = ManualAddressDialogForm(address=hex(selected_address),
                                                        index=type_defs.VALUE_INDEX.INDEX_AOB)
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, zero_terminate = manual_address_dialog.get_values()
            self.parent().add_entry_to_addresstable(description, address, typeofaddress, length, zero_terminate)

    def verticalScrollBar_HexView_mouse_release_event(self, event):
        GuiUtils.center_scroll_bar(self.verticalScrollBar_HexView)

    def verticalScrollBar_Disassemble_mouse_release_event(self, event):
        GuiUtils.center_scroll_bar(self.verticalScrollBar_Disassemble)

    def check_hex_view_scrollbar(self):
        if GDB_Engine.inferior_status != type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
            return
        maximum = self.verticalScrollBar_HexView.maximum()
        minimum = self.verticalScrollBar_HexView.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_HexView.value()
        if midst - 10 < current_value < midst + 10:
            return
        current_address = self.hex_view_currently_displayed_address
        if current_value < midst:
            next_address = current_address - 0x40
        else:
            next_address = current_address + 0x40
        self.hex_dump_address(next_address)

    def check_disassemble_scrollbar(self):
        if GDB_Engine.inferior_status != type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
            return
        maximum = self.verticalScrollBar_Disassemble.maximum()
        minimum = self.verticalScrollBar_Disassemble.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_Disassemble.value()
        if midst - 10 < current_value < midst + 10:
            return
        current_address = self.disassemble_currently_displayed_address
        if current_value < midst:
            next_address = GDB_Engine.find_address_of_closest_instruction(current_address, instructions_per_scroll,
                                                                          "previous")
        else:
            next_address = GDB_Engine.find_address_of_closest_instruction(current_address, instructions_per_scroll,
                                                                          "next")
        self.disassemble_expression(next_address)

    def on_hex_view_current_changed(self, QModelIndex_current):
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SingleSelection)
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        self.hex_view_last_selected_address_int = selected_address
        self.tableView_HexView_Ascii.selectionModel().setCurrentIndex(QModelIndex_current,
                                                                      QItemSelectionModel.ClearAndSelect)
        self.tableWidget_HexView_Address.selectRow(QModelIndex_current.row())
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.NoSelection)

    def on_ascii_view_current_changed(self, QModelIndex_current):
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView_HexView_Hex.selectionModel().setCurrentIndex(QModelIndex_current,
                                                                    QItemSelectionModel.ClearAndSelect)
        self.tableWidget_HexView_Address.selectRow(QModelIndex_current.row())
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.NoSelection)

    def hex_dump_address(self, int_address, offset=HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT):
        information = SysUtils.get_region_info(GDB_Engine.currentpid, int_address)
        if information is not None:
            self.label_HexView_Information.setText(
                "Protection:" + information.region.perms + " | Base:" + information.start + "-" + information.end)
        else:
            self.label_HexView_Information.setText("This region is invalid")
        self.tableWidget_HexView_Address.setRowCount(0)
        self.tableWidget_HexView_Address.setRowCount(HEX_VIEW_ROW_COUNT * HEX_VIEW_COL_COUNT)
        for row, current_offset in enumerate(range(HEX_VIEW_ROW_COUNT)):
            self.tableWidget_HexView_Address.setItem(row, 0, QTableWidgetItem(hex(int_address + current_offset * 16)))
        tableWidget_HexView_column_size = self.tableWidget_HexView_Address.sizeHintForColumn(0) + 5
        self.tableWidget_HexView_Address.setMaximumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setMinimumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setColumnWidth(0, tableWidget_HexView_column_size)
        self.hex_model.refresh(int_address, offset)
        self.ascii_model.refresh(int_address, offset)
        self.hex_view_currently_displayed_address = int_address
        if int_address <= self.hex_view_last_selected_address_int <= int_address + offset:
            difference = self.hex_view_last_selected_address_int - int_address
            model_index = QModelIndex(
                self.hex_model.index(int(difference / HEX_VIEW_COL_COUNT), difference % HEX_VIEW_COL_COUNT))
            self.tableView_HexView_Hex.selectionModel().select(model_index, QItemSelectionModel.ClearAndSelect)
            self.tableView_HexView_Ascii.selectionModel().select(model_index, QItemSelectionModel.ClearAndSelect)
        else:
            self.tableView_HexView_Hex.clearSelection()
            self.tableView_HexView_Ascii.clearSelection()

    def refresh_hex_view(self):
        if self.tableWidget_HexView_Address.rowCount() == 0:
            entry_point = GDB_Engine.find_entry_point()
            if not entry_point:
                # **Shrugs**
                entry_point = "0x00400000"
            self.hex_dump_address(int(entry_point, 16))
            self.tableView_HexView_Hex.resize_to_contents()
            self.tableView_HexView_Ascii.resize_to_contents()
        else:
            self.hex_dump_address(self.hex_view_currently_displayed_address)

    # offset can also be an address as hex str
    def disassemble_expression(self, expression, offset="+200", append_to_travel_history=False):
        disas_data = GDB_Engine.disassemble(expression, offset)
        if not disas_data:
            QMessageBox.information(self, "Error", "Cannot access memory at expression " + expression)
            return
        program_counter = GDB_Engine.convert_symbol_to_address("$pc")
        program_counter_int = int(program_counter, 16)
        row_colour = {}
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
        for row, item in enumerate(disas_data):
            comment = ""
            current_address = int(SysUtils.extract_address(item[0]), 16)
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
                tooltip_text = "Referenced by:\n"
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
                tooltip_text += "\n\nPress 'E' to see a detailed list of referrers"
                try:
                    row_colour[row].append(REF_COLOUR)
                except KeyError:
                    row_colour[row] = [REF_COLOUR]
                real_ref_count = 0
                if jmp_ref_exists:
                    real_ref_count += len(jmp_referrers)
                if call_ref_exists:
                    real_ref_count += len(call_referrers)
                item[0] = "{" + str(real_ref_count) + "}" + item[0]
            if current_address == program_counter_int:
                item[0] = ">>>" + item[0]
                try:
                    row_colour[row].append(PC_COLOUR)
                except KeyError:
                    row_colour[row] = [PC_COLOUR]
            for bookmark_item in self.tableWidget_Disassemble.bookmarks.keys():
                if current_address == bookmark_item:
                    try:
                        row_colour[row].append(BOOKMARK_COLOUR)
                    except KeyError:
                        row_colour[row] = [BOOKMARK_COLOUR]
                    item[0] = "(M)" + item[0]
                    comment = self.tableWidget_Disassemble.bookmarks[bookmark_item]
                    break
            for breakpoint in breakpoint_info:
                int_breakpoint_address = int(breakpoint.address, 16)
                if current_address == int_breakpoint_address:
                    try:
                        row_colour[row].append(BREAKPOINT_COLOUR)
                    except KeyError:
                        row_colour[row] = [BREAKPOINT_COLOUR]
                    breakpoint_mark = "(B"
                    if breakpoint.enabled == "n":
                        breakpoint_mark += "-disabled"
                    else:
                        if breakpoint.disp != "keep":
                            breakpoint_mark += "-" + breakpoint.disp
                        if breakpoint.enable_count:
                            breakpoint_mark += "-" + breakpoint.enable_count
                    breakpoint_mark += ")"
                    item[0] = breakpoint_mark + item[0]
                    break
            if current_address == self.disassemble_last_selected_address_int:
                self.tableWidget_Disassemble.selectRow(row)
            addr_item = QTableWidgetItem(item[0])
            bytes_item = QTableWidgetItem(item[1])
            opcodes_item = QTableWidgetItem(item[2])
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
        self.handle_colours(row_colour)
        self.tableWidget_Disassemble.horizontalHeader().setStretchLastSection(True)

        # We append the old record to travel history as last action because we wouldn't like to see unnecessary
        # addresses in travel history if any error occurs while displaying the next location
        if append_to_travel_history:
            self.tableWidget_Disassemble.travel_history.append(previous_first_address)
        self.disassemble_currently_displayed_address = current_first_address

    def refresh_disassemble_view(self):
        self.disassemble_expression(self.disassemble_currently_displayed_address)

    # Set colour of a row if a specific address is encountered(e.g $pc, a bookmarked address etc.)
    def handle_colours(self, row_colour):
        for row in row_colour:
            current_row = row_colour[row]
            if PC_COLOUR in current_row:
                if BREAKPOINT_COLOUR in current_row:
                    colour = Qt.green
                elif BOOKMARK_COLOUR in current_row:
                    colour = Qt.yellow
                else:
                    colour = PC_COLOUR
                self.set_row_colour(row, colour)
                continue
            if BREAKPOINT_COLOUR in current_row:
                if BOOKMARK_COLOUR in current_row:
                    colour = Qt.magenta
                else:
                    colour = BREAKPOINT_COLOUR
                self.set_row_colour(row, colour)
                continue
            if BOOKMARK_COLOUR in current_row:
                self.set_row_colour(row, BOOKMARK_COLOUR)
                continue
            if REF_COLOUR in current_row:
                self.set_row_colour(row, REF_COLOUR)

    # color parameter should be Qt.colour
    def set_row_colour(self, row, colour):
        for col in range(self.tableWidget_Disassemble.columnCount()):
            self.tableWidget_Disassemble.item(row, col).setData(Qt.BackgroundColorRole, QColor(colour))

    def on_process_stop(self):
        if GDB_Engine.stop_reason == type_defs.STOP_REASON.PAUSE:
            self.setWindowTitle("Memory Viewer - Paused")
            return
        self.updating_memoryview = True
        time0 = time()
        thread_info = GDB_Engine.get_current_thread_information()
        self.setWindowTitle("Memory Viewer - Currently Debugging Thread " + thread_info)
        self.disassemble_expression("$pc")
        self.update_registers()
        if self.stackedWidget_StackScreens.currentWidget() == self.StackTrace:
            self.update_stacktrace()
        elif self.stackedWidget_StackScreens.currentWidget() == self.Stack:
            self.update_stack()
        self.refresh_hex_view()
        if self.isVisible():
            self.show()
        else:
            self.showMaximized()
        if bring_disassemble_to_front:
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
        QApplication.processEvents()
        time1 = time()
        print("UPDATED MEMORYVIEW IN:" + str(time1 - time0))
        self.updating_memoryview = False

    def on_process_running(self):
        self.setWindowTitle("Memory Viewer - Running")

    def add_breakpoint_condition(self, int_address):
        condition_text = "Enter the expression for condition, for instance:\n\n" + \
                         "$eax==0x523\n" + \
                         "$rax>0 && ($rbp<0 || $rsp==0)\n" + \
                         "printf($r10)==3"
        breakpoint = GDB_Engine.check_address_in_breakpoints(int_address)
        if breakpoint:
            condition_line_edit_text = breakpoint.condition
        else:
            condition_line_edit_text = ""
        condition_dialog = InputDialogForm(item_list=[(condition_text, condition_line_edit_text, Qt.AlignLeft)])
        if condition_dialog.exec_():
            condition = condition_dialog.get_values()
            if not GDB_Engine.modify_breakpoint(hex(int_address), type_defs.BREAKPOINT_MODIFY.CONDITION,
                                                condition=condition):
                QMessageBox.information(self, "Error", "Failed to set condition for address " + hex(int_address) +
                                        "\nCheck terminal for details")

    def update_registers(self):
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
        stack_trace_info = GDB_Engine.get_stacktrace_info()
        self.tableWidget_StackTrace.setRowCount(0)
        self.tableWidget_StackTrace.setRowCount(len(stack_trace_info))
        for row, item in enumerate(stack_trace_info):
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_RETURN_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_FRAME_ADDRESS_COL, QTableWidgetItem(item[1]))

    def set_stack_widget(self, stack_widget):
        self.stackedWidget_StackScreens.setCurrentWidget(stack_widget)
        if stack_widget == self.Stack:
            self.update_stack()
        elif stack_widget == self.StackTrace:
            self.update_stacktrace()

    def tableWidget_StackTrace_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_StackTrace.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_StackTrace)

        menu = QMenu()
        switch_to_stack = menu.addAction("Full Stack")
        menu.addSeparator()
        clipboard_menu = menu.addMenu("Copy to Clipboard")
        copy_return = clipboard_menu.addAction("Copy Return Address")
        copy_frame = clipboard_menu.addAction("Copy Frame Address")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [clipboard_menu.menuAction()])
        refresh = menu.addAction("Refresh[R]")
        font_size = self.tableWidget_StackTrace.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        selected_row = GuiUtils.get_current_row(self.tableWidget_Stack)
        current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.NoModifier, Qt.Key_R), self.update_stack),
            ((Qt.ControlModifier, Qt.Key_D),
             lambda: self.disassemble_expression(current_address, append_to_travel_history=True)),
            ((Qt.ControlModifier, Qt.Key_H), lambda: self.hex_dump_address(int(current_address, 16)))
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.tableWidget_Stack.keyPressEvent_original(event)

    def tableWidget_Stack_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_Stack.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_Stack)
        current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        menu = QMenu()
        switch_to_stacktrace = menu.addAction("Stacktrace")
        menu.addSeparator()
        clipboard_menu = menu.addMenu("Copy to Clipboard")
        copy_address = clipboard_menu.addAction("Copy Address")
        copy_value = clipboard_menu.addAction("Copy Value")
        copy_points_to = clipboard_menu.addAction("Copy Points to")
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        show_in_disas = menu.addAction("Disassemble 'value' pointer address[Ctrl+D]")
        show_in_hex = menu.addAction("Show 'value' pointer in HexView[Ctrl+H]")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [clipboard_menu.menuAction(), show_in_disas, show_in_hex])
        font_size = self.tableWidget_Stack.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.NoModifier, Qt.Key_R), self.update_stacktrace)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.tableWidget_StackTrace.keyPressEvent_original(event)

    def widget_Disassemble_wheel_event(self, event):
        steps = event.angleDelta()
        current_address = self.disassemble_currently_displayed_address
        if steps.y() > 0:
            next_address = GDB_Engine.find_address_of_closest_instruction(current_address, instructions_per_scroll,
                                                                          "previous")
        else:
            next_address = GDB_Engine.find_address_of_closest_instruction(current_address, instructions_per_scroll,
                                                                          "next")
        self.disassemble_expression(next_address)

    def widget_HexView_wheel_event(self, event):
        steps = event.angleDelta()
        current_address = self.hex_view_currently_displayed_address
        if steps.y() > 0:
            next_address = current_address - 0x40
        else:
            next_address = current_address + 0x40
        self.hex_dump_address(next_address)

    def widget_HexView_key_press_event(self, event):
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()

        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.ControlModifier, Qt.Key_G), self.exec_hex_view_go_to_dialog),
            ((Qt.ControlModifier, Qt.Key_D),
             lambda: self.disassemble_expression(hex(selected_address), append_to_travel_history=True)),
            ((Qt.ControlModifier, Qt.Key_A), self.exec_hex_view_add_address_dialog),
            ((Qt.NoModifier, Qt.Key_R), self.refresh_hex_view)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.tableView_HexView_Hex.keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        actions = type_defs.KeyboardModifiersTupleDict([
            ((Qt.NoModifier, Qt.Key_Space), lambda: self.follow_instruction(selected_row)),
            ((Qt.ControlModifier, Qt.Key_E), lambda: self.exec_examine_referrers_widget(current_address_text)),
            ((Qt.ControlModifier, Qt.Key_G), self.exec_disassemble_go_to_dialog),
            ((Qt.ControlModifier, Qt.Key_H), lambda: self.hex_dump_address(current_address_int)),
            ((Qt.ControlModifier, Qt.Key_B), lambda: self.bookmark_address(current_address_int)),
            ((Qt.ControlModifier, Qt.Key_D), self.dissect_current_region),
            ((Qt.ControlModifier, Qt.Key_T), self.exec_trace_instructions_dialog),
            ((Qt.NoModifier, Qt.Key_R), self.refresh_disassemble_view)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.tableWidget_Disassemble.keyPressEvent_original(event)

    def tableWidget_Disassemble_item_double_clicked(self, index):
        if index.column() == DISAS_COMMENT_COL:
            selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = int(SysUtils.extract_address(current_address_text), 16)
            if current_address in self.tableWidget_Disassemble.bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def tableWidget_Disassemble_item_selection_changed(self):
        try:
            selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
            selected_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            self.disassemble_last_selected_address_int = int(SysUtils.extract_address(selected_address_text), 16)
        except (TypeError, ValueError, AttributeError):
            pass

    # Search the item in given row for location changing instructions
    # Go to the address pointed by that instruction if it contains any
    def follow_instruction(self, selected_row):
        address = SysUtils.extract_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text(),
            search_for_location_changing_instructions=True)
        if address:
            self.disassemble_expression(address, append_to_travel_history=True)

    def disassemble_go_back(self):
        if self.tableWidget_Disassemble.travel_history:
            last_location = self.tableWidget_Disassemble.travel_history[-1]
            self.disassemble_expression(last_location)
            self.tableWidget_Disassemble.travel_history.pop()

    def tableWidget_Disassemble_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_Disassemble.item(row, column).text())

        def copy_all_columns(row):
            copied_string = ""
            for column in range(self.tableWidget_Disassemble.columnCount()):
                copied_string += self.tableWidget_Disassemble.item(row, column).text() + "\t"
            QApplication.clipboard().setText(copied_string)

        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction("Go to expression[Ctrl+G]")
        back = menu.addAction("Back")
        show_in_hex_view = menu.addAction("Show this address in HexView[Ctrl+H]")
        menu.addSeparator()
        followable = SysUtils.extract_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text(),
            search_for_location_changing_instructions=True)
        follow = menu.addAction("Follow[Space]")
        if not followable:
            GuiUtils.delete_menu_entries(menu, [follow])
        examine_referrers = menu.addAction("Examine Referrers[Ctrl+E]")
        if not GuiUtils.contains_reference_mark(current_address_text):
            GuiUtils.delete_menu_entries(menu, [examine_referrers])
        bookmark = menu.addAction("Bookmark this address[Ctrl+B]")
        delete_bookmark = menu.addAction("Delete this bookmark")
        change_comment = menu.addAction("Change comment")
        is_bookmarked = current_address_int in self.tableWidget_Disassemble.bookmarks
        if not is_bookmarked:
            GuiUtils.delete_menu_entries(menu, [delete_bookmark, change_comment])
        else:
            GuiUtils.delete_menu_entries(menu, [bookmark])
        go_to_bookmark = menu.addMenu("Go to bookmarked address")
        bookmark_action_list = []
        nested_list = []
        for item in self.tableWidget_Disassemble.bookmarks.keys():
            item_str = hex(item)
            nested_list.append((item_str,))
        for index, item in enumerate(GDB_Engine.convert_multiple_addresses_to_symbols(nested_list)):
            if item is "":
                text_append = nested_list[index][0] + "(Unreachable)"
            else:
                text_append = item
            bookmark_action_list.append(go_to_bookmark.addAction(text_append))
        menu.addSeparator()
        toggle_breakpoint = menu.addAction("Toggle Breakpoint[F5]")
        add_condition = menu.addAction("Add/Change condition for breakpoint")
        if not GDB_Engine.check_address_in_breakpoints(current_address_int):
            GuiUtils.delete_menu_entries(menu, [add_condition])
        menu.addSeparator()
        track_breakpoint = menu.addAction("Find out which addresses this instruction accesses")
        trace_instructions = menu.addAction("Break and trace instructions[Ctrl+T]")
        dissect_region = menu.addAction("Dissect this region[Ctrl+D]")
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        clipboard_menu = menu.addMenu("Copy to Clipboard")
        copy_address = clipboard_menu.addAction("Copy Address")
        copy_bytes = clipboard_menu.addAction("Copy Bytes")
        copy_opcode = clipboard_menu.addAction("Copy Opcode")
        copy_comment = clipboard_menu.addAction("Copy Comment")
        copy_all = clipboard_menu.addAction("Copy All")
        font_size = self.tableWidget_Disassemble.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        if action in bookmark_action_list:
            self.disassemble_expression(SysUtils.extract_address(action.text()), append_to_travel_history=True)

    def dissect_current_region(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        dissect_code_dialog = DissectCodeDialogForm(int_address=int(current_address, 16))
        dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
        dissect_code_dialog.exec_()
        self.refresh_disassemble_view()

    def exec_examine_referrers_widget(self, current_address_text):
        if not GuiUtils.contains_reference_mark(current_address_text):
            return
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)
        examine_referrers_widget = ExamineReferrersWidgetForm(current_address_int, self)
        examine_referrers_widget.show()

    def exec_trace_instructions_dialog(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        trace_instructions_window = TraceInstructionsWindowForm(current_address, parent=self)
        trace_instructions_window.showMaximized()

    def exec_track_breakpoint_dialog(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_instruction = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        track_breakpoint_widget = TrackBreakpointWidgetForm(current_address, current_instruction, self)
        track_breakpoint_widget.show()

    def exec_disassemble_go_to_dialog(self):
        selected_row = GuiUtils.get_current_row(self.tableWidget_Disassemble)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        go_to_dialog = InputDialogForm(item_list=[("Enter the expression", current_address)])
        if go_to_dialog.exec_():
            traveled_exp = go_to_dialog.get_values()
            self.disassemble_expression(traveled_exp, append_to_travel_history=True)

    def bookmark_address(self, int_address):
        if int_address in self.tableWidget_Disassemble.bookmarks:
            QMessageBox.information(self, "Error", "This address has already been bookmarked")
            return
        comment_dialog = InputDialogForm(item_list=[("Enter the comment for bookmarked address", "")])
        if comment_dialog.exec_():
            comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = comment
        self.refresh_disassemble_view()

    def change_bookmark_comment(self, int_address):
        current_comment = self.tableWidget_Disassemble.bookmarks[int_address]
        comment_dialog = InputDialogForm(item_list=[("Enter the comment for bookmarked address", current_comment)])
        if comment_dialog.exec_():
            new_comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = new_comment
        self.refresh_disassemble_view()

    def delete_bookmark(self, int_address):
        if int_address in self.tableWidget_Disassemble.bookmarks:
            del self.tableWidget_Disassemble.bookmarks[int_address]
            self.refresh_disassemble_view()

    def actionBookmarks_triggered(self):
        bookmark_widget = BookmarkWidgetForm(self)
        bookmark_widget.show()
        bookmark_widget.activateWindow()

    def actionStackTrace_Info_triggered(self):
        self.stacktrace_info_widget = StackTraceInfoWidgetForm()
        self.stacktrace_info_widget.show()

    def actionBreakpoints_triggered(self):
        breakpoint_widget = BreakpointInfoWidgetForm(self)
        breakpoint_widget.show()
        breakpoint_widget.activateWindow()

    def actionFunctions_triggered(self):
        functions_info_widget = FunctionsInfoWidgetForm(self)
        functions_info_widget.show()

    def actionGDB_Log_File_triggered(self):
        log_file_widget = LogFileWidgetForm()
        log_file_widget.showMaximized()

    def actionMemory_Regions_triggered(self):
        memory_regions_widget = MemoryRegionsWidgetForm(self)
        memory_regions_widget.show()

    def actionReferenced_Strings_triggered(self):
        ref_str_widget = ReferencedStringsWidgetForm(self)
        ref_str_widget.show()

    def actionReferenced_Calls_triggered(self):
        ref_call_widget = ReferencedCallsWidgetForm(self)
        ref_call_widget.show()

    def actionInject_so_file_triggered(self):
        file_path = QFileDialog.getOpenFileName(self, "Select the .so file", "", "Shared object library (*.so)")[0]
        if file_path:
            if GDB_Engine.inject_with_dlopen_call(file_path):
                QMessageBox.information(self, "Success!", "The file has been injected")
            else:
                QMessageBox.information(self, "Error", "Failed to inject the .so file")

    def actionCall_Function_triggered(self):
        label_text = "Enter the expression for the function that'll be called from the inferior" \
                     "\nYou can view functions list from View->Functions" \
                     "\n\nFor instance:" \
                     '\nCalling printf("1234") will yield something like this' \
                     '\n↓' \
                     '\n$28 = 4' \
                     '\n\n$28 is the assigned convenience variable' \
                     '\n4 is the result' \
                     '\nYou can use the assigned variable from the GDB Console'
        call_dialog = InputDialogForm(item_list=[(label_text, "")])
        if call_dialog.exec_():
            result = GDB_Engine.call_function_from_inferior(call_dialog.get_values())
            if result[0]:
                QMessageBox.information(self, "Success!", result[0] + " = " + result[1])
            else:
                QMessageBox.information(self, "Failed", "Failed to call the expression " + call_dialog.get_values())

    def actionSearch_Opcode_triggered(self):
        start_address = int(self.disassemble_currently_displayed_address, 16)
        end_address = start_address + 0x30000
        search_opcode_widget = SearchOpcodeWidgetForm(hex(start_address), hex(end_address), self)
        search_opcode_widget.show()

    def actionDissect_Code_triggered(self):
        self.dissect_code_dialog = DissectCodeDialogForm()
        self.dissect_code_dialog.exec_()
        self.refresh_disassemble_view()

    def actionLibPINCE_triggered(self):
        libPINCE_widget = LibPINCEReferenceWidgetForm(is_window=True)
        libPINCE_widget.showMaximized()

    def pushButton_ShowFloatRegisters_clicked(self):
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
        self.setWindowFlags(Qt.Window)
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
        nested_list = []
        for item in self.parent().tableWidget_Disassemble.bookmarks.keys():
            item_str = hex(item)
            nested_list.append((item_str,))
        for index, item in enumerate(GDB_Engine.convert_multiple_addresses_to_symbols(nested_list)):
            if item is "":
                text_append = nested_list[index][0] + "(Unreachable)"
            else:
                text_append = item
            self.listWidget.addItem(text_append)

    def change_display(self):
        try:
            current_item = self.listWidget.currentItem().text()
        except AttributeError:
            return
        current_address = SysUtils.extract_address(current_item)
        self.lineEdit_Info.setText(GDB_Engine.get_address_info(current_address))
        self.lineEdit_Comment.setText(self.parent().tableWidget_Disassemble.bookmarks[int(current_address, 16)])

    def listWidget_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def exec_add_entry_dialog(self):
        entry_dialog = InputDialogForm(item_list=[("Enter the expression", "")])
        if entry_dialog.exec_():
            text = entry_dialog.get_values()
            address = GDB_Engine.convert_symbol_to_address(text)
            if address is "":
                QMessageBox.information(self, "Error", "Invalid expression or address")
                return
            self.parent().bookmark_address(int(address, 16))
            self.refresh_table()

    def exec_change_comment_dialog(self, current_address):
        self.parent().change_bookmark_comment(current_address)
        self.refresh_table()

    def listWidget_context_menu_event(self, event):
        if GuiUtils.get_current_row(self.listWidget) != -1:
            current_item = self.listWidget.currentItem().text()
            current_address = int(SysUtils.extract_address(current_item), 16)
        else:
            current_item = current_address = None
        if current_item is not None:
            if current_address not in self.parent().tableWidget_Disassemble.bookmarks:
                QMessageBox.information(self, "Error", "Invalid entries detected, refreshing the page")
                self.refresh_table()
                return
        menu = QMenu()
        add_entry = menu.addAction("Add new entry")
        change_comment = menu.addAction("Change comment of this record")
        delete_record = menu.addAction("Delete this record[Del]")
        if current_item is None:
            GuiUtils.delete_menu_entries(menu, [change_comment, delete_record])
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        font_size = self.listWidget.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        current_item = self.listWidget.currentItem().text()
        current_address = int(SysUtils.extract_address(current_item), 16)
        self.parent().delete_bookmark(current_address)
        self.refresh_table()

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class FloatRegisterWidgetForm(QTabWidget, FloatRegisterWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Window)
        self.update_registers()
        self.tableWidget_FPU.itemDoubleClicked.connect(self.set_register)
        self.tableWidget_XMM.itemDoubleClicked.connect(self.set_register)

    def update_registers(self):
        self.tableWidget_FPU.setRowCount(0)
        self.tableWidget_FPU.setRowCount(8)
        self.tableWidget_XMM.setRowCount(0)
        self.tableWidget_XMM.setRowCount(8)
        float_registers = GDB_Engine.read_float_registers()

        # st0-7, xmm0-7
        for row, index in enumerate(range(8)):
            current_st_register = "st" + str(index)
            current_xmm_register = "xmm" + str(index)
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(current_st_register))
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_VALUE_COL,
                                         QTableWidgetItem(float_registers[current_st_register]))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(current_xmm_register))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_VALUE_COL,
                                         QTableWidgetItem(float_registers[current_xmm_register]))

    def set_register(self, index):
        current_row = index.row()
        if self.currentWidget() == self.FPU:
            current_table_widget = self.tableWidget_FPU
        elif self.currentWidget() == self.XMM:
            current_table_widget = self.tableWidget_XMM
        current_register = current_table_widget.item(current_row, FLOAT_REGISTERS_NAME_COL).text()
        current_value = current_table_widget.item(current_row, FLOAT_REGISTERS_VALUE_COL).text()
        label_text = "Enter the new value of register " + current_register.upper()
        register_dialog = InputDialogForm(item_list=[(label_text, current_value)])
        if register_dialog.exec_():
            if self.currentWidget() == self.XMM:
                current_register += ".v4_float"
            GDB_Engine.set_convenience_variable(current_register, register_dialog.get_values())
            self.update_registers()


class StackTraceInfoWidgetForm(QWidget, StackTraceInfoWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.Window)
        self.listWidget_ReturnAddresses.currentRowChanged.connect(self.update_frame_info)
        self.update_stacktrace()

    def update_stacktrace(self):
        self.listWidget_ReturnAddresses.clear()
        return_addresses = GDB_Engine.get_stack_frame_return_addresses()
        self.listWidget_ReturnAddresses.addItems(return_addresses)

    def update_frame_info(self, index):
        frame_info = GDB_Engine.get_stack_frame_info(index)
        self.textBrowser_Info.setText(frame_info)


class BreakpointInfoWidgetForm(QTabWidget, BreakpointInfoWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.Window)
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
        self.tableWidget_BreakpointInfo.resizeColumnsToContents()
        self.tableWidget_BreakpointInfo.horizontalHeader().setStretchLastSection(True)
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
            ((Qt.NoModifier, Qt.Key_Delete), lambda: self.delete_breakpoint(current_address)),
            ((Qt.NoModifier, Qt.Key_R), self.refresh)
        ])
        try:
            actions[event.modifiers(), event.key()]()
        except KeyError:
            self.tableWidget_BreakpointInfo.keyPressEvent_original(event)

    def exec_enable_count_dialog(self, current_address):
        hit_count_dialog = InputDialogForm(item_list=[("Enter the hit count(1 or higher)", "")])
        if hit_count_dialog.exec_():
            count = hit_count_dialog.get_values()
            try:
                count = int(count)
            except ValueError:
                QMessageBox.information(self, "Error", "Hit count must be an integer")
            else:
                if count < 1:
                    QMessageBox.information(self, "Error", "Hit count can't be lower than 1")
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
        change_condition = menu.addAction("Change condition of this breakpoint")
        enable = menu.addAction("Enable this breakpoint")
        disable = menu.addAction("Disable this breakpoint")
        enable_once = menu.addAction("Disable this breakpoint after hit")
        enable_count = menu.addAction("Disable this breakpoint after X hits")
        enable_delete = menu.addAction("Delete this breakpoint after hit")
        menu.addSeparator()
        delete_breakpoint = menu.addAction("Delete this breakpoint[Del]")
        menu.addSeparator()
        if current_address is None:
            deletion_list = [change_condition, enable, disable, enable_once, enable_count, enable_delete,
                             delete_breakpoint]
            GuiUtils.delete_menu_entries(menu, deletion_list)
        refresh = menu.addAction("Refresh[R]")
        font_size = self.tableWidget_BreakpointInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        self.setWindowFlags(Qt.Window)
        if watchpoint_type == type_defs.WATCHPOINT_TYPE.WRITE_ONLY:
            string = "writing to"
        elif watchpoint_type == type_defs.WATCHPOINT_TYPE.READ_ONLY:
            string = "reading from"
        elif watchpoint_type == type_defs.WATCHPOINT_TYPE.BOTH:
            string = "accessing to"
        self.setWindowTitle("Opcodes " + string + " the address " + address)
        breakpoints = GDB_Engine.track_watchpoint(address, length, watchpoint_type)
        if not breakpoints:
            QMessageBox.information(self, "Error", "Unable to track watchpoint at expression " + address)
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
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_list)
        self.update_timer.start()

    def update_list(self):
        info = GDB_Engine.get_track_watchpoint_info(self.breakpoints)
        if not info:
            return
        if self.info == info:
            return
        self.info = info
        self.tableWidget_Opcodes.setRowCount(0)
        self.tableWidget_Opcodes.setRowCount(len(info))
        for row, key in enumerate(info):
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_COUNT_COL, QTableWidgetItem(str(info[key][0])))
            self.tableWidget_Opcodes.setItem(row, TRACK_WATCHPOINT_ADDR_COL, QTableWidgetItem(info[key][1]))
        self.tableWidget_Opcodes.resizeColumnsToContents()
        self.tableWidget_Opcodes.horizontalHeader().setStretchLastSection(True)
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
        for row, index in enumerate(range(8)):
            current_st_register = "st" + str(index)
            string = current_st_register + "=" + info[key][3][current_st_register]
            self.textBrowser_Info.append(string)
        self.textBrowser_Info.append(" ")
        for row, index in enumerate(range(8)):
            current_xmm_register = "xmm" + str(index)
            string = current_xmm_register + "=" + info[key][3][current_xmm_register]
            self.textBrowser_Info.append(string)
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
        if not GDB_Engine.delete_breakpoint(self.address):
            QMessageBox.information(self, "Error", "Unable to delete watchpoint at expression " + self.address)
            return
        self.stopped = True
        self.pushButton_Stop.setText("Close")

    def closeEvent(self, QCloseEvent):
        if GDB_Engine.inferior_status is type_defs.INFERIOR_STATUS.INFERIOR_RUNNING:
            QCloseEvent.ignore()
            raise type_defs.InferiorRunningException
        try:
            self.update_timer.stop()
        except AttributeError:
            pass
        global instances
        instances.remove(self)
        GDB_Engine.execute_with_temporary_interruption(GDB_Engine.delete_breakpoint, self.address)


class TrackBreakpointWidgetForm(QWidget, TrackBreakpointWidget):
    def __init__(self, address, instruction, parent=None):
        super().__init__()
        self.setupUi(self)
        self.parent = lambda: parent
        global instances
        instances.append(self)
        self.setWindowFlags(Qt.Window)
        GuiUtils.center_to_parent(self)
        self.setWindowTitle("Addresses accessed by instruction '" + instruction + "'")
        label_text = "Enter the register expression(s) you want to track" \
                     "\nRegister names should start with a '$' sign" \
                     "\nEach expression should be separated with a comma" \
                     "\n\nFor instance:" \
                     "\nLet's say the instruction is 'mov [rax+rbx],30'" \
                     "\nThen you should enter '$rax+$rbx'(without quotes)" \
                     "\nSo PINCE can track address [rax+rbx]" \
                     "\n\nAnother example:" \
                     "\nIf you enter '$rax,$rbx*$rcx+4,$rbp'(without quotes)" \
                     "\nPINCE will track down addresses [rax],[rbx*rcx+4] and [rbp]"
        register_expression_dialog = InputDialogForm(item_list=[(label_text, "")])
        if register_expression_dialog.exec_():
            register_expressions = register_expression_dialog.get_values()
        else:
            return
        breakpoint = GDB_Engine.track_breakpoint(address, register_expressions)
        if not breakpoint:
            QMessageBox.information(self, "Error", "Unable to track breakpoint at expression " + address)
            return
        self.label_Info.setText("Pause the process to refresh 'Value' part of the table(" +
                                global_hotkeys["pause_hotkey"] + " or " + global_hotkeys["break_hotkey"] + ")")
        self.address = address
        self.breakpoint = breakpoint
        self.info = {}
        self.last_selected_row = 0
        self.stopped = False
        GuiUtils.fill_value_combobox(self.comboBox_ValueType)
        self.comboBox_ValueType.enterEvent = self.comboBox_ValueType_enter_event
        self.combobox_change_count = 0
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.tableWidget_TrackInfo.itemDoubleClicked.connect(self.tableWidget_TrackInfo_item_double_clicked)
        self.tableWidget_TrackInfo.selectionModel().currentChanged.connect(self.tableWidget_TrackInfo_current_changed)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
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
        self.tableWidget_TrackInfo.resizeColumnsToContents()
        self.tableWidget_TrackInfo.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def update_values(self):
        param_list = []
        value_type = self.comboBox_ValueType.currentIndex()
        for row in range(self.tableWidget_TrackInfo.rowCount()):
            address = self.tableWidget_TrackInfo.item(row, TRACK_BREAKPOINT_ADDR_COL).text()
            param_list.append((address, value_type, 10))
        value_list = GDB_Engine.read_multiple_addresses(param_list)
        for row, value in enumerate(value_list):
            self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_VALUE_COL, QTableWidgetItem(str(value)))
        self.tableWidget_TrackInfo.resizeColumnsToContents()
        self.tableWidget_TrackInfo.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def tableWidget_TrackInfo_current_changed(self, QModelIndex_current):
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

    def tableWidget_TrackInfo_item_double_clicked(self, index):
        address = self.tableWidget_TrackInfo.item(index.row(), TRACK_BREAKPOINT_ADDR_COL).text()
        self.parent().parent().add_entry_to_addresstable("Changed by address " + self.address, address,
                                                         self.comboBox_ValueType.currentIndex(),
                                                         10, True, True)

    def pushButton_Stop_clicked(self):
        if self.stopped:
            self.close()
        if not GDB_Engine.delete_breakpoint(self.address):
            QMessageBox.information(self, "Error", "Unable to delete breakpoint at expression " + self.address)
            return
        self.stopped = True
        self.pushButton_Stop.setText("Close")
        self.parent().refresh_disassemble_view()

    def comboBox_ValueType_current_index_changed(self):
        self.combobox_change_count += 1
        self.update_values()

    def comboBox_ValueType_enter_event(self, event):
        if self.combobox_change_count == 0:
            QToolTip.showText(event.globalPos(), "Change me fam, you won't regret it")
        elif self.combobox_change_count == 1:
            QToolTip.showText(event.globalPos(), "Yeah, just like that...")
        elif self.combobox_change_count == 2:
            QToolTip.showText(event.globalPos(), "You like it, don't you?")
        elif self.combobox_change_count == 3:
            QToolTip.showText(event.globalPos(), "Switch me harder!")
        elif self.combobox_change_count == 4:
            QToolTip.showText(event.globalPos(), "Make me reach indexes no combobox has been reached before!")
        elif self.combobox_change_count > 4:
            try:
                self.reach_the_stars()
            except IndexError:
                QToolTip.showText(event.globalPos(), str(traceback.format_exc()))

    def reach_the_stars(self):
        a = [1, 2, 3]
        a[42] = 0

    def closeEvent(self, QCloseEvent):
        if GDB_Engine.inferior_status is type_defs.INFERIOR_STATUS.INFERIOR_RUNNING:
            QCloseEvent.ignore()
            raise type_defs.InferiorRunningException
        try:
            self.update_timer.stop()
        except AttributeError:
            pass
        global instances
        instances.remove(self)
        GDB_Engine.execute_with_temporary_interruption(GDB_Engine.delete_breakpoint, self.address)
        self.parent().refresh_disassemble_view()


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
        return max_trace_count, trigger_condition, stop_condition, step_mode, stop_after_trace, \
               collect_general_registers, collect_flag_registers, collect_segment_registers, collect_float_registers

    def accept(self):
        if int(self.lineEdit_MaxTraceCount.text()) >= 1:
            super(TraceInstructionsPromptDialogForm, self).accept()
        else:
            QMessageBox.information(self, "Error", "Max trace count must be greater than or equal to 1")


class TraceInstructionsWaitWidgetForm(QWidget, TraceInstructionsWaitWidget):
    widget_closed = pyqtSignal()

    def __init__(self, address, breakpoint, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.Window | Qt.FramelessWindowHint)
        GuiUtils.center(self)
        self.address = address
        self.breakpoint = breakpoint
        pince_directory = SysUtils.get_current_script_directory()
        self.movie = QMovie(pince_directory + "/media/TraceInstructionsWaitWidget/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(215, 100))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.movie.setCacheMode(QMovie.CacheAll)
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
        self.label_StatusText.setText(status_info[1])
        QApplication.processEvents()

    def closeEvent(self, QCloseEvent):
        self.status_timer.stop()
        self.label_StatusText.setText("Processing the collected data")
        self.pushButton_Cancel.setVisible(False)
        self.adjustSize()
        QApplication.processEvents()
        status_info = GDB_Engine.get_trace_instructions_status(self.breakpoint)
        if status_info[0] == type_defs.TRACE_STATUS.STATUS_TRACING or \
                status_info[0] == type_defs.TRACE_STATUS.STATUS_PROCESSING:
            GDB_Engine.cancel_trace_instructions(self.breakpoint)
            while GDB_Engine.get_trace_instructions_status(self.breakpoint)[0] \
                    != type_defs.TRACE_STATUS.STATUS_FINISHED:
                sleep(0.1)
                QApplication.processEvents()
        try:
            GDB_Engine.delete_breakpoint(self.address)
        except type_defs.InferiorRunningException:
            pass
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
        if prompt_dialog.exec_():
            params = (address,) + prompt_dialog.get_values()
            breakpoint = GDB_Engine.trace_instructions(*params)
            if not breakpoint:
                QMessageBox.information(self, "Error", "Failed to set breakpoint at address " + address)
                return
            self.breakpoint = breakpoint
            self.wait_dialog = TraceInstructionsWaitWidgetForm(address, breakpoint, self)
            self.wait_dialog.widget_closed.connect(self.show_trace_info)
            self.wait_dialog.show()

    def display_collected_data(self):
        self.textBrowser_RegisterInfo.clear()
        try:
            current_dict = self.treeWidget_InstructionInfo.currentItem().trace_data[1]
        except:
            return
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
        while current_root_index != None:
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
        file_path = \
            QFileDialog.getSaveFileName(self, "Save trace file", trace_file_path,
                                        "Trace File (*.trace);;All Files (*)")[0]
        if file_path:
            if not SysUtils.save_file(self.trace_data, file_path + ".trace"):
                QMessageBox.information(self, "Error", "Couldn't save the file, check terminal for details")

    def load_file(self):
        trace_file_path = SysUtils.get_user_path(type_defs.USER_PATHS.TRACE_INSTRUCTIONS_PATH)
        file_path = \
            QFileDialog.getOpenFileName(self, "Open trace file", trace_file_path,
                                        "Trace File (*.trace);;All Files (*)")[0]
        if file_path:
            self.treeWidget_InstructionInfo.clear()
            trace_data = SysUtils.load_file(file_path, return_on_fail=[])
            self.show_trace_info(trace_data)

    def treeWidget_InstructionInfo_context_menu_event(self, event):
        menu = QMenu()
        expand_all = menu.addAction("Expand All")
        collapse_all = menu.addAction("Collapse All")
        font_size = self.treeWidget_InstructionInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            expand_all: self.treeWidget_InstructionInfo.expandAll,
            collapse_all: self.treeWidget_InstructionInfo.collapseAll
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_InstructionInfo_item_double_clicked(self, index):
        try:
            address = SysUtils.extract_address(self.treeWidget_InstructionInfo.currentItem().trace_data[0])
        except:
            return
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
        self.setWindowFlags(Qt.Window)
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
        ignore_case = self.checkBox_IgnoreCase.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(gdb_input=input_text, ignore_case=ignore_case)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec_()

    def process_data(self, gdb_input, ignore_case):
        return GDB_Engine.search_functions(gdb_input, ignore_case)

    def apply_data(self, output):
        self.tableWidget_SymbolInfo.setSortingEnabled(False)
        self.tableWidget_SymbolInfo.setRowCount(0)
        self.tableWidget_SymbolInfo.setRowCount(len(output))
        for row, item in enumerate(output):
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_SYMBOL_COL, QTableWidgetItem(item[1]))
        self.tableWidget_SymbolInfo.resizeColumnsToContents()
        self.tableWidget_SymbolInfo.horizontalHeader().setStretchLastSection(True)
        self.tableWidget_SymbolInfo.setSortingEnabled(True)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current):
        symbol = self.tableWidget_SymbolInfo.item(QModelIndex_current.row(), FUNCTIONS_INFO_SYMBOL_COL).text()
        self.textBrowser_AddressInfo.clear()
        for item in SysUtils.split_symbol(symbol):
            info = GDB_Engine.get_symbol_info(item)
            self.textBrowser_AddressInfo.append(info)

    def tableWidget_SymbolInfo_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_SymbolInfo.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_SymbolInfo)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        copy_symbol = menu.addAction("Copy Symbol")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_symbol])
        font_size = self.tableWidget_SymbolInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        self.parent().disassemble_expression(address, append_to_travel_history=True)

    def pushButton_Help_clicked(self):
        text = "\tHere's some useful regex tips:" \
               "\n'^string' searches for everything that starts with 'string'" \
               "\n'[ab]cd' searches for both 'acd' and 'bcd'" \
               "\n\n\tHow to interpret symbols:" \
               "\nA symbol that looks like 'func(param)@plt' consists of 3 pieces" \
               "\nfunc, func(param), func(param)@plt" \
               "\nThese 3 functions will have different addresses" \
               "\n@plt means this function is a subroutine for the original one" \
               "\nThere can be more than one of the same function" \
               "\nIt means that the function is overloaded"
        InputDialogForm(item_list=[(text, None, Qt.AlignLeft)], buttons=[QDialogButtonBox.Ok]).exec_()

    def closeEvent(self, QCloseEvent):
        global instances
        instances.remove(self)


class HexEditDialogForm(QDialog, HexEditDialog):
    def __init__(self, address, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
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
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: red;}")
            return
        aob_array = aob_string.split()
        try:
            self.lineEdit_AsciiView.setText(SysUtils.aob_to_str(aob_array, "utf-8"))
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: white;}")
        except ValueError:
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: red;}")

    def lineEdit_AsciiView_text_edited(self):
        ascii_str = self.lineEdit_AsciiView.text()
        try:
            self.lineEdit_HexView.setText(SysUtils.str_to_aob(ascii_str, "utf-8"))
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: white;}")
        except ValueError:
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: red;}")

    def refresh_view(self):
        address = self.lineEdit_Address.text()
        length = self.lineEdit_Length.text()
        aob_array = GDB_Engine.hex_dump(address, length)
        ascii_str = SysUtils.aob_to_str(aob_array, "utf-8")
        self.lineEdit_AsciiView.setText(ascii_str)
        self.lineEdit_HexView.setText(" ".join(aob_array))

    def accept(self):
        address = self.lineEdit_Address.text()
        value = self.lineEdit_HexView.text()
        GDB_Engine.set_single_address(address, type_defs.VALUE_INDEX.INDEX_AOB, value)
        super(HexEditDialogForm, self).accept()


class LibPINCEReferenceWidgetForm(QWidget, LibPINCEReferenceWidget):
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
            self.setWindowFlags(Qt.Window)
        self.show_type_defs()
        self.splitter.setStretchFactor(0, 1)
        self.widget_Resources.resize(700, self.widget_Resources.height())
        libPINCE_directory = SysUtils.get_libpince_directory()
        self.textBrowser_TypeDefs.setText(open(libPINCE_directory + "/type_defs.py").read())
        source_menu_items = ["(Tagged only)", "(All)"]
        self.libPINCE_source_files = ["GDB_Engine", "SysUtils", "GuiUtils"]
        source_menu_items.extend(self.libPINCE_source_files)
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
            QApplication.clipboard().setText(self.tableWidget_ResourceTable.item(row, column).text())

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
        action = menu.exec_(event.globalPos())
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
            QApplication.clipboard().setText(self.treeWidget_ResourceTree.currentItem().text(column))

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
        action = menu.exec_(event.globalPos())
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
        checked_source_files = self.convert_to_modules(self.libPINCE_source_files)
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
            checked_source_files = self.libPINCE_source_files
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
        self.tableWidget_ResourceTable.sortByColumn(LIBPINCE_REFERENCE_ITEM_COL, Qt.AscendingOrder)
        self.tableWidget_ResourceTable.resizeColumnsToContents()
        self.tableWidget_ResourceTable.horizontalHeader().setStretchLastSection(True)

    def pushButton_TextDown_clicked(self):
        if self.found_count == 0:
            return
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.Start)
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
        cursor.movePosition(QTextCursor.Start)
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
        self.textBrowser_TypeDefs.selectAll()
        self.textBrowser_TypeDefs.setTextBackgroundColor(QColor("white"))
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QBrush(QColor("red")))
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
            return
        cursor = self.textBrowser_TypeDefs.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.Start)
        self.textBrowser_TypeDefs.setTextCursor(cursor)
        self.textBrowser_TypeDefs.find(pattern)
        self.current_found = 1
        self.label_FoundCount.setText("1/" + str(found_count))

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
        self.setWindowFlags(Qt.Window)
        self.log_path = SysUtils.get_gdb_log_file(GDB_Engine.currentpid)
        self.setWindowTitle("Log File of PID " + str(GDB_Engine.currentpid))
        self.label_FilePath.setText("Contents of " + self.log_path + " (only last 20000 bytes are shown)")
        self.contents = ""
        self.refresh_contents()
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_contents)
        self.refresh_timer.start()

    def refresh_contents(self):
        log_file = open(self.log_path)
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
            cursor.movePosition(QTextCursor.End)
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
        self.setWindowFlags(Qt.Window)
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
        ignore_case = self.checkBox_IgnoreCase.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(regex=regex, start_address=start_address,
                                                                          end_address=end_address,
                                                                          ignore_case=ignore_case,
                                                                          enable_regex=enable_regex)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec_()

    def process_data(self, regex, start_address, end_address, ignore_case, enable_regex):
        return GDB_Engine.search_opcode(regex, start_address, end_address, ignore_case, enable_regex)

    def apply_data(self, disas_data):
        if disas_data is None:
            QMessageBox.information(self, "Error", "Given regex isn't valid, check terminal to see the error")
            return
        self.tableWidget_Opcodes.setSortingEnabled(False)
        self.tableWidget_Opcodes.setRowCount(0)
        self.tableWidget_Opcodes.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            self.tableWidget_Opcodes.setItem(row, SEARCH_OPCODE_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Opcodes.setItem(row, SEARCH_OPCODE_OPCODES_COL, QTableWidgetItem(item[1]))
        self.tableWidget_Opcodes.setSortingEnabled(True)

    def pushButton_Help_clicked(self):
        text = "\tHere's some useful regex examples:" \
               "\n'call|rax' searches for opcodes that contain 'call' or 'rax'" \
               "\n'[re]cx' searches for both 'rcx' and 'ecx'" \
               "\nUse the char '\\' to escape special chars such as '['" \
               "\n'\[rsp\]' searches for opcodes that contain '[rsp]'"
        InputDialogForm(item_list=[(text, None, Qt.AlignLeft)], buttons=[QDialogButtonBox.Ok]).exec_()

    def tableWidget_Opcodes_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_Opcodes.item(row, SEARCH_OPCODE_ADDR_COL).text()
        self.parent().disassemble_expression(SysUtils.extract_address(address), append_to_travel_history=True)

    def tableWidget_Opcodes_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_Opcodes.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_Opcodes)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        copy_opcode = menu.addAction("Copy Opcode")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_opcode])
        font_size = self.tableWidget_Opcodes.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        self.setWindowFlags(Qt.Window)
        self.refresh_table()
        self.tableWidget_MemoryRegions.contextMenuEvent = self.tableWidget_MemoryRegions_context_menu_event
        self.tableWidget_MemoryRegions.itemDoubleClicked.connect(self.tableWidget_MemoryRegions_item_double_clicked)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)

    def refresh_table(self):
        memory_regions = SysUtils.get_memory_regions(GDB_Engine.currentpid)
        self.tableWidget_MemoryRegions.setRowCount(0)
        self.tableWidget_MemoryRegions.setRowCount(len(memory_regions))
        for row, region in enumerate(memory_regions):
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_ADDR_COL, QTableWidgetItem(region.addr))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PERM_COL, QTableWidgetItem(region.perms))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_SIZE_COL, QTableWidgetItem(hex(region.size)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PATH_COL, QTableWidgetItem(region.path))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_RSS_COL, QTableWidgetItem(hex(region.rss)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PSS_COL, QTableWidgetItem(hex(region.pss)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_SHRCLN_COL,
                                                   QTableWidgetItem(hex(region.shared_clean)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_SHRDRTY_COL,
                                                   QTableWidgetItem(hex(region.shared_dirty)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PRIVCLN_COL,
                                                   QTableWidgetItem(hex(region.private_clean)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PRIVDRTY_COL,
                                                   QTableWidgetItem(hex(region.private_dirty)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_REF_COL,
                                                   QTableWidgetItem(hex(region.referenced)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_ANON_COL,
                                                   QTableWidgetItem(hex(region.anonymous)))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_SWAP_COL, QTableWidgetItem(hex(region.swap)))
        self.tableWidget_MemoryRegions.resizeColumnsToContents()
        self.tableWidget_MemoryRegions.horizontalHeader().setStretchLastSection(True)

    def tableWidget_MemoryRegions_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_MemoryRegions.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_MemoryRegions)

        menu = QMenu()
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        copy_addresses = menu.addAction("Copy Addresses")
        copy_size = menu.addAction("Copy Size")
        copy_path = menu.addAction("Copy Path")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_addresses, copy_size, copy_path])
        font_size = self.tableWidget_MemoryRegions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            refresh: self.refresh_table,
            copy_addresses: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_ADDR_COL),
            copy_size: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_SIZE_COL),
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
        self.checkBox_IncludeSystemRegions.stateChanged.connect(self.show_memory_regions)
        self.pushButton_StartCancel.clicked.connect(self.pushButton_StartCancel_clicked)
        self.refresh_timer = QTimer()
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(self.refresh_dissect_status)
        if int_address != -1:
            self.checkBox_IncludeSystemRegions.setChecked(True)
            self.show_memory_regions()
            for row in range(self.tableWidget_ExecutableMemoryRegions.rowCount()):
                item = self.tableWidget_ExecutableMemoryRegions.item(row, DISSECT_CODE_ADDR_COL).text()
                start_addr, end_addr = item.split("-")
                if int(start_addr, 16) <= int_address <= int(end_addr, 16):
                    self.tableWidget_ExecutableMemoryRegions.clearSelection()
                    self.tableWidget_ExecutableMemoryRegions.selectRow(row)
                    self.pushButton_StartCancel_clicked()
                    break
            else:
                QMessageBox.information(self, "Error", hex(int_address) + " isn't in a valid region range")

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
        self.pushButton_StartCancel.setText("Start")

    def init_after_scan_gui(self):
        self.is_scanning = True
        self.label_ScanInfo.setText("Currently scanning region:")
        self.pushButton_StartCancel.setText("Cancel")

    def refresh_dissect_status(self):
        current_region, region_count, current_range, \
        string_count, jump_count, call_count = GDB_Engine.get_dissect_code_status()
        if not current_region:
            return
        self.label_RegionInfo.setText(current_region)
        self.label_RegionCountInfo.setText(region_count)
        self.label_CurrentRange.setText(current_range)
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
        executable_regions = SysUtils.get_memory_regions_by_perms(GDB_Engine.currentpid)[2]
        if not self.checkBox_IncludeSystemRegions.isChecked():
            executable_regions = SysUtils.exclude_system_memory_regions(executable_regions)
        self.region_list = executable_regions
        self.tableWidget_ExecutableMemoryRegions.setRowCount(0)
        self.tableWidget_ExecutableMemoryRegions.setRowCount(len(executable_regions))
        for row, region in enumerate(executable_regions):
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_ADDR_COL, QTableWidgetItem(region.addr))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_PATH_COL, QTableWidgetItem(region.path))
        self.tableWidget_ExecutableMemoryRegions.resizeColumnsToContents()
        self.tableWidget_ExecutableMemoryRegions.horizontalHeader().setStretchLastSection(True)

    def scan_finished(self):
        self.init_pre_scan_gui()
        if not self.is_canceled:
            self.label_ScanInfo.setText("Scan finished")
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
            self.label_ScanInfo.setText("Scan was canceled")
            self.init_pre_scan_gui()
        else:
            if not GDB_Engine.inferior_status is type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
                QMessageBox.information(self, "Error", "Please stop the process first")
                return
            selected_rows = self.tableWidget_ExecutableMemoryRegions.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, "Error", "Select at least one region")
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
        self.setWindowFlags(Qt.Window)
        self.tableWidget_References.setColumnWidth(REF_STR_ADDR_COL, 150)
        self.tableWidget_References.setColumnWidth(REF_STR_COUNT_COL, 80)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = GDB_Engine.get_dissect_code_data()
        if len(str_dict) == 0 and len(jmp_dict) == 0 and len(call_dict) == 0:
            confirm_dialog = InputDialogForm(item_list=[("You need to dissect code first\nProceed?",)])
            if confirm_dialog.exec_():
                dissect_code_dialog = DissectCodeDialogForm()
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec_()
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_STR_ADDR_COL, Qt.AscendingOrder)
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
                                                         self.checkBox_IgnoreCase.isChecked(),
                                                         self.checkBox_Regex.isChecked())
        if item_list is None:
            QMessageBox.information(self, "Error",
                                    "An exception occurred while trying to compile the given regex\n")
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_STR_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_STR_COUNT_COL, table_widget_item)
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.EditRole, item[2])
            self.tableWidget_References.setItem(row, REF_STR_VAL_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        str_dict = GDB_Engine.get_dissect_code_data(True, False, False)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_STR_ADDR_COL).text()
        referrers = str_dict[hex(int(addr, 16))]
        nested_list = []
        for item in referrers:
            nested_list.append((hex(item),))
        for item in GDB_Engine.convert_multiple_addresses_to_symbols(nested_list):
            self.listWidget_Referrers.addItem(self.pad_hex(item))
        self.listWidget_Referrers.sortItems(Qt.AscendingOrder)
        str_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_STR_ADDR_COL).text()
        self.parent().hex_dump_address(int(address, 16))

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        copy_value = menu.addAction("Copy Value")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address, copy_value])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
            QApplication.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        self.setWindowFlags(Qt.Window)
        self.tableWidget_References.setColumnWidth(REF_CALL_ADDR_COL, 480)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = GDB_Engine.get_dissect_code_data()
        if len(str_dict) == 0 and len(jmp_dict) == 0 and len(call_dict) == 0:
            confirm_dialog = InputDialogForm(item_list=[("You need to dissect code first\nProceed?",)])
            if confirm_dialog.exec_():
                dissect_code_dialog = DissectCodeDialogForm()
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec_()
        str_dict.close()
        jmp_dict.close()
        call_dict.close()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_CALL_ADDR_COL, Qt.AscendingOrder)
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
                                                       self.checkBox_IgnoreCase.isChecked(),
                                                       self.checkBox_Regex.isChecked())
        if item_list is None:
            QMessageBox.information(self, "Error",
                                    "An exception occurred while trying to compile the given regex\n")
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_CALL_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_CALL_COUNT_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        call_dict = GDB_Engine.get_dissect_code_data(False, False, True)[0]
        addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_CALL_ADDR_COL).text()
        referrers = call_dict[hex(int(SysUtils.extract_address(addr), 16))]
        nested_list = []
        for item in referrers:
            nested_list.append((hex(item),))
        for item in GDB_Engine.convert_multiple_addresses_to_symbols(nested_list):
            self.listWidget_Referrers.addItem(self.pad_hex(item))
        self.listWidget_Referrers.sortItems(Qt.AscendingOrder)
        call_dict.close()

    def tableWidget_References_item_double_clicked(self, index):
        row = index.row()
        address = self.tableWidget_References.item(row, REF_CALL_ADDR_COL).text()
        self.parent().disassemble_expression(SysUtils.extract_address(address), append_to_travel_history=True)

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def tableWidget_References_context_menu_event(self, event):
        def copy_to_clipboard(row, column):
            QApplication.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = GuiUtils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, REF_CALL_ADDR_COL)
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            QApplication.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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
        self.setWindowFlags(Qt.Window)
        self.splitter.setStretchFactor(0, 1)
        self.textBrowser_DisasInfo.resize(600, self.textBrowser_DisasInfo.height())
        self.referenced_hex = hex(int_address)
        self.hex_len = 16 if GDB_Engine.inferior_arch == type_defs.INFERIOR_ARCH.ARCH_64 else 8
        self.collect_referrer_data()
        self.refresh_table()
        self.listWidget_Referrers.sortItems(Qt.AscendingOrder)
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
            jmp_referrers = [(hex(item),) for item in jmp_referrers]
            self.referrer_data.extend(
                [item for item in GDB_Engine.convert_multiple_addresses_to_symbols(jmp_referrers)])
        try:
            call_referrers = call_dict[self.referenced_hex]
        except KeyError:
            pass
        else:
            call_referrers = [(hex(item),) for item in call_referrers]
            self.referrer_data.extend(
                [item for item in GDB_Engine.convert_multiple_addresses_to_symbols(call_referrers)])
        jmp_dict.close()
        call_dict.close()

    def refresh_table(self):
        searched_str = self.lineEdit_Regex.text()
        ignore_case = self.checkBox_IgnoreCase.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        if enable_regex:
            try:
                if ignore_case:
                    regex = re.compile(searched_str, re.IGNORECASE)
                else:
                    regex = re.compile(searched_str)
            except:
                QMessageBox.information(self, "Error",
                                        "An exception occurred while trying to compile the given regex\n")
                return
        self.listWidget_Referrers.setSortingEnabled(False)
        self.listWidget_Referrers.clear()
        for row, item in enumerate(self.referrer_data):
            if enable_regex:
                if not regex.search(item):
                    continue
            else:
                if ignore_case:
                    if item.lower().find(searched_str.lower()) == -1:
                        continue
                else:
                    if item.find(searched_str) == -1:
                        continue
            self.listWidget_Referrers.addItem(item)
        self.listWidget_Referrers.setSortingEnabled(True)
        self.listWidget_Referrers.sortItems(Qt.AscendingOrder)

    def listWidget_Referrers_current_changed(self, QModelIndex_current):
        if QModelIndex_current.row() < 0:
            return
        self.textBrowser_DisasInfo.clear()
        disas_data = GDB_Engine.disassemble(
            SysUtils.extract_address(self.listWidget_Referrers.item(QModelIndex_current.row()).text()), "+200")
        for item in disas_data:
            self.textBrowser_DisasInfo.append(item[0] + item[2])
        cursor = self.textBrowser_DisasInfo.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.textBrowser_DisasInfo.setTextCursor(cursor)
        self.textBrowser_DisasInfo.ensureCursorVisible()

    def listWidget_Referrers_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def listWidget_Referrers_context_menu_event(self, event):
        def copy_to_clipboard(row):
            QApplication.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = GuiUtils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        if selected_row == -1:
            GuiUtils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
