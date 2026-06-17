from PyQt6.QtWidgets import QDialog, QWidget, QTreeWidgetItem, QMessageBox

from GUI.Utils import guiutils
from GUI.Session.session import StructureManager
from GUI.Widgets.Structures.Form.StructureEditorDialog import Ui_Dialog
from GUI.Widgets.Structures.MemberEditorDialog import MemberEditorDialog
from libpince import typedefs, utils
from tr.tr import TranslationConstants as tr


class StructureEditorDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, structure_name: str | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)

        self._members: list[typedefs.StructureMember] = []
        self._original_name: str | None = structure_name

        self.pushButton_Add.clicked.connect(self._add_member)
        self.pushButton_Edit.clicked.connect(self._edit_member)
        self.pushButton_Remove.clicked.connect(self._remove_member)
        self.pushButton_Up.clicked.connect(self._move_up)
        self.pushButton_Down.clicked.connect(self._move_down)

        if structure_name is not None:
            struct = StructureManager.get(structure_name)
            if struct is not None:
                self.lineEdit_Name.setText(struct.name)
                self._members = list(struct.members)

        self._rebuild_tree()
        guiutils.center_to_parent(self)

    def _rebuild_tree(self) -> None:
        self.treeWidget_Members.clear()
        for m in self._members:
            offset_text = utils.upper_hex(hex(m.offset))
            if m.value_type is not None:
                type_text = m.value_type.text()
            else:
                prefix = "ptr → " if m.is_pointer else "inline → "
                type_text = prefix + m.struct_ref
            item = QTreeWidgetItem([offset_text, m.name, type_text])
            self.treeWidget_Members.addTopLevelItem(item)
        for column in range(self.treeWidget_Members.columnCount()):
            self.treeWidget_Members.resizeColumnToContents(column)

    def _selected_index(self) -> int:
        item = self.treeWidget_Members.currentItem()
        if item is None:
            return -1
        return self.treeWidget_Members.indexOfTopLevelItem(item)

    def _add_member(self) -> None:
        dlg = MemberEditorDialog(self)
        if dlg.exec():
            self._members.append(dlg.get_member())
            self._rebuild_tree()

    def _edit_member(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        dlg = MemberEditorDialog(self, self._members[idx])
        if dlg.exec():
            self._members[idx] = dlg.get_member()
            self._rebuild_tree()

    def _remove_member(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        del self._members[idx]
        self._rebuild_tree()

    def _move_up(self) -> None:
        idx = self._selected_index()
        if idx <= 0:
            return
        self._members[idx - 1], self._members[idx] = self._members[idx], self._members[idx - 1]
        self._rebuild_tree()
        self.treeWidget_Members.setCurrentItem(self.treeWidget_Members.topLevelItem(idx - 1))

    def _move_down(self) -> None:
        idx = self._selected_index()
        if idx < 0 or idx >= len(self._members) - 1:
            return
        self._members[idx], self._members[idx + 1] = self._members[idx + 1], self._members[idx]
        self._rebuild_tree()
        self.treeWidget_Members.setCurrentItem(self.treeWidget_Members.topLevelItem(idx + 1))

    def accept(self) -> None:
        name = self.lineEdit_Name.text().strip()
        if not name:
            QMessageBox.warning(self, tr.ERROR, tr.STRUCTURE_NAME_EMPTY)
            return
        struct = typedefs.Structure(name, list(self._members))
        if self._original_name is not None and name != self._original_name:
            if not StructureManager.rename(self._original_name, name):
                QMessageBox.warning(self, tr.ERROR, tr.STRUCTURE_NAME_TAKEN)
                return
            StructureManager.update(struct)
        elif self._original_name is None:
            if not StructureManager.add(struct):
                QMessageBox.warning(self, tr.ERROR, tr.STRUCTURE_NAME_TAKEN)
                return
        else:
            StructureManager.update(struct)
        super().accept()
