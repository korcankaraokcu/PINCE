#!/usr/bin/python3
from PyQt5.QtGui import QIcon, QMovie, QPixmap, QCursor
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QDialog, QCheckBox, QWidget
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray
from time import sleep, time
from threading import Thread
import os
import pickle

import GuiUtils
import SysUtils
import GDB_Engine
import type_defs

from GUI.mainwindow import Ui_MainWindow as MainWindow
from GUI.selectprocess import Ui_MainWindow as ProcessWindow
from GUI.addaddressmanuallydialog import Ui_Dialog as ManualAddressDialog
from GUI.loadingwidget import Ui_Form as LoadingWidget
from GUI.dialogwithbuttons import Ui_Dialog as DialogWithButtons

# the PID of the process we'll attach to
currentpid = 0
selfpid = os.getpid()

FROZEN_COL = type_defs.FROZEN_COL
DESC_COL = type_defs.DESC_COL
ADDR_COL = type_defs.ADDR_COL
TYPE_COL = type_defs.TYPE_COL
VALUE_COL = type_defs.VALUE_COL

COMBOBOX_BYTE = type_defs.COMBOBOX_BYTE
COMBOBOX_2BYTES = type_defs.COMBOBOX_2BYTES
COMBOBOX_4BYTES = type_defs.COMBOBOX_4BYTES
COMBOBOX_8BYTES = type_defs.COMBOBOX_8BYTES
COMBOBOX_FLOAT = type_defs.COMBOBOX_FLOAT
COMBOBOX_DOUBLE = type_defs.COMBOBOX_DOUBLE
COMBOBOX_STRING = type_defs.COMBOBOX_STRING
COMBOBOX_AOB = type_defs.COMBOBOX_AOB


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

    # communicates with the inferior via files and reads the values from them
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
        self.tableWidget_addresstable.setColumnWidth(TYPE_COL, 100)
        self.await_exit_thread = AwaitProcessExit()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        self.processbutton.clicked.connect(self.processbutton_onclick)
        self.pushButton_NewFirstScan.clicked.connect(self.newfirstscan_onclick)
        self.pushButton_NextScan.clicked.connect(self.nextscan_onclick)
        self.pushButton_AddAddressManually.clicked.connect(self.addaddressmanually_onclick)
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

    def update_address_table_manually(self):
        table_contents_send = []
        row_count = self.tableWidget_addresstable.rowCount()
        for row in range(row_count):
            address = self.tableWidget_addresstable.item(row, ADDR_COL).text()
            value_type = self.tableWidget_addresstable.item(row, TYPE_COL).text()
            table_contents_send.append([address, value_type])
        directory_path = SysUtils.get_PINCE_IPC_directory(currentpid)
        send_file = directory_path + "/address-table-from-PINCE.txt"
        recv_file = directory_path + "/address-table-to-PINCE.txt"
        open(recv_file, "w").close()
        pickle.dump(table_contents_send, open(send_file, "wb"))
        GDB_Engine.send_command("pince-update-address-table")
        table_contents_recv = pickle.load(open(recv_file, "rb"))
        for row, item in enumerate(table_contents_recv):
            self.tableWidget_addresstable.setItem(row, VALUE_COL, QTableWidgetItem(str(item)))

    # gets the information from the dialog then adds it to addresstable
    def addaddressmanually_onclick(self):
        manual_address_dialog = ManualAddressDialogForm()
        if manual_address_dialog.exec_():
            description, address, typeofaddress, length, unicode, zero_terminate = manual_address_dialog.getvalues()
            self.add_element_to_addresstable(description, address, typeofaddress, length, unicode,
                                             zero_terminate)

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
        GDB_Engine.send_command('x _start')  # test
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

    # closes all windows on exit
    def closeEvent(self, event):
        if not currentpid == 0:
            GDB_Engine.detach()
        application = QApplication.instance()
        application.closeAllWindows()

    # FIXME: calling this function in a long for loop slows the process down significantly
    def add_element_to_addresstable(self, description, address, typeofaddress, length=0, unicode=False,
                                    zero_terminate=True):
        frozen_checkbox = QCheckBox()
        typeofaddress_text = GuiUtils.valuetype_to_text(typeofaddress, length, unicode, zero_terminate)

        # this line lets us take symbols as parameters, pretty rad isn't it?
        # TODO: Implement a loop-version of convert_symbol_to_address
        address = GDB_Engine.convert_symbol_to_address(address)
        self.tableWidget_addresstable.setRowCount(self.tableWidget_addresstable.rowCount() + 1)
        currentrow = self.tableWidget_addresstable.rowCount() - 1
        self.tableWidget_addresstable.setCellWidget(currentrow, FROZEN_COL, frozen_checkbox)
        self.tableWidget_addresstable.setItem(currentrow, DESC_COL, QTableWidgetItem(description))
        self.tableWidget_addresstable.setItem(currentrow, ADDR_COL, QTableWidgetItem(address))
        self.tableWidget_addresstable.setItem(currentrow, TYPE_COL, QTableWidgetItem(typeofaddress_text))

        # TODO: Implement a loop-version of read_value_from_single_address
        value = GDB_Engine.read_value_from_single_address(address, typeofaddress, length, unicode, zero_terminate)
        self.tableWidget_addresstable.setItem(currentrow, VALUE_COL, QTableWidgetItem(value))

    def on_address_table_double_click(self, index):
        manual_address_dialog = ManualAddressDialogForm()
        if index.column() is VALUE_COL:
            print("ehuehue")
        else:
            if manual_address_dialog.exec_():
                print("asdf")


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        GuiUtils.center_to_parent(self)
        self.loadingwidget = LoadingWidgetForm()
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
            self.setCentralWidget(self.loadingwidget)
            self.loadingwidget.show()
            print("processing")  # loading_widget start
            result = GDB_Engine.can_attach(str(pid))
            if not result:
                print("done")  # loading_widget finish
                QMessageBox.information(self, "Error", "Permission denied, could not attach to the process")
                return
            if not currentpid == 0:
                GDB_Engine.detach()
            currentpid = pid
            thread_injection_successful = GDB_Engine.attach(str(currentpid))
            p = SysUtils.get_process_information(currentpid)
            self.parent().label_SelectedProcess.setText(str(p.pid) + " - " + p.name())
            self.parent().QWidget_Toolbox.setEnabled(True)
            self.parent().pushButton_NextScan.setEnabled(False)
            self.parent().pushButton_UndoScan.setEnabled(False)
            readable_only, writeable, executable, readable = SysUtils.get_memory_regions_by_perms(currentpid)  # test
            SysUtils.exclude_system_memory_regions(readable)
            print(len(readable))
            print("done")  # loading_widget finish
            if not thread_injection_successful:
                QMessageBox.information(self, "Warning",
                                        "Unable to inject threads, following features has been disabled:" +
                                        "\nPINCE non-stop mode" +
                                        "\nContinuous Address Table Update" +
                                        "\nVariable Locking")
            self.loadingwidget.hide()
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
                if address_type is COMBOBOX_AOB:
                    length = self.lineEdit_length.text()
                    self.label_valueofaddress.setText(GDB_Engine.read_single_address(address, address_type, length))
                elif address_type is COMBOBOX_STRING:
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
        if self.comboBox_ValueType.currentIndex() == COMBOBOX_STRING:
            self.label_length.show()
            self.lineEdit_length.show()
            self.checkBox_Unicode.show()
            self.checkBox_zeroterminate.show()
        elif self.comboBox_ValueType.currentIndex() == COMBOBOX_AOB:
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
        length = self.lineEdit_length.text()
        try:
            length = int(length)
        except:
            QMessageBox.information(self, "Error", "Length is not valid")
            return
        self.length = length
        self.update_thread._is_stopped = True
        super(ManualAddressDialogForm, self).accept()

    def getvalues(self):
        description = self.lineEdit_description.text()
        address = self.lineEdit_address.text()
        unicode = False
        zero_terminate = False
        if self.checkBox_Unicode.isChecked():
            unicode = True
        if self.checkBox_zeroterminate.isChecked():
            zero_terminate = True
        typeofaddress = self.comboBox_ValueType.currentIndex()
        return description, address, typeofaddress, self.length, unicode, zero_terminate


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
    def __init__(self, parent=None, label_text=""):
        super().__init__(parent=parent)
        self.setupUi(self)
        label_text = str(label_text)
        self.label.setText(label_text)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = MainForm()
    window.show()
    sys.exit(app.exec_())
