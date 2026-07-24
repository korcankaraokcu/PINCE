"""
Copyright (C) Korcan Karaokçu <korcankaraokcu@gmail.com>

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

from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QTreeWidget, QWidget


class AddressTree(QTreeWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def dropEvent(self, event: QDropEvent | None) -> None:
        super().dropEvent(event)
        self.parent().parent().update_address_table()
        self.parent().parent().mark_address_tree_changed()
