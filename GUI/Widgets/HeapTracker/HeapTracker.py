from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QWidget

from libpince import debugcore, heaptrack


class HeapTrackerDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Heap Tracker")
        self.resize(700, 400)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["Address", "Size", "Pointer fields", "Pointers (offset:value)"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh", self)
        self.jump_button = QPushButton("Show in Hex View", self)
        buttons.addWidget(self.refresh_button)
        buttons.addWidget(self.jump_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.refresh_button.clicked.connect(self.refresh)
        self.jump_button.clicked.connect(self.jump_to_selected)
        self.refresh()

    def refresh(self) -> None:
        self.table.setRowCount(0)
        if debugcore.currentpid == -1:
            QMessageBox.information(self, "Heap Tracker", "No process attached.")
            return
        try:
            summary = heaptrack.summarize_heap(debugcore.currentpid)
        except Exception as e:
            QMessageBox.information(self, "Heap Tracker", f"Failed to analyze heap: {e}")
            return
        self.table.setRowCount(len(summary))
        for row, block in enumerate(summary):
            addr_item = QTableWidgetItem(hex(block["address"]))
            addr_item.setData(Qt.ItemDataRole.UserRole, block["address"])
            size_item = QTableWidgetItem(str(block["size"]))
            ptrs = block.get("pointer_fields", [])
            count_item = QTableWidgetItem(str(len(ptrs)))
            details = ", ".join(f"+0x{off:x}:{hex(val)}" for off, val in ptrs[:8])
            detail_item = QTableWidgetItem(details)
            self.table.setItem(row, 0, addr_item)
            self.table.setItem(row, 1, size_item)
            self.table.setItem(row, 2, count_item)
            self.table.setItem(row, 3, detail_item)
        self.table.resizeColumnsToContents()

    def jump_to_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        address = item.data(Qt.ItemDataRole.UserRole)
        parent = self.parent()
        if parent and hasattr(parent, "hex_dump_address"):
            try:
                parent.hex_dump_address(hex(address))
                return
            except Exception:
                pass
        QMessageBox.information(self, "Heap Tracker", f"Selected block: {hex(address)}")
