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
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtGui import QColor
from GUI.CustomAbstractTableModels.HexModel import QHexModel

from libpince import SysUtils, GDB_Engine


class QAsciiModel(QHexModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(row_count, column_count, parent)

    def data(self, QModelIndex, int_role=None):
        if not QModelIndex.isValid():
            return QVariant()
        if int_role == Qt.BackgroundColorRole:
            address = self.current_address + QModelIndex.row() * self.column_count + QModelIndex.column()
            if SysUtils.modulo_address(address, GDB_Engine.inferior_arch) in self.breakpoint_list:
                return QVariant(QColor(Qt.red))
        elif int_role != Qt.DisplayRole:
            return QVariant()
        if self.data_array is None:
            return QVariant()
        return QVariant(
            SysUtils.aob_to_str(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()]))
