from PyQt5.QtCore import QVariant, Qt
from GUI.CustomAbstractTableModels.HexModel import QHexModel

import SysUtils


class QAsciiModel(QHexModel):
    # data_array is returned from GDB_Engine.hex_dump()
    def __init__(self, row_count, column_count, data_array=None, parent=None):
        super().__init__(row_count, column_count, data_array, parent)

    def data(self, QModelIndex, int_role=None):
        if not QModelIndex.isValid():
            return QVariant()
        elif int_role != Qt.DisplayRole:
            return QVariant()
        if self.data_array is None:
            return QVariant()
        return QVariant(
            SysUtils.aob_to_ascii(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()]))
