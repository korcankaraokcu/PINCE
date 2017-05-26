"""
Copyright (C) 2016 Korcan Karaokçu <korcankaraokcu@gmail.com>

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
from PyQt5.QtWidgets import QTableView, QAbstractItemView
from PyQt5.QtCore import Qt


class QHexView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(16)
        self.horizontalHeader().setDefaultSectionSize(23)
        self.setStyleSheet("QTableView {background-color: transparent;}")
        self.setShowGrid(False)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAutoScroll(False)

    def wheelEvent(self, QWheelEvent):
        QWheelEvent.ignore()

    def resize_to_contents(self):
        size = self.columnWidth(0) * self.model().columnCount()
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)

    def get_current_offset(self):
        return self.currentIndex().row() * self.model().columnCount() + self.currentIndex().column()
