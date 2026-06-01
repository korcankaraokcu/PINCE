from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QPushButton, QLineEdit, QMessageBox
from GUI.Widgets.PointerScanFilter.Form.PointerScanFilterDialog import Ui_Dialog
from GUI.Utils import guiutils
from tr.tr import TranslationConstants as tr
from libpince import utils
from libpince.scancore import memscan
import os


class PointerScanFilterDialog(QDialog, Ui_Dialog):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.pushButton_PrevFile.clicked.connect(self.pushButton_PrevFile_clicked)
        self.pushButton_CurrentFile.clicked.connect(self.pushButton_CurrentFile_clicked)
        self.pushButton_NewFile.clicked.connect(self.pushButton_NewFile_clicked)
        self.filter_button: QPushButton = self.buttonBox.addButton(tr.FILTER, QDialogButtonBox.ButtonRole.ActionRole)
        self.filter_button.clicked.connect(self.filter_button_clicked)
        self.filter_button.setEnabled(False)
        self.result_map_path = ""

    def pointer_map_file_prompt(self, file_path_field: QLineEdit, is_open: bool) -> None:
        if is_open:
            file_path, _ = QFileDialog.getOpenFileName(
                self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), tr.FILE_TYPES_POINTER_MAP
            )
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), tr.FILE_TYPES_POINTER_MAP
            )
        if file_path != "":
            if not is_open:
                file_path = utils.append_file_extension(file_path, "lmptr")
            file_path_field.setText(file_path)
            if self.is_filterable_state():
                self.filter_button.setEnabled(True)

    def is_filterable_state(self) -> bool:
        return (
            self.lineEdit_PrevFile.text() != ""
            and self.lineEdit_CurrentFile.text() != ""
            and self.lineEdit_NewFile.text() != ""
        )

    def pushButton_PrevFile_clicked(self) -> None:
        self.pointer_map_file_prompt(self.lineEdit_PrevFile, True)

    def pushButton_CurrentFile_clicked(self) -> None:
        self.pointer_map_file_prompt(self.lineEdit_CurrentFile, True)

    def pushButton_NewFile_clicked(self) -> None:
        self.pointer_map_file_prompt(self.lineEdit_NewFile, False)

    def filter_button_clicked(self) -> None:
        if not self.is_filterable_state():
            return
        self.filter_button.setEnabled(False)
        self.filter_button.setText(tr.FILTERING)
        new_paths = memscan.compare_pointer_maps(
            self.lineEdit_PrevFile.text(), self.lineEdit_CurrentFile.text(), self.lineEdit_NewFile.text()
        )
        self.result_map_path = self.lineEdit_NewFile.text()
        self.accept()
        QMessageBox.information(self, tr.SUCCESS, tr.POINTER_FILTER_SUCCESS.format(new_paths))
