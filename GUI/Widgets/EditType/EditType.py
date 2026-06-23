from PyQt6.QtWidgets import QDialog, QWidget, QMessageBox, QApplication
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Validators.HexValidator import HexValidator
from GUI.Widgets.EditType.Form.EditTypeDialog import Ui_Dialog
from libpince import typedefs, utils
from tr.tr import TranslationConstants as tr


class EditTypeDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, value_type: typedefs.ValueType | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(HexValidator(99, self))
        self.lineEdit_Length.setFixedWidth(40)
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        QApplication.processEvents()
        self.adjustSize()
        guiutils.center_to_parent(self)

    def comboBox_ValueType_current_index_changed(self) -> None:
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        QApplication.processEvents()
        self.adjustSize()

    def repr_changed(self) -> None:
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self) -> typedefs.ValueType:
        value_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = self.lineEdit_Length.text()
        length = utils.safe_str_to_int(length, 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        return typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)
