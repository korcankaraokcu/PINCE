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
from PyQt5.QtWidgets import QLabel, QMenu
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt
from libPINCE import GDB_Engine
from libPINCE import GuiUtils
from PINCE import InputDialogForm


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
        register_dialog = InputDialogForm(
            item_list=[("Enter the new value of register " + self.objectName(), registers[current_register])])
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
