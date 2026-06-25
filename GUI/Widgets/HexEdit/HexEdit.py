import re

from PyQt6.QtWidgets import QDialog, QWidget, QMessageBox
from GUI.Utils import guiutils
from GUI.Validators.HexValidator import HexValidator
from GUI.Widgets.HexEdit.Form.HexEditDialog import Ui_Dialog
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr


class HexEditDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, address: int, length: int = 20) -> None:
        super().__init__(parent)
        self.setupUi(self)
        # Guards against the AsciiView<->HexView selection sync recursing into itself, since both
        # setSelection() and deselect() re-emit selectionChanged while we mirror the selection
        self.is_syncing_selection = False
        self.lineEdit_Length.setValidator(HexValidator(999, self))
        self.lineEdit_HexView.setValidator(guiutils.validator_map["bytearray"])
        self.lineEdit_Address.setText(hex(address))
        self.lineEdit_Length.setText(str(length))
        self.refresh_view()
        self.lineEdit_AsciiView.selectionChanged.connect(self.lineEdit_AsciiView_selection_changed)
        self.lineEdit_HexView.selectionChanged.connect(self.lineEdit_HexView_selection_changed)
        guiutils.center_to_parent(self)

        self.lineEdit_HexView.textEdited.connect(self.lineEdit_HexView_text_edited)
        self.lineEdit_AsciiView.textEdited.connect(self.lineEdit_AsciiView_text_edited)
        self.pushButton_Refresh.pressed.connect(self.refresh_view)
        self.lineEdit_Address.textChanged.connect(self.refresh_view)
        self.lineEdit_Length.textChanged.connect(self.refresh_view)

    def lineEdit_AsciiView_selection_changed(self) -> None:
        if self.is_syncing_selection:
            return
        hex_start = hex_length = 0
        selected_text = self.lineEdit_AsciiView.selectedText()
        if selected_text:
            selection_start = self.lineEdit_AsciiView.selectionStart()
            selection_end = selection_start + len(selected_text)
            tokens = list(re.finditer(r"\S+", self.lineEdit_HexView.text()))
            if selection_end <= len(tokens):
                hex_start = tokens[selection_start].start()
                hex_length = tokens[selection_end - 1].end() - hex_start
        # is_syncing_selection must always be reset, otherwise a single failure permanently breaks the sync. With no
        # selection we only deselect; setSelection would move the cursor (e.g. when setText regenerates this field)
        self.is_syncing_selection = True
        try:
            self.lineEdit_HexView.deselect()
            if hex_length:
                self.lineEdit_HexView.setSelection(hex_start, hex_length)
        finally:
            self.is_syncing_selection = False

    def lineEdit_HexView_selection_changed(self) -> None:
        if self.is_syncing_selection:
            return
        ascii_start = ascii_length = 0
        selected_text = self.lineEdit_HexView.selectedText()
        if selected_text:
            text = self.lineEdit_HexView.text()
            selection_start = self.lineEdit_HexView.selectionStart()
            selection_end = selection_start + len(selected_text)
            try:
                tokens = list(re.finditer(r"\S+", text))
                for token in tokens:
                    byte = token.group(0)
                    if byte != "??" and (len(byte) > 2 or not 0 <= int(byte, 16) <= 0xFF):
                        raise ValueError
                selected_bytes = [index for index, token in enumerate(tokens) if token.start() < selection_end and selection_start < token.end()]
                if selected_bytes:
                    ascii_start = selected_bytes[0]
                    ascii_length = selected_bytes[-1] - ascii_start + 1
            except ValueError:
                # Malformed hex (e.g. while the field is being edited) can't be decoded; clear the ascii selection
                ascii_start = ascii_length = 0
        # is_syncing_selection must always be reset, otherwise a single failure permanently breaks the sync. With no
        # selection we only deselect; setSelection would move the cursor (e.g. when setText regenerates this field)
        self.is_syncing_selection = True
        try:
            self.lineEdit_AsciiView.deselect()
            if ascii_length:
                self.lineEdit_AsciiView.setSelection(ascii_start, ascii_length)
        finally:
            self.is_syncing_selection = False

    def lineEdit_HexView_text_edited(self) -> None:
        aob_string = self.lineEdit_HexView.text()
        if not utils.parse_string(aob_string, typedefs.VALUE_INDEX.AOB):
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")
            return
        aob_array = aob_string.split()
        self.lineEdit_AsciiView.setText(utils.aob_to_str(aob_array))
        # Both views now hold valid, matching data, so clear any leftover error highlight from either side
        self.lineEdit_HexView.setStyleSheet("")  # This should set background color back to QT default
        self.lineEdit_AsciiView.setStyleSheet("")

    def lineEdit_AsciiView_text_edited(self) -> None:
        ascii_str = self.lineEdit_AsciiView.text()
        try:
            self.lineEdit_HexView.setText(utils.str_to_aob(ascii_str))
            # Both views now hold valid, matching data, so clear any leftover error highlight from either side
            self.lineEdit_AsciiView.setStyleSheet("")
            self.lineEdit_HexView.setStyleSheet("")
        except UnicodeError:
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def refresh_view(self) -> None:
        self.lineEdit_AsciiView.clear()
        self.lineEdit_HexView.clear()
        # Reloading from memory replaces any user edit, so clear any leftover error highlight
        self.lineEdit_AsciiView.setStyleSheet("")
        self.lineEdit_HexView.setStyleSheet("")
        address = debugcore.examine_expression(self.lineEdit_Address.text()).address
        if not address:
            return
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
            address = int(address, 0)
        except ValueError:
            return
        aob_array = debugcore.hex_dump(address, length)
        ascii_str = utils.aob_to_str(aob_array)
        self.lineEdit_AsciiView.setText(ascii_str)
        self.lineEdit_HexView.setText(" ".join(aob_array))

    def accept(self) -> None:
        expression = self.lineEdit_Address.text()
        address = debugcore.examine_expression(expression).address
        if not address:
            QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_EXPRESSION.format(expression))
            return
        value = self.lineEdit_HexView.text()
        parsed = utils.parse_string(value, typedefs.VALUE_INDEX.AOB)
        if parsed is None:
            QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
            return
        debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, value)
        super().accept()
