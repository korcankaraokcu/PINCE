from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
import GDB_Engine
from PINCE import DialogWithButtonsForm


class QFlagRegisterLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_value(self, value):
        new = value
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
        current_flag = self.objectName().lower()
        label_text = "Enter the new value of flag " + self.objectName() + "(0 or 1)" + \
                     "\nInputting other than 0 or 1 may fuck something up badly... VERY BADLY"
        register_dialog = DialogWithButtonsForm(label_text=label_text,
                                                hide_line_edit=False, line_edit_text=registers[current_flag])
        if register_dialog.exec_():
            GDB_Engine.set_register_flag(current_flag, register_dialog.get_values())
            self.set_value(GDB_Engine.read_registers()[current_flag])
