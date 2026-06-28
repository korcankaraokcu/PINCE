from PyQt6.QtWidgets import QDialog, QWidget
from GUI.Utils import guiutils
from GUI.Widgets.TrackSelector.Form.TrackSelectorDialog import Ui_Dialog


class TrackSelectorDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.selection = None
        self.pushButton_Pointer.clicked.connect(lambda: self.change_selection("pointer"))
        self.pushButton_Pointed.clicked.connect(lambda: self.change_selection("pointed"))
        guiutils.center_to_parent(self)

    def change_selection(self, selection: str) -> None:
        self.selection = selection
        self.close()
