from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import Qt, QTimer, QModelIndex
from GUI.Utils import guiutils
from GUI.Widgets.TrackBreakpoint.Form.TrackBreakpointWidget import Ui_Form
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr
import os

# represents the index of columns in track breakpoint table(which addresses this instruction accesses thingy)
TRACK_BREAKPOINT_COUNT_COL = 0
TRACK_BREAKPOINT_ADDR_COL = 1
TRACK_BREAKPOINT_VALUE_COL = 2
TRACK_BREAKPOINT_SOURCE_COL = 3


class TrackBreakpointWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget, address: str, instruction: str, register_expressions: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.update_list_timer = QTimer(self, timeout=self.update_list)
        self.update_values_timer = QTimer(self, timeout=self.update_values)
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

    def update_list(self) -> None:
        info = debugcore.get_track_breakpoint_info(self.breakpoint)
        if not info:
            return
        if info == self.info:
            return
        self.info = info
        self.tableWidget_TrackInfo.setRowCount(0)
        row = 0
        for register_expression in info:
            for address in info[register_expression]:
                self.tableWidget_TrackInfo.setRowCount(row + 1)
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_COUNT_COL, QTableWidgetItem(str(info[register_expression][address])))
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_ADDR_COL, QTableWidgetItem(address))
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_SOURCE_COL, QTableWidgetItem("[" + register_expression + "]"))
                row += 1
        self.update_values()

    def update_values(self) -> None:
        with debugcore.memory_handle() as mem_handle:
            value_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
            for row in range(self.tableWidget_TrackInfo.rowCount()):
                address = self.tableWidget_TrackInfo.item(row, TRACK_BREAKPOINT_ADDR_COL).text()
                value = debugcore.read_memory(address, value_type, 10, mem_handle=mem_handle)
                value = "" if value is None else str(value)
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_VALUE_COL, QTableWidgetItem(value))
        guiutils.resize_to_contents(self.tableWidget_TrackInfo)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def tableWidget_TrackInfo_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

    def tableWidget_TrackInfo_item_double_clicked(self, index: QTableWidgetItem) -> None:
        address = self.tableWidget_TrackInfo.item(index.row(), TRACK_BREAKPOINT_ADDR_COL).text()
        vt = typedefs.ValueType(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        self.parent().parent().add_entry_to_addresstable(tr.ACCESSED_BY.format(self.address), address, vt)
        self.parent().parent().update_address_table()

    def pushButton_Stop_clicked(self) -> None:
        if self.stopped:
            self.close()
            return
        if not debugcore.delete_breakpoint(utils.safe_int_cast(self.breakpoint)):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_BREAKPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)
        self.parent().refresh_disassemble_view()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.update_list_timer.stop()
        self.update_values_timer.stop()
        if self.breakpoint:
            if not self.stopped:
                debugcore.delete_breakpoint(utils.safe_int_cast(self.breakpoint))
            breakpoint_file = utils.get_track_breakpoint_file(debugcore.currentpid, self.breakpoint)
            if os.path.exists(breakpoint_file):
                os.remove(breakpoint_file)
        self.parent().refresh_disassemble_view()
        super().closeEvent(event)
