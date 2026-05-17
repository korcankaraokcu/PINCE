from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from GUI.Widgets.PointerScan.Form.PointerScanWindow import Ui_MainWindow
from GUI.Widgets.PointerScanFilter.PointerScanFilter import PointerScanFilterDialog
from GUI.Widgets.PointerScanSearch.PointerScanSearch import PointerScanSearchDialog
from GUI.Utils import guiutils
from GUI.States import states
from libpince import debugcore, utils
from libpince.scancore import memscan
from tr.tr import TranslationConstants as tr
import os
import tempfile


class PointerScanWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent, default_scan_address: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        states.process_signals.attach.connect(self.on_process_changed)
        states.process_signals.exit.connect(self.on_process_changed)
        self.actionOpen.triggered.connect(self.actionOpen_triggered)
        self.actionSaveAs.triggered.connect(self.actionSaveAs_triggered)
        self.actionScan.triggered.connect(self.scan_triggered)
        self.actionFilter.triggered.connect(self.filter_triggered)
        self.default_scan_address = default_scan_address
        if debugcore.currentpid == -1:
            self.actionScan.setEnabled(False)
        guiutils.center_to_parent(self)

    def on_process_changed(self) -> None:
        self.actionScan.setEnabled(debugcore.currentpid != -1)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.textEdit.clear()
        return super().closeEvent(event)

    def actionOpen_triggered(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), tr.FILE_TYPES_POINTER_MAP
        )
        if file_path != "":
            self.textEdit.clear()
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            try:
                memscan.dump_pointer_map_text(file_path, temp_path)
                with open(temp_path) as file:
                    self.textEdit.setPlainText(file.read())
            finally:
                try:
                    os.remove(temp_path)
                except FileNotFoundError:
                    pass

    def actionSaveAs_triggered(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), None)
        if file_path != "":
            with open(file_path, "w") as file:
                file.write(self.textEdit.toPlainText())

    def scan_triggered(self) -> None:
        PointerScanSearchDialog(self, self.default_scan_address).exec()

    def filter_triggered(self) -> None:
        PointerScanFilterDialog(self).exec()
