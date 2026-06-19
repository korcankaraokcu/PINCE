from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget

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

        guiutils.fill_value_combobox(self.comboBox_Type)
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
            idx = self.comboBox_Type.findData(member.value_type.value_index)
            if idx >= 0:
                self.comboBox_Type.setCurrentIndex(idx)
            else:
                self.comboBox_Type.setCurrentIndex(0)
            if typedefs.VALUE_INDEX.has_length(member.value_type.value_index):
                self.lineEdit_Length.setText(str(member.value_type.length))
            idx = self.comboBox_Repr.findData(member.value_type.value_repr)
            if idx >= 0:
                self.comboBox_Repr.setCurrentIndex(idx)
            else:
                self.comboBox_Repr.setCurrentIndex(0)
            idx = self.comboBox_Endian.findData(member.value_type.endian)
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
        has_len = typedefs.VALUE_INDEX.has_length(self.comboBox_Type.currentData(Qt.ItemDataRole.UserRole))
        self.label_Length.setVisible(has_len)
        self.lineEdit_Length.setVisible(has_len)
        is_int = typedefs.VALUE_INDEX.is_integer(self.comboBox_Type.currentData(Qt.ItemDataRole.UserRole))
        self.label_Repr.setVisible(is_int)
        self.comboBox_Repr.setVisible(is_int)

    def get_member(self) -> typedefs.StructureMember:
        name = self.lineEdit_Name.text().strip()
        offset = utils.safe_str_to_int(self.lineEdit_Offset.text(), 16)
        kind = self.comboBox_Kind.currentData()
        if kind == KIND_VALUE:
            value_index = self.comboBox_Type.currentData(Qt.ItemDataRole.UserRole)
            has_length = typedefs.VALUE_INDEX.has_length(value_index)
            length = utils.safe_str_to_int(self.lineEdit_Length.text(), 0) if has_length else 10
            value_repr = (
                self.comboBox_Repr.currentData()
                if typedefs.VALUE_INDEX.is_integer(value_index)
                else typedefs.VALUE_REPR.UNSIGNED
            )
            endian = self.comboBox_Endian.currentData()
            vt = typedefs.ValueType(value_index, length, True, value_repr, endian)
            return typedefs.StructureMember(name, offset, value_type=vt)
        else:
            struct_ref = self.comboBox_StructRef.currentText()
            is_pointer = kind == KIND_POINTER
            return typedefs.StructureMember(name, offset, struct_ref=struct_ref, is_pointer=is_pointer)
