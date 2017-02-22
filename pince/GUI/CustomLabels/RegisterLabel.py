from PyQt5.QtWidgets import QLabel, QMenu
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
from pince.libPINCE import GDB_Engine
from pince.libPINCE import GuiUtils
#from pince.PINCE import DialogWithButtonsForm


class QRegisterLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_value(self, value):
        new = self.objectName() + "=" + value
        old = self.text()
        if old != new:
            self.setStyleSheet("color: red")
        else:
            self.setStyleSheet("color: black")
        self.setText(new)

    def enterEvent(self, QEvent):
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mouseDoubleClickEvent(self, QMouseEvent):
        registers = GDB_Engine.read_registers()
        current_register = self.objectName().lower()
        register_dialog = DialogWithButtonsForm(label_text="Enter the new value of register " + self.objectName(),
                                                hide_line_edit=False, line_edit_text=registers[current_register])
        if register_dialog.exec_():
            GDB_Engine.set_convenience_variable(current_register, register_dialog.get_values())
            self.set_value(GDB_Engine.read_registers()[current_register])

    def contextMenuEvent(self, QContextMenuEvent):
        menu = QMenu()
        show_in_hex_view = menu.addAction("Show in HexView")
        show_in_disassembler = menu.addAction("Show in Disassembler")
        font_size = self.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec_(QContextMenuEvent.globalPos())
        if action == show_in_hex_view:
            parent = GuiUtils.search_parents_by_function(self, "hex_dump_address")
            if parent.objectName() == "MainWindow_MemoryView":
                address = self.text().split("=")[-1]
                address_int = int(address, 16)
                parent.hex_dump_address(address_int)
        elif action == show_in_disassembler:
            parent = GuiUtils.search_parents_by_function(self, "disassemble_expression")
            if parent.objectName() == "MainWindow_MemoryView":
                address = self.text().split("=")[-1]
                parent.disassemble_expression(address)
