from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import Qt, QTimer, QModelIndex
from GUI.Utils import guiutils
from GUI.Widgets.TrackWatchpoint.Form.TrackWatchpointWidget import Ui_Form
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr
import os

# represents the index of columns in track watchpoint table(what accesses this address thingy)
TRACK_WATCHPOINT_COUNT_COL = 0
TRACK_WATCHPOINT_ADDR_COL = 1


class TrackWatchpointWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget, address: str, length: int, watchpoint_type: int) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.update_timer = QTimer(self, timeout=self.update_list)
        self.stopped = False
        self.address = address
        self.info = {}
        self.last_selected_row = 0
        if watchpoint_type == typedefs.WATCHPOINT_TYPE.WRITE_ONLY:
            string = tr.INSTR_WRITING_TO.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.READ_ONLY:
            string = tr.INSTR_READING_FROM.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.BOTH:
            string = tr.INSTR_ACCESSING_TO.format(address)
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
        self.tableWidget_Addresses.itemDoubleClicked.connect(self.tableWidget_Addresses_item_double_clicked)
        self.tableWidget_Addresses.selectionModel().currentChanged.connect(self.tableWidget_Addresses_current_changed)
        self.update_timer.start(100)
        self.show()

    def update_list(self) -> None:
        info = debugcore.get_track_watchpoint_info(self.breakpoints)
        if not info or self.info == info:
            return
        self.info = info
        self.tableWidget_Addresses.setRowCount(0)
        self.tableWidget_Addresses.setRowCount(len(info))
        for row, key in enumerate(info):
            self.tableWidget_Addresses.setItem(row, TRACK_WATCHPOINT_COUNT_COL, QTableWidgetItem(str(info[key][0])))
            self.tableWidget_Addresses.setItem(row, TRACK_WATCHPOINT_ADDR_COL, QTableWidgetItem(info[key][1]))
        guiutils.resize_to_contents(self.tableWidget_Addresses)
        self.tableWidget_Addresses.selectRow(self.last_selected_row)

    def tableWidget_Addresses_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

        info = self.info
        key_list = list(info)
        if not key_list:
            return
        self.last_selected_row = min(self.last_selected_row, len(key_list) - 1)
        key = key_list[self.last_selected_row]
        self.textBrowser_Info.clear()
        for item in info[key][2]:
            self.textBrowser_Info.append(item + "=" + str(info[key][2][item]))
        self.textBrowser_Info.append(" ")
        for item in info[key][3]:
            self.textBrowser_Info.append(item + "=" + info[key][3][item])
        self.textBrowser_Info.verticalScrollBar().setValue(self.textBrowser_Info.verticalScrollBar().minimum())
        self.textBrowser_Disassemble.setPlainText(info[key][4])

    def tableWidget_Addresses_item_double_clicked(self, index: QTableWidgetItem) -> None:
        address = self.tableWidget_Addresses.item(index.row(), TRACK_WATCHPOINT_ADDR_COL).text()
        self.parent().memory_view_window.disassemble_expression(address)
        self.parent().memory_view_window.show()
        self.parent().memory_view_window.activateWindow()

    def pushButton_Stop_clicked(self) -> None:
        if self.stopped:
            self.close()
            return
        # Internal chained breakpoints check will delete the rest from self.breakpoints
        if not debugcore.delete_breakpoint(utils.safe_int_cast(self.breakpoints[0])):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_WATCHPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.update_timer.stop()
        if self.breakpoints:
            if not self.stopped:
                # Internal chained breakpoints check will delete the rest from self.breakpoints
                debugcore.delete_breakpoint(utils.safe_int_cast(self.breakpoints[0]))
            watchpoint_file = utils.get_track_watchpoint_file(debugcore.currentpid, self.breakpoints)
            if os.path.exists(watchpoint_file):
                os.remove(watchpoint_file)
        super().closeEvent(event)
