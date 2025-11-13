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

from PyQt6.QtGui import QKeyEvent, QWheelEvent
from PyQt6.QtWidgets import QTableView, QAbstractItemView
from PyQt6.QtCore import QItemSelectionModel, QModelIndex, Qt
from GUI.ItemDelegates.HexDelegate import QHexDelegate
from GUI.AbstractTableModels.HexModel import QHexModel
from libpince import utils, debugcore, typedefs


class QHexView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(False)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet("QTableView {background-color: transparent;}")
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAutoScroll(False)
        self.write_type = typedefs.VALUE_INDEX.AOB
        self.delegate = QHexDelegate()
        self.delegate.closeEditor.connect(self.on_editor_close)
        self.setItemDelegate(self.delegate)

    def adjust_cell_size(self, char_count: int):
        font_metrics = self.fontMetrics()
        col_width = font_metrics.horizontalAdvance("F" * char_count) + 4 * char_count
        row_height = font_metrics.height()
        self.horizontalHeader().setMinimumSectionSize(col_width)
        self.horizontalHeader().setDefaultSectionSize(col_width)
        self.horizontalHeader().setMaximumSectionSize(col_width)
        self.verticalHeader().setMinimumSectionSize(row_height)
        self.verticalHeader().setDefaultSectionSize(row_height)
        self.verticalHeader().setMaximumSectionSize(row_height)

    def wheelEvent(self, event: QWheelEvent):
        event.ignore()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return and self.state() != QAbstractItemView.State.EditingState:
            self.edit(self.currentIndex())
        else:
            return super().keyPressEvent(event)

    def selectionCommand(self, index: QModelIndex, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Disable multi-selection when Ctrl key is pressed
            return QItemSelectionModel.SelectionFlag.ClearAndSelect
        else:
            return super().selectionCommand(index, event)

    def resize_to_contents(self):
        size = self.columnWidth(0) * self.model().columnCount()
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)

    def on_editor_close(self):
        if not self.delegate.editor.isModified():
            return
        model: QHexModel = self.model()
        cell = self.currentIndex()
        index = cell.row() * model.columnCount() + cell.column()
        address = utils.modulo_address(model.current_address + index, debugcore.inferior_arch)
        data = self.delegate.editor.text()
        if self.write_type == typedefs.VALUE_INDEX.AOB:
            data = data.upper()
        debugcore.write_memory(address, self.write_type, data, False)
        model.update_index(index, data)
