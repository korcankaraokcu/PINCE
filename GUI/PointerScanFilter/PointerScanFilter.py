from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QPushButton, QLineEdit
from GUI.PointerScanFilter.Form.PointerScanFilterDialog import Ui_Dialog as PointerScanFilterForm
from GUI.Utils import guiutils
from tr.tr import TranslationConstants as tr
import os, collections


class PointerScanFilterDialog(QDialog, PointerScanFilterForm):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)
        self.pushButton_File1Browse.clicked.connect(self.pushButton_File1Browse_clicked)
        self.pushButton_File2Browse.clicked.connect(self.pushButton_File2Browse_clicked)
        self.filter_button: QPushButton | None = self.buttonBox.addButton(
            tr.FILTER, QDialogButtonBox.ButtonRole.ActionRole
        )
        if self.filter_button:
            self.filter_button.clicked.connect(self.filter_button_clicked)
            self.filter_button.setEnabled(False)
        self.filter_result: list[str] | None = None

    def browse_scandata_file(self, file_path_field: QLineEdit) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_POINTER_MAP, None, tr.FILE_TYPES_SCANDATA)
        if file_path != "":
            file_path_field.setText(file_path)
            self.check_filterable_state()

    def check_filterable_state(self) -> None:
        if self.lineEdit_File1Path.text() != "" and self.lineEdit_File2Path.text() != "" and self.filter_button:
            self.filter_button.setEnabled(True)

    def pushButton_File1Browse_clicked(self) -> None:
        self.browse_scandata_file(self.lineEdit_File1Path)

    def pushButton_File2Browse_clicked(self) -> None:
        self.browse_scandata_file(self.lineEdit_File2Path)

    def filter_button_clicked(self) -> None:
        if self.lineEdit_File1Path.text() == "" or self.lineEdit_File2Path.text() == "" or self.filter_button == None:
            return
        self.filter_button.setEnabled(False)
        self.filter_button.setText(tr.FILTERING)
        lines: list[str]
        with open(self.lineEdit_File1Path.text()) as file:
            lines = file.read().split(os.linesep)
        with open(self.lineEdit_File2Path.text()) as file:
            lines.extend(file.read().split(os.linesep))
        counts = collections.Counter(lines)
        self.filter_result = list(set([line for line in lines if counts[line] > 1 and line != ""]))
        self.accept()

    def get_filter_result(self) -> list[str] | None:
        return self.filter_result
