from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem, QMenu, QApplication, QWidget

from GUI.Widgets.MonoDissect.Form.MonoDissectDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import monocore, utils
from tr.tr import TranslationConstants as tr

ROLE_KIND = Qt.ItemDataRole.UserRole  # "image" | "class" | "fields" | "methods" | "field" | "method"
ROLE_DATA = Qt.ItemDataRole.UserRole + 1  # the dict from monocore
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2  # bool, children populated


class MonoDissectDialog(QDialog, Ui_Dialog):
    disassemble_requested = pyqtSignal(object)  # native address (int)
    breakpoint_requested = pyqtSignal(object)  # native address (int)
    add_to_table_requested = pyqtSignal(str, object)  # description, address (int)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.treeWidget_Mono.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lineEdit_Search.textChanged.connect(self.search_text_changed)
        self.treeWidget_Mono.itemExpanded.connect(self.tree_item_expanded)
        self.treeWidget_Mono.customContextMenuRequested.connect(self.tree_context_menu)
        guiutils.center_to_parent(self)
        self.populate_assemblies()

    def populate_assemblies(self) -> None:
        client = monocore.get_client()
        if client is None:
            self.label_Status.setText(tr.MONO_NOT_READY)
            return
        self.treeWidget_Mono.clear()
        for assembly in client.assemblies():
            item = QTreeWidgetItem([assembly["name"], ""])
            item.setData(0, ROLE_KIND, "image")
            item.setData(0, ROLE_DATA, assembly)
            item.setData(0, ROLE_LOADED, False)
            item.addChild(QTreeWidgetItem(["", ""]))  # placeholder for the expand arrow
            self.treeWidget_Mono.addTopLevelItem(item)

    def tree_item_expanded(self, item: QTreeWidgetItem) -> None:
        if item.data(0, ROLE_LOADED):
            return
        kind = item.data(0, ROLE_KIND)
        item.takeChildren()  # drop placeholder
        client = monocore.get_client()
        if client is None:
            return
        if kind == "image":
            data = item.data(0, ROLE_DATA)
            for klass in client.classes(data["image"]):
                ns = klass["namespace"]
                label = f"{ns}.{klass['name']}" if ns else klass["name"]
                child = QTreeWidgetItem([label, ""])
                child.setData(0, ROLE_KIND, "class")
                child.setData(0, ROLE_DATA, klass)
                child.setData(0, ROLE_LOADED, False)
                child.addChild(QTreeWidgetItem(["", ""]))
                item.addChild(child)
        elif kind == "class":
            data = item.data(0, ROLE_DATA)
            fields_node = QTreeWidgetItem([tr.FIELDS, ""])
            fields_node.setData(0, ROLE_KIND, "fields")
            fields_node.setData(0, ROLE_DATA, data)
            fields_node.setData(0, ROLE_LOADED, False)
            fields_node.addChild(QTreeWidgetItem(["", ""]))
            methods_node = QTreeWidgetItem([tr.METHODS, ""])
            methods_node.setData(0, ROLE_KIND, "methods")
            methods_node.setData(0, ROLE_DATA, data)
            methods_node.setData(0, ROLE_LOADED, False)
            methods_node.addChild(QTreeWidgetItem(["", ""]))
            item.addChild(fields_node)
            item.addChild(methods_node)
        elif kind == "fields":
            klass = item.data(0, ROLE_DATA)["klass"]
            for fld in client.fields(klass):
                marker = "static " if fld["is_static"] else ""
                value = f"{marker}{fld['type']} @ {utils.upper_hex(hex(fld['offset']))}"
                child = QTreeWidgetItem([fld["name"], value])
                child.setData(0, ROLE_KIND, "field")
                child.setData(0, ROLE_DATA, {"field": fld, "class": item.data(0, ROLE_DATA)})
                item.addChild(child)
        elif kind == "methods":
            klass = item.data(0, ROLE_DATA)["klass"]
            for meth in client.methods(klass):
                child = QTreeWidgetItem([meth["full_name"] or meth["name"], ""])
                child.setData(0, ROLE_KIND, "method")
                child.setData(0, ROLE_DATA, meth)
                item.addChild(child)
        item.setData(0, ROLE_LOADED, True)

    def search_text_changed(self, text: str) -> None:
        text = text.lower()

        def filter_item(item: QTreeWidgetItem) -> bool:
            visible_child = False
            for i in range(item.childCount()):
                if filter_item(item.child(i)):
                    visible_child = True
            match = text in item.text(0).lower()
            item.setHidden(not (match or visible_child) if text else False)
            return match or visible_child

        for i in range(self.treeWidget_Mono.topLevelItemCount()):
            filter_item(self.treeWidget_Mono.topLevelItem(i))

    def tree_context_menu(self, position) -> None:
        item = self.treeWidget_Mono.itemAt(position)
        if item is None:
            return
        kind = item.data(0, ROLE_KIND)
        client = monocore.get_client()
        if client is None:
            return
        menu = QMenu(self)
        if kind == "method":
            method = item.data(0, ROLE_DATA)["method"]
            action_disas = menu.addAction(tr.DISASSEMBLE)
            action_break = menu.addAction(tr.SET_BREAKPOINT)
            action_copy = menu.addAction(tr.COPY_ADDRESS)
            chosen = menu.exec(self.treeWidget_Mono.viewport().mapToGlobal(position))
            if chosen is None:
                return
            address = client.compile_method(method)
            if chosen == action_disas:
                self.disassemble_requested.emit(address)
            elif chosen == action_break:
                self.breakpoint_requested.emit(address)
            elif chosen == action_copy:
                QApplication.clipboard().setText(utils.upper_hex(hex(address)))
        elif kind == "field":
            payload = item.data(0, ROLE_DATA)
            fld = payload["field"]
            klass = payload["class"]["klass"]
            if fld["is_static"]:
                # Static field: resolve to an absolute address.
                action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST)
                action_copy = menu.addAction(tr.COPY_ADDRESS)
                chosen = menu.exec(self.treeWidget_Mono.viewport().mapToGlobal(position))
                if chosen is None:
                    return
                address = client.static_field_address(klass, fld["field"])
                if chosen == action_table:
                    self.add_to_table_requested.emit(fld["name"], address)
                elif chosen == action_copy:
                    QApplication.clipboard().setText(utils.upper_hex(hex(address)))
            else:
                # Instance field: only the offset is meaningful.
                action_copy = menu.addAction(tr.COPY_OFFSET)
                chosen = menu.exec(self.treeWidget_Mono.viewport().mapToGlobal(position))
                if chosen == action_copy:
                    QApplication.clipboard().setText(utils.upper_hex(hex(fld["offset"])))
