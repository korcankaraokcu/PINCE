from PyQt6.QtWidgets import QDialog, QWidget, QDialogButtonBox
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.EditInstruction.Form.EditInstructionDialog import Ui_Dialog
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr


class EditInstructionDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, address: str, bytes_aob: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.orig_bytes = bytes_aob
        self.lineEdit_Address.setText(address)
        self.lineEdit_Bytes.setText(bytes_aob)
        self.lineEdit_Bytes_text_edited()
        self.lineEdit_Bytes.textEdited.connect(self.lineEdit_Bytes_text_edited)
        self.lineEdit_Instruction.textEdited.connect(self.lineEdit_Instruction_text_edited)
        guiutils.center_to_parent(self)

    def set_valid(self, valid: bool) -> None:
        if valid:
            self.is_valid = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.is_valid = False
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def lineEdit_Bytes_text_edited(self) -> None:
        bytes_aob = self.lineEdit_Bytes.text()
        if utils.parse_string(bytes_aob, typedefs.VALUE_INDEX.AOB):
            address = utils.safe_str_to_int(self.lineEdit_Address.text(), 0)
            instruction = utils.disassemble(bytes_aob, address, debugcore.inferior_arch)
            if instruction:
                self.set_valid(True)
                self.lineEdit_Instruction.setText(instruction)
                return
        self.set_valid(False)
        self.lineEdit_Instruction.setText("??")

    def lineEdit_Instruction_text_edited(self) -> None:
        instruction = self.lineEdit_Instruction.text()
        address = utils.safe_str_to_int(self.lineEdit_Address.text(), 0)
        result = utils.assemble(instruction, address, debugcore.inferior_arch)
        if result:
            byte_list = result[0]
            self.set_valid(True)
            bytes_str = " ".join([format(num, "02x") for num in byte_list])
            self.lineEdit_Bytes.setText(bytes_str)
        else:
            self.set_valid(False)
            self.lineEdit_Bytes.setText("??")

    def accept(self) -> None:
        if not self.is_valid:
            return

        # No need to check for validity since address is not editable and instruction is checked in text_edited
        address = utils.safe_str_to_int(self.lineEdit_Address.text(), 0)
        bytes_aob = self.lineEdit_Bytes.text()
        if bytes_aob != self.orig_bytes:
            new_length = len(bytes_aob.split())
            old_length = len(self.orig_bytes.split())
            if new_length < old_length:
                bytes_aob += " 90" * (old_length - new_length)  # Append NOPs if we are short on bytes
            elif new_length > old_length:
                if not utilwidgets.InputDialog(self, tr.NEW_INSTR.format(new_length, old_length)).exec():
                    return
            debugcore.modify_instruction(address, bytes_aob)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        super().accept()
