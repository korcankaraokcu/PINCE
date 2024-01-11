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
from PyQt6.QtWidgets import QTableView, QAbstractItemView
from PyQt6.QtCore import Qt
from GUI.ItemDelegates.HexDelegate import QHexDelegate
from GUI.AbstractTableModels.HexModel import QHexModel
from libpince import utils, debugcore, typedefs


class QHexView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setMinimumSectionSize(21)
        self.verticalHeader().setDefaultSectionSize(21)
        self.horizontalHeader().setMinimumSectionSize(25)
        self.horizontalHeader().setDefaultSectionSize(25)
        self.setShowGrid(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAutoScroll(False)
        self.write_type = typedefs.VALUE_INDEX.AOB
        self.delegate = QHexDelegate()
        self.delegate.closeEditor.connect(self.on_editor_close)
        self.setItemDelegate(self.delegate)

    def wheelEvent(self, QWheelEvent):
        QWheelEvent.ignore()

    def resize_to_contents(self):
        size = self.columnWidth(0) * self.model().columnCount()
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)

    def get_selected_address(self):
        index_list = self.selectionModel().selectedIndexes()  # Use selectionModel instead of currentIndex
        model: QHexModel = self.model()
        current_address = model.current_address
        if index_list:
            cell = index_list[0]
            current_address = current_address + cell.row() * model.columnCount() + cell.column()
        return utils.modulo_address(current_address, debugcore.inferior_arch)

    def on_editor_close(self):
        model: QHexModel = self.model()
        cell = self.selectionModel().selectedIndexes()[0]
        index = cell.row() * model.columnCount() + cell.column()
        address = utils.modulo_address(model.current_address + index, debugcore.inferior_arch)
        data = self.delegate.editor.text()
        debugcore.write_memory(address, self.write_type, data, False)
        model.update_index(index, data)
