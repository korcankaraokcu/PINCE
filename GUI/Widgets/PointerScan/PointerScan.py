from PyQt6.QtWidgets import QMainWindow, QFileDialog
from GUI.Widgets.PointerScan.Form.PointerScanWindow import Ui_MainWindow
from GUI.Widgets.PointerScanFilter.PointerScanFilter import PointerScanFilterDialog
from GUI.Widgets.PointerScanSearch.PointerScanSearch import PointerScanSearchDialog
from GUI.Utils import guiutils
from GUI.States import states
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import os


class PointerScanWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.tableWidget_ScanResult.hide()
        states.process_signals.attach.connect(self.on_process_changed)
        states.process_signals.exit.connect(self.on_process_changed)
        self.pushButton_Clear.pressed.connect(self.pushButton_Clear_pressed)
        self.pushButton_Sort.pressed.connect(self.pushButton_Sort_pressed)
        self.actionOpen.triggered.connect(self.actionOpen_triggered)
        self.actionSaveAs.triggered.connect(self.actionSaveAs_triggered)
        self.actionScan.triggered.connect(self.scan_triggered)
        self.actionFilter.triggered.connect(self.filter_triggered)
        if debugcore.currentpid == -1:
            self.actionScan.setEnabled(False)
        guiutils.center_to_parent(self)

    def on_process_changed(self) -> None:
        val: bool = False if debugcore.currentpid == -1 else True
        self.actionScan.setEnabled(val)

    def pushButton_Clear_pressed(self) -> None:
        self.textEdit.clear()

    def pushButton_Sort_pressed(self) -> None:
        text: str = self.textEdit.toPlainText()
        if text == "":
            return
        text_list: list[str] = text.split(os.linesep)
        # Sometimes files will have ending newlines.
        # We want to get rid of them otherwise they'll be at top.
        if text_list[-1] == "":
            del text_list[-1]
        text_list.sort()
        self.textEdit.setText(os.linesep.join(text_list))

    def actionOpen_triggered(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            self.textEdit.clear()
            with open(file_path) as file:
                self.textEdit.setText(file.read())

    def actionSaveAs_triggered(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path = utils.append_file_extension(file_path, "scandata")
            with open(file_path, "w") as file:
                file.write(self.textEdit.toPlainText())

    def scan_triggered(self) -> None:
        dialog = PointerScanSearchDialog(self, "0x0")
        dialog.exec()

    def filter_triggered(self) -> None:
        dialog = PointerScanFilterDialog(self)
        if dialog.exec():
            filter_result: list[str] | None = dialog.get_filter_result()
            if filter_result == None:
                return
            self.textEdit.clear()
            self.textEdit.setText(os.linesep.join(filter_result))
