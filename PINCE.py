#!/usr/bin/python3
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QCursor, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QCheckBox, QWidget, \
    QShortcut, QKeySequenceEdit, QTabWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray, QSettings, QCoreApplication
from time import sleep
from threading import Thread
import os
import webbrowser

import GuiUtils
import SysUtils
import GDB_Engine
import type_defs

from GUI.mainwindow import Ui_MainWindow as MainWindow
from GUI.selectprocess import Ui_MainWindow as ProcessWindow
from GUI.addaddressmanuallydialog import Ui_Dialog as ManualAddressDialog
from GUI.loadingwidget import Ui_Form as LoadingWidget
from GUI.dialogwithbuttons import Ui_Dialog as DialogWithButtons
from GUI.settingsdialog import Ui_Dialog as SettingsDialog
from GUI.consolewidget import Ui_Form as ConsoleWidget
from GUI.aboutwidget import Ui_TabWidget as AboutWidget
from GUI.memoryviewerwindow import Ui_MainWindow as MemoryViewWindow

# the PID of the process we'll attach to
currentpid = 0
selfpid = os.getpid()

# settings
update_table = bool
table_update_interval = float
pause_hotkey = str
continue_hotkey = str
initial_code_injection_method = int

FROZEN_COL = type_defs.FROZEN_COL
DESC_COL = type_defs.DESC_COL
ADDR_COL = type_defs.ADDR_COL
TYPE_COL = type_defs.TYPE_COL
VALUE_COL = type_defs.VALUE_COL

INDEX_BYTE = type_defs.INDEX_BYTE
INDEX_2BYTES = type_defs.INDEX_2BYTES
INDEX_4BYTES = type_defs.INDEX_4BYTES
INDEX_8BYTES = type_defs.INDEX_8BYTES
INDEX_FLOAT = type_defs.INDEX_FLOAT
INDEX_DOUBLE = type_defs.INDEX_DOUBLE
INDEX_STRING = type_defs.INDEX_STRING
INDEX_AOB = type_defs.INDEX_AOB

DISAS_ADDR_COL = type_defs.DISAS_ADDR_COL
DISAS_BYTES_COL = type_defs.DISAS_BYTES_COL
DISAS_OPCODES_COL = type_defs.DISAS_OPCODES_COL
DISAS_COMMENT_COL = type_defs.DISAS_COMMENT_COL

INFERIOR_STOPPED = type_defs.INFERIOR_STOPPED
INFERIOR_RUNNING = type_defs.INFERIOR_RUNNING

NO_INJECTION = type_defs.NO_INJECTION
SIMPLE_DLOPEN_CALL = type_defs.SIMPLE_DLOPEN_CALL
LINUX_INJECT = type_defs.LINUX_INJECT

INJECTION_SUCCESSFUL = type_defs.INJECTION_SUCCESSFUL
INJECTION_FAILED = type_defs.INJECTION_FAILED
NO_INJECTION_ATTEMPT = type_defs.NO_INJECTION_ATTEMPT


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while currentpid is 0 or SysUtils.is_process_valid(currentpid):
            sleep(0.01)
        self.process_exited.emit()


# Await async output from gdb
class AwaitAsyncOutput(QThread):
    async_output_ready = pyqtSignal()

    def run(self):
        while True:
            with GDB_Engine.gdb_async_condition:
                GDB_Engine.gdb_async_condition.wait()
            self.async_output_ready.emit()


class CheckInferiorStatus(QThread):
    status_stopped = pyqtSignal()
    status_running = pyqtSignal()
    current_status = INFERIOR_RUNNING

    def run(self):
        while True:
            if self.current_status is not GDB_Engine.inferior_status:
                if GDB_Engine.inferior_status is INFERIOR_STOPPED:
                    self.status_stopped.emit()
                else:
                    self.status_running.emit()
                self.current_status = GDB_Engine.inferior_status
            sleep(0.01)


class UpdateAddressTableThread(QThread):
    update_table_signal = pyqtSignal()

    def run(self):
        while True:
            while not update_table:
                sleep(0.1)
            if GDB_Engine.inferior_status is INFERIOR_STOPPED:
                self.update_table_signal.emit()
            sleep(table_update_interval)


# A thread that updates the address table constantly
# planned for future
class UpdateAddressTable_planned(QThread):
    def __init__(self, pid):
        super().__init__()
        self.pid = pid

    # communicates with the inferior via files and reads the values from them
    # planned for future
    def run(self):
        SysUtils.do_cleanups(self.pid)
        directory_path = SysUtils.get_PINCE_IPC_directory(self.pid)
        SysUtils.is_path_valid(directory_path, "create")
        send_file = directory_path + "/PINCE-to-Inferior.txt"
        recv_file = directory_path + "/Inferior-to-PINCE.txt"
        status_file = directory_path + "/status.txt"
        abort_file = directory_path + "/abort.txt"
        open(send_file, "w").close()
        open(recv_file, "w").close()
        FILE = open(status_file, "w")

        # Inferior will try to check PINCE's presence with this information
        FILE.write(str(selfpid))
        FILE.close()
        SysUtils.fix_path_permissions(send_file)
        SysUtils.fix_path_permissions(recv_file)
        SysUtils.fix_path_permissions(status_file)
        while True:
            sleep(0.01)
            status_word = "waiting"
            while status_word not in "sync-request-recieve":
                sleep(0.01)
                status = open(status_file, "r")
                status_word = status.read()
                status.close()
                try:
                    abort = open(abort_file, "r")
                    abort.close()
                    return
                except:
                    pass
            status = open(status_file, "w")
            status.write("sync-request-send")
            status.close()
            FILE = open(send_file, "w")
            FILE.close()
            FILE = open(recv_file, "r")
            readed = FILE.read()
            # print(readed)
            FILE.close()


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
        self.apply_settings()
        self.await_exit_thread = AwaitProcessExit()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.check_status_thread = CheckInferiorStatus()
        self.check_status_thread.status_stopped.connect(self.on_status_stopped)
        self.check_status_thread.status_running.connect(self.on_status_running)
        self.check_status_thread.start()
        self.update_address_table_thread = UpdateAddressTableThread()
        self.update_address_table_thread.update_table_signal.connect(self.update_address_table_manually)
        self.update_address_table_thread.start()
        self.shortcut_pause = QShortcut(QKeySequence(pause_hotkey), self)
        self.shortcut_pause.activated.connect(self.pause_hotkey_pressed)
        self.shortcut_continue = QShortcut(QKeySequence(continue_hotkey), self)
        self.shortcut_continue.activated.connect(self.continue_hotkey_pressed)
        self.tableWidget_addresstable.keyPressEvent = self.tableWidget_addresstable_keyPressEvent
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
        self.settings.setValue("always_on_top", False)
        self.settings.setValue("auto_update_address_table", True)
        self.settings.setValue("address_table_update_interval", 0.5)
        self.settings.endGroup()
        self.settings.beginGroup("Hotkeys")
        self.settings.setValue("pause", "F2")
        self.settings.setValue("continue", "F3")
        self.settings.endGroup()
        self.settings.beginGroup("CodeInjection")
        self.settings.setValue("initial_code_injection_method", SIMPLE_DLOPEN_CALL)
        self.settings.endGroup()

    def apply_settings(self):
        if self.settings.value("General/always_on_top", type=bool):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()
        global update_table
        global table_update_interval
        global pause_hotkey
        global continue_hotkey
        global initial_code_injection_method
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
        initial_code_injection_method = self.settings.value("CodeInjection/initial_code_injection_method", type=int)

    def pause_hotkey_pressed(self):
        GDB_Engine.interrupt_inferior()

    def continue_hotkey_pressed(self):
        GDB_Engine.continue_inferior()

    # I don't know if this is some kind of retarded hack
    def tableWidget_addresstable_keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            selected_rows = self.tableWidget_addresstable.selectionModel().selectedRows()
            for item in selected_rows:
                self.tableWidget_addresstable.removeRow(item.row())

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
            self.add_element_to_addresstable(description=description, address=address, typeofaddress=typeofaddress,
                                             length=length, unicode=unicode,
                                             zero_terminate=zero_terminate)

    def memoryview_onlick(self):
        try:
            self.memory_view_window.show()
        except AttributeError:
            self.memory_view_window = MemoryViewWindowForm()
            self.memory_view_window.show()
        self.memory_view_window.activateWindow()

    def wikibutton_onclick(self):
        webbrowser.open("https://github.com/korcankaraokcu/PINCE/wiki")

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
        confirm_dialog = DialogWithButtonsForm(label_text="This will clear the contents of address table\n\tProceed?")
        if confirm_dialog.exec_():
            self.tableWidget_addresstable.setRowCount(0)

    def on_inferior_exit(self):
        global currentpid
        GDB_Engine.detach()
        currentpid = 0
        self.label_SelectedProcess.setText("No Process Selected")
        QMessageBox.information(self, "Warning", "Process has been terminated")
        self.await_exit_thread.start()

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
        if not currentpid == 0:
            GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    def add_element_to_addresstable(self, description, address, typeofaddress, length=0, unicode=False,
                                    zero_terminate=True):
        frozen_checkbox = QCheckBox()
        typeofaddress_text = GuiUtils.valuetype_to_text(typeofaddress, length, unicode, zero_terminate)

        # this line lets us take symbols as parameters, pretty rad isn't it?
        address = GDB_Engine.convert_symbol_to_address(address)
        self.tableWidget_addresstable.setRowCount(self.tableWidget_addresstable.rowCount() + 1)
        currentrow = self.tableWidget_addresstable.rowCount() - 1
        value = GDB_Engine.read_value_from_single_address(address, typeofaddress, length, unicode, zero_terminate)
        self.tableWidget_addresstable.setCellWidget(currentrow, FROZEN_COL, frozen_checkbox)
        self.change_address_table_elements(row=currentrow, description=description, address=address,
                                           typeofaddress=typeofaddress_text, value=value)

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
                    if GuiUtils.text_to_length(value_type) is not -1:
                        unknown_type = SysUtils.parse_string(value_text, value_index)[1]
                        length = len(unknown_type)
                        self.tableWidget_addresstable.setItem(row, TYPE_COL, QTableWidgetItem(
                            GuiUtils.change_text_length(value_type, length)))
                    table_contents.append([address, value_index])
                table_contents.append(value_text)
                GDB_Engine.set_multiple_addresses(table_contents)
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
            description, address, value_type = self.read_address_table_elements(row=current_row)
            index, length, unicode, zero_terminate = GuiUtils.text_to_valuetype(value_type)
            manual_address_dialog = ManualAddressDialogForm(description=description, address=address, index=index,
                                                            length=length, unicode=unicode,
                                                            zero_terminate=zero_terminate)
            if manual_address_dialog.exec_():
                description, address, typeofaddress, length, unicode, zero_terminate = manual_address_dialog.get_values()
                typeofaddress_text = GuiUtils.valuetype_to_text(index=typeofaddress, length=length, unicode=unicode,
                                                                zero_terminate=zero_terminate)
                address = GDB_Engine.convert_symbol_to_address(address)
                value = GDB_Engine.read_value_from_single_address(address=address, typeofaddress=typeofaddress,
                                                                  length=length, unicode=unicode,
                                                                  zero_terminate=zero_terminate)
                self.change_address_table_elements(row=current_row, description=description, address=address,
                                                   typeofaddress=typeofaddress_text, value=value)

    # Changes the column values of the given row
    def change_address_table_elements(self, row, description="", address="", typeofaddress="", value=""):
        self.tableWidget_addresstable.setItem(row, DESC_COL, QTableWidgetItem(description))
        self.tableWidget_addresstable.setItem(row, ADDR_COL, QTableWidgetItem(address))
        self.tableWidget_addresstable.setItem(row, TYPE_COL, QTableWidgetItem(typeofaddress))
        self.tableWidget_addresstable.setItem(row, VALUE_COL, QTableWidgetItem(value))

    # Returns the column values of the given row
    def read_address_table_elements(self, row):
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
        # self.loadingwidget = LoadingWidgetForm()
        processlist = SysUtils.get_process_list()
        self.refresh_process_table(self.processtable, processlist)
        self.pushButton_Close.clicked.connect(self.pushbutton_close_onclick)
        self.pushButton_Open.clicked.connect(self.pushbutton_open_onclick)
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

    # gets the pid out of the selection to set currentpid
    def pushbutton_open_onclick(self):
        global currentpid
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
            if pid == currentpid:
                QMessageBox.information(self, "Error", "You're debugging this process already")
                return
            tracedby = SysUtils.is_traced(pid)
            if tracedby:
                QMessageBox.information(self, "Error",
                                        "That process is already being traced by " + tracedby + ", could not attach to the process")
                return
            self.setCursor(QCursor(Qt.WaitCursor))
            # self.setCentralWidget(self.loadingwidget)
            # self.loadingwidget.show()
            print("processing")  # loading_widget start
            result = GDB_Engine.can_attach(str(pid))
            if not result:
                print("done")  # loading_widget finish
                QMessageBox.information(self, "Error", "Permission denied, could not attach to the process")
                return
            if not currentpid == 0:
                GDB_Engine.detach()
            currentpid = pid
            code_injection_status = GDB_Engine.attach(str(currentpid), initial_code_injection_method)
            p = SysUtils.get_process_information(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            self.parent().pushButton_NextScan.setEnabled(False)
            self.parent().pushButton_UndoScan.setEnabled(False)
            readable_only, writeable, executable, readable = SysUtils.get_memory_regions_by_perms(currentpid)  # test
            SysUtils.exclude_system_memory_regions(readable)
            print(len(readable))
            print("done")  # loading_widget finish
            # if not thread_injection_successful:
            #    QMessageBox.information(self, "Warning",
            #                            "Unable to inject threads, following features has been disabled:" +
            #                            "\nPINCE non-stop mode" +
            #                            "\nContinuous Address Table Update" +
            #                            "\nVariable Locking")
            if code_injection_status is INJECTION_FAILED:
                QMessageBox.information(self, "Warning", "Couldn't inject the .so file")
            # self.loadingwidget.hide()
            self.close()


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent=None, description="No Description", address="0x", index=INDEX_4BYTES, length=10,
                 unicode=False,
                 zero_terminate=True):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.lineEdit_description.setText(description)
        self.lineEdit_address.setText(address)
        self.comboBox_ValueType.setCurrentIndex(index)
        if self.comboBox_ValueType.currentIndex() is INDEX_STRING:
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
        elif self.comboBox_ValueType.currentIndex() is INDEX_AOB:
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
        self.lineEdit_length.textChanged.connect(self.length_text_on_change)
        self.checkBox_Unicode.stateChanged.connect(self.unicode_box_on_check)
        self.checkBox_zeroterminate.stateChanged.connect(self.zeroterminate_box_on_check)
        self.update_needed = True
        self.lineEdit_address.textChanged.connect(self.address_on_change)
        self.update_thread = Thread(target=self.update_value_of_address)
        self.update_thread.daemon = True
        self.update_thread.start()

    # constantly updates the value of the address
    def update_value_of_address(self):
        while not self.update_thread._is_stopped:
            sleep(0.01)
            if self.update_needed:
                self.update_needed = False
                address = self.lineEdit_address.text()
                address_type = self.comboBox_ValueType.currentIndex()
                if address_type is INDEX_AOB:
                    length = self.lineEdit_length.text()
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type, length))
                elif address_type is INDEX_STRING:
                    length = self.lineEdit_length.text()
                    is_unicode = self.checkBox_Unicode.isChecked()
                    is_zeroterminate = self.checkBox_zeroterminate.isChecked()
                    self.label_valueofaddress.setText(
                        GDB_Engine.read_single_address(address, address_type, length, is_unicode, is_zeroterminate))
                else:
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type))

    def address_on_change(self):
        self.update_needed = True

    def length_text_on_change(self):
        self.update_needed = True

    def unicode_box_on_check(self):
        self.update_needed = True

    def zeroterminate_box_on_check(self):
        self.update_needed = True

    def valuetype_on_current_index_change(self):
        if self.comboBox_ValueType.currentIndex() is INDEX_STRING:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() is INDEX_AOB:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.hide()
            self.checkBox_zeroterminate.hide()
        else:
            self.label_length.hide()
            self.lineEdit_length.hide()
            self.checkBox_Unicode.hide()
            self.checkBox_zeroterminate.hide()
        self.update_needed = True

    def reject(self):
        self.update_thread._is_stopped = True
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
        self.update_thread._is_stopped = True
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


# FIXME: the gif in qlabel won't update itself, also the design of this class is generally shitty
# FIXME: this class is temporary and buggy, so all implementations of this shit should be fixed as soon as this class gets fixed
# I designed(sorry) this as a widget, but you can transform it to anything if it's going to fix the gif problem
class LoadingWidgetForm(QWidget, LoadingWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        pince_directory = SysUtils.get_current_script_directory()
        self.movie = QMovie(pince_directory + "/media/loading_widget_gondola.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(50, 50))
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.not_finished = True
        # self.update_thread = Thread(target=self.update_widget)
        # self.update_thread.daemon = True
        # self.movie.frameChanged.connect(self.update_shit)
        # self.loading_thread = LoadingWindowThread()
        # self.loading_thread.update_needed.connect(QApplication.processEvents)

    def showEvent(self, QShowEvent):  # from here
        QApplication.processEvents()
        # self.update_thread.start()

    def hideEvent(self, QHideEvent):
        self.not_finished = False

    def update_widget(self):
        while self.not_finished:
            QApplication.processEvents()

    def change_text(self, text):
        self.label_StatusText.setText(text)
        QApplication.processEvents()


class LoadingWindowThread(QThread):
    not_finished = True
    update_needed = pyqtSignal()

    def run(self):
        while self.not_finished:
            sleep(0.001)
            self.update_needed.emit()  # to here should be reworked


class DialogWithButtonsForm(QDialog, DialogWithButtons):
    def __init__(self, parent=None, label_text="", hide_line_edit=True, line_edit_text="", parse_string=False,
                 value_index=INDEX_4BYTES):
        super().__init__(parent=parent)
        self.setupUi(self)
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
            if not SysUtils.parse_string(string, self.value_index)[0]:
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
        self.listWidget_Functions.currentRowChanged.connect(self.on_hotkey_index_change)
        self.keySequenceEdit.keySequenceChanged.connect(self.on_key_sequence_change)
        self.pushButton_ClearHotkey.clicked.connect(self.on_clear_button_pressed)
        self.pushButton_ResetSettings.clicked.connect(self.on_reset_button_pressed)
        self.config_gui()

    def accept(self):
        try:
            current_table_update_interval = float(self.lineEdit_UpdateInterval.text())
        except:
            QMessageBox.information(self, "Error", "Update interval must be a float")
            return
        if current_table_update_interval < 0:
            QMessageBox.information(self, "Error", "Update interval cannot be a negative number")
            return
        elif current_table_update_interval == 0:

            # Easter egg #2
            if not DialogWithButtonsForm(self, label_text="You are asking for it, aren't you?").exec_():
                return
        elif current_table_update_interval < 0.1:
            if not DialogWithButtonsForm(self, label_text="Update interval should be bigger than 0.1 seconds" +
                    "\nSetting update interval less than 0.1 seconds may cause slowness" +
                    "\n\tProceed?").exec_():
                return
        self.settings.setValue("General/always_on_top", self.checkBox_AlwaysOnTop.isChecked())
        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        self.settings.setValue("General/address_table_update_interval", current_table_update_interval)
        self.settings.setValue("Hotkeys/pause", self.pause_hotkey)
        self.settings.setValue("Hotkeys/continue", self.continue_hotkey)
        if self.radioButton_SimpleDLopenCall.isChecked():
            injection_method = SIMPLE_DLOPEN_CALL
        elif self.radioButton_LinuxInject.isChecked():
            injection_method = LINUX_INJECT
        self.settings.setValue("CodeInjection/initial_code_injection_method", injection_method)
        super(SettingsDialogForm, self).accept()

    def config_gui(self):
        self.settings = QSettings()
        if self.settings.value("General/always_on_top", type=bool):
            self.checkBox_AlwaysOnTop.setChecked(True)
        else:
            self.checkBox_AlwaysOnTop.setChecked(False)
        if self.settings.value("General/auto_update_address_table", type=bool):
            self.checkBox_AutoUpdateAddressTable.setChecked(True)
        else:
            self.checkBox_AutoUpdateAddressTable.setChecked(False)
        self.lineEdit_UpdateInterval.setText(
            str(self.settings.value("General/address_table_update_interval", type=float)))
        self.pause_hotkey = self.settings.value("Hotkeys/pause")
        self.continue_hotkey = self.settings.value("Hotkeys/continue")
        injection_method = self.settings.value("CodeInjection/initial_code_injection_method", type=int)
        if injection_method == SIMPLE_DLOPEN_CALL:
            self.radioButton_SimpleDLopenCall.setChecked(True)
        elif injection_method == LINUX_INJECT:
            self.radioButton_LinuxInject.setChecked(True)

    def change_display(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def on_hotkey_index_change(self, index):
        if index is 0:
            self.keySequenceEdit.setKeySequence(self.pause_hotkey)
        elif index is 1:
            self.keySequenceEdit.setKeySequence(self.continue_hotkey)

    def on_key_sequence_change(self):
        current_index = self.listWidget_Functions.currentIndex().row()
        if current_index is 0:
            self.pause_hotkey = self.keySequenceEdit.keySequence().toString()
        elif current_index is 1:
            self.continue_hotkey = self.keySequenceEdit.keySequence().toString()

    def on_clear_button_pressed(self):
        self.keySequenceEdit.clear()

    def on_reset_button_pressed(self):
        confirm_dialog = DialogWithButtonsForm(label_text="This will reset to the default settings\n\tProceed?")
        if confirm_dialog.exec_():
            self.reset_settings.emit()
        else:
            return
        self.config_gui()


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
                console_output = GDB_Engine.send_command(console_input)
                if console_output == None:
                    console_output = "Inferior is running"
            else:
                GDB_Engine.interrupt_inferior()
                console_output = "STOPPED"
        self.textBrowser.append("-->" + console_input)
        self.textBrowser.append(console_output)

    def on_async_output(self):
        self.textBrowser.append(GDB_Engine.gdb_async_output)
        self.textBrowser.verticalScrollBar().setValue(self.textBrowser.verticalScrollBar().maximum())


class AboutWidgetForm(QTabWidget, AboutWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        license_text = open("LICENSE.md").read()
        contributors_text = open("CONTRIBUTORS.txt").read()
        self.textBrowser_License.setPlainText(license_text)
        self.textBrowser_Contributors.setPlainText(contributors_text)


class MemoryViewWindowForm(QMainWindow, MemoryViewWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center(self)
        disas_data = GDB_Engine.disassemble("_start", "+600")
        self.tableWidget_Disassemble.setRowCount(0)
        self.tableWidget_Disassemble.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            self.tableWidget_Disassemble.setItem(row, DISAS_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Disassemble.setItem(row, DISAS_BYTES_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Disassemble.setItem(row, DISAS_OPCODES_COL, QTableWidgetItem(item[2]))
        self.tableWidget_Disassemble.resizeColumnsToContents()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
