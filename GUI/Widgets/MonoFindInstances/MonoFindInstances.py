from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QTreeWidgetItem

from GUI.Widgets.MonoFindInstances.Form.MonoFindInstancesDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import monocore, utils
from tr.tr import TranslationConstants as tr

if TYPE_CHECKING:
    from GUI.Widgets.MonoDissect.MonoDissect import MonoDissectDialog

# Tree roles, mirrored from MonoDissect (the shared field-node helpers read these).
ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_DATA = Qt.ItemDataRole.UserRole + 1
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2

_MAX_INSTANCES = 2000  # cap the results tree so a huge heap can't build an unwieldy list


class MonoFindInstancesDialog(QDialog, Ui_Dialog):
    """A class' live instances, each drillable into its fields at live addresses.

    Tree building, drill down and the field menu come from the owning MonoDissectDialog,
    rooted here at a concrete instance address rather than the class' singleton static.
    """

    def __init__(self, owner: "MonoDissectDialog", class_data: dict, type_label: str, addresses: list[int]) -> None:
        super().__init__(owner)
        self.setupUi(self)
        self.owner = owner
        self.setWindowTitle(tr.MONO_FIND_INSTANCES_TITLE.format(type_label))
        shown = addresses[:_MAX_INSTANCES]
        header = tr.MONO_INSTANCES_FOUND.format(len(addresses))
        if len(shown) < len(addresses):
            header += " " + tr.MONO_INSTANCES_TRUNCATED.format(len(shown))
        self.label_Header.setText(header)
        self.treeWidget_Instances.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.treeWidget_Instances.itemExpanded.connect(self.tree_item_expanded)
        self.treeWidget_Instances.customContextMenuRequested.connect(self.tree_context_menu)
        for i, address in enumerate(shown):
            node = QTreeWidgetItem([f"#{i}", utils.upper_hex(hex(address))])
            node.setData(0, ROLE_KIND, "instance")
            node.setData(0, ROLE_DATA, {"address": address, "class": class_data})
            node.setData(0, ROLE_LOADED, False)
            node.addChild(QTreeWidgetItem(["", ""]))  # placeholder for the expand arrow
            self.treeWidget_Instances.addTopLevelItem(node)
        guiutils.center_to_parent(self)

    def tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_LOADED):
            return
        kind = item.data(0, ROLE_KIND)
        item.takeChildren()  # drop placeholder
        client = monocore.get_client()
        if client is None:
            return
        if kind == "instance":
            payload = item.data(0, ROLE_DATA)
            base = payload["address"]
            class_data = payload["class"]
            for fld in client.fields(class_data["klass"]):
                self.owner._add_field_node(item, fld, class_data, [fld["offset"]], class_data, instance_base=base)
            item.setData(0, ROLE_LOADED, True)
        elif kind == "ref_field":
            self.owner._expand_ref_field(item, client)
        for column in range(self.treeWidget_Instances.columnCount()):
            self.treeWidget_Instances.resizeColumnToContents(column)

    def tree_context_menu(self, position) -> None:
        item = self.treeWidget_Instances.itemAt(position)
        if item is None:
            return
        client = monocore.get_client()
        if client is None:
            return
        kind = item.data(0, ROLE_KIND)
        global_pos = self.treeWidget_Instances.viewport().mapToGlobal(position)
        if kind in ("field", "ref_field"):
            self.owner._field_context_menu(client, item, global_pos)
        elif kind == "instance":
            payload = item.data(0, ROLE_DATA)
            menu = QMenu(self)
            action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST)
            action_copy = menu.addAction(tr.COPY_ADDRESS)
            invoke_menu = menu.addMenu(tr.MONO_INVOKE)
            try:
                methods = client.methods(payload["class"]["klass"])
            except monocore.MonoError:
                methods = []
            method_actions = {invoke_menu.addAction(m["full_name"] or m["name"]): m for m in methods}
            invoke_menu.setEnabled(bool(method_actions))
            chosen = menu.exec(global_pos)
            if chosen == action_table:
                self.owner.add_to_table_requested.emit(
                    f"{payload['class'].get('name', '?')} {item.text(0)}", hex(payload["address"])
                )
            elif chosen == action_copy:
                QApplication.clipboard().setText(utils.upper_hex(hex(payload["address"])))
            elif chosen in method_actions:
                self.owner.open_invoke_for_method(
                    client, method_actions[chosen], payload["class"], instance_ptr=payload["address"]
                )
