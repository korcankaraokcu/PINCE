from PyQt5.QtWidgets import QTableView, QAbstractItemView
from PyQt5.QtCore import Qt


class QHexView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(15)
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
        size = self.sizeHintForColumn(0) * self.model().columnCount()
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)

    def get_current_offset(self):
        return self.currentIndex().row() * self.model().columnCount() + self.currentIndex().column()
