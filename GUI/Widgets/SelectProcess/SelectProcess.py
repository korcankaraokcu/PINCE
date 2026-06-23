from PyQt6.QtWidgets import QMainWindow, QWidget, QTableWidget, QTableWidgetItem, QMessageBox, QFileDialog
from PyQt6.QtGui import QKeyEvent, QCursor
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.SelectProcess.Form.SelectProcess import Ui_MainWindow
from libpince import utils
from tr.tr import TranslationConstants as tr
import os


class SelectProcessWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
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
    def generate_new_list(self) -> None:
        text = self.lineEdit_SearchProcess.text()
        processlist = utils.search_processes(text)
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.pushButton_Open_clicked()
        elif event.key() == Qt.Key.Key_F1:
            self.pushButton_CreateProcess_clicked()
        else:
            return super().keyPressEvent(event)

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget: QTableWidget, processlist: list[tuple[str, str, str]]) -> None:
        tablewidget.setRowCount(0)
        for pid, user, name in processlist:
            current_row = tablewidget.rowCount()
            tablewidget.insertRow(current_row)
            tablewidget.setItem(current_row, 0, QTableWidgetItem(pid))
            tablewidget.setItem(current_row, 1, QTableWidgetItem(user))
            tablewidget.setItem(current_row, 2, QTableWidgetItem(name))

    # gets the pid out of the selection to attach
    def pushButton_Open_clicked(self) -> None:
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

    def pushButton_CreateProcess_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_BINARY, os.path.expanduser("~"))
        if file_path:
            arg_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_OPTIONAL_ARGS, ""), (tr.LD_PRELOAD_OPTIONAL, "")])
            if arg_dialog.exec():
                args, ld_preload_path = arg_dialog.get_values()
            else:
                return
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            if self.parent().create_new_process(file_path, args, ld_preload_path):
                self.close()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
