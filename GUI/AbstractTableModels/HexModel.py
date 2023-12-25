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
from PyQt6.QtCore import QAbstractTableModel, QVariant, Qt
from PyQt6.QtGui import QColor, QColorConstants

from libpince import utils, debugcore

breakpoint_red = QColor(QColorConstants.Red)
breakpoint_red.setAlpha(96)

class QHexModel(QAbstractTableModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(parent)
        self.data_array = []
        self.breakpoint_list = set()
        self.row_count = row_count
        self.column_count = column_count
        self.current_address = 0

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.row_count

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def data(self, QModelIndex, int_role=None):
        if self.data_array and QModelIndex.isValid():
            if int_role == Qt.ItemDataRole.BackgroundRole:
                address = self.current_address + QModelIndex.row() * self.column_count + QModelIndex.column()
                if utils.modulo_address(address, debugcore.inferior_arch) in self.breakpoint_list:
                    return QVariant(breakpoint_red)
            elif int_role == Qt.ItemDataRole.DisplayRole:
                return QVariant(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()])

        return QVariant()

    def refresh(self, int_address, offset, data_array=None, breakpoint_info=None):
        int_address = utils.modulo_address(int_address, debugcore.inferior_arch)
        self.breakpoint_list.clear()
        if data_array is None:
            self.data_array = debugcore.hex_dump(int_address, offset)
        else:
            self.data_array = data_array
        if breakpoint_info is None:
            breakpoint_info = debugcore.get_breakpoint_info()
        for bp in breakpoint_info:
            breakpoint_address = int(bp.address, 16)
            for i in range(bp.size):
                self.breakpoint_list.add(utils.modulo_address(breakpoint_address + i, debugcore.inferior_arch))
        self.current_address = int_address
        self.layoutChanged.emit()
