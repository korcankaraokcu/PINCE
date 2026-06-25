"""
Copyright (C) 2026 brkzlr <brksys@icloud.com>

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

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QObject, Qt
from libpince import typedefs
from tr.tr import TranslationConstants as tr


def _base_sort_key(row: tuple[str, list[int]]) -> tuple[str, int]:
    base = row[0]
    try:
        return ("", int(base, 16))  # absolute address: sorted numerically, grouped ahead of module-relative bases
    except ValueError:
        pass
    split = max(base.rfind("+0x"), base.rfind("-0x"))  # "module+/-0xHEX": group by module, then numeric offset
    if split <= 0:
        return (base, 0)
    try:
        return (base[:split], int(base[split:], 16))
    except ValueError:
        return (base, 0)


class PointerScanModel(QAbstractTableModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.rows: list[tuple[str, list[int]]] = []
        self.offset_columns = 0

    def set_data(self, rows: list[tuple[str, list[int]]], offset_columns: int) -> None:
        self.beginResetModel()
        self.rows = rows
        self.offset_columns = offset_columns
        self.endResetModel()

    def clear(self) -> None:
        self.set_data([], 0)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1 + self.offset_columns if self.rows else 0  # 0 columns hides the header while empty

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> str | None:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        base, offsets = self.rows[index.row()]
        column = index.column()
        if column == 0:
            return base
        return hex(offsets[column - 1]) if column - 1 < len(offsets) else ""

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> str | None:
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return tr.BASE_ADDRESS if section == 0 else f"{tr.OFFSET} {section}"

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self.rows or column < 0:
            return
        if column == 0:
            key = _base_sort_key
        else:
            offset_index = column - 1
            key = lambda row: row[1][offset_index] if offset_index < len(row[1]) else float("inf")
        self.beginResetModel()
        self.rows.sort(key=key, reverse=order == Qt.SortOrder.DescendingOrder)
        self.endResetModel()

    def pointer_chain_request(self, row: int) -> typedefs.PointerChainRequest:
        base, offsets = self.rows[row]
        return typedefs.PointerChainRequest(base, list(offsets))

    def format_row(self, row: int) -> str:
        base, offsets = self.rows[row]
        return " -> ".join([base, *map(hex, offsets)])
