from PyQt5.QtWidgets import QLabel


class QFlagRegisterLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

    def read_register(self):
        self.setText(self.objectName() + "=" + "")

    def set_register(self):
        self.setText(self.objectName() + "=" + "")
