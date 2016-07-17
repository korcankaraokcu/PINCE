from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
import GDB_Engine
from PINCE import DialogWithButtonsForm


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
        register_dialog = DialogWithButtonsForm(self, label_text="Enter the new value of register " + self.objectName(),
                                                hide_line_edit=False, line_edit_text=registers[current_register])
        if register_dialog.exec_():
            GDB_Engine.set_convenience_variable(current_register, register_dialog.get_values())
            self.set_value(GDB_Engine.read_registers()[current_register])
