"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
from libpince import GDB_Engine
from PINCE import InputDialogForm


class QFlagRegisterLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_value(self, value):
        new = value
        old = self.text()
        if old != new:
            self.setStyleSheet("color: red")
        else:
            self.setStyleSheet("")
        self.setText(new)

    def enterEvent(self, QEvent):
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def mouseDoubleClickEvent(self, QMouseEvent):
        registers = GDB_Engine.read_registers()
        current_flag = self.objectName().lower()
        label_text = "Enter the new value of flag " + self.objectName()
        register_dialog = InputDialogForm(item_list=[(label_text, ["0", "1", int(registers[current_flag])])])
        if register_dialog.exec_():
            GDB_Engine.set_register_flag(current_flag, register_dialog.get_values())
            self.set_value(GDB_Engine.read_registers()[current_flag])
