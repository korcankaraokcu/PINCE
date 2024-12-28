from PyQt6.QtWidgets import QDialog, QWidget, QCheckBox, QHBoxLayout, QTableWidgetItem
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Widgets.HandleSignals.Form.HandleSignalsDialog import Ui_Dialog
import json


class HandleSignalsDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, signal_data):
        super().__init__(parent)
        self.setupUi(self)
        self.signal_data = json.loads(signal_data)
        self.tableWidget_Signals.setRowCount(len(self.signal_data))
        for index, (signal, stop, pass_to_program) in enumerate(self.signal_data):
            self.tableWidget_Signals.setItem(index, 0, QTableWidgetItem(signal))
            widget, checkbox = self.create_checkbox_widget()
            self.tableWidget_Signals.setCellWidget(index, 1, widget)
            if stop:
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)
            widget, checkbox = self.create_checkbox_widget()
            self.tableWidget_Signals.setCellWidget(index, 2, widget)
            if pass_to_program:
                checkbox.setCheckState(Qt.CheckState.Checked)
            else:
                checkbox.setCheckState(Qt.CheckState.Unchecked)
        self.tableWidget_Signals.resizeColumnsToContents()
        guiutils.center_to_parent(self)

    def create_checkbox_widget(self):
        widget = QWidget()
        checkbox = QCheckBox()
        layout = QHBoxLayout(widget)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return widget, checkbox

    def get_values(self):
        signal_data = []
        for index in range(len(self.signal_data)):
            current_signal = []
            current_signal.append(self.signal_data[index][0])
            widget = self.tableWidget_Signals.cellWidget(index, 1)
            checkbox = widget.findChild(QCheckBox)
            current_signal.append(True if checkbox.checkState() == Qt.CheckState.Checked else False)
            widget = self.tableWidget_Signals.cellWidget(index, 2)
            checkbox = widget.findChild(QCheckBox)
            current_signal.append(True if checkbox.checkState() == Qt.CheckState.Checked else False)
            signal_data.append(current_signal)
        return json.dumps(signal_data)
