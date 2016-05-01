#!/usr/bin/python3
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QCheckBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from time import sleep, time
from threading import Thread
import os

import GuiUtils
import SysUtils
import GDB_Engine

from GUI.mainwindow import Ui_MainWindow as MainWindow
from GUI.selectprocess import Ui_MainWindow as ProcessWindow
from GUI.addaddressmanuallydialog import Ui_Dialog as ManualAddressDialog

# the PID of the process we'll attach to
currentpid = 0
selfpid = os.getpid()


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while SysUtils.is_process_valid(currentpid) or currentpid is 0:
            sleep(0.1)
        self.process_exited.emit()


# A thread that updates the address table constantly
class UpdateAddressTable(QThread):
    def __init__(self, pid):
        super().__init__()
        self.pid = pid

    def run(self):
        directory_path = "/tmp/PINCE/" + self.pid
        SysUtils.is_path_valid(directory_path, "create")
        send_file = directory_path + "/PINCE-to-Inferior.txt"
        recv_file = directory_path + "/Inferior-to-PINCE.txt"
        status_file = directory_path + "/status.txt"
        abort_file = directory_path + "/abort.txt"
        abort_verify_file = directory_path + "/abort-verify.txt"
        FILE = open(send_file, "w")
        FILE.close()
        FILE = open(recv_file, "w")
        FILE.close()
        FILE = open(status_file, "w")
        FILE.close()
        while True:
            status_word = "waiting"
            while status_word not in "sync-request-recieve":
                status = open(status_file, "r")
                status_word = status.read()
                status.close()
                try:
                    abort = open(abort_file, "r")
                    abort.close()
                    os.remove(abort_file)
                    abort_verify = open(abort_verify_file, "w")
                    abort_verify.close()
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
            print(readed)
            FILE.close()


# the mainwindow
class MainForm(QMainWindow, MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        GuiUtils.center(self)
        self.tableWidget_addresstable.setColumnWidth(0, 50)  # Frozen
        self.tableWidget_addresstable.setColumnWidth(1, 150)  # Description
        self.tableWidget_addresstable.setColumnWidth(2, 200)  # Address
        self.tableWidget_addresstable.setColumnWidth(3, 100)  # Type
        self.await_exit_thread = AwaitProcessExit()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.processbutton.clicked.connect(self.processbutton_onclick)
        self.pushButton_NewFirstScan.clicked.connect(self.newfirstscan_onclick)
        self.pushButton_NextScan.clicked.connect(self.nextscan_onclick)
        self.pushButton_AddAddressManually.clicked.connect(self.addaddressmanually_onclick)
        self.processbutton.setIcon(QIcon.fromTheme('computer'))
        self.pushButton_Open.setIcon(QIcon.fromTheme('document-open'))
        self.pushButton_Save.setIcon(QIcon.fromTheme('document-save'))
        self.pushButton_Settings.setIcon(QIcon.fromTheme('preferences-system'))
        self.pushButton_CopyToAddressList.setIcon(QIcon.fromTheme('emblem-downloads'))
        self.pushButton_CleanAddressList.setIcon(QIcon.fromTheme('user-trash'))

    # communicates with the inferior via a file and reads the values from it
    def update_address_table(pid):
        directory_path = "/tmp/PINCE/" + pid
        SysUtils.is_path_valid(directory_path, "create")
        file_send = open(directory_path + "/PINCE-to-Inferior", "w")
        sleep(0.5)
        file_recv = open(directory_path + "/Inferior-to-PINCE", "r")
        file_send.write("0")
        file_recv.close()
        file_send.close()
        SysUtils.do_cleanups(pid)

    # gets the information from the dialog then adds it to addresstable
    def addaddressmanually_onclick(self):
        self.manual_address_dialog = ManualAddressDialogForm()
        if self.manual_address_dialog.exec_():
            description, address, typeofaddress = self.manual_address_dialog.getvalues()
            self.add_element_to_addresstable(description, address, typeofaddress)

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
        t0 = time()
        print(GDB_Engine.send_command("source IPC/ScriptUtils.py"))
        t1 = time()
        print(t1 - t0)
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

    def on_inferior_exit(self):
        global currentpid
        GDB_Engine.detach()
        currentpid = 0
        self.label_SelectedProcess.setText("No Process Selected")
        QMessageBox.information(self, "Warning", "Process has been terminated")
        self.await_exit_thread.start()

    # closes all windows on exit
    def closeEvent(self, event):
        if not currentpid == 0:
            GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    def add_element_to_addresstable(self, description, address, typeofaddress):
        frozen_checkbox = QCheckBox()
        typeofaddress = GuiUtils.valuetype_to_text(typeofaddress)

        # this line lets us take symbols as parameters, pretty rad isn't?
        # warning: if you pass an actual symbol to the function below in a long for loop, it slows the process down significantly
        address = GDB_Engine.convert_symbol_to_address(address)
        self.tableWidget_addresstable.setRowCount(self.tableWidget_addresstable.rowCount() + 1)
        currentrow = self.tableWidget_addresstable.rowCount() - 1
        self.tableWidget_addresstable.setCellWidget(currentrow, 0, frozen_checkbox)
        self.tableWidget_addresstable.setItem(currentrow, 1, QTableWidgetItem(description))
        self.tableWidget_addresstable.setItem(currentrow, 2, QTableWidgetItem(address))
        self.tableWidget_addresstable.setItem(currentrow, 3, QTableWidgetItem(typeofaddress))


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_parent(self)
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
            print("processing")  # progressbar start
            result = GDB_Engine.can_attach(str(pid))
            if not result:
                print("done")  # progressbar finish
                QMessageBox.information(self, "Error", "Permission denied, could not attach to the process")
                return
            if not currentpid == 0:
                GDB_Engine.detach()
            currentpid = pid
            is_thread_injection_successful = GDB_Engine.attach(str(currentpid))
            p = SysUtils.get_process_information(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            self.parent().pushButton_NextScan.setEnabled(False)
            self.parent().pushButton_UndoScan.setEnabled(False)
            readable_only, writeable, executable, readable = SysUtils.get_memory_regions_by_perms(currentpid)  # test
            SysUtils.exclude_system_memory_regions(readable)
            print(len(readable))
            print("done")  # progressbar finish
            if not is_thread_injection_successful:
                QMessageBox.information(self, "Warning", "Unable to inject threads, PINCE may(will) not work properly")
            self.close()


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.label_length.hide()
        self.lineEdit_length.hide()
        self.checkBox_Unicode.hide()
        self.checkBox_zeroterminate.hide()
        self.comboBox_ValueType.currentIndexChanged.connect(self.valuetype_on_current_index_change)
        self.lineEdit_length.textChanged.connect(self.length_text_on_change)
        self.checkBox_Unicode.stateChanged.connect(self.unicode_box_on_check)
        self.checkBox_zeroterminate.stateChanged.connect(self.zeroterminate_box_on_check)
        self.update_needed = False
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
                if address_type is 7:
                    length = self.lineEdit_length.text()
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type, length))
                elif address_type is 6:
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
        if self.comboBox_ValueType.currentIndex() == 6:  # if index points to string
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() == 7:  # if index points to array of bytes
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
        self.update_thread._is_stopped = True
        super(ManualAddressDialogForm, self).accept()

    def getvalues(self):
        description = self.lineEdit_description.text()
        address = self.lineEdit_address.text()
        typeofaddress = self.comboBox_ValueType.currentIndex()
        return description, address, typeofaddress


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
