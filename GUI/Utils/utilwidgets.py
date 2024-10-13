from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout, QLineEdit, QLabel, QWidget, QComboBox
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils

# This module includes utility widgets that doesn't have ui files


class InputDialog(QDialog):
    """A dialog that allows for one or more QLabels and corresponding QLineEdit fields"""

    def __init__(
        self,
        parent: QWidget,
        items: str | list[tuple[str, str]],
        alignment=Qt.AlignmentFlag.AlignCenter,
        cancel_button=True,
    ):
        """
        Args:
            parent (QWidget): Parent of this dialog
            items (str | list[tuple[str, str]]): If a string is provided, a single label will be created
            If a list is provided, it must be in this format -> [(label_text, lineedit_text)]
            Providing a list will create labels and lineedits by using given texts, stacked vertically
            alignment (Qt.AlignmentFlag): Text alignment of the labels
            cancel_button (bool): Both Ok and Cancel buttons will appear if True, only Ok button will appear if False
        """
        super().__init__(parent)
        self.input_fields: list[QLineEdit] = []
        layout = QVBoxLayout()
        if isinstance(items, str):
            label = QLabel(items)
            label.setAlignment(alignment)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)
        elif isinstance(items, list):
            for label_text, edit_text in items:
                label = QLabel(label_text)
                label.setAlignment(alignment)
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(label)
                lineedit = QLineEdit(edit_text)
                layout.addWidget(lineedit)
                self.input_fields.append(lineedit)
        else:
            raise Exception("Type of items isn't str or list")
        if cancel_button:
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        else:
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        self.setLayout(layout)
        self.adjustSize()
        if self.input_fields:
            self.input_fields[0].setFocus()
        guiutils.center_to_parent(self)

    def get_values(self) -> list[str] | None:
        if self.input_fields:
            return [item.text() for item in self.input_fields]


class ComboBoxDialog(QDialog):
    """A dialog that allows for one QLabel and a corresponding QComboBox"""

    def __init__(self, parent: QWidget, label_text: str, items: list[str], current_index: int = 0):
        """
        Args:
            parent (QWidget): Parent of this dialog
            label_text (str): Text of the label
            items (list[str]): List of strings that'll be used as items of the combobox
            current_index (int): Sets the current index of the combobox
        """
        super().__init__(parent)
        layout = QVBoxLayout()
        label = QLabel(label_text)
        self.combobox = QComboBox()
        self.combobox.addItems(items)
        self.combobox.setCurrentIndex(current_index)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(label)
        layout.addWidget(self.combobox)
        layout.addWidget(button_box)
        self.setLayout(layout)
        self.adjustSize()
        guiutils.center_to_parent(self)

    def get_values(self):
        return self.combobox.currentText()
