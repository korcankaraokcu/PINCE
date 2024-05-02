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

from PyQt6.QtWidgets import QLabel, QMenu, QApplication
from PyQt6.QtGui import QCursor, QMouseEvent, QEnterEvent, QContextMenuEvent
from PyQt6.QtCore import Qt
from libpince import debugcore, typedefs
from PINCE import InputDialogForm
from GUI.Utils import guiutils
from tr.tr import TranslationConstants as tr


class QRegisterLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def set_value(self, value):
        new = self.objectName() + "=" + value
        old = self.text()
        if old != new:
            self.setStyleSheet("color: red")
        else:
            self.setStyleSheet("")
        self.setText(new)

    def enterEvent(self, event: QEnterEvent):
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        super().enterEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if (
            event.button() != Qt.MouseButton.LeftButton
            or debugcore.currentpid == -1
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
        ):
            return
        registers = debugcore.read_registers()
        current_register = self.objectName().lower()
        items = [(tr.ENTER_REGISTER_VALUE.format(self.objectName()), registers[current_register])]
        memory_view = guiutils.search_parents_by_function(self, "set_debug_menu_shortcuts")
        register_dialog = InputDialogForm(memory_view, items)
        if register_dialog.exec():
            if debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                return
            debugcore.set_convenience_variable(current_register, register_dialog.get_values())
            self.set_value(debugcore.read_registers()[current_register])

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu()
        copy = menu.addAction(tr.COPY)
        menu.addSeparator()
        show_in_hex_view = menu.addAction(tr.SHOW_HEXVIEW)
        show_in_disassembler = menu.addAction(tr.SHOW_DISASSEMBLER)
        font_size = self.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        memory_view = guiutils.search_parents_by_function(self, "set_debug_menu_shortcuts")
        if action == show_in_hex_view:
            address = self.text().split("=")[-1]
            address_int = int(address, 16)
            memory_view.hex_dump_address(address_int)
        elif action == show_in_disassembler:
            address = self.text().split("=")[-1]
            memory_view.disassemble_expression(address)
        elif action == copy:
            QApplication.instance().clipboard().setText(self.text().split("=")[1])
