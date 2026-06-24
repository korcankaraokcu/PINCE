from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QPushButton, QMessageBox, QWidget
from GUI.Widgets.PointerScanSearch.Form.PointerScanSearchDialog import Ui_Dialog
from GUI.Utils import guiutils, guitypedefs
from libpince import debugcore, typedefs, utils
from libpince.libmemscan.memscan import Libmemscan, PointerEndianness, PointerScanOptions, ScanLevel
from tr.tr import TranslationConstants as tr
import os


class PointerScanSearchDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, address: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        for endian, text in (
            (PointerEndianness.NATIVE, tr.HOST),
            (PointerEndianness.LITTLE, tr.LITTLE),
            (PointerEndianness.BIG, tr.BIG),
        ):
            self.comboBox_Endian.addItem(text, endian)
        for width in (8, 4):
            self.comboBox_PointerSize.addItem(f"{width} Bytes", width)
        guiutils.fill_scope_combobox(self.comboBox_ScanScope)
        inferior_pointer_width = 4 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 8
        pointer_size_index = self.comboBox_PointerSize.findData(inferior_pointer_width)
        if pointer_size_index != -1:
            self.comboBox_PointerSize.setCurrentIndex(pointer_size_index)
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
        self.memscan: Libmemscan | None = None
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
        if self.memscan is not None:
            self.memscan.set_stop_flag(True)
        if self.cancel_button:
            self.cancel_button.setText(tr.STOPPING)
            self.cancel_button.setEnabled(False)

    def cleanup(self) -> None:
        if self.progress_bar_timer:
            self.progress_bar_timer.stop()
            self.progress_bar_timer = None
        if self.memscan is not None:
            self.memscan.close()
            self.memscan = None

    def scan_button_clicked(self) -> None:
        if debugcore.currentpid == -1 or self.scan_button == None or self.memscan_thread is not None:
            return
        addr_val = utils.safe_str_to_int(self.lineEdit_Address.text(), 16)
        ptrmap_file_path = self.lineEdit_Path.text()
        scan_level = ScanLevel.HEAP_STACK_EXE_BSS
        if self.checkBox_CheckAdvOptions.isChecked():
            scan_level = self.comboBox_ScanScope.currentData()
            ptr_opts = PointerScanOptions(pointer_width=self.comboBox_PointerSize.currentData())
            ptr_opts.endianness = self.comboBox_Endian.currentData()
            ptr_opts.max_depth = self.spinBox_Depth.value()
            ptr_opts.max_positive_offset = self.spinBox_MaxOffset.value()
            ptr_opts.max_negative_offset = self.spinBox_MinOffset.value()
            ptr_opts.max_results = self.spinBox_MaxResults.value() if self.checkBox_MaxResults.isChecked() else None
            ptr_opts.module_base_only = self.checkBox_Module.isChecked()
        else:
            ptr_opts = PointerScanOptions(
                pointer_width=4 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 8
            )
        self.cleanup()
        scanner = Libmemscan(os.path.join(utils.get_libpince_directory(), "libmemscan", "libmemscan.so"))
        try:
            scanner.set_scan_level(scan_level)
            scanner.attach(debugcore.currentpid)
        except Exception as error:
            scanner.close()
            QMessageBox.information(self, tr.ERROR, str(error))
            return
        self.memscan = scanner
        self.parent().default_scan_address = hex(addr_val)
        self.scan_button.setText(tr.SCANNING)
        self.scan_button.setEnabled(False)
        self.pushButton_Path.setEnabled(False)
        if self.cancel_button:
            self.cancel_button.setText(tr.STOP)
        self.memscan_thread = guitypedefs.InterruptableWorker(
            self.memscan.pointer_scan, addr_val, ptrmap_file_path, ptr_opts
        )
        self.memscan_thread.signals.finished.connect(self.memscan_callback)
        self.memscan_thread.signals.error.connect(self.memscan_error)
        self.memscan_thread.start()
        self.started_path_resolve = False
        self.progressBar.setValue(0)
        self.progressBar.setFormat(f"{tr.SCANNING_POINTERS} - %p%")
        self.progressBar.setVisible(True)
        self.progress_bar_timer = QTimer(self, timeout=self.update_progress_bar)
        self.progress_bar_timer.start(100)

    def update_progress_bar(self) -> None:
        if self.memscan is None:
            return
        if self.started_path_resolve is False:
            scan_progress = int(round(self.memscan.get_scan_progress() * 100))
            self.progressBar.setValue(scan_progress)
            self.started_path_resolve = scan_progress == 100
            if self.started_path_resolve:
                self.progressBar.setFormat(f"{tr.RESOLVING_POINTERS} - %p%")
        else:
            resolve_progress = int(round(self.memscan.get_pointer_resolve_progress() * 100))
            self.progressBar.setValue(resolve_progress)

    def memscan_callback(self, paths_found: int) -> None:
        self.memscan_thread.wait()
        self.memscan_thread = None
        self.cleanup()
        self.result_map_path = self.lineEdit_Path.text()
        guiutils.own_path_as_user(self.result_map_path)
        self.accept()
        QMessageBox.information(self, tr.SUCCESS, tr.POINTER_SCAN_SUCCESS.format(paths_found))

    def memscan_error(self, error: Exception) -> None:
        self.memscan_thread.wait()
        self.memscan_thread = None
        self.cleanup()
        if self.scan_button:
            self.scan_button.setText(tr.SCAN)
            self.scan_button.setEnabled(True)
        self.pushButton_Path.setEnabled(True)
        if self.cancel_button:
            self.cancel_button.setText(tr.CANCEL)
            self.cancel_button.setEnabled(True)
        QMessageBox.information(self, tr.ERROR, str(error))
