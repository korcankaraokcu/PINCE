from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem, QMenu, QApplication, QWidget

from GUI.Widgets.MonoDissect.Form.MonoDissectDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import monocore, utils, typedefs
from tr.tr import TranslationConstants as tr

ROLE_KIND = Qt.ItemDataRole.UserRole  # "image" | "class" | "fields" | "methods" | "field" | "method"
ROLE_DATA = Qt.ItemDataRole.UserRole + 1  # the dict from monocore
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2  # bool, children populated


class MonoDissectDialog(QDialog, Ui_Dialog):
    disassemble_requested = pyqtSignal(object)  # native address (int)
    breakpoint_requested = pyqtSignal(object)  # native address (int)
    add_to_table_requested = pyqtSignal(str, object)  # description, address-expr (str | PointerChainRequest)

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
            action_invoke = menu.addAction(tr.INVOKE_NO_ARGS)
            chosen = menu.exec(self.treeWidget_Mono.viewport().mapToGlobal(position))
            if chosen is None:
                return
            if chosen == action_invoke:
                result = monocore.get_client().invoke(method)
                QApplication.clipboard().setText(utils.upper_hex(hex(result.get("result", 0))))
            else:
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
                    self.add_to_table_requested.emit(fld["name"], hex(address))
                elif chosen == action_copy:
                    QApplication.clipboard().setText(utils.upper_hex(hex(address)))
            else:
                # Instance field: lives at <object pointer> + offset, so it has no absolute address.
                # If the class exposes a self-referential static (the singleton / Instance pattern),
                # we'll use a pointer chain so the field resolves to a live object automatically.
                root = self._singleton_root(client, payload["class"])
                action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST) if root is not None else None
                action_copy = menu.addAction(tr.COPY_OFFSET)
                chosen = menu.exec(self.treeWidget_Mono.viewport().mapToGlobal(position))
                if chosen is None:
                    return
                if action_table is not None and chosen == action_table:
                    base = client.static_field_address(klass, root["field"])
                    pointer = typedefs.PointerChainRequest(base, [fld["offset"]])
                    self.add_to_table_requested.emit(f"{payload['class']['name']}.{fld['name']}", pointer)
                elif chosen == action_copy:
                    QApplication.clipboard().setText(utils.upper_hex(hex(fld["offset"])))

    def _singleton_root(self, client: monocore.MonoClient, klass_info: dict) -> dict | None:
        """Return the class' self-referential static field (singleton / Instance pattern), if any.

        Such a field (e.g. Player.Current : Player) holds a pointer to a live instance, so it can
        root a pointer chain that resolves the class's instance fields to that object automatically.
        """
        full_name = f"{klass_info['namespace']}.{klass_info['name']}" if klass_info["namespace"] else klass_info["name"]
        for candidate in client.fields(klass_info["klass"]):
            if candidate["is_static"] and candidate["type"] == full_name:
                return candidate
        return None
