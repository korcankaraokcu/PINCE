from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.QtGui import QShortcut, QKeySequence, QKeyEvent
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Widgets.TextEdit.Form.TextEditDialog import Ui_Dialog


class TextEditDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget, text: str = "") -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.textEdit.setPlainText(str(text))
        self.accept_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.accept_shortcut.activated.connect(self.accept)
        guiutils.center_to_parent(self)

    def get_values(self) -> str:
        return self.textEdit.toPlainText()

    def keyPressEvent(self, QKeyEvent: QKeyEvent) -> None:
        if QKeyEvent.key() == Qt.Key.Key_Enter:
            pass
        else:
            super().keyPressEvent(QKeyEvent)
