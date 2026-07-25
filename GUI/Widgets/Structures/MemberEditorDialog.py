from PyQt6.QtWidgets import QDialog, QMessageBox, QWidget

from GUI.Utils import guiutils
from GUI.Session.session import StructureManager
from GUI.Widgets.Structures.Form.MemberEditorDialog import Ui_Dialog
from libpince import typedefs, utils
from tr.tr import TranslationConstants as tr

KIND_VALUE = 0
KIND_POINTER = 1
KIND_INLINE = 2


class MemberEditorDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, member: typedefs.StructureMember | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)

        self.comboBox_Kind.addItem(tr.VALUE_MEMBER, KIND_VALUE)
        self.comboBox_Kind.addItem(tr.POINTER_MEMBER, KIND_POINTER)
        self.comboBox_Kind.addItem(tr.INLINE_MEMBER, KIND_INLINE)

        guiutils.fill_value_combobox(self.comboBox_Type, member.value_type if member else None)
        guiutils.fill_endianness_combobox(self.comboBox_Endian)

        self.comboBox_Repr.addItem(tr.REPR_UNSIGNED, typedefs.VALUE_REPR.UNSIGNED)
        self.comboBox_Repr.addItem(tr.REPR_SIGNED, typedefs.VALUE_REPR.SIGNED)
        self.comboBox_Repr.addItem(tr.REPR_HEX, typedefs.VALUE_REPR.HEX)

        struct_names = StructureManager.list_names()
        for name in struct_names:
            self.comboBox_StructRef.addItem(name)
        if not struct_names:
            # Nothing to link to yet so only value members are valid.
            kind_model = self.comboBox_Kind.model()
            kind_model.item(KIND_POINTER).setEnabled(False)
            kind_model.item(KIND_INLINE).setEnabled(False)

        self.comboBox_Kind.currentIndexChanged.connect(self._kind_changed)
        self.comboBox_Type.currentIndexChanged.connect(self._type_changed)

        if member is not None:
            self._load_member(member)
        else:
            self.comboBox_Kind.setCurrentIndex(self.comboBox_Kind.findData(KIND_VALUE))

        self._kind_changed()
        guiutils.center_to_parent(self)

    def _load_member(self, member: typedefs.StructureMember) -> None:
        self.lineEdit_Name.setText(member.name)
        self.lineEdit_Offset.setText(hex(member.offset))
        if member.value_type is not None:
            self.comboBox_Kind.setCurrentIndex(self.comboBox_Kind.findData(KIND_VALUE))
            if isinstance(member.value_type, (typedefs.StringValueType, typedefs.ByteArrayValueType)):
                self.lineEdit_Length.setText(str(member.value_type.length))
            idx = self.comboBox_Repr.findData(getattr(member.value_type, "value_repr", typedefs.VALUE_REPR.UNSIGNED))
            if idx >= 0:
                self.comboBox_Repr.setCurrentIndex(idx)
            else:
                self.comboBox_Repr.setCurrentIndex(0)
            idx = self.comboBox_Endian.findData(getattr(member.value_type, "endian", typedefs.ENDIANNESS.HOST))
            if idx >= 0:
                self.comboBox_Endian.setCurrentIndex(idx)
            else:
                self.comboBox_Endian.setCurrentIndex(0)
        else:
            if member.is_pointer:
                self.comboBox_Kind.setCurrentIndex(self.comboBox_Kind.findData(KIND_POINTER))
            else:
                self.comboBox_Kind.setCurrentIndex(self.comboBox_Kind.findData(KIND_INLINE))
            idx = self.comboBox_StructRef.findText(member.struct_ref)
            if idx < 0 and member.struct_ref:
                # Keep a link to a structure that's no longer registered instead of silently re-pointing it.
                self.comboBox_StructRef.addItem(member.struct_ref)
                idx = self.comboBox_StructRef.findText(member.struct_ref)
            if idx >= 0:
                self.comboBox_StructRef.setCurrentIndex(idx)

    def _kind_changed(self) -> None:
        kind = self.comboBox_Kind.currentData()
        is_value = kind == KIND_VALUE
        self.label_Type.setVisible(is_value)
        self.comboBox_Type.setVisible(is_value)
        self.label_Length.setVisible(is_value)
        self.lineEdit_Length.setVisible(is_value)
        self.label_Repr.setVisible(is_value)
        self.comboBox_Repr.setVisible(is_value)
        self.label_Endian.setVisible(is_value)
        self.comboBox_Endian.setVisible(is_value)
        self.label_StructRef.setVisible(not is_value)
        self.comboBox_StructRef.setVisible(not is_value)
        self._type_changed()

    def _type_changed(self) -> None:
        value_type = self.comboBox_Type.currentData()
        has_len = isinstance(value_type, (typedefs.StringValueType, typedefs.ByteArrayValueType))
        self.label_Length.setVisible(has_len)
        self.lineEdit_Length.setVisible(has_len)
        is_int = isinstance(value_type, typedefs.IntegerValueType)
        self.label_Repr.setVisible(is_int)
        self.comboBox_Repr.setVisible(is_int)

    def accept(self) -> None:
        try:
            int(self.lineEdit_Offset.text(), 16)
        except ValueError:
            QMessageBox.warning(self, tr.ERROR, tr.PARSE_ERROR)
            return
        if self.lineEdit_Length.isVisible():
            try:
                length = int(self.lineEdit_Length.text(), 0)
            except ValueError:
                QMessageBox.warning(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if length <= 0:
                QMessageBox.warning(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_member(self) -> typedefs.StructureMember:
        name = self.lineEdit_Name.text().strip()
        offset = utils.safe_str_to_int(self.lineEdit_Offset.text(), 16)
        kind = self.comboBox_Kind.currentData()
        if kind == KIND_VALUE:
            value_type = self.comboBox_Type.currentData()
            has_length = isinstance(value_type, (typedefs.StringValueType, typedefs.ByteArrayValueType))
            length = utils.safe_str_to_int(self.lineEdit_Length.text(), 0) if has_length else 10
            value_repr = self.comboBox_Repr.currentData() if isinstance(value_type, typedefs.IntegerValueType) else typedefs.VALUE_REPR.UNSIGNED
            endian = self.comboBox_Endian.currentData()
            vt = guiutils.configure_value_type(
                value_type,
                length=length,
                zero_terminate=True,
                value_repr=value_repr,
                endian=endian,
            )
            return typedefs.StructureMember(name, offset, value_type=vt)
        else:
            struct_ref = self.comboBox_StructRef.currentText()
            is_pointer = kind == KIND_POINTER
            return typedefs.StructureMember(name, offset, struct_ref=struct_ref, is_pointer=is_pointer)
