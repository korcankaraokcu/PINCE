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
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor, QColorConstants
from libpince import utils, debugcore


class QHexModel(QAbstractTableModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(parent)
        self.data_array = []
        self.breakpoint_list = set()
        self.row_count = row_count
        self.column_count = column_count
        self.current_address = 0
        offset = row_count*column_count
        self.cell_animation = [0]*offset
        self.cell_change_color = QColor(QColorConstants.Red)
        self.breakpoint_color = QColor(QColorConstants.Green)
        self.breakpoint_color.setAlpha(96)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.row_count

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def flags(self, index: QModelIndex):
        return super().flags(index) | Qt.ItemFlag.ItemIsEditable

    def data(self, model_index: QModelIndex, int_role=None):
        if self.data_array and model_index.isValid():
            index = model_index.row() * self.column_count + model_index.column()
            if int_role == Qt.ItemDataRole.BackgroundRole:
                address = self.current_address + index
                if utils.modulo_address(address, debugcore.inferior_arch) in self.breakpoint_list:
                    return self.breakpoint_color
                self.cell_change_color.setAlpha(20*self.cell_animation[index])
                return self.cell_change_color
            elif int_role == Qt.ItemDataRole.DisplayRole:
                return self.display_data(index)

    def display_data(self, index):
        return self.data_array[index]

    def translate_data(self, data):
        return data

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
        self.cell_animation = [0]*offset
        self.layoutChanged.emit()

    def update_loop(self, updated_array):
        for index, item in enumerate(self.cell_animation):
            if item > 0:
                self.cell_animation[index] = item-1
        for index, item in enumerate(updated_array):
            if item != self.data_array[index]:
                self.cell_animation[index] = 6
        self.data_array = updated_array
        self.layoutChanged.emit()

    def update_index(self, index, data):
        data = self.translate_data(data)
        if self.data_array[index] != data:
            self.cell_animation[index] = 6
            self.data_array[index] = data
            self.layoutChanged.emit()
