# -*- coding: utf-8 -*-
# !/usr/bin/env python3
"""
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>
Copyright (C) 2016 Çağrı Ulaş <cagriulas@gmail.com>

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
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QCursor, QKeySequence, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QCheckBox, QWidget, \
    QShortcut, QKeySequenceEdit, QTabWidget, QMenu, QFileDialog, QAbstractItemView
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray, QSettings, QCoreApplication, QEvent, \
    QItemSelectionModel, QTimer, QModelIndex
from time import sleep, time
import os
import pexpect
import sys
import traceback

from libPINCE import GuiUtils, SysUtils, GDB_Engine, type_defs

from GUI.MainWindow import Ui_MainWindow as MainWindow
from GUI.SelectProcess import Ui_MainWindow as ProcessWindow
from GUI.AddAddressManuallyDialog import Ui_Dialog as ManualAddressDialog
from GUI.LoadingDialog import Ui_Dialog as LoadingDialog
from GUI.DialogWithButtons import Ui_Dialog as DialogWithButtons
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
from GUI.FunctionsInfoWidget import Ui_Form as FunctionsInfoWidget

from GUI.CustomAbstractTableModels.HexModel import QHexModel
from GUI.CustomAbstractTableModels.AsciiModel import QAsciiModel

selfpid = os.getpid()

# settings
update_table = bool
table_update_interval = float
pause_hotkey = str
continue_hotkey = str
code_injection_method = int
bring_disassemble_to_front = bool
instructions_per_scroll = int
gdb_path = str

# represents the index of columns in breakpoint table
BREAK_NUM_COL = 0
BREAK_ADDR_COL = 1
BREAK_TYPE_COL = 2
BREAK_SIZE_COL = 3
BREAK_ON_HIT_COL = 4
BREAK_COND_COL = 5

# row colours for disassemble qtablewidget
PC_COLOUR = Qt.blue
BOOKMARK_COLOUR = Qt.yellow
DEFAULT_COLOUR = Qt.white
BREAKPOINT_COLOUR = Qt.red

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
STACK_INT_REPRESENTATION_COL = 2
STACK_FLOAT_REPRESENTATION_COL = 3

# represents row and column counts of Hex table
HEX_VIEW_COL_COUNT = 16
HEX_VIEW_ROW_COUNT = 42  # J-JUST A COINCIDENCE, I SWEAR!

# represents the index of columns in track watchpoint table(what accesses this address thingy)
TRACK_WATCHPOINT_COUNT_COL = 0
TRACK_WATCHPOINT_ADDR_COL = 1

# represents the index of columns in function info table
FUNCTIONS_INFO_ADDR_COL = 0
FUNCTIONS_INFO_SYMBOL_COL = 1

# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = traceback.print_exception


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while True:
            if GDB_Engine.currentpid is 0 or SysUtils.is_process_valid(GDB_Engine.currentpid):
                pass
            else:
                self.process_exited.emit()
            sleep(0.1)


# Await async output from gdb
class AwaitAsyncOutput(QThread):
    async_output_ready = pyqtSignal()

    def run(self):
        while True:
            with GDB_Engine.gdb_async_condition:
                GDB_Engine.gdb_async_condition.wait()
            self.async_output_ready.emit()


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
        self.tableWidget_addresstable.setColumnWidth(FROZEN_COL, 25)
        self.tableWidget_addresstable.setColumnWidth(DESC_COL, 150)
        self.tableWidget_addresstable.setColumnWidth(ADDR_COL, 150)
        self.tableWidget_addresstable.setColumnWidth(TYPE_COL, 120)
        QCoreApplication.setOrganizationName("PINCE")
        QCoreApplication.setOrganizationDomain("github.com/korcankaraokcu/PINCE")
        QCoreApplication.setApplicationName("PINCE")
        self.settings = QSettings()
        if not SysUtils.is_path_valid(self.settings.fileName()):
            self.set_default_settings()
        try:
            self.apply_settings()
        except Exception as e:
            print("An exception occurred while trying to load settings, rolling back to the default configuration\n", e)
            self.settings.clear()
            self.set_default_settings()
        self.memory_view_window = MemoryViewWindowForm()
        self.memory_view_window.address_added.connect(self.add_entry_to_addresstable)
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
        self.shortcut_pause = QShortcut(QKeySequence(pause_hotkey), self)
        self.shortcut_pause.activated.connect(self.pause_hotkey_pressed)
        self.shortcut_continue = QShortcut(QKeySequence(continue_hotkey), self)
        self.shortcut_continue.activated.connect(self.continue_hotkey_pressed)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_addresstable.keyPressEvent_original = self.tableWidget_addresstable.keyPressEvent
        self.tableWidget_addresstable.keyPressEvent = self.tableWidget_addresstable_keyPressEvent
        self.tableWidget_addresstable.contextMenuEvent = self.tableWidget_addresstable_context_menu_event
        self.processbutton.clicked.connect(self.processbutton_onclick)
        self.pushButton_NewFirstScan.clicked.connect(self.newfirstscan_onclick)
        self.pushButton_NextScan.clicked.connect(self.nextscan_onclick)
        self.pushButton_Settings.clicked.connect(self.settingsbutton_onclick)
        self.pushButton_Console.clicked.connect(self.consolebutton_onclick)
        self.pushButton_Wiki.clicked.connect(self.wikibutton_onclick)
        self.pushButton_About.clicked.connect(self.aboutbutton_onclick)
        self.pushButton_AddAddressManually.clicked.connect(self.addaddressmanually_onclick)
        self.pushButton_MemoryView.clicked.connect(self.memoryview_onlick)
        self.pushButton_RefreshAdressTable.clicked.connect(self.update_address_table_manually)
        self.pushButton_CleanAddressTable.clicked.connect(self.delete_address_table_contents)
        self.tableWidget_addresstable.itemDoubleClicked.connect(self.on_address_table_double_click)
        icons_directory = SysUtils.get_current_script_directory() + "/media/icons"
        self.processbutton.setIcon(QIcon(QPixmap(icons_directory + "/monitor.png")))
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
        self.settings.endGroup()
        self.settings.beginGroup("Hotkeys")
        self.settings.setValue("pause", "F2")
        self.settings.setValue("continue", "F3")
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
        self.apply_settings()

    def apply_settings(self):
        global update_table
        global table_update_interval
        global pause_hotkey
        global continue_hotkey
        global code_injection_method
        global bring_disassemble_to_front
        global instructions_per_scroll
        global gdb_path
        update_table = self.settings.value("General/auto_update_address_table", type=bool)
        table_update_interval = self.settings.value("General/address_table_update_interval", type=float)
        pause_hotkey = self.settings.value("Hotkeys/pause")
        continue_hotkey = self.settings.value("Hotkeys/continue")
        try:
            self.shortcut_pause.setKey(QKeySequence(pause_hotkey))
        except AttributeError:
            pass
        try:
            self.shortcut_continue.setKey(QKeySequence(continue_hotkey))
        except AttributeError:
            pass
        try:
            self.memory_view_window.set_dynamic_debug_hotkeys()
        except AttributeError:
            pass
        code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        bring_disassemble_to_front = self.settings.value("Disassemble/bring_disassemble_to_front", type=bool)
        instructions_per_scroll = self.settings.value("Disassemble/instructions_per_scroll", type=int)
        gdb_path = self.settings.value("Debug/gdb_path", type=str)

    def pause_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior()

    def continue_hotkey_pressed(self):
        GDB_Engine.continue_inferior()

    def tableWidget_addresstable_context_menu_event(self, event):
        menu = QMenu()
        browse_region = menu.addAction("Browse this memory region[B]")
        disassemble = menu.addAction("Disassemble this address[D]")
        menu.addSeparator()
        delete_record = menu.addAction("Delete selected records[Del]")
        menu.addSeparator()
        what_writes = menu.addAction("Find out what writes to this address")
        what_reads = menu.addAction("Find out what reads this address")
        what_accesses = menu.addAction("Find out what accesses this address")
        font_size = self.tableWidget_addresstable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == browse_region:
            self.browse_region_for_selected_row()
        elif action == disassemble:
            self.disassemble_selected_row()
        elif action == delete_record:
            self.delete_selected_records()
        elif action == what_writes:
            self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.WRITE_ONLY)
        elif action == what_reads:
            self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.READ_ONLY)
        elif action == what_accesses:
            self.exec_track_watchpoint_widget(type_defs.WATCHPOINT_TYPE.BOTH)

    def exec_track_watchpoint_widget(self, watchpoint_type):
        last_selected_row = self.tableWidget_addresstable.selectionModel().selectedRows()[-1].row()
        address = self.tableWidget_addresstable.item(last_selected_row, ADDR_COL).text()
        length = GuiUtils.text_to_valuetype(self.tableWidget_addresstable.item(last_selected_row, TYPE_COL).text())[1]
        track_watchpoint_widget = TrackWatchpointWidgetForm(address, length, watchpoint_type, self)
        track_watchpoint_widget.show()

    def browse_region_for_selected_row(self):
        last_selected_row = self.tableWidget_addresstable.selectionModel().selectedRows()[-1].row()
        self.memory_view_window.hex_dump_address(
            int(self.tableWidget_addresstable.item(last_selected_row, ADDR_COL).text(), 16))
        self.memory_view_window.show()
        self.memory_view_window.activateWindow()

    def disassemble_selected_row(self):
        last_selected_row = self.tableWidget_addresstable.selectionModel().selectedRows()[-1].row()
        self.memory_view_window.disassemble_expression(
            self.tableWidget_addresstable.item(last_selected_row, ADDR_COL).text(), append_to_travel_history=True)
        self.memory_view_window.show()
        self.memory_view_window.activateWindow()

    def delete_selected_records(self):
        selected_rows = self.tableWidget_addresstable.selectionModel().selectedRows()
        while selected_rows:
            selected_rows = self.tableWidget_addresstable.selectionModel().selectedRows()
            if selected_rows:
                first_selected_row = selected_rows[0].row()
                self.tableWidget_addresstable.removeRow(first_selected_row)

    def tableWidget_addresstable_keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.delete_selected_records()
        elif e.key() == Qt.Key_B:
            self.browse_region_for_selected_row()
        elif e.key() == Qt.Key_D:
            self.disassemble_selected_row()
        elif e.key() == Qt.Key_R:
            self.update_address_table_manually()
        else:
            self.tableWidget_addresstable.keyPressEvent_original(e)

    def update_address_table_manually(self):
        table_contents = []
        row_count = self.tableWidget_addresstable.rowCount()
        for row in range(row_count):
            address = self.tableWidget_addresstable.item(row, ADDR_COL).text()
            index, length, unicode, zero_terminate = GuiUtils.text_to_valuetype(
                self.tableWidget_addresstable.item(row, TYPE_COL).text())
            table_contents.append([address, index, length, unicode, zero_terminate])
        new_table_contents = GDB_Engine.read_multiple_addresses(table_contents)
        for row, item in enumerate(new_table_contents):
            self.tableWidget_addresstable.setItem(row, VALUE_COL, QTableWidgetItem(str(item)))

    # gets the information from the dialog then adds it to addresstable
    def addaddressmanually_onclick(self):
        manual_address_dialog = ManualAddressDialogForm()
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, unicode, zero_terminate = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(description=description, address=address, typeofaddress=typeofaddress,
                                           length=length, unicode=unicode,
                                           zero_terminate=zero_terminate)

    def memoryview_onlick(self):
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def wikibutton_onclick(self):
        output = pexpect.run("who").decode("utf-8")
        user_name = output.split()[0]
        pexpect.run('sudo -u ' + user_name + ' python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def aboutbutton_onclick(self):
        self.about_widget = AboutWidgetForm()
        self.about_widget.show()

    def settingsbutton_onclick(self):
        settings_dialog = SettingsDialogForm()
        settings_dialog.reset_settings.connect(self.set_default_settings)
        if settings_dialog.exec_():
            self.apply_settings()

    def consolebutton_onclick(self):
        self.console_widget = ConsoleWidgetForm()
        self.console_widget.show()

    def newfirstscan_onclick(self):
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

    def nextscan_onclick(self):
        # GDB_Engine.send_command('interrupt\nx _start\nc &')  # test
        GDB_Engine.send_command("x/100x _start")
        # t = Thread(target=GDB_Engine.test)  # test
        # t2=Thread(target=test2)
        # t.start()
        # t2.start()
        if self.tableWidget_valuesearchtable.rowCount() <= 0:
            return

    # shows the process select window
    def processbutton_onclick(self):
        self.processwindow = ProcessForm(self)
        self.processwindow.show()

    def delete_address_table_contents(self):
        confirm_dialog = DialogWithButtonsForm(label_text="This will clear the contents of address table\nProceed?")
        if confirm_dialog.exec_():
            self.tableWidget_addresstable.setRowCount(0)

    def on_inferior_exit(self):
        self.on_status_running()
        self.label_SelectedProcess.setText("No Process Selected")

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
        if not GDB_Engine.currentpid == 0:
            GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    def add_entry_to_addresstable(self, description, address, typeofaddress, length=0, unicode=False,
                                  zero_terminate=True):
        frozen_checkbox = QCheckBox()
        typeofaddress_text = GuiUtils.valuetype_to_text(typeofaddress, length, unicode, zero_terminate)

        # this line lets us take symbols as parameters, pretty rad isn't it?
        address_text = GDB_Engine.convert_symbol_to_address(address)
        if address_text:
            address = address_text
        self.tableWidget_addresstable.setRowCount(self.tableWidget_addresstable.rowCount() + 1)
        currentrow = self.tableWidget_addresstable.rowCount() - 1
        value = GDB_Engine.read_single_address(address, typeofaddress, length, unicode, zero_terminate)
        self.tableWidget_addresstable.setCellWidget(currentrow, FROZEN_COL, frozen_checkbox)
        self.change_address_table_entries(row=currentrow, description=description, address=address,
                                          typeofaddress=typeofaddress_text, value=str(value))
        self.show()  # In case of getting called from elsewhere
        self.activateWindow()

    def on_address_table_double_click(self, index):
        current_row = index.row()
        current_column = index.column()
        if current_column is VALUE_COL:
            value = self.tableWidget_addresstable.item(current_row, VALUE_COL).text()
            value_index = GuiUtils.text_to_index(self.tableWidget_addresstable.item(current_row, TYPE_COL).text())
            dialog = DialogWithButtonsForm(label_text="Enter the new value", hide_line_edit=False,
                                           line_edit_text=value, parse_string=True, value_index=value_index)
            if dialog.exec_():
                table_contents = []
                value_text = dialog.get_values()
                selected_rows = self.tableWidget_addresstable.selectionModel().selectedRows()
                for item in selected_rows:
                    row = item.row()
                    address = self.tableWidget_addresstable.item(row, ADDR_COL).text()
                    value_type = self.tableWidget_addresstable.item(row, TYPE_COL).text()
                    value_index = GuiUtils.text_to_index(value_type)
                    if value_index == type_defs.VALUE_INDEX.INDEX_STRING or value_index == type_defs.VALUE_INDEX.INDEX_AOB:
                        unknown_type = SysUtils.parse_string(value_text, value_index)
                        if unknown_type is not None:
                            length = len(unknown_type)
                            self.tableWidget_addresstable.setItem(row, TYPE_COL, QTableWidgetItem(
                                GuiUtils.change_text_length(value_type, length)))
                    table_contents.append([address, value_index])
                GDB_Engine.set_multiple_addresses(table_contents, value_text)
                self.update_address_table_manually()

        elif current_column is DESC_COL:
            description = self.tableWidget_addresstable.item(current_row, DESC_COL).text()
            dialog = DialogWithButtonsForm(label_text="Enter the new description", hide_line_edit=False,
                                           line_edit_text=description)
            if dialog.exec_():
                description_text = dialog.get_values()
                selected_rows = self.tableWidget_addresstable.selectionModel().selectedRows()
                for item in selected_rows:
                    self.tableWidget_addresstable.setItem(item.row(), DESC_COL, QTableWidgetItem(description_text))
        elif current_column is ADDR_COL or current_column is TYPE_COL:
            description, address, value_type = self.read_address_table_entries(row=current_row)
            index, length, unicode, zero_terminate = GuiUtils.text_to_valuetype(value_type)
            manual_address_dialog = ManualAddressDialogForm(description=description, address=address, index=index,
                                                            length=length, unicode=unicode,
                                                            zero_terminate=zero_terminate)
            if manual_address_dialog.exec_():
                description, address, typeofaddress, length, unicode, zero_terminate = manual_address_dialog.get_values()
                typeofaddress_text = GuiUtils.valuetype_to_text(value_index=typeofaddress, length=length,
                                                                is_unicode=unicode,
                                                                zero_terminate=zero_terminate)
                address_text = GDB_Engine.convert_symbol_to_address(address)
                if address_text:
                    address = address_text
                value = GDB_Engine.read_single_address(address=address, value_index=typeofaddress,
                                                       length=length, is_unicode=unicode,
                                                       zero_terminate=zero_terminate)
                self.change_address_table_entries(row=current_row, description=description, address=address,
                                                  typeofaddress=typeofaddress_text, value=str(value))

    # Changes the column values of the given row
    def change_address_table_entries(self, row, description="", address="", typeofaddress="", value=""):
        self.tableWidget_addresstable.setItem(row, DESC_COL, QTableWidgetItem(description))
        self.tableWidget_addresstable.setItem(row, ADDR_COL, QTableWidgetItem(address))
        self.tableWidget_addresstable.setItem(row, TYPE_COL, QTableWidgetItem(typeofaddress))
        self.tableWidget_addresstable.setItem(row, VALUE_COL, QTableWidgetItem(value))

    # Returns the column values of the given row
    def read_address_table_entries(self, row):
        description = self.tableWidget_addresstable.item(row, DESC_COL).text()
        address = self.tableWidget_addresstable.item(row, ADDR_COL).text()
        value_type = self.tableWidget_addresstable.item(row, TYPE_COL).text()
        return description, address, value_type


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_to_parent(self)
        processlist = SysUtils.get_process_list()
        self.refresh_process_table(self.processtable, processlist)
        self.pushButton_Close.clicked.connect(self.pushbutton_close_onclick)
        self.pushButton_Open.clicked.connect(self.pushbutton_open_onclick)
        self.pushButton_CreateProcess.clicked.connect(self.pushbutton_createprocess_onclick)
        self.lineEdit_searchprocess.textChanged.connect(self.generate_new_list)
        self.processtable.itemDoubleClicked.connect(self.pushbutton_open_onclick)

    # refreshes process list
    def generate_new_list(self):
        text = self.lineEdit_searchprocess.text()
        processlist = SysUtils.search_in_processes_by_name(text)
        self.refresh_process_table(self.processtable, processlist)

    # closes the window whenever ESC key is pressed
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget, processlist):
        tablewidget.setRowCount(0)
        tablewidget.setRowCount(len(processlist))
        for i, row in enumerate(processlist):
            tablewidget.setItem(i, 0, QTableWidgetItem(str(row.pid)))
            tablewidget.setItem(i, 1, QTableWidgetItem(row.username()))
            tablewidget.setItem(i, 2, QTableWidgetItem(row.name()))

    # self-explanatory
    def pushbutton_close_onclick(self):
        self.close()

    # gets the pid out of the selection to attach
    def pushbutton_open_onclick(self):
        currentitem = self.processtable.item(self.processtable.currentIndex().row(), 0)
        if currentitem is None:
            QMessageBox.information(self, "Error", "Please select a process first")
        else:
            pid = int(currentitem.text())
            if not SysUtils.is_process_valid(pid):
                QMessageBox.information(self, "Error", "Selected process is not valid")
                return
            if pid == selfpid:
                QMessageBox.information(self, "Error", "What the fuck are you trying to do?")  # planned easter egg
                return
            if pid == GDB_Engine.currentpid:
                QMessageBox.information(self, "Error", "You're debugging this process already")
                return
            tracedby = SysUtils.is_traced(pid)
            if tracedby:
                QMessageBox.information(self, "Error",
                                        "That process is already being traced by " + tracedby + ", could not attach to the process")
                return
            self.setCursor(QCursor(Qt.WaitCursor))
            print("processing")
            result = GDB_Engine.can_attach(pid)
            if not result:
                print("done")
                QMessageBox.information(self, "Error", "Permission denied, could not attach to the process")
                return
            if not GDB_Engine.currentpid == 0:
                GDB_Engine.detach()
            GDB_Engine.init_gdb(gdb_path)
            GDB_Engine.attach(pid)
            p = SysUtils.get_process_information(GDB_Engine.currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.enable_scan_gui()
            readable_only, writeable, executable, readable = SysUtils.get_memory_regions_by_perms(
                GDB_Engine.currentpid)  # test
            SysUtils.exclude_system_memory_regions(readable)
            print(len(readable))
            print("done")
            self.close()

    def pushbutton_createprocess_onclick(self):
        file_path = QFileDialog.getOpenFileName(self, "Select the target binary")[0]
        if file_path:
            if not GDB_Engine.currentpid == 0:
                GDB_Engine.detach()
            arg_dialog = DialogWithButtonsForm(label_text="Enter the optional arguments", hide_line_edit=False)
            if arg_dialog.exec_():
                args = arg_dialog.get_values()
            else:
                args = ""
            self.setCursor(QCursor(Qt.WaitCursor))
            GDB_Engine.init_gdb(gdb_path)
            GDB_Engine.create_process(file_path, args)
            p = SysUtils.get_process_information(GDB_Engine.currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.enable_scan_gui()
            self.close()

    def enable_scan_gui(self):
        self.parent().QWidget_Toolbox.setEnabled(True)
        self.parent().pushButton_NextScan.setEnabled(False)
        self.parent().pushButton_UndoScan.setEnabled(False)


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent=None, description="No Description", address="0x",
                 index=type_defs.VALUE_INDEX.INDEX_4BYTES, length=10,
                 unicode=False,
                 zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.lineEdit_description.setText(description)
        self.lineEdit_address.setText(address)
        self.comboBox_ValueType.setCurrentIndex(index)
        if self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_STRING:
            self.label_length.show()
            self.lineEdit_length.show()
            try:
                length = str(length)
            except:
                length = "10"
            self.lineEdit_length.setText(length)
            self.checkBox_Unicode.show()
            self.checkBox_Unicode.setChecked(unicode)
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
            self.checkBox_Unicode.hide()
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_Unicode.hide()
            self.checkBox_zeroterminate.hide()
        self.comboBox_ValueType.currentIndexChanged.connect(self.valuetype_on_current_index_change)
        self.lineEdit_length.textChanged.connect(self.update_value_of_address)
        self.checkBox_Unicode.stateChanged.connect(self.update_value_of_address)
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
        if action == refresh:
            self.update_value_of_address()

    def update_value_of_address(self):
        address = self.lineEdit_address.text()
        address_type = self.comboBox_ValueType.currentIndex()
        if address_type is type_defs.VALUE_INDEX.INDEX_AOB:
            length = self.lineEdit_length.text()
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type, length))
        elif address_type is type_defs.VALUE_INDEX.INDEX_STRING:
            length = self.lineEdit_length.text()
            is_unicode = self.checkBox_Unicode.isChecked()
            is_zeroterminate = self.checkBox_zeroterminate.isChecked()
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type, length, is_unicode,
                                                             is_zeroterminate))
        else:
            self.label_valueofaddress.setText(
                GDB_Engine.read_single_address_by_expression(address, address_type))

    def valuetype_on_current_index_change(self):
        if self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_STRING:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() is type_defs.VALUE_INDEX.INDEX_AOB:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.hide()
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_Unicode.hide()
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
        unicode = False
        zero_terminate = False
        if self.checkBox_Unicode.isChecked():
            unicode = True
        if self.checkBox_zeroterminate.isChecked():
            zero_terminate = True
        typeofaddress = self.comboBox_ValueType.currentIndex()
        return description, address, typeofaddress, length, unicode, zero_terminate


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
        pince_directory = SysUtils.get_current_script_directory()
        self.image_list = os.listdir(pince_directory + "/media/LoadingDialog")
        self.image_list.sort()
        self.current_image_index = 0
        self.change_loading_picture()
        self.image_timer = QTimer()
        self.image_timer.setInterval(3000)
        self.image_timer.timeout.connect(self.change_loading_picture)
        self.image_timer.start()

    def change_loading_picture(self):
        pince_directory = SysUtils.get_current_script_directory()
        image_name = self.image_list[self.current_image_index]
        self.movie = QMovie(pince_directory + "/media/LoadingDialog/" + image_name, QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(50, 50))
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.current_image_index += 1
        self.current_image_index %= len(self.image_list)
        self.movie.start()

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


class DialogWithButtonsForm(QDialog, DialogWithButtons):
    def __init__(self, parent=None, label_text="", hide_line_edit=True, line_edit_text="", parse_string=False,
                 value_index=type_defs.VALUE_INDEX.INDEX_4BYTES, align=Qt.AlignCenter):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.label.setAlignment(align)
        self.parse_string = parse_string
        self.value_index = value_index
        label_text = str(label_text)
        self.label.setText(label_text)
        if hide_line_edit:
            self.lineEdit.hide()
        else:
            line_edit_text = str(line_edit_text)
            self.lineEdit.setText(line_edit_text)

    def get_values(self):
        line_edit_text = self.lineEdit.text()
        return line_edit_text

    def accept(self):
        if self.parse_string:
            string = self.lineEdit.text()
            if SysUtils.parse_string(string, self.value_index) is None:
                QMessageBox.information(self, "Error", "Can't parse the input")
                return
        super(DialogWithButtonsForm, self).accept()


class SettingsDialogForm(QDialog, SettingsDialog):
    reset_settings = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        # Yet another retarded hack, thanks to pyuic5 not supporting QKeySequenceEdit
        self.keySequenceEdit = QKeySequenceEdit()
        self.verticalLayout_Hotkey.addWidget(self.keySequenceEdit)
        self.listWidget_Options.currentRowChanged.connect(self.change_display)
        icons_directory = SysUtils.get_current_script_directory() + "/media/icons"
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
            current_insturctions_shown = int(self.lineEdit_InstructionsPerScroll.text())
        except:
            QMessageBox.information(self, "Error", "Instruction count must be an integer")
            return
        if current_insturctions_shown < 1:
            QMessageBox.information(self, "Error", "Instruction count cannot be lower than 1" +
                                    "\nIt would be retarded anyways, wouldn't it?")
            return
        if current_table_update_interval < 0:
            QMessageBox.information(self, "Error", "Update interval cannot be a negative number")
            return
        elif current_table_update_interval == 0:

            # Easter egg #2
            if not DialogWithButtonsForm(label_text="You are asking for it, aren't you?").exec_():
                return
        elif current_table_update_interval < 0.1:
            if not DialogWithButtonsForm(label_text="Update interval should be bigger than 0.1 seconds" +
                    "\nSetting update interval less than 0.1 seconds may cause slowness" +
                    "\n\tProceed?").exec_():
                return
        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        self.settings.setValue("General/address_table_update_interval", current_table_update_interval)
        self.settings.setValue("Hotkeys/pause", self.pause_hotkey)
        self.settings.setValue("Hotkeys/continue", self.continue_hotkey)
        if self.radioButton_SimpleDLopenCall.isChecked():
            injection_method = type_defs.INJECTION_METHOD.SIMPLE_DLOPEN_CALL
        elif self.radioButton_AdvancedInjection.isChecked():
            injection_method = type_defs.INJECTION_METHOD.ADVANCED_INJECTION
        self.settings.setValue("CodeInjection/code_injection_method", injection_method)
        self.settings.setValue("Disassemble/bring_disassemble_to_front",
                               self.checkBox_BringDisassembleToFront.isChecked())
        self.settings.setValue("Disassemble/instructions_per_scroll", current_insturctions_shown)
        self.settings.setValue("Debug/gdb_path", self.lineEdit_GDBPath.text())
        super(SettingsDialogForm, self).accept()

    def config_gui(self):
        self.settings = QSettings()
        self.checkBox_AutoUpdateAddressTable.setChecked(
            self.settings.value("General/auto_update_address_table", type=bool))
        self.lineEdit_UpdateInterval.setText(
            str(self.settings.value("General/address_table_update_interval", type=float)))
        self.pause_hotkey = self.settings.value("Hotkeys/pause")
        self.continue_hotkey = self.settings.value("Hotkeys/continue")
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
        if index is 0:
            self.keySequenceEdit.setKeySequence(self.pause_hotkey)
        elif index is 1:
            self.keySequenceEdit.setKeySequence(self.continue_hotkey)

    def keySequenceEdit_key_sequence_changed(self):
        current_index = self.listWidget_Functions.currentIndex().row()
        if current_index is 0:
            self.pause_hotkey = self.keySequenceEdit.keySequence().toString()
        elif current_index is 1:
            self.continue_hotkey = self.keySequenceEdit.keySequence().toString()

    def pushButton_ClearHotkey_clicked(self):
        self.keySequenceEdit.clear()

    def pushButton_ResetSettings_clicked(self):
        confirm_dialog = DialogWithButtonsForm(label_text="This will reset to the default settings\nProceed?")
        if confirm_dialog.exec_():
            self.reset_settings.emit()
        else:
            return
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
        GuiUtils.center(self)
        self.await_async_output_thread = AwaitAsyncOutput()
        self.await_async_output_thread.async_output_ready.connect(self.on_async_output)
        self.await_async_output_thread.start()
        self.pushButton_Send.clicked.connect(self.communicate)
        self.pushButton_SendCtrl.clicked.connect(lambda: self.communicate(control=True))
        self.shortcut_send = QShortcut(QKeySequence("Return"), self)
        self.shortcut_send.activated.connect(self.communicate)
        self.shortcut_send_ctrl = QShortcut(QKeySequence("Ctrl+C"), self)
        self.shortcut_send_ctrl.activated.connect(lambda: self.communicate(control=True))
        self.textBrowser.append("Hotkeys:")
        self.textBrowser.append("--------------------")
        self.textBrowser.append("Send=Enter         |\nSend ctrl+c=Ctrl+C |")
        self.textBrowser.append("--------------------")
        self.textBrowser.append("Commands:")
        self.textBrowser.append("---------------------------")
        self.textBrowser.append("/clear: Clear the console |")
        self.textBrowser.append("---------------------------")
        self.textBrowser.append("You can change the output mode from bottom right")
        self.textBrowser.append("Note: Changing output mode only affects commands sent. Any other " +
                                "output coming from external sources(e.g async output) will be shown in MI format")

    def communicate(self, control=False):
        if control:
            console_input = "/Ctrl+C"
        else:
            console_input = self.lineEdit.text()
        if console_input.lower() == "/clear":
            self.textBrowser.clear()
            console_output = "Cleared"
        elif console_input.strip().lower().startswith("-"):
            console_output = "GDB/MI commands aren't supported yet"
        elif console_input.strip().lower() == "q" or console_input.strip().lower() == "quit":
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
                if GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_STOPPED:
                    console_output = "Inferior is already stopped"
                else:
                    console_output = ""
        self.textBrowser.append("-->" + console_input)
        self.textBrowser.append(console_output)
        self.textBrowser.verticalScrollBar().setValue(self.textBrowser.verticalScrollBar().maximum())

    def on_async_output(self):
        self.textBrowser.append(GDB_Engine.gdb_async_output)
        self.textBrowser.verticalScrollBar().setValue(self.textBrowser.verticalScrollBar().maximum())


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

    # TODO: Change this nonsense when the huge refactorization happens
    address_added = pyqtSignal(object, object, object, object, object, object)

    def set_dynamic_debug_hotkeys(self):
        self.shortcut_break.setKey(QKeySequence(pause_hotkey))
        self.shortcut_run.setKey(QKeySequence(continue_hotkey))
        self.actionBreak.setText("Break[" + pause_hotkey + "]")
        self.actionRun.setText("Run[" + continue_hotkey + "]")

    def set_debug_menu_shortcuts(self):
        self.shortcut_break = QShortcut(QKeySequence(pause_hotkey), self)
        self.shortcut_break.activated.connect(GDB_Engine.interrupt_inferior)
        self.shortcut_run = QShortcut(QKeySequence(continue_hotkey), self)
        self.shortcut_run.activated.connect(GDB_Engine.continue_inferior)
        self.shortcut_step = QShortcut(QKeySequence("F7"), self)
        self.shortcut_step.activated.connect(GDB_Engine.step_instruction)
        self.shortcut_step_over = QShortcut(QKeySequence("F8"), self)
        self.shortcut_step_over.activated.connect(GDB_Engine.step_over_instruction)
        self.shortcut_execute_till_return = QShortcut(QKeySequence("Shift+F8"), self)
        self.shortcut_execute_till_return.activated.connect(GDB_Engine.execute_till_return)
        self.shortcut_toggle_breakpoint = QShortcut(QKeySequence("F5"), self)
        self.shortcut_toggle_breakpoint.activated.connect(self.toggle_breakpoint)

    def initialize_debug_context_menu(self):
        self.actionBreak.triggered.connect(GDB_Engine.interrupt_inferior)
        self.actionRun.triggered.connect(GDB_Engine.continue_inferior)
        self.actionStep.triggered.connect(GDB_Engine.step_instruction)
        self.actionStep_Over.triggered.connect(GDB_Engine.step_over_instruction)
        self.actionExecute_Till_Return.triggered.connect(GDB_Engine.execute_till_return)
        self.actionToggle_Breakpoint.triggered.connect(self.toggle_breakpoint)

    def initialize_view_context_menu(self):
        self.actionBookmarks.triggered.connect(self.on_ViewBookmarks_triggered)
        self.actionStackTrace_Info.triggered.connect(self.on_ViewStacktrace_Info_triggered)
        self.actionBreakpoints.triggered.connect(self.on_ViewBreakpoints_triggered)
        self.actionFunctions.triggered.connect(self.on_ViewFunctions_triggered)

    def initialize_tools_context_menu(self):
        self.actionInject_so_file.triggered.connect(self.on_inject_so_file_triggered)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        self.process_stopped.connect(self.on_process_stop)
        self.process_running.connect(self.on_process_running)
        self.set_debug_menu_shortcuts()
        self.set_dynamic_debug_hotkeys()
        self.initialize_view_context_menu()
        self.initialize_debug_context_menu()
        self.initialize_tools_context_menu()
        self.initialize_disassemble_view()
        self.initialize_register_view()
        self.initialize_stack_view()
        self.initialize_hex_view()

        self.label_HexView_Information.contextMenuEvent = self.label_HexView_Information_context_menu_event

        self.splitter_Disassemble_Registers.setStretchFactor(0, 1)
        self.widget_StackView.resize(420, self.widget_StackView.height())  # blaze it
        self.widget_Registers.resize(330, self.widget_Registers.height())

    def initialize_register_view(self):
        self.pushButton_ShowFloatRegisters.clicked.connect(self.on_show_float_registers_button_clicked)

    def initialize_stack_view(self):
        self.tableWidget_StackTrace.setColumnWidth(STACKTRACE_RETURN_ADDRESS_COL, 350)

        self.tableWidget_Stack.contextMenuEvent = self.tableWidget_Stack_context_menu_event
        self.tableWidget_StackTrace.contextMenuEvent = self.tableWidget_StackTrace_context_menu_event
        self.tableWidget_StackTrace.itemDoubleClicked.connect(self.tableWidget_StackTrace_double_click)

    def initialize_disassemble_view(self):
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

        self.tableWidget_Disassemble.itemDoubleClicked.connect(self.on_disassemble_double_click)
        self.tableWidget_Disassemble.itemSelectionChanged.connect(self.on_disassemble_item_selection_changed)

    def initialize_hex_view(self):
        self.hex_view_last_selected_address_int = 0
        self.hex_view_currently_displayed_address = 0
        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        self.tableView_HexView_Hex.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Ascii.contextMenuEvent = self.widget_HexView_context_menu_event

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

    def toggle_breakpoint(self):
        selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
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
            watchpoint_dialog = DialogWithButtonsForm(label_text="Enter the watchpoint length in size of bytes",
                                                      hide_line_edit=False)
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
        menu = QMenu()
        copy = menu.addAction("Copy to Clipboard")
        font_size = self.label_HexView_Information.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == copy:
            QApplication.clipboard().setText(self.label_HexView_Information.text())

    def widget_HexView_context_menu_event(self, event):
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        menu = QMenu()
        go_to = menu.addAction("Go to expression[G]")
        disassemble = menu.addAction("Disassemble this address[D]")
        menu.addSeparator()
        add_address = menu.addAction("Add this address to address list[A]")
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        if not GDB_Engine.check_address_in_breakpoints(selected_address):
            watchpoint_menu = menu.addMenu("Set Watchpoint")
            write_only_watchpoint = watchpoint_menu.addAction("Write Only")
            read_only_watchpoint = watchpoint_menu.addAction("Read Only")
            both_watchpoint = watchpoint_menu.addAction("Both")
            add_condition = -1
            delete_breakpoint = -1
        else:
            write_only_watchpoint = -1
            read_only_watchpoint = -1
            both_watchpoint = -1
            add_condition = menu.addAction("Add/Change condition for breakpoint")
            delete_breakpoint = menu.addAction("Delete Breakpoint")
        font_size = self.widget_HexView.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == go_to:
            self.exec_hex_view_go_to_dialog()
        elif action == disassemble:
            self.disassemble_expression(hex(selected_address), append_to_travel_history=True)
        elif action == add_address:
            self.exec_hex_view_add_address_dialog()
        elif action == refresh:
            self.hex_dump_address(self.hex_view_currently_displayed_address)
        elif action == write_only_watchpoint:
            self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.WRITE_ONLY)
        elif action == read_only_watchpoint:
            self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.READ_ONLY)
        elif action == both_watchpoint:
            self.toggle_watchpoint(selected_address, type_defs.WATCHPOINT_TYPE.BOTH)
        elif action == add_condition:
            self.add_breakpoint_condition(selected_address)
        elif action == delete_breakpoint:
            self.toggle_watchpoint(selected_address)

    def exec_hex_view_go_to_dialog(self):
        current_address = hex(self.hex_view_currently_displayed_address)
        go_to_dialog = DialogWithButtonsForm(label_text="Enter the expression", hide_line_edit=False,
                                             line_edit_text=current_address)
        if go_to_dialog.exec_():
            expression = go_to_dialog.get_values()
            dest_address = GDB_Engine.convert_symbol_to_address(expression)
            if dest_address is None:
                QMessageBox.information(self, "Error", "Cannot access memory at expression " + expression)
                return
            self.hex_dump_address(int(dest_address, 16))

    def exec_hex_view_add_address_dialog(self):
        selected_address = self.hex_view_currently_displayed_address + self.tableView_HexView_Hex.get_current_offset()
        manual_address_dialog = ManualAddressDialogForm(address=hex(selected_address),
                                                        index=type_defs.VALUE_INDEX.INDEX_AOB)
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, unicode, zero_terminate = manual_address_dialog.get_values()
            self.address_added.emit(description, address, typeofaddress, length, unicode, zero_terminate)

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
            entry_point_address = GDB_Engine.convert_symbol_to_address("_start")
            self.hex_dump_address(int(entry_point_address, 16))
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
        program_counter = GDB_Engine.convert_symbol_to_address("$pc", check=False)
        program_counter_int = int(program_counter, 16)
        row_of_pc = False
        rows_of_encountered_bookmarks_list = []
        breakpoint_list = []
        rows_of_encountered_breakpoints_list = []
        breakpoint_info = GDB_Engine.get_breakpoint_info()
        for item in breakpoint_info:
            breakpoint_list.append(int(item.address, 16))

        # TODO: Change this nonsense when the huge refactorization happens
        current_first_address = SysUtils.extract_address(disas_data[0][0])  # address of first list entry
        try:
            previous_first_address = SysUtils.extract_address(
                self.tableWidget_Disassemble.item(0, DISAS_ADDR_COL).text())
        except AttributeError:
            previous_first_address = current_first_address

        self.tableWidget_Disassemble.setRowCount(0)
        self.tableWidget_Disassemble.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            comment = ""
            current_address = int(SysUtils.extract_address(item[0]), 16)
            if current_address == program_counter_int:
                item[0] = ">>>" + item[0]
                row_of_pc = row
            for bookmark_item in self.tableWidget_Disassemble.bookmarks.keys():
                if current_address == bookmark_item:
                    rows_of_encountered_bookmarks_list.append(row)
                    item[0] = "(M)" + item[0]
                    comment = self.tableWidget_Disassemble.bookmarks[bookmark_item]
                    break
            for breakpoint in breakpoint_list:
                if current_address == breakpoint:
                    rows_of_encountered_breakpoints_list.append(row)
                    item[0] = "(B)" + item[0]
                    break
            if current_address == self.disassemble_last_selected_address_int:
                self.tableWidget_Disassemble.selectRow(row)
            self.tableWidget_Disassemble.setItem(row, DISAS_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Disassemble.setItem(row, DISAS_BYTES_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Disassemble.setItem(row, DISAS_OPCODES_COL, QTableWidgetItem(item[2]))
            self.tableWidget_Disassemble.setItem(row, DISAS_COMMENT_COL, QTableWidgetItem(comment))
        self.handle_colours(row_of_pc, rows_of_encountered_bookmarks_list, rows_of_encountered_breakpoints_list)
        self.tableWidget_Disassemble.resizeColumnsToContents()
        self.tableWidget_Disassemble.horizontalHeader().setStretchLastSection(True)

        # We append the old record to travel history as last action because we wouldn't like to see unnecessary
        # addresses in travel history if any error occurs while displaying the next location
        if append_to_travel_history:
            self.tableWidget_Disassemble.travel_history.append(previous_first_address)
        self.disassemble_currently_displayed_address = current_first_address

    def refresh_disassemble_view(self):
        self.disassemble_expression(self.disassemble_currently_displayed_address)

    # Set colour of a row if a specific address is encountered(e.g $pc, a bookmarked address etc.)
    def handle_colours(self, row_of_pc, encountered_bookmark_list, encountered_breakpoints_list):
        if row_of_pc:
            self.set_row_colour(row_of_pc, PC_COLOUR)
        if encountered_bookmark_list:
            for encountered_row in encountered_bookmark_list:
                self.set_row_colour(encountered_row, BOOKMARK_COLOUR)
        if encountered_breakpoints_list:
            for encountered_row in encountered_breakpoints_list:
                self.set_row_colour(encountered_row, BREAKPOINT_COLOUR)

    # color parameter should be Qt.colour
    def set_row_colour(self, row, colour):
        for item in range(self.tableWidget_Disassemble.columnCount()):
            self.tableWidget_Disassemble.item(row, item).setData(Qt.BackgroundColorRole, QColor(colour))

    def on_process_stop(self):
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
        time1 = time()
        print("UPDATED MEMORYVIEW IN:" + str(time1 - time0))

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
        condition_dialog = DialogWithButtonsForm(label_text=condition_text, hide_line_edit=False,
                                                 line_edit_text=condition_line_edit_text, align=Qt.AlignLeft)
        if condition_dialog.exec_():
            condition = condition_dialog.get_values()
            if not GDB_Engine.add_breakpoint_condition(hex(int_address), condition):
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

    def tableWidget_StackTrace_context_menu_event(self, event):
        menu = QMenu()
        switch_to_stack = menu.addAction("Full Stack")
        font_size = self.tableWidget_StackTrace.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == switch_to_stack:
            self.stackedWidget_StackScreens.setCurrentWidget(self.Stack)
            self.update_stack()

    def update_stack(self):
        stack_info = GDB_Engine.get_stack_info()
        self.tableWidget_Stack.setRowCount(0)
        self.tableWidget_Stack.setRowCount(len(stack_info))
        for row, item in enumerate(stack_info):
            self.tableWidget_Stack.setItem(row, STACK_POINTER_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Stack.setItem(row, STACK_VALUE_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Stack.setItem(row, STACK_INT_REPRESENTATION_COL, QTableWidgetItem(item[2]))
            self.tableWidget_Stack.setItem(row, STACK_FLOAT_REPRESENTATION_COL, QTableWidgetItem(item[3]))
        self.tableWidget_Stack.resizeColumnsToContents()

    def tableWidget_Stack_context_menu_event(self, event):
        menu = QMenu()
        switch_to_stacktrace = menu.addAction("Stacktrace")
        font_size = self.tableWidget_Stack.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == switch_to_stacktrace:
            self.stackedWidget_StackScreens.setCurrentWidget(self.StackTrace)
            self.update_stacktrace()

    def tableWidget_StackTrace_double_click(self, index):
        if index.column() == STACKTRACE_RETURN_ADDRESS_COL:
            selected_row = self.tableWidget_StackTrace.selectionModel().selectedRows()[-1].row()
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_RETURN_ADDRESS_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            self.disassemble_expression(current_address, append_to_travel_history=True)

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

        if event.key() == Qt.Key_G:
            self.exec_hex_view_go_to_dialog()
        elif event.key() == Qt.Key_D:
            self.disassemble_expression(hex(selected_address), append_to_travel_history=True)
        elif event.key() == Qt.Key_A:
            self.exec_hex_view_add_address_dialog()
        elif event.key() == Qt.Key_R:
            self.refresh_hex_view()
        else:
            self.tableView_HexView_Hex.keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event):
        selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        if event.key() == Qt.Key_Space:
            self.follow_instruction(selected_row)
        elif event.key() == Qt.Key_G:
            self.exec_disassemble_go_to_dialog()
        elif event.key() == Qt.Key_H:
            self.hex_dump_address(current_address_int)
        elif event.key() == Qt.Key_B:
            self.bookmark_address(current_address_int)
        elif event.key() == Qt.Key_R:
            self.refresh_disassemble_view()
        else:
            self.tableWidget_Disassemble.keyPressEvent_original(event)

    def on_disassemble_double_click(self, index):
        if index.column() == DISAS_COMMENT_COL:
            selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = int(SysUtils.extract_address(current_address_text), 16)
            if current_address in self.tableWidget_Disassemble.bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def on_disassemble_item_selection_changed(self):
        try:
            selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
            selected_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            selected_address_int = int(SysUtils.extract_address(selected_address_text), 16)
            self.disassemble_last_selected_address_int = selected_address_int
        except:
            pass

    # Search the item in given row for location changing instructions
    # Go to the address pointed by that instruction if it contains any
    def follow_instruction(self, selected_row):
        address = SysUtils.extract_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text(),
            search_for_location_changing_instructions=True)
        if address:
            self.disassemble_expression(address, append_to_travel_history=True)

    def tableWidget_Disassemble_context_menu_event(self, event):
        selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction("Go to expression[G]")
        back = menu.addAction("Back")
        show_in_hex_view = menu.addAction("Show this address in HexView[H]")
        followable = SysUtils.extract_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text(),
            search_for_location_changing_instructions=True)
        if followable:
            follow = menu.addAction("Follow[Space]")
        else:
            follow = -1
        is_bookmarked = current_address_int in self.tableWidget_Disassemble.bookmarks
        if not is_bookmarked:
            bookmark = menu.addAction("Bookmark this address[B]")
            delete_bookmark = -1
            change_comment = -1
        else:
            bookmark = -1
            delete_bookmark = menu.addAction("Delete this bookmark")
            change_comment = menu.addAction("Change comment")
        go_to_bookmark = menu.addMenu("Go to bookmarked address")
        bookmark_action_list = []
        for item in self.tableWidget_Disassemble.bookmarks.keys():

            # FIXME: Implement and use optimized version of convert_address_to_symbol if performance issues occur
            current_text = GDB_Engine.convert_address_to_symbol(hex(item), include_address=True)
            if current_text is None:
                text_append = hex(item) + "(Unreachable)"
            else:
                text_append = current_text
            bookmark_action_list.append(go_to_bookmark.addAction(text_append))
        menu.addSeparator()
        toggle_breakpoint = menu.addAction("Toggle Breakpoint[F5]")
        if GDB_Engine.check_address_in_breakpoints(current_address_int):
            add_condition = menu.addAction("Add/Change condition for breakpoint")
        else:
            add_condition = -1
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        menu.addSeparator()
        clipboard_menu = menu.addMenu("Copy to Clipboard")
        copy_address = clipboard_menu.addAction("Copy Address")
        copy_bytes = clipboard_menu.addAction("Copy Bytes")
        copy_opcode = clipboard_menu.addAction("Copy Opcode")
        copy_comment = clipboard_menu.addAction("Copy Comment")
        font_size = self.tableWidget_Disassemble.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == go_to:
            self.exec_disassemble_go_to_dialog()
        elif action == back:
            if self.tableWidget_Disassemble.travel_history:
                last_location = self.tableWidget_Disassemble.travel_history[-1]
                self.disassemble_expression(last_location)
                self.tableWidget_Disassemble.travel_history.pop()
        elif action == show_in_hex_view:
            self.hex_dump_address(current_address_int)
        elif action == follow:
            self.follow_instruction(selected_row)
        elif action == bookmark:
            self.bookmark_address(current_address_int)
        elif action == delete_bookmark:
            self.delete_bookmark(current_address_int)
        elif action == change_comment:
            self.change_bookmark_comment(current_address_int)
        elif action == toggle_breakpoint:
            self.toggle_breakpoint()
        elif action == add_condition:
            self.add_breakpoint_condition(current_address_int)
        elif action == refresh:
            self.refresh_disassemble_view()
        elif action == copy_address:
            QApplication.clipboard().setText(self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text())
        elif action == copy_bytes:
            QApplication.clipboard().setText(self.tableWidget_Disassemble.item(selected_row, DISAS_BYTES_COL).text())
        elif action == copy_opcode:
            QApplication.clipboard().setText(self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text())
        elif action == copy_comment:
            QApplication.clipboard().setText(self.tableWidget_Disassemble.item(selected_row, DISAS_COMMENT_COL).text())
        for item in bookmark_action_list:
            if action == item:
                self.disassemble_expression(SysUtils.extract_address(action.text()), append_to_travel_history=True)

    def exec_disassemble_go_to_dialog(self):
        selected_row = self.tableWidget_Disassemble.selectionModel().selectedRows()[-1].row()
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)

        go_to_dialog = DialogWithButtonsForm(label_text="Enter the expression", hide_line_edit=False,
                                             line_edit_text=current_address)
        if go_to_dialog.exec_():
            traveled_exp = go_to_dialog.get_values()
            self.disassemble_expression(traveled_exp, append_to_travel_history=True)

    def bookmark_address(self, int_address):
        if int_address in self.tableWidget_Disassemble.bookmarks:
            QMessageBox.information(self, "Error", "This address has already been bookmarked")
            return
        comment_dialog = DialogWithButtonsForm(label_text="Enter the comment for bookmarked address",
                                               hide_line_edit=False)
        if comment_dialog.exec_():
            comment = comment_dialog.get_values()
        else:
            return
        self.tableWidget_Disassemble.bookmarks[int_address] = comment
        self.refresh_disassemble_view()

    def change_bookmark_comment(self, int_address):
        current_comment = self.tableWidget_Disassemble.bookmarks[int_address]
        comment_dialog = DialogWithButtonsForm(label_text="Enter the comment for bookmarked address",
                                               hide_line_edit=False, line_edit_text=current_comment)
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

    def on_ViewBookmarks_triggered(self):
        self.bookmark_widget = BookmarkWidgetForm(self)
        self.bookmark_widget.show()

    def on_ViewStacktrace_Info_triggered(self):
        self.stacktrace_info_widget = StackTraceInfoWidgetForm()
        self.stacktrace_info_widget.show()

    def on_ViewBreakpoints_triggered(self):
        self.breakpoint_widget = BreakpointInfoWidgetForm(self)
        self.breakpoint_widget.show()

    def on_ViewFunctions_triggered(self):
        functions_info_widget = FunctionsInfoWidgetForm(self)
        functions_info_widget.show()

    def on_inject_so_file_triggered(self):
        file_path = QFileDialog.getOpenFileName(self, "Select the .so file", "", "Shared object library (*.so)")[0]
        if file_path:
            if GDB_Engine.inject_with_dlopen_call(file_path):
                QMessageBox.information(self, "Success!", "The file has been injected")
            else:
                QMessageBox.information(self, "Error", "Failed to inject the .so file")

    def on_show_float_registers_button_clicked(self):
        self.float_registers_widget = FloatRegisterWidgetForm()
        self.float_registers_widget.show()
        GuiUtils.center_to_window(self.float_registers_widget, self.widget_Registers)


class BookmarkWidgetForm(QWidget, BookmarkWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.Window)
        self.listWidget.contextMenuEvent = self.listWidget_context_menu_event
        self.listWidget.currentRowChanged.connect(self.change_display)
        self.listWidget.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.shortcut_delete = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete.activated.connect(self.delete_record)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        self.refresh_table()

    def refresh_table(self):
        self.listWidget.clear()
        for item in self.parent().tableWidget_Disassemble.bookmarks.keys():

            # FIXME: Implement and use optimized version of convert_address_to_symbol if performance issues occur
            current_text = GDB_Engine.convert_address_to_symbol(hex(item), include_address=True)
            if current_text is None:
                text_append = hex(item) + "(Unreachable)"
            else:
                text_append = current_text
            self.listWidget.addItem(text_append)

    def change_display(self):
        try:
            current_item = self.listWidget.currentItem().text()
        except AttributeError:
            return
        current_address = SysUtils.extract_address(current_item)
        self.lineEdit_Info.setText(GDB_Engine.get_info_about_address(current_address))
        self.lineEdit_Comment.setText(self.parent().tableWidget_Disassemble.bookmarks[int(current_address, 16)])

    def on_item_double_clicked(self, item):
        self.parent().disassemble_expression(SysUtils.extract_address(item.text()), append_to_travel_history=True)

    def listWidget_context_menu_event(self, event):
        if self.listWidget.count() != 0:
            current_item = self.listWidget.currentItem().text()
            current_address = int(SysUtils.extract_address(current_item), 16)
        else:
            current_item = None
            current_address = None
        if current_item is not None:
            if current_address not in self.parent().tableWidget_Disassemble.bookmarks:
                QMessageBox.information(self, "Error", "Invalid entries detected, refreshing the page")
                self.refresh_table()
                return
        menu = QMenu()
        add_entry = menu.addAction("Add new entry")
        if current_item is not None:
            change_comment = menu.addAction("Change comment of this record")
            delete_record = menu.addAction("Delete this record[Del]")
        else:
            change_comment = -1
            delete_record = -1
        menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        font_size = self.listWidget.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == add_entry:
            entry_dialog = DialogWithButtonsForm(label_text="Enter the expression", hide_line_edit=False)
            if entry_dialog.exec_():
                text = entry_dialog.get_values()
                address = GDB_Engine.convert_symbol_to_address(text)
                if address is None:
                    QMessageBox.information(self, "Error", "Invalid expression or address")
                    return
                self.parent().bookmark_address(int(address, 16))
                self.refresh_table()
        elif action == change_comment:
            self.parent().change_bookmark_comment(current_address)
            self.refresh_table()
        elif action == delete_record:
            self.delete_record()
        elif action == refresh:
            self.refresh_table()

    def delete_record(self):
        current_item = self.listWidget.currentItem().text()
        current_address = int(SysUtils.extract_address(current_item), 16)
        self.parent().delete_bookmark(current_address)
        self.refresh_table()


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
        register_dialog = DialogWithButtonsForm(label_text=label_text, hide_line_edit=False,
                                                line_edit_text=current_value)
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
        super().__init__(parent=parent)
        self.setupUi(self)
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
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ADDR_COL, QTableWidgetItem(item.address))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_TYPE_COL, QTableWidgetItem(item.breakpoint_type))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_SIZE_COL, QTableWidgetItem(str(item.size)))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ON_HIT_COL, QTableWidgetItem(item.on_hit))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_COND_COL, QTableWidgetItem(item.condition))
        self.tableWidget_BreakpointInfo.resizeColumnsToContents()
        self.tableWidget_BreakpointInfo.horizontalHeader().setStretchLastSection(True)
        self.textBrowser_BreakpointInfo.clear()
        self.textBrowser_BreakpointInfo.setText(GDB_Engine.send_command("info break", cli_output=True))

    def tableWidget_BreakpointInfo_key_press_event(self, event):
        try:
            selected_row = self.tableWidget_BreakpointInfo.selectionModel().selectedRows()[-1].row()
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
        except IndexError:
            current_address = None

        if event.key() == Qt.Key_Delete:
            if current_address is not None:
                self.delete_breakpoint(current_address)
        elif event.key() == Qt.Key_R:
            self.refresh()
        else:
            self.tableWidget_BreakpointInfo.keyPressEvent_original(event)

    def tableWidget_BreakpointInfo_context_menu_event(self, event):
        try:
            selected_row = self.tableWidget_BreakpointInfo.selectionModel().selectedRows()[-1].row()
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = SysUtils.extract_address(current_address_text)
            current_address_int = int(current_address, 16)
        except IndexError:
            current_address = None
            current_address_int = None

        menu = QMenu()
        if current_address is None:
            change_condition = -1
            delete_breakpoint = -1
        else:
            change_condition = menu.addAction("Change condition of this breakpoint")
            delete_breakpoint = menu.addAction("Delete this breakpoint[Del]")
            menu.addSeparator()
        refresh = menu.addAction("Refresh[R]")
        font_size = self.tableWidget_BreakpointInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == change_condition:
            self.change_condition(current_address_int)
        elif action == delete_breakpoint:
            self.delete_breakpoint(current_address)
        elif action == refresh:
            self.refresh()

    def change_condition(self, int_address):
        self.parent().add_breakpoint_condition(int_address)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def delete_breakpoint(self, address):
        GDB_Engine.delete_breakpoint(address)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def tableWidget_BreakpointInfo_double_clicked(self, index):
        current_address_text = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_ADDR_COL).text()
        current_address = SysUtils.extract_address(current_address_text)
        current_address_int = int(current_address, 16)

        if index.column() == BREAK_COND_COL:
            self.change_condition(current_address_int)
        else:
            current_breakpoint_type = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_TYPE_COL).text()
            if "breakpoint" in current_breakpoint_type:
                self.parent().disassemble_expression(current_address, append_to_travel_history=True)
            else:
                self.parent().hex_dump_address(current_address_int)


class TrackWatchpointWidgetForm(QWidget, TrackWatchpointWidget):
    def __init__(self, address, length, watchpoint_type, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
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
        GDB_Engine.delete_breakpoint(self.address)


class FunctionsInfoWidgetForm(QWidget, FunctionsInfoWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        self.setWindowFlags(Qt.Window)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_SymbolInfo.selectionModel().currentChanged.connect(self.tableWidget_SymbolInfo_current_changed)
        self.tableWidget_SymbolInfo.itemDoubleClicked.connect(self.tableWidget_SymbolInfo_item_double_clicked)
        self.tableWidget_SymbolInfo.contextMenuEvent = self.tableWidget_SymbolInfo_context_menu_event
        icons_directory = SysUtils.get_current_script_directory() + "/media/icons"
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)

    def refresh_table(self):
        input_text = self.lineEdit_SearchInput.text()
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(gdb_input=input_text)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec_()

    def process_data(self, gdb_input):
        return GDB_Engine.get_info_about_functions(gdb_input)

    def apply_data(self, output):
        self.tableWidget_SymbolInfo.setRowCount(0)
        self.tableWidget_SymbolInfo.setRowCount(len(output))
        for row, item in enumerate(output):
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_ADDR_COL, QTableWidgetItem(item.address))
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_SYMBOL_COL, QTableWidgetItem(item.symbol))
        self.tableWidget_SymbolInfo.resizeColumnsToContents()
        self.tableWidget_SymbolInfo.horizontalHeader().setStretchLastSection(True)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current):
        address = self.tableWidget_SymbolInfo.item(QModelIndex_current.row(), FUNCTIONS_INFO_ADDR_COL).text()
        info = GDB_Engine.get_info_about_address(address)
        self.lineEdit_AddressInfo.setText(info)

    def tableWidget_SymbolInfo_context_menu_event(self, event):
        selected_row = self.tableWidget_SymbolInfo.selectionModel().selectedRows()[-1].row()

        menu = QMenu()
        copy_address = menu.addAction("Copy Address")
        copy_symbol = menu.addAction("Copy Symbol")
        font_size = self.tableWidget_SymbolInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(event.globalPos())
        if action == copy_address:
            QApplication.clipboard().setText(
                self.tableWidget_SymbolInfo.item(selected_row, FUNCTIONS_INFO_ADDR_COL).text())
        elif action == copy_symbol:
            QApplication.clipboard().setText(
                self.tableWidget_SymbolInfo.item(selected_row, FUNCTIONS_INFO_SYMBOL_COL).text())

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
        DialogWithButtonsForm(label_text=text, align=Qt.AlignLeft).exec_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
