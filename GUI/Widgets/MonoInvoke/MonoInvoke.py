from typing import Any

from PyQt6.QtWidgets import QDialog, QLabel, QLineEdit, QWidget

from GUI.Widgets.MonoInvoke.Form.MonoInvokeDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import monocore, utils
from tr.tr import TranslationConstants as tr


class MonoInvokeDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, method_info: dict, signature: dict, instance_ptr: int | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.method = method_info["method"]
        self.signature = signature
        self.label_Method.setText(method_info["full_name"] or method_info["name"])
        self.params: list[dict] = []  # one descriptor per parameter (see _add_param)

        # Instance ("this") pointer. Disabled for static methods, prefilled for instance ones.
        self.instance_input = QLineEdit(self)
        if signature.get("static", True):
            self.instance_input.setText("0")
            self.instance_input.setEnabled(False)
        elif instance_ptr:
            self.instance_input.setText(utils.upper_hex(hex(instance_ptr)))
        self.formLayout.addRow(tr.MONO_INVOKE_INSTANCE, self.instance_input)

        client = monocore.get_client()
        for param in signature.get("params", []):
            self.params.append(self._add_param(client, param))

        self.pushButton_Call.clicked.connect(self.call)
        guiutils.center_to_parent(self)

    def _add_param(self, client: "monocore.MonoClient | None", param: dict) -> dict:
        """Add a parameter's inputs and return a descriptor used to build its invoke arg.

        A struct expands into one input per primitive field.
        A struct whose fields aren't all primitive falls back to a single raw hex bytes input.
        """
        tag, name = param["tag"], param["name"]
        if tag == "struct":
            layout = client.struct_fields(param["klass"]) if client and param.get("klass") else None
            if layout:
                self.formLayout.addRow(QLabel(f"{name} ({param['type']})"))
                fields = []
                for fld in layout:
                    edit = QLineEdit(self)
                    self.formLayout.addRow(f"{fld['name']} ({fld['type']})", edit)
                    fields.append({**fld, "edit": edit})
                return {"kind": "struct", "size": param["size"], "fields": fields}
            edit = QLineEdit(self)
            if param.get("size"):
                edit.setPlaceholderText(tr.MONO_INVOKE_STRUCT_HINT.format(param["size"]))
                kind = "struct_raw"
            else:  # collector couldn't resolve the value size so we can't marshal it by value
                edit.setEnabled(False)
                edit.setPlaceholderText(param["type"])
                kind = "unsupported"
            self.formLayout.addRow(f"{name} ({param['type']})", edit)
            return {"kind": kind, "size": param.get("size", 0), "edit": edit}
        edit = QLineEdit(self)
        if tag == "unsupported":
            edit.setEnabled(False)
            edit.setPlaceholderText(param["type"])
        self.formLayout.addRow(f"{name} ({param['type']})", edit)
        return {"kind": "unsupported" if tag == "unsupported" else "scalar", "tag": tag, "edit": edit}

    def call(self) -> None:
        client = monocore.get_client()
        if client is None:
            self.label_Result.setText(tr.MONO_NOT_READY)
            return
        if any(p["kind"] == "unsupported" for p in self.params):
            self.label_Result.setText(tr.MONO_INVOKE_UNSUPPORTED)
            return
        try:
            obj = int(self.instance_input.text().strip() or "0", 0)
        except ValueError:
            self.label_Result.setText(tr.MONO_INVOKE_BAD_INSTANCE)
            return
        try:
            args = [self._param_arg(p) for p in self.params]
        except ValueError:
            self.label_Result.setText(tr.MONO_INVOKE_BAD_ARG)
            return
        try:
            response = client.invoke(self.method, obj, args)
        except monocore.MonoError as error:
            self.label_Result.setText(str(error))
            return
        if response["exception"]:
            self.label_Result.setText(tr.MONO_INVOKE_EXCEPTION.format(utils.upper_hex(hex(response["exception"]))))
        elif response["tag"] is None:
            self.label_Result.setText(tr.MONO_INVOKE_VOID)
        elif response["tag"] == "struct":
            self.label_Result.setText(tr.MONO_INVOKE_RESULT.format(self._format_struct(client, response["result"])))
        else:
            self.label_Result.setText(tr.MONO_INVOKE_RESULT.format(response["result"]))

    def _param_arg(self, p: dict) -> tuple[str, Any]:
        """Build one (tag, value) invoke arg from a parameter descriptor."""
        if p["kind"] == "scalar":
            return (p["tag"], self.parse_value(p["tag"], p["edit"].text().strip()))
        if p["kind"] == "struct":
            buf = bytearray(p["size"])  # gaps (padding) stay zero
            for fld in p["fields"]:
                raw = monocore.pack_value(fld["tag"], self.parse_value(fld["tag"], fld["edit"].text().strip()))
                buf[fld["offset"] : fld["offset"] + len(raw)] = raw
            return ("struct", bytes(buf))
        raw = bytes.fromhex(p["edit"].text().strip().replace(" ", ""))  # struct_raw fallback
        if len(raw) != p["size"]:
            raise ValueError("struct byte length mismatch")
        return ("struct", raw)

    def _format_struct(self, client: "monocore.MonoClient", raw: bytes) -> str:
        """Render a returned struct as "field=value, ..." or hex bytes if its fields aren't primitive."""
        ret_klass = self.signature["ret"].get("klass", 0)
        layout = client.struct_fields(ret_klass) if ret_klass else None
        if not layout:
            return raw.hex()
        return ", ".join(
            f"{fld['name']}={monocore.unpack_value(fld['tag'], raw[fld['offset'] : fld['offset'] + fld['width']])}"
            for fld in layout
        )

    def parse_value(self, tag: str, text: str) -> Any:
        if tag in ("str", "char"):
            return text
        if tag == "bool":
            return text.lower() in ("1", "true", "yes")
        if tag in ("r4", "r8"):
            return float(text)
        return int(text, 0)
