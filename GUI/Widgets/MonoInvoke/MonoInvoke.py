from typing import Any

from PyQt6.QtWidgets import QDialog, QLineEdit, QWidget

from GUI.Widgets.MonoInvoke.Form.MonoInvokeDialog import Ui_Dialog
from GUI.Utils import guiutils
from libpince import monocore, utils
from tr.tr import TranslationConstants as tr


class MonoInvokeDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, method_info: dict, signature: dict, instance_ptr: int | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.method = method_info["method"]
        self.label_Method.setText(method_info["full_name"] or method_info["name"])
        self.param_tags: list[str] = []
        self.param_inputs: list[QLineEdit] = []

        # Instance ("this") pointer. Disabled for static methods, prefilled for instance ones.
        self.instance_input = QLineEdit(self)
        if signature.get("static", True):
            self.instance_input.setText("0")
            self.instance_input.setEnabled(False)
        elif instance_ptr:
            self.instance_input.setText(utils.upper_hex(hex(instance_ptr)))
        self.formLayout.addRow(tr.MONO_INVOKE_INSTANCE, self.instance_input)

        for param in signature.get("params", []):
            edit = QLineEdit(self)
            if param["tag"] == "unsupported":
                edit.setEnabled(False)
                edit.setPlaceholderText(param["type"])
            self.formLayout.addRow(f"{param['name']} ({param['type']})", edit)
            self.param_tags.append(param["tag"])
            self.param_inputs.append(edit)

        self.pushButton_Call.clicked.connect(self.call)
        guiutils.center_to_parent(self)

    def call(self) -> None:
        client = monocore.get_client()
        if client is None:
            self.label_Result.setText(tr.MONO_NOT_READY)
            return
        if "unsupported" in self.param_tags:
            self.label_Result.setText(tr.MONO_INVOKE_UNSUPPORTED)
            return
        try:
            obj = int(self.instance_input.text().strip() or "0", 0)
        except ValueError:
            self.label_Result.setText(tr.MONO_INVOKE_BAD_INSTANCE)
            return
        try:
            args = [
                (tag, self.parse_value(tag, edit.text().strip()))
                for tag, edit in zip(self.param_tags, self.param_inputs)
            ]
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
        else:
            self.label_Result.setText(tr.MONO_INVOKE_RESULT.format(response["result"]))

    def parse_value(self, tag: str, text: str) -> Any:
        if tag in ("str", "char"):
            return text
        if tag == "bool":
            return text.lower() in ("1", "true", "yes")
        if tag in ("r4", "r8"):
            return float(text)
        return int(text, 0)
