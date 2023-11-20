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
from PyQt6.QtWidgets import QLabel, QMenu
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt
from libpince import GDB_Engine, type_defs
from PINCE import InputDialogForm
from GUI.Utils import guiutils


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

    def enterEvent(self, QEvent):
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mouseDoubleClickEvent(self, QMouseEvent):
        if GDB_Engine.currentpid == -1 or GDB_Engine.inferior_status == type_defs.INFERIOR_STATUS.INFERIOR_RUNNING:
            return
        registers = GDB_Engine.read_registers()
        current_register = self.objectName().lower()
        register_dialog = InputDialogForm(
            item_list=[("Enter the new value of register " + self.objectName(), registers[current_register])])
        if register_dialog.exec():
            GDB_Engine.set_convenience_variable(current_register, register_dialog.get_values())
            self.set_value(GDB_Engine.read_registers()[current_register])

    def contextMenuEvent(self, QContextMenuEvent):
        if GDB_Engine.currentpid == -1:
            return
        menu = QMenu()
        show_in_hex_view = menu.addAction("Show in HexView")
        show_in_disassembler = menu.addAction("Show in Disassembler")
        font_size = self.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(QContextMenuEvent.globalPos())
        if action == show_in_hex_view:
            parent = guiutils.search_parents_by_function(self, "hex_dump_address")
            if parent.objectName() == "MainWindow_MemoryView":
                address = self.text().split("=")[-1]
                address_int = int(address, 16)
                parent.hex_dump_address(address_int)
        elif action == show_in_disassembler:
            parent = guiutils.search_parents_by_function(self, "disassemble_expression")
            if parent.objectName() == "MainWindow_MemoryView":
                address = self.text().split("=")[-1]
                parent.disassemble_expression(address)
