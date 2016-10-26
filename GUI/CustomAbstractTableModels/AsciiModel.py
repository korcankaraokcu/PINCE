from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtGui import QColor
from GUI.CustomAbstractTableModels.HexModel import QHexModel

from libPINCE import SysUtils


class QAsciiModel(QHexModel):
    def __init__(self, row_count, column_count, parent=None):
        super().__init__(row_count, column_count, parent)

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
        return QVariant(
            SysUtils.aob_to_ascii(self.data_array[QModelIndex.row() * self.column_count + QModelIndex.column()]))
