from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent, QKeyEvent


class QScanRegionTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        super().mousePressEvent(event)
        item = self.itemAt(event.pos())
        if item and item.column() == 0:
            row = item.row()
            self.selectRow(row)

    def mouseReleaseEvent(self, event: QMouseEvent | None) -> None:
        super().mouseReleaseEvent(event)
        item = self.itemAt(event.pos())
        if item and item.column() == 0:
            new_state = item.checkState()
            for selected_item in self.selectedItems():
                if selected_item.column() == 0:
                    selected_item.setCheckState(new_state)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event.key() == Qt.Key.Key_Space:
            current_row = self.currentRow()
            selected_indexes = self.selectedIndexes()
            # If only one item is selected and then clicked while ctrl is being held
            # There'll be no selected rows even with a current row present
            if current_row != -1 and selected_indexes:
                if self.currentItem().isSelected():
                    selected_row = current_row
                else:
                    selected_row = selected_indexes[0].row()
                cur_state = self.item(selected_row, 0).checkState()
                new_state = Qt.CheckState.Unchecked if cur_state == Qt.CheckState.Checked else Qt.CheckState.Checked
                for selected_item in self.selectedItems():
                    if selected_item.column() == 0:
                        selected_item.setCheckState(new_state)
        else:
            super().keyPressEvent(event)
