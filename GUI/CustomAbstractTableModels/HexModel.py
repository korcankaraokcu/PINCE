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
from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt
from PyQt5.QtGui import QColor

from libPINCE import SysUtils, GDB_Engine


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
        if not QModelIndex.isValid():
            return QVariant()
        if int_role == Qt.BackgroundColorRole:
            if QModelIndex.row() * self.column_count + QModelIndex.column() in self.breakpoint_list:
                return QVariant(QColor(Qt.red))
        elif int_role != Qt.DisplayRole:
            return QVariant()
        if self.data_array is None:
            return QVariant()
        return QVariant(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()])

    def refresh(self, int_address, offset):
        int_address = SysUtils.modulo_address(int_address, GDB_Engine.inferior_arch)
        self.breakpoint_list.clear()
        hex_list = GDB_Engine.hex_dump(int_address, offset)
        self.data_array = hex_list

        breakpoint_list = GDB_Engine.get_breakpoint_info()
        for breakpoint in breakpoint_list:
            difference = int(breakpoint.address, 16) - int_address
            if difference < 0:
                continue
            size = breakpoint.size
            for i in range(size):
                self.breakpoint_list.add(difference + i)
        self.current_address = int_address
        self.layoutChanged.emit()
