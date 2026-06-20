from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QTreeWidgetItem, QWidget

from GUI.Session.session import StructureManager
from GUI.Utils import guiutils
from GUI.Widgets.Structures.Form.StructuresWindow import Ui_Form
from GUI.Widgets.Structures.StructureEditorDialog import StructureEditorDialog
from GUI.Widgets.Structures.StructureViewDialog import StructureViewDialog
from GUI.Widgets.Structures.materialize import structure_to_group_record
from libpince import debugcore
from tr.tr import TranslationConstants as tr


class StructuresWindow(QWidget, Ui_Form):
    add_to_table_requested = pyqtSignal(list)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.pushButton_New.clicked.connect(self._new_structure)
        self.pushButton_Edit.clicked.connect(self._edit_structure)
        self.pushButton_Delete.clicked.connect(self._delete_structure)
        self.pushButton_ViewAtAddress.clicked.connect(self._view_at_address)
        self.pushButton_AddToTable.clicked.connect(self._add_to_table)
        self.treeWidget_Structures.itemDoubleClicked.connect(self._edit_structure)

        self._view_windows: list[StructureViewDialog] = []
        self.refresh()
        guiutils.center_to_parent(self)

    def refresh(self) -> None:
        self.treeWidget_Structures.clear()
        for name in StructureManager.list_names():
            item = QTreeWidgetItem([name])
            self.treeWidget_Structures.addTopLevelItem(item)
        self.treeWidget_Structures.resizeColumnToContents(0)

    def _selected_name(self) -> str | None:
        item = self.treeWidget_Structures.currentItem()
        return item.text(0) if item else None

    def _new_structure(self) -> None:
        dlg = StructureEditorDialog(self)
        if dlg.exec():
            self.refresh()

    def _edit_structure(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        dlg = StructureEditorDialog(self, name)
        if dlg.exec():
            self.refresh()

    def _delete_structure(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        result = QMessageBox.question(self, tr.DELETE_STRUCTURE, tr.DELETE_STRUCTURE_PROMPT.format(name))
        if result == QMessageBox.StandardButton.Yes:
            StructureManager.delete(name)
            self.refresh()

    def _view_at_address(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        address, ok = QInputDialog.getText(self, tr.VIEW_AT_ADDRESS, tr.ENTER_BASE_ADDRESS)
        if not ok or not address.strip():
            return
        view = StructureViewDialog(self, name, address)
        view.add_to_table_requested.connect(self.add_to_table_requested)
        self._view_windows.append(view)
        view.finished.connect(lambda _result, v=view: self._forget_view(v))
        view.show()

    def _forget_view(self, view: StructureViewDialog) -> None:
        if view in self._view_windows:
            self._view_windows.remove(view)

    def _add_to_table(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        address, ok = QInputDialog.getText(self, tr.ADD_TO_ADDRESS_TABLE, tr.ENTER_BASE_ADDRESS)
        if not ok or not address.strip():
            return
        struct = StructureManager.get(name)
        if struct is None:
            return
        base_expr = debugcore.convert_to_hex(address.strip())
        self.add_to_table_requested.emit([structure_to_group_record(struct, base_expr)])
