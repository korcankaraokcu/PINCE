from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QWidget, QMessageBox, QApplication
from GUI.Utils import guiutils
from GUI.Validators.HexValidator import HexValidator
from GUI.Widgets.EditType.Form.EditTypeDialog import Ui_Dialog
from libpince import typedefs, utils
from tr.tr import TranslationConstants as tr


class EditTypeDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, value_type: typedefs.ValueType | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        vt = typedefs.IntegerValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(HexValidator(99, self))
        self.lineEdit_Length.setFixedWidth(40)
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt, include_bit_field=True)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, getattr(vt, "endian", typedefs.ENDIANNESS.HOST))
        if isinstance(vt, (typedefs.StringValueType, typedefs.ByteArrayValueType)):
            self.lineEdit_Length.setText(str(vt.length))
        elif isinstance(vt, typedefs.BitFieldValueType):
            self.lineEdit_Length.setText(str(vt.bits))
            self.spinBox_StartBit.setValue(vt.start_bit)
        if isinstance(vt, typedefs.StringValueType):
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        value_repr = getattr(vt, "value_repr", typedefs.VALUE_REPR.UNSIGNED)
        if value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        self.comboBox_ValueType_current_index_changed()
        guiutils.center_to_parent(self)

    def comboBox_ValueType_current_index_changed(self) -> None:
        value_type = self.comboBox_ValueType.currentData()
        is_bit_field = isinstance(value_type, typedefs.BitFieldValueType)
        self.widget_Length.setVisible(isinstance(value_type, (typedefs.StringValueType, typedefs.ByteArrayValueType)) or is_bit_field)
        self.label_Length.setText(
            QCoreApplication.translate("Dialog", "Bit length") if is_bit_field else QCoreApplication.translate("Dialog", "Length")
        )
        self.label_StartBit.setVisible(is_bit_field)
        self.spinBox_StartBit.setVisible(is_bit_field)
        self.checkBox_ZeroTerminate.setVisible(isinstance(value_type, typedefs.StringValueType))
        self.label_Endianness.setVisible(not is_bit_field)
        self.comboBox_Endianness.setVisible(not is_bit_field)
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
            if isinstance(self.comboBox_ValueType.currentData(), typedefs.BitFieldValueType) and length > 64:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
        super().accept()

    def get_values(self) -> typedefs.ValueType:
        value_type = self.comboBox_ValueType.currentData()
        length = self.lineEdit_Length.text()
        length = utils.safe_str_to_int(length, 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        if isinstance(value_type, typedefs.BitFieldValueType):
            return typedefs.BitFieldValueType(length, self.spinBox_StartBit.value(), value_repr=value_repr)
        endian = self.comboBox_Endianness.currentData()
        return guiutils.configure_value_type(
            value_type,
            length=length,
            zero_terminate=zero_terminate,
            value_repr=value_repr,
            endian=endian,
        )
