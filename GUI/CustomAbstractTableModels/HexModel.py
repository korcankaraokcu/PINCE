from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt
from PyQt5.QtGui import QColor

from libPINCE import GDB_Engine


class QHexModel(QAbstractTableModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(parent)
        self.data_array = []
        self.breakpoint_list = set()
        self.row_count = row_count
        self.column_count = column_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.row_count

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def data(self, QModelIndex, int_role=None):
        if not QModelIndex.isValid():
            return QVariant()
        if int_role == Qt.BackgroundColorRole:
            if QModelIndex.row() * self.column_count + QModelIndex.column() in self.breakpoint_list:
                return QVariant(QColor(Qt.red))
        elif int_role != Qt.DisplayRole:
            return QVariant()
        if self.data_array is None:
            return QVariant()
        return QVariant(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()])

    def refresh(self, int_address, offset):
        self.breakpoint_list.clear()
        hex_list = GDB_Engine.hex_dump(int_address, offset)
        self.data_array = hex_list

        breakpoint_list = GDB_Engine.get_breakpoint_info()
        for breakpoint in breakpoint_list:
            difference = int(breakpoint.address, 16) - int_address
            if difference < 0:
                continue
            size = breakpoint.size
            for i in range(size):
                self.breakpoint_list.add(difference + i)
        self.layoutChanged.emit()
