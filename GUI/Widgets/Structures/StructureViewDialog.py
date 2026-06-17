from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QDialog, QMessageBox, QTreeWidgetItem, QWidget

from GUI.Session.session import StructureManager
from GUI.States import states
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.Structures.Form.StructureViewDialog import Ui_Dialog
from GUI.Widgets.Structures.materialize import structure_to_group_record
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr

ROLE_MEMBER = Qt.ItemDataRole.UserRole
ROLE_ADDR = Qt.ItemDataRole.UserRole + 1
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2

_MAX_DEPTH = 16


class StructureViewDialog(QDialog, Ui_Dialog):
    add_to_table_requested = pyqtSignal(list)

    def __init__(self, parent: QWidget, structure_name: str, base_address: str = "") -> None:
        super().__init__(parent)
        self.setupUi(self)

        self.structure_name = structure_name
        self.base = utils.safe_str_to_int(base_address, 16) if base_address else 0

        self.lineEdit_Base.setText(hex(self.base) if self.base else "")
        self.pushButton_AddToTable.clicked.connect(self._add_to_table)

        self.treeWidget_View.itemExpanded.connect(self._on_item_expanded)
        self.treeWidget_View.itemDoubleClicked.connect(self._on_item_double_clicked)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh_values)

        self._build_tree()
        self._start_refresh()
        guiutils.center_to_parent(self)

    def _add_to_table(self) -> None:
        struct = StructureManager.get(self.structure_name)
        if struct is None:
            return
        self.add_to_table_requested.emit([structure_to_group_record(struct, self.base)])

    def _build_tree(self) -> None:
        self.treeWidget_View.clear()
        struct = StructureManager.get(self.structure_name)
        if struct is None:
            return
        self._build_level(self.treeWidget_View.invisibleRootItem(), struct, self.base, 0)
        self.treeWidget_View.resizeColumnToContents(0)
        self.treeWidget_View.resizeColumnToContents(1)
        self.treeWidget_View.resizeColumnToContents(2)

    def _build_level(self, parent: QTreeWidgetItem, struct: typedefs.Structure, base_addr: int, depth: int) -> None:
        if depth > _MAX_DEPTH:
            return
        for member in struct.members:
            addr = base_addr + member.offset
            offset_text = utils.upper_hex(hex(member.offset))
            if member.value_type is not None:
                value = debugcore.read_memory(
                    addr,
                    member.value_type.value_index,
                    member.value_type.length,
                    member.value_type.zero_terminate,
                    member.value_type.value_repr,
                    member.value_type.endian,
                )
                value_text = str(value) if value is not None else "??"
                type_text = member.value_type.text()
                item = QTreeWidgetItem([offset_text, member.name, type_text, value_text])
                item.setData(0, ROLE_MEMBER, member)
                item.setData(0, ROLE_ADDR, addr)
                parent.addChild(item)
            else:
                type_text = ("ptr → " if member.is_pointer else "inline → ") + member.struct_ref
                item = QTreeWidgetItem([offset_text, member.name, type_text, ""])
                item.setData(0, ROLE_MEMBER, member)
                item.setData(0, ROLE_ADDR, addr)
                item.setData(0, ROLE_LOADED, False)
                item.addChild(QTreeWidgetItem(["", "", "", ""]))
                parent.addChild(item)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_LOADED):
            return
        item.takeChildren()
        member: typedefs.StructureMember = item.data(0, ROLE_MEMBER)
        if member is None or member.struct_ref is None:
            return
        member_addr = item.data(0, ROLE_ADDR)  # already base + member.offset
        if member.is_pointer:
            ptr_index = (
                typedefs.VALUE_INDEX.INT32
                if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
                else typedefs.VALUE_INDEX.INT64
            )
            child_base = debugcore.read_memory(member_addr, ptr_index)  # one hop deref at the member's address
            if child_base is None or child_base == 0:
                item.setData(0, ROLE_LOADED, True)
                return
        else:
            child_base = member_addr
        child_struct = StructureManager.get(member.struct_ref)
        if child_struct is None:
            item.setData(0, ROLE_LOADED, True)
            return
        depth = self._get_depth(item)
        self._build_level(item, child_struct, child_base, depth + 1)
        item.setData(0, ROLE_LOADED, True)

    def _get_depth(self, item: QTreeWidgetItem) -> int:
        depth = 0
        node = item.parent()
        while node is not None:
            depth += 1
            node = node.parent()
        return depth

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 3:
            return
        member: typedefs.StructureMember = item.data(0, ROLE_MEMBER)
        if member is None or member.value_type is None:
            return
        addr = item.data(0, ROLE_ADDR)
        current_value = item.text(3)
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_VALUE, current_value)])
        if dialog.exec():
            new_value = dialog.get_values()[0]
            parsed = utils.parse_string(new_value, member.value_type.value_index)
            if parsed is None:
                QMessageBox.warning(self, tr.ERROR, tr.PARSE_ERROR)
                return
            debugcore.write_memory(
                addr,
                member.value_type.value_index,
                parsed,
                member.value_type.zero_terminate,
                member.value_type.endian,
            )
            self._refresh_single(item, member, addr)

    def _refresh_single(self, item: QTreeWidgetItem, member: typedefs.StructureMember, addr: int) -> None:
        value = debugcore.read_memory(
            addr,
            member.value_type.value_index,
            member.value_type.length,
            member.value_type.zero_terminate,
            member.value_type.value_repr,
            member.value_type.endian,
        )
        item.setText(3, str(value) if value is not None else "??")

    def _start_refresh(self) -> None:
        self._refresh_timer.start(states.table_update_interval)

    def _refresh_values(self) -> None:
        if not self.isVisible():
            return  # stop polling while hidden, showEvent re-arms on the next show
        if debugcore.currentpid == -1:
            self._start_refresh()
            return
        self._refresh_item(self.treeWidget_View.invisibleRootItem())
        self._start_refresh()

    def showEvent(self, event: QShowEvent) -> None:
        self._start_refresh()
        return super().showEvent(event)

    def _refresh_item(self, item: QTreeWidgetItem) -> None:
        for i in range(item.childCount()):
            child = item.child(i)
            member: typedefs.StructureMember = child.data(0, ROLE_MEMBER)
            if member is not None and member.value_type is not None:
                addr = child.data(0, ROLE_ADDR)
                value = debugcore.read_memory(
                    addr,
                    member.value_type.value_index,
                    member.value_type.length,
                    member.value_type.zero_terminate,
                    member.value_type.value_repr,
                    member.value_type.endian,
                )
                child.setText(3, str(value) if value is not None else "??")
            if child.isExpanded():
                self._refresh_item(child)
