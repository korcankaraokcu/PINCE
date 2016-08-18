from PyQt5.QtCore import QAbstractTableModel, QVariant, Qt


class QHexModel(QAbstractTableModel):
    # data_array is returned from GDB_Engine.hex_dump()
    def __init__(self, row_count, column_count, data_array=None, parent=None):
        super().__init__(parent)
        self.data_array = data_array
        self.row_count = row_count
        self.column_count = column_count

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.row_count

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.column_count

    def data(self, QModelIndex, int_role=None):
        if not QModelIndex.isValid():
            return QVariant()
        elif int_role != Qt.DisplayRole:
            return QVariant()
        if self.data_array is None:
            return QVariant()
        return QVariant(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()])

    def refresh(self, new_data_array):
        self.data_array = new_data_array
