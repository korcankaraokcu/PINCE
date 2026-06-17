from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QMessageBox, QTreeWidgetItem, QWidget

from GUI.Widgets.MonoDissect.Form.MonoDissectDialog import Ui_Dialog
from GUI.Widgets.MonoInvoke.MonoInvoke import MonoInvokeDialog
from GUI.Widgets.MonoFindInstances.MonoFindInstances import MonoFindInstancesDialog
from GUI.Utils import guiutils
from libpince import debugcore, monocore, utils, typedefs
from tr.tr import TranslationConstants as tr

ROLE_KIND = Qt.ItemDataRole.UserRole  # "image" | "class" | "fields" | "methods" | "field" | "method" | "ref_field"
ROLE_DATA = Qt.ItemDataRole.UserRole + 1  # the dict from monocore
ROLE_LOADED = Qt.ItemDataRole.UserRole + 2  # bool, children populated

_INHERITED_BRUSH = QBrush(QColor(140, 140, 140))
_MAX_INHERIT_DEPTH = 32
_MAX_DRILL_DEPTH = 16


class MonoDissectDialog(QDialog, Ui_Dialog):
    disassemble_requested = pyqtSignal(object)  # native address (int)
    breakpoint_requested = pyqtSignal(object)  # native address (int)
    add_to_table_requested = pyqtSignal(str, object)  # description, address-expr (str | PointerChainRequest)
    export_structure_requested = pyqtSignal(object)  # class_data dict

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.treeWidget_Mono.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lineEdit_Search.textChanged.connect(self.search_text_changed)
        self.treeWidget_Mono.itemExpanded.connect(self.tree_item_expanded)
        self.treeWidget_Mono.itemExpanded.connect(self.resize_columns)
        self.treeWidget_Mono.customContextMenuRequested.connect(self.tree_context_menu)
        self.checkBox_ShowInherited.toggled.connect(self._on_inherited_toggled)
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
        self.resize_columns()

    def _on_inherited_toggled(self, checked: bool) -> None:
        self.populate_assemblies()

    def _add_field_node(
        self,
        parent: QTreeWidgetItem,
        fld: dict,
        class_data: dict,
        offsets: list[int],
        root_class: dict,
        suffix: str = "",
        instance_base: int | None = None,
    ) -> None:
        if fld["flags"] & 0x40:  # FIELD_ATTRIBUTE_LITERAL: const, no runtime address
            value = f"const {fld['type']}"
        else:
            marker = "static " if fld["is_static"] else ""
            value = f"{marker}{fld['type']} @ {utils.upper_hex(hex(fld['offset']))}"
        is_ref = not fld["is_static"] and fld.get("tag") == "object"
        child = QTreeWidgetItem([fld["name"], value + suffix])
        child.setData(0, ROLE_KIND, "ref_field" if is_ref else "field")
        # instance_base roots the path at a concrete object (Find Instances) vs the singleton static
        child.setData(
            0,
            ROLE_DATA,
            {
                "field": fld,
                "class": class_data,
                "offsets": offsets,
                "root_class": root_class,
                "instance_base": instance_base,
            },
        )
        if is_ref:  # drillable: lazily expand into the referenced type's fields
            child.setData(0, ROLE_LOADED, False)
            child.addChild(QTreeWidgetItem(["", ""]))
        parent.addChild(child)

    def _add_inherited_fields(
        self, client: monocore.MonoClient, parent_item: QTreeWidgetItem, class_data: dict
    ) -> None:
        ptr = class_data.get("parent", 0)
        depth = 0
        while ptr != 0 and depth < _MAX_INHERIT_DEPTH:
            try:
                info = client.class_info(ptr)
            except monocore.MonoError:
                break
            owner_label = f"({info['name']})"
            for fld in client.fields(ptr):
                if fld["flags"] & 0x40:
                    value = f"const {fld['type']}"
                else:
                    marker = "static " if fld["is_static"] else ""
                    value = f"{marker}{fld['type']} @ {utils.upper_hex(hex(fld['offset']))}"
                child = QTreeWidgetItem([fld["name"], f"{value} {owner_label}"])
                child.setData(0, ROLE_KIND, "field")
                child.setData(
                    0,
                    ROLE_DATA,
                    {"field": fld, "class": {"klass": ptr, "name": info["name"], "namespace": info["namespace"]}},
                )
                for col in range(parent_item.columnCount()):
                    child.setForeground(col, _INHERITED_BRUSH)
                parent_item.addChild(child)
            ptr = info.get("parent", 0)
            depth += 1

    def _add_inherited_methods(
        self, client: monocore.MonoClient, parent_item: QTreeWidgetItem, class_data: dict
    ) -> None:
        ptr = class_data.get("parent", 0)
        depth = 0
        while ptr != 0 and depth < _MAX_INHERIT_DEPTH:
            try:
                info = client.class_info(ptr)
            except monocore.MonoError:
                break
            owner_label = f"({info['name']})"
            for meth in client.methods(ptr):
                label = f"{meth['full_name'] or meth['name']} {owner_label}"
                child = QTreeWidgetItem([label, ""])
                child.setData(0, ROLE_KIND, "method")
                child.setData(0, ROLE_DATA, meth)
                for col in range(parent_item.columnCount()):
                    child.setForeground(col, _INHERITED_BRUSH)
                parent_item.addChild(child)
            ptr = info.get("parent", 0)
            depth += 1

    def _drill_depth(self, item: QTreeWidgetItem) -> int:
        depth = 0
        node = item
        while node is not None:
            if node.data(0, ROLE_KIND) == "ref_field":
                depth += 1
            node = node.parent()
        return depth

    def resize_columns(self) -> None:
        for column in range(self.treeWidget_Mono.columnCount()):
            self.treeWidget_Mono.resizeColumnToContents(column)

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
            class_data = item.data(0, ROLE_DATA)
            klass = class_data["klass"]
            for fld in client.fields(klass):
                self._add_field_node(item, fld, class_data, [fld["offset"]], class_data)
            if self.checkBox_ShowInherited.isChecked():
                self._add_inherited_fields(client, item, class_data)
        elif kind == "methods":
            class_data = item.data(0, ROLE_DATA)
            klass = class_data["klass"]
            for meth in client.methods(klass):
                child = QTreeWidgetItem([meth["full_name"] or meth["name"], ""])
                child.setData(0, ROLE_KIND, "method")
                child.setData(0, ROLE_DATA, meth)
                item.addChild(child)
            if self.checkBox_ShowInherited.isChecked():
                self._add_inherited_methods(client, item, class_data)
        elif kind == "ref_field":
            self._expand_ref_field(item, client)
            return
        item.setData(0, ROLE_LOADED, True)

    def _expand_ref_field(self, item: QTreeWidgetItem, client: monocore.MonoClient) -> None:
        """Expand a reference field into its type's fields (shared by both trees).

        Children accumulate the offset path and inherit instance_base (None when singleton).
        """
        payload = item.data(0, ROLE_DATA)
        fld = payload["field"]
        parent_offsets = payload.get("offsets", [])
        root_class = payload.get("root_class", payload["class"])
        instance_base = payload.get("instance_base")
        if self._drill_depth(item) >= _MAX_DRILL_DEPTH:
            item.addChild(QTreeWidgetItem([tr.MONO_DRILL_MAX_DEPTH, ""]))
            item.setData(0, ROLE_LOADED, True)
            return
        try:
            ref_klass = client.type_klass(fld["field"])
        except monocore.MonoError:
            ref_klass = 0
        if ref_klass == 0:
            item.addChild(QTreeWidgetItem([tr.MONO_DRILL_UNRESOLVABLE, ""]))
        else:
            try:
                ref_info = client.class_info(ref_klass)
            except monocore.MonoError:
                ref_info = {"name": "?", "namespace": ""}
            ns = ref_info.get("namespace")
            type_label = f"{ns}.{ref_info['name']}" if ns else ref_info.get("name", "?")
            ref_class = {**ref_info, "klass": ref_klass}
            for sub_fld in client.fields(ref_klass):
                offsets = parent_offsets + [sub_fld["offset"]]
                self._add_field_node(item, sub_fld, ref_class, offsets, root_class, f"  [{type_label}]", instance_base)
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
        client = monocore.get_client()
        if client is None:
            return
        kind = item.data(0, ROLE_KIND)
        global_pos = self.treeWidget_Mono.viewport().mapToGlobal(position)
        if kind == "method":
            self._method_context_menu(client, item, global_pos)
        elif kind in ("field", "ref_field"):
            self._field_context_menu(client, item, global_pos)
        elif kind == "class":
            self._class_context_menu(client, item, global_pos)

    def _method_context_menu(self, client: monocore.MonoClient, item: QTreeWidgetItem, global_pos) -> None:
        method = item.data(0, ROLE_DATA)["method"]
        menu = QMenu(self)
        action_disas = menu.addAction(tr.DISASSEMBLE)
        action_break = menu.addAction(tr.SET_BREAKPOINT)
        action_copy = menu.addAction(tr.COPY_ADDRESS)
        action_invoke = menu.addAction(tr.MONO_INVOKE)
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen == action_invoke:
            methods_node = item.parent()
            class_info = methods_node.data(0, ROLE_DATA) if methods_node is not None else None
            self.open_invoke_for_method(client, item.data(0, ROLE_DATA), class_info)
            return
        address = client.compile_method(method)
        if chosen == action_disas:
            self.disassemble_requested.emit(address)
        elif chosen == action_break:
            self.breakpoint_requested.emit(address)
        elif chosen == action_copy:
            QApplication.clipboard().setText(utils.upper_hex(hex(address)))

    def _class_context_menu(self, client: monocore.MonoClient, item: QTreeWidgetItem, global_pos) -> None:
        menu = QMenu(self)
        action_find = menu.addAction(tr.MONO_FIND_INSTANCES)
        action_export = menu.addAction(tr.EXPORT_AS_STRUCTURE)
        chosen = menu.exec(global_pos)
        if chosen == action_find:
            self._find_instances(item.data(0, ROLE_DATA))
        elif chosen == action_export:
            self.export_structure_requested.emit(item.data(0, ROLE_DATA))

    def _field_context_menu(self, client: monocore.MonoClient, item: QTreeWidgetItem, global_pos) -> None:
        """Build the field/ref_field context menu. Shared with the Find Instances tree."""
        payload = item.data(0, ROLE_DATA)
        fld = payload["field"]
        menu = QMenu(item.treeWidget())  # parent to the clicked tree's window, not always this dialog
        if fld["is_static"]:
            if fld["flags"] & 0x40:  # FIELD_ATTRIBUTE_LITERAL: const, no runtime address
                return
            # Static field: resolve to an absolute address.
            action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST)
            action_copy = menu.addAction(tr.COPY_ADDRESS)
            chosen = menu.exec(global_pos)
            if chosen is None:
                return
            try:
                address = client.static_field_address(payload["class"]["klass"], fld["field"])
            except monocore.MonoError:
                QMessageBox.information(self, tr.ERROR, tr.MONO_STATIC_UNAVAILABLE)
                return
            if chosen == action_table:
                self.add_to_table_requested.emit(fld["name"], hex(address))
            elif chosen == action_copy:
                QApplication.clipboard().setText(utils.upper_hex(hex(address)))
            return
        offsets = payload.get("offsets", [fld["offset"]])
        instance_base = payload.get("instance_base")
        if instance_base is not None:
            # Concrete instance (Find Instances): the path always resolves.
            action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST)
            action_copy = menu.addAction(tr.COPY_OFFSET)
            chosen = menu.exec(global_pos)
            if chosen is None:
                return
            if chosen == action_table:
                expr = self._instance_address_expr(instance_base, offsets)
                self.add_to_table_requested.emit(f"{payload['root_class'].get('name', '?')}.{fld['name']}", expr)
            elif chosen == action_copy:
                QApplication.clipboard().setText(utils.upper_hex(hex(fld["offset"])))
            return
        # Instance field -> no absolute address.
        # If the dissect root has a self-referential static (the singleton / Instance pattern),
        # resolve via a pointer chain whose offsets are the full drilled path,
        # so deep leaves still hit the live object.
        root_class = payload.get("root_class", payload["class"])
        root = self._singleton_root(client, root_class)
        action_table = menu.addAction(tr.ADD_TO_ADDRESS_LIST) if root is not None else None
        action_copy = menu.addAction(tr.COPY_OFFSET)
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if action_table is not None and chosen == action_table:
            try:
                base = client.static_field_address(root_class["klass"], root["field"])
            except monocore.MonoError:
                QMessageBox.information(self, tr.ERROR, tr.MONO_STATIC_UNAVAILABLE)
                return
            # hex base keeps read_pointer_chain on its fast path (an int base forces a GDB lookup)
            pointer = typedefs.PointerChainRequest(hex(base), offsets)
            self.add_to_table_requested.emit(f"{root_class.get('name', '?')}.{fld['name']}", pointer)
        elif chosen == action_copy:
            QApplication.clipboard().setText(utils.upper_hex(hex(fld["offset"])))

    def _instance_address_expr(self, instance_base: int, offsets: list[int]) -> "str | typedefs.PointerChainRequest":
        """Address for a drilled field on a concrete instance: one hop is absolute,
        deeper hops chain through the intermediate reference fields."""
        if len(offsets) == 1:
            return hex(instance_base + offsets[0])
        # hex base keeps read_pointer_chain on its fast path (an int base forces a GDB lookup)
        return typedefs.PointerChainRequest(hex(instance_base + offsets[0]), offsets[1:])

    def _find_instances(self, class_data: dict) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            addresses = monocore.find_instances(class_data["klass"])
        except monocore.MonoError:
            addresses = None  # marker unavailable
        finally:
            QApplication.restoreOverrideCursor()
        if addresses is None:
            QMessageBox.information(self, tr.ERROR, tr.MONO_INSTANCE_MARKER_UNAVAILABLE)
            return
        if not addresses:
            QMessageBox.information(self, tr.MONO_FIND_INSTANCES, tr.MONO_NO_INSTANCES)
            return
        ns = class_data.get("namespace")
        type_label = f"{ns}.{class_data['name']}" if ns else class_data.get("name", "?")
        MonoFindInstancesDialog(self, class_data, type_label, addresses).show()

    def open_invoke_for_method(
        self, client: monocore.MonoClient, method_info: dict, class_info: dict | None, instance_ptr: int | None = None
    ) -> None:
        """Open the Invoke dialog for a method."""
        signature = client.signature(method_info["method"])
        klass = class_info["klass"] if class_info else 0
        if instance_ptr is None and not signature.get("static", True) and class_info is not None:
            # No concrete instance given: try the class' self-referential static (singleton pattern).
            root = self._singleton_root(client, class_info)
            if root is not None:
                try:
                    slot = client.static_field_address(klass, root["field"])
                    value_index = (
                        typedefs.VALUE_INDEX.INT32
                        if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32
                        else typedefs.VALUE_INDEX.INT64
                    )
                    instance_ptr = debugcore.read_memory(slot, value_index)
                except monocore.MonoError:
                    instance_ptr = None
        MonoInvokeDialog(self, method_info, signature, instance_ptr=instance_ptr, klass=klass).show()

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
