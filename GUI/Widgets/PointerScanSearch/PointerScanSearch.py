from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QPushButton, QMessageBox, QWidget
from GUI.Widgets.PointerScanSearch.Form.PointerScanSearchDialog import Ui_Dialog
from GUI.Utils import guiutils, guitypedefs
from libpince import debugcore, utils
from libpince.scancore import memscan
from libpince.libmemscan.memscan import PointerScanOptions
from tr.tr import TranslationConstants as tr
import os


class PointerScanSearchDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, address: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.lineEdit_Address.setText(address)
        self.lineEdit_Path.setText(os.path.expanduser("~") + f"/{utils.get_process_name(debugcore.currentpid)}.lmptr")
        self.pushButton_Path.clicked.connect(self.pushButton_Path_clicked)
        self.checkBox_CheckAdvOptions.toggled.connect(self.checkBox_CheckAdvOptions_checked)
        self.spinBox_MaxResults.setEnabled(self.checkBox_MaxResults.isChecked())
        self.checkBox_MaxResults.toggled.connect(self.checkBox_MaxResults_checked)
        self.scan_button: QPushButton | None = self.buttonBox.addButton(tr.SCAN, QDialogButtonBox.ButtonRole.ActionRole)
        if self.scan_button:
            self.scan_button.clicked.connect(self.scan_button_clicked)
        self.cancel_button: QPushButton | None = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        self.memscan_thread: guitypedefs.InterruptableWorker | None = None
        self.progress_bar_timer: QTimer | None = None
        self.started_path_resolve = False
        self.result_map_path = ""

    def checkBox_CheckAdvOptions_checked(self, checked: bool) -> None:
        self.verticalWidget_AdvOptions.setEnabled(checked)

    def checkBox_MaxResults_checked(self, checked: bool) -> None:
        self.spinBox_MaxResults.setEnabled(checked)

    def pushButton_Path_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), tr.FILE_TYPES_POINTER_MAP
        )
        if file_path != "":
            file_path = utils.append_file_extension(file_path, "lmptr")
            self.lineEdit_Path.setText(file_path)

    def reject(self) -> None:
        if self.memscan_thread is None:
            self.cleanup()
            return super().reject()
        memscan.set_stop_flag(True)
        if self.cancel_button:
            self.cancel_button.setText(tr.STOPPING)
            self.cancel_button.setEnabled(False)

    def cleanup(self) -> None:
        if self.progress_bar_timer:
            self.progress_bar_timer.stop()
            self.progress_bar_timer = None

    def scan_button_clicked(self) -> None:
        if debugcore.currentpid == -1 or self.scan_button == None:
            return
        self.scan_button.setText(tr.SCANNING)
        self.scan_button.setEnabled(False)
        self.pushButton_Path.setEnabled(False)
        if self.cancel_button:
            self.cancel_button.setText(tr.STOP)
        addr_val = utils.safe_str_to_int(self.lineEdit_Address.text(), 16)
        self.parent().default_scan_address = hex(addr_val)
        ptrmap_file_path = self.lineEdit_Path.text()
        if self.checkBox_CheckAdvOptions.isChecked():
            ptr_opts = PointerScanOptions()
            ptr_opts.endianness = self.comboBox_Endian.currentIndex()
            ptr_opts.pointer_width = 8 if self.comboBox_PointerSize.currentIndex() == 0 else 4
            ptr_opts.max_depth = self.spinBox_Depth.value()
            ptr_opts.max_positive_offset = self.spinBox_MaxOffset.value()
            ptr_opts.max_negative_offset = self.spinBox_MinOffset.value()
            ptr_opts.max_results = self.spinBox_MaxResults.value() if self.checkBox_MaxResults.isChecked() else None
            ptr_opts.module_base_only = self.checkBox_Module.isChecked()
        else:
            ptr_opts = None
        self.memscan_thread = guitypedefs.InterruptableWorker(
            memscan.pointer_scan, addr_val, ptrmap_file_path, ptr_opts
        )
        self.memscan_thread.signals.finished.connect(self.memscan_callback)
        self.memscan_thread.signals.error.connect(self.memscan_error)
        self.memscan_thread.start()
        self.started_path_resolve = False
        self.progressBar.setValue(0)
        self.progressBar.setFormat(f"{tr.SCANNING_POINTERS} - %p%")
        self.progressBar.setVisible(True)
        self.progress_bar_timer = QTimer(timeout=self.update_progress_bar)
        self.progress_bar_timer.start(100)

    def update_progress_bar(self) -> None:
        if self.started_path_resolve is False:
            scan_progress = int(round(memscan.get_scan_progress() * 100))
            self.progressBar.setValue(scan_progress)
            self.started_path_resolve = scan_progress == 100
            if self.started_path_resolve:
                self.progressBar.setFormat(f"{tr.RESOLVING_POINTERS} - %p%")
        else:
            resolve_progress = int(round(memscan.get_pointer_resolve_progress() * 100))
            self.progressBar.setValue(resolve_progress)

    def memscan_callback(self, paths_found: int) -> None:
        self.cleanup()
        self.memscan_thread.wait()
        self.memscan_thread = None
        self.result_map_path = self.lineEdit_Path.text()
        self.accept()
        QMessageBox.information(self, tr.SUCCESS, tr.POINTER_SCAN_SUCCESS.format(paths_found))

    def memscan_error(self, error: Exception) -> None:
        self.cleanup()
        self.memscan_thread.wait()
        self.memscan_thread = None
        if self.scan_button:
            self.scan_button.setText(tr.SCAN)
            self.scan_button.setEnabled(True)
        self.pushButton_Path.setEnabled(True)
        if self.cancel_button:
            self.cancel_button.setText(tr.CANCEL)
            self.cancel_button.setEnabled(True)
        QMessageBox.information(self, tr.ERROR, str(error))
