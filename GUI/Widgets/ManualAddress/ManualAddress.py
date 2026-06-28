from PyQt6.QtWidgets import QDialog, QWidget, QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Validators.HexValidator import HexValidator
from GUI.Widgets.ManualAddress.Form.AddAddressManuallyDialog import Ui_Dialog
from GUI.Widgets.ManualAddress.PointerChainOffset import PointerChainOffset
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr


class ManualAddressDialog(QDialog, Ui_Dialog):
    def __init__(
        self,
        parent: QWidget,
        description: str = tr.NO_DESCRIPTION,
        address: str | typedefs.PointerChainRequest = "0x",
        value_type: typedefs.ValueType | None = None,
        relative_base: str = "",
    ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.relative_base = relative_base
        self.lineEdit_PtrStartAddress.setFixedWidth(180)
        self.lineEdit_Address.setFixedWidth(180)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(HexValidator(99, self))
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        self.lineEdit_Description.setText(description)
        self.lineEdit_Description.setFixedWidth(180)
        self.offsetsList: list[PointerChainOffset] = []
        if not isinstance(address, typedefs.PointerChainRequest):
            self.lineEdit_Address.setText(address)
            self.widget_Pointer.hide()
        else:
            self.checkBox_IsPointer.setChecked(True)
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(address.get_base_address_as_str())
            self.create_offsets_list(address)
            self.widget_Pointer.show()
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.comboBox_Endianness.currentIndexChanged.connect(self.update_value)
        self.lineEdit_Length.textChanged.connect(self.update_value)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        self.checkBox_Signed.stateChanged.connect(self.repr_changed)
        self.checkBox_ZeroTerminate.stateChanged.connect(self.update_value)
        self.checkBox_IsPointer.stateChanged.connect(self.checkBox_IsPointer_state_changed)
        self.lineEdit_PtrStartAddress.textChanged.connect(self.update_value)
        self.lineEdit_Address.textChanged.connect(self.update_value)
        self.pushButton_AddOffset.clicked.connect(lambda: self.addOffsetLayout(True))
        self.pushButton_RemoveOffset.clicked.connect(self.removeOffsetLayout)
        self.label_Value.contextMenuEvent = self.label_Value_context_menu_event
        self.update_value()
        guiutils.center_to_parent(self)

    def label_Value_context_menu_event(self, event: QContextMenuEvent) -> None:
        menu = QMenu()
        refresh = menu.addAction(tr.REFRESH)
        font_size = self.label_Value.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {refresh: self.update_value}
        try:
            actions[action]()
        except KeyError:
            pass

    def addOffsetLayout(self, should_update: bool = True) -> None:
        offsetFrame = PointerChainOffset(len(self.offsetsList), self.widget_Pointer)
        self.offsetsList.append(offsetFrame)
        self.verticalLayout_Pointers.insertWidget(0, self.offsetsList[-1])
        offsetFrame.offset_changed_signal.connect(self.update_value)
        if should_update:
            self.update_value()

    def removeOffsetLayout(self) -> None:
        if len(self.offsetsList) == 1:
            return
        frame = self.offsetsList[-1]
        frame.deleteLater()
        self.verticalLayout_Pointers.removeWidget(frame)
        del self.offsetsList[-1]
        self.update_value()

    def update_deref_labels(self, pointer_chain_result: typedefs.PointerChainResult) -> None:
        if pointer_chain_result is not None:
            base_deref = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[0])
            self.label_BaseAddressDeref.setText(f" → {base_deref}")
            for index, offsetFrame in enumerate(self.offsetsList):
                if index + 1 >= len(pointer_chain_result.pointer_chain):
                    offsetFrame.update_deref_label("<font color=red>??</font>")
                    continue
                previousDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index])
                currentDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index + 1])
                offsetText = utils.upper_hex(offsetFrame.offsetText.text())
                operationalSign = "" if offsetText.startswith("-") else "+"
                calculation = f"{previousDerefText} {operationalSign} {offsetText}"
                if index + 1 != len(pointer_chain_result.pointer_chain) - 1:
                    offsetFrame.update_deref_label(f" [{calculation}] → {currentDerefText}")
                else:
                    offsetFrame.update_deref_label(f" {calculation} = {currentDerefText}")
        else:
            self.label_BaseAddressDeref.setText(" → <font color=red>??</font>")
            for offsetFrame in self.offsetsList:
                offsetFrame.update_deref_label("<font color=red>??</font>")

    def caps_hex_or_error_indicator(self, address: int) -> str:
        if address == 0:
            return "<font color=red>??</font>"
        return utils.upper_hex(hex(address))

    def _apply_relative_base(self, expression: str) -> str:
        # Prepend the parent base so a relative offset resolves while the stored expression stays relative.
        if self.relative_base and expression.startswith(("+", "-")):
            return self.relative_base + expression
        return expression

    def update_value(self) -> None:
        if self.checkBox_IsPointer.isChecked():
            hex_converted_expr = debugcore.convert_to_hex(self._apply_relative_base(self.lineEdit_PtrStartAddress.text()))
            pointer_chain_req = typedefs.PointerChainRequest(hex_converted_expr, self.get_offsets_int_list())
            pointer_chain_result = debugcore.read_pointer_chain(pointer_chain_req)
            address = None
            if pointer_chain_result is not None and pointer_chain_result.get_final_address() not in {0, None}:
                address_text = pointer_chain_result.get_final_address_as_hex()
                address = pointer_chain_result.get_final_address()
            else:
                address_text = "??"
            self.lineEdit_Address.setText(address_text)
            self.update_deref_labels(pointer_chain_result)
        else:
            hex_converted_expr = debugcore.convert_to_hex(self._apply_relative_base(self.lineEdit_Address.text()))
            address = debugcore.examine_expression(hex_converted_expr).address
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        address_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = utils.safe_str_to_int(self.lineEdit_Length.text(), 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        value = debugcore.read_memory(address, address_type, length, zero_terminate, value_repr, endian)
        self.label_Value.setText("<font color=red>??</font>" if value is None else str(value))
        old_width = self.width()
        QApplication.processEvents()
        self.adjustSize()
        self.resize(old_width, self.minimumHeight())

    def comboBox_ValueType_current_index_changed(self) -> None:
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        self.update_value()

    def repr_changed(self) -> None:
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)
        self.update_value()

    def checkBox_IsPointer_state_changed(self) -> None:
        if self.checkBox_IsPointer.isChecked():
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(self.lineEdit_Address.text())
            if len(self.offsetsList) == 0:
                self.addOffsetLayout(False)
            self.widget_Pointer.show()
        else:
            self.lineEdit_Address.setText(self.lineEdit_PtrStartAddress.text())
            self.lineEdit_PtrStartAddress.setText("")
            self.lineEdit_Address.setReadOnly(False)
            self.widget_Pointer.hide()
        self.update_value()

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self) -> tuple[str, str | typedefs.PointerChainRequest, typedefs.ValueType]:
        description = self.lineEdit_Description.text()
        length = self.lineEdit_Length.text()
        length = utils.safe_str_to_int(length, 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        value_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        vt = typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)
        if self.checkBox_IsPointer.isChecked():
            base_expression = debugcore.convert_to_hex(self.lineEdit_PtrStartAddress.text())
            address = typedefs.PointerChainRequest(base_expression, self.get_offsets_int_list())
        else:
            address = debugcore.convert_to_hex(self.lineEdit_Address.text())
        return description, address, vt

    def get_offsets_int_list(self) -> list[int]:
        offsetsIntList = []
        for frame in self.offsetsList:
            offsetText = frame.layout().itemAt(1).widget().text()
            try:
                offsetValue = int(offsetText, 16)
            except ValueError:
                offsetValue = 0
            offsetsIntList.append(offsetValue)
        return offsetsIntList

    def create_offsets_list(self, pointer_chain_req: typedefs.PointerChainRequest) -> None:
        if not isinstance(pointer_chain_req, typedefs.PointerChainRequest):
            raise TypeError("Passed non-PointerChainRequest type to create_offsets_list!")

        for offset in pointer_chain_req.offsets_list:
            self.addOffsetLayout(False)
            frame = self.offsetsList[-1]
            frame.layout().itemAt(1).widget().setText(hex(offset))

    def get_type_size(self) -> int:
        return typedefs.index_to_valuetype_dict[self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)][0]
