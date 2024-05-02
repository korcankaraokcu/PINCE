from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QLineEdit, QPushButton, QHBoxLayout, QSizePolicy, QSpacerItem
from PyQt6.QtCore import Qt, pyqtSignal
from operator import add as opAdd, sub as opSub

from GUI.Utils import guiutils


# Only intended to be used by ManualAddressForm
class PointerChainOffset(QFrame):
    offset_changed_signal = pyqtSignal(name="offsetChanged")

    def __init__(self, offset_index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.offset_index = offset_index
        self.initUI()

    def initUI(self):
        offsetLayout = QHBoxLayout(self)
        offsetLayout.setContentsMargins(0, 3, 0, 3)
        self.setLayout(offsetLayout)
        buttonLeft = QPushButton("<", self)
        buttonLeft.setFixedWidth(20)
        offsetLayout.addWidget(buttonLeft)
        self.offsetText = QLineEdit(self)
        self.offsetText.setValidator(guiutils.validator_map["int_hex"])
        self.offsetText.setText(hex(0))
        self.offsetText.setFixedWidth(70)
        self.offsetText.textChanged.connect(self.offset_changed)
        offsetLayout.addWidget(self.offsetText)
        buttonRight = QPushButton(">", self)
        buttonRight.setFixedWidth(20)
        offsetLayout.addWidget(buttonRight)
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding)
        self.derefLabel = QLabel(self)
        self.derefLabel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.derefLabel.setText(" -> <font color=red>??</font>")
        offsetLayout.addWidget(self.derefLabel)
        offsetLayout.addItem(spacer)
        buttonLeft.clicked.connect(lambda: self.on_offset_arrow_clicked(self.offsetText, opSub))
        buttonRight.clicked.connect(lambda: self.on_offset_arrow_clicked(self.offsetText, opAdd))

    def get_offset_as_int(self):
        return int(self.offsetText.text(), 16)

    def on_offset_arrow_clicked(self, offsetTextWidget, operator_func):
        offsetText = offsetTextWidget.text()
        try:
            offsetValue = int(offsetText, 16)
        except ValueError:
            offsetValue = 0
        # first parent is the widget_pointer, second parent is the ManualAddressDialog
        sizeVal = self.parent().parent().get_type_size() if hasattr(self.parent().parent(), "get_type_size") else 1
        offsetValue = operator_func(offsetValue, sizeVal)
        offsetTextWidget.setText(hex(offsetValue))

    def offset_changed(self):
        self.offset_changed_signal.emit()

    def update_deref_label(self, text: str):
        self.derefLabel.setText(text)
