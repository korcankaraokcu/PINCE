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
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from libpince import debugcore, typedefs
from PINCE import InputDialogForm
from tr.tr import TranslationConstants as tr


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
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mouseDoubleClickEvent(self, QMouseEvent):
        if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
            return
        registers = debugcore.read_registers()
        current_flag = self.objectName().lower()
        label_text = tr.ENTER_FLAG_VALUE.format(self.objectName())
        register_dialog = InputDialogForm(item_list=[(label_text, ["0", "1", int(registers[current_flag])])])
        if register_dialog.exec():
            if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                return
            debugcore.set_register_flag(current_flag, register_dialog.get_values())
            self.set_value(debugcore.read_registers()[current_flag])
