from PyQt6.QtWidgets import QDialog, QWidget, QTableWidgetItem, QMessageBox
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from GUI.Utils import guiutils
from GUI.Widgets.DissectCode.Form.DissectCodeDialog import Ui_Dialog
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr

# represents the index of columns in dissect code table
DISSECT_CODE_ADDR_COL = 0
DISSECT_CODE_PATH_COL = 1


class DissectCodeDialog(QDialog, Ui_Dialog):
    scan_finished_signal = pyqtSignal()

    def __init__(self, parent: QWidget, int_address: int = -1) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.init_pre_scan_gui()
        self.update_dissect_results()
        self.show_memory_regions()
        self.splitter.setStretchFactor(0, 1)
        self.pushButton_StartCancel.clicked.connect(self.pushButton_StartCancel_clicked)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(self.refresh_dissect_status)
        if int_address != -1:
            for row in range(self.tableWidget_ExecutableMemoryRegions.rowCount()):
                item = self.tableWidget_ExecutableMemoryRegions.item(row, DISSECT_CODE_ADDR_COL).text()
                start_addr, end_addr = item.split("-")
                if utils.safe_str_to_int(start_addr, 16) <= int_address <= utils.safe_str_to_int(end_addr, 16):
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

        def __init__(self, region_list: list, discard_invalid_strings: bool) -> None:
            super().__init__()
            self.region_list = region_list
            self.discard_invalid_strings = discard_invalid_strings

        def run(self) -> None:
            debugcore.dissect_code(self.region_list, self.discard_invalid_strings)
            if not self.is_canceled:
                self.output_ready.emit()

    def init_pre_scan_gui(self) -> None:
        self.is_scanning = False
        self.is_canceled = False
        self.pushButton_StartCancel.setText(tr.START)

    def init_after_scan_gui(self) -> None:
        self.is_scanning = True
        self.label_ScanInfo.setText(tr.CURRENT_SCAN_REGION)
        self.pushButton_StartCancel.setText(tr.CANCEL)

    def refresh_dissect_status(self) -> None:
        region, region_count, range, string_count, jump_count, call_count = debugcore.get_dissect_code_status()
        if not region:
            return
        self.label_RegionInfo.setText(region)
        self.label_RegionCountInfo.setText(region_count)
        self.label_CurrentRange.setText(range)
        self.label_StringReferenceCount.setText(str(string_count))
        self.label_JumpReferenceCount.setText(str(jump_count))
        self.label_CallReferenceCount.setText(str(call_count))

    def update_dissect_results(self) -> None:
        referenced_strings = None
        referenced_jumps = None
        referenced_calls = None
        try:
            referenced_strings, referenced_jumps, referenced_calls = debugcore.get_dissect_code_data()
        except:
            return
        try:
            self.label_StringReferenceCount.setText(str(len(referenced_strings)))
            self.label_JumpReferenceCount.setText(str(len(referenced_jumps)))
            self.label_CallReferenceCount.setText(str(len(referenced_calls)))
        finally:
            for ref_dict in (referenced_strings, referenced_jumps, referenced_calls):
                if ref_dict is not None:
                    ref_dict.close()

    def show_memory_regions(self) -> None:
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

    def scan_finished(self) -> None:
        self.init_pre_scan_gui()
        if not self.is_canceled:
            self.label_ScanInfo.setText(tr.SCAN_FINISHED)
        self.is_canceled = False
        self.refresh_timer.stop()
        self.refresh_dissect_status()
        self.update_dissect_results()
        self.scan_finished_signal.emit()

    def pushButton_StartCancel_clicked(self) -> None:
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
            self.background_thread = self.BackgroundThread(selected_regions, self.checkBox_DiscardInvalidStrings.isChecked())
            self.background_thread.output_ready.connect(self.scan_finished)
            self.init_after_scan_gui()
            self.refresh_timer.start()
            self.background_thread.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        debugcore.cancel_dissect_code()
        self.refresh_timer.stop()
        if hasattr(self, "background_thread"):
            self.is_canceled = True
            self.background_thread.is_canceled = True
            self.background_thread.wait()
        super().closeEvent(event)
