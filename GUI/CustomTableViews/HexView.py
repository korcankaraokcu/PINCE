from PyQt5.QtWidgets import QTableView, QAbstractItemView
from PyQt5.QtCore import Qt


class QHexView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)

        # TODO: 15 is a magic number, it makes the entries in address listwidget and hexview be in the same height
        # TODO: Change design of the hexview group if any display problems occur in different pyqt versions
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
        size = self.sizeHintForColumn(0) * (self.model().columnCount() + 1)
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)
