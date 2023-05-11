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
from PyQt6.QtCore import QVariant, Qt
from PyQt6.QtGui import QColorConstants
from GUI.CustomAbstractTableModels.HexModel import QHexModel

from libpince import SysUtils, GDB_Engine


class QAsciiModel(QHexModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(row_count, column_count, parent)

    def data(self, QModelIndex, int_role=None):
        if self.data_array and QModelIndex.isValid():
            if int_role == Qt.ItemDataRole.BackgroundRole:
                address = self.current_address + QModelIndex.row() * self.column_count + QModelIndex.column()
                if SysUtils.modulo_address(address, GDB_Engine.inferior_arch) in self.breakpoint_list:
                    return QVariant(QColorConstants.Red)
            elif int_role == Qt.ItemDataRole.DisplayRole:
                return QVariant(SysUtils.aob_to_str(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()]))
        return QVariant()
