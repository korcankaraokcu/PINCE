from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QPushButton, QMessageBox
from GUI.Widgets.PointerScanSearch.Form.PointerScanSearchDialog import Ui_Dialog
from GUI.Utils import guiutils, guitypedefs
from libpince import debugcore, utils
from libpince.debugcore import ptrscan
from libpince.libptrscan.ptrscan import FFIRange, FFIParam
from tr.tr import TranslationConstants as tr
import os


class PointerScanSearchDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, address) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.lineEdit_Address.setText(address)
        self.lineEdit_Path.setText(os.getcwd() + f"/{utils.get_process_name(debugcore.currentpid)}.scandata")
        self.pushButton_PathBrowse.clicked.connect(self.pushButton_PathBrowse_clicked)
        self.scan_button: QPushButton | None = self.buttonBox.addButton(tr.SCAN, QDialogButtonBox.ButtonRole.ActionRole)
        if self.scan_button:
            self.scan_button.clicked.connect(self.scan_button_clicked)
        self.ptrscan_thread: guitypedefs.InterruptableWorker | None = None

    def pushButton_PathBrowse_clicked(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path = utils.append_file_extension(file_path, "scandata")
            self.lineEdit_Path.setText(file_path)

    def reject(self) -> None:
        if self.ptrscan_thread:
            self.ptrscan_thread.stop()
        return super().reject()

    def scan_button_clicked(self) -> None:
        if debugcore.currentpid == -1 or self.scan_button == None:
            return
        self.scan_button.setText(tr.SCANNING)
        self.scan_button.setEnabled(False)
        self.pushButton_PathBrowse.setEnabled(False)
        params: FFIParam = FFIParam()
        addr_val = utils.safe_str_to_int(self.lineEdit_Address.text(), 16)
        params.addr(addr_val)
        params.depth(self.spinBox_Depth.value())
        params.srange(FFIRange(self.spinBox_ScanRangeStart.value(), self.spinBox_ScanRangeEnd.value()))
        lrange_start: int = self.spinBox_ScanLRangeStart.value()
        lrange_end: int = self.spinBox_ScanLRangeEnd.value()
        if lrange_start == 0 and lrange_end == 0:
            lrange_val = None
        else:
            lrange_val = FFIRange(lrange_start, lrange_end)
        params.lrange(lrange_val)
        params.node(utils.return_optional_int(self.spinBox_Node.value()))
        try:
            last_val = int(self.lineEdit_Last.text(), 16)
        except ValueError:
            last_val = None
        params.last(last_val)
        params.max(utils.return_optional_int(self.spinBox_Max.value()))
        params.cycle(self.checkBox_Cycle.isChecked())
        ptrscan.set_modules(ptrscan.list_modules_pince())  # TODO: maybe cache this and let user refresh with a button
        ptrscan.create_pointer_map()  # TODO: maybe cache this and let user refresh with a button
        ptrmap_file_path = self.lineEdit_Path.text()
        if os.path.isfile(ptrmap_file_path):
            os.remove(ptrmap_file_path)
        self.ptrscan_thread = guitypedefs.InterruptableWorker(ptrscan.scan_pointer_chain, params, ptrmap_file_path)
        self.ptrscan_thread.signals.finished.connect(self.ptrscan_callback)
        self.ptrscan_thread.start()

    def ptrscan_callback(self) -> None:
        self.accept()
        QMessageBox.information(self, tr.SUCCESS, tr.POINTER_SCAN_SUCCESS)
