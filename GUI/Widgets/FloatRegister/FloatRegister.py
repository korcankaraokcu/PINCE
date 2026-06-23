from PyQt6.QtWidgets import QTabWidget, QWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.FloatRegister.Form.FloatRegisterWidget import Ui_TabWidget
from libpince import debugcore
from tr.tr import TranslationConstants as tr

# represents the index of columns in floating point table
NAME_COL = 0
VALUE_COL = 1


class FloatRegisterWidget(QTabWidget, Ui_TabWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_FPU.itemDoubleClicked.connect(self.set_register)
        self.tableWidget_XMM.itemDoubleClicked.connect(self.set_register)

    def update_registers(self) -> None:
        float_registers = list(debugcore.read_float_registers().items())
        st_registers = float_registers[:8]
        xmm_registers = float_registers[8:]
        self.tableWidget_FPU.setRowCount(len(st_registers))
        self.tableWidget_XMM.setRowCount(len(xmm_registers))
        for row, (name, value) in enumerate(st_registers):
            self.tableWidget_FPU.setItem(row, NAME_COL, QTableWidgetItem(name))
            self.tableWidget_FPU.setItem(row, VALUE_COL, QTableWidgetItem(value))
        for row, (name, value) in enumerate(xmm_registers):
            self.tableWidget_XMM.setItem(row, NAME_COL, QTableWidgetItem(name))
            self.tableWidget_XMM.setItem(row, VALUE_COL, QTableWidgetItem(value))

    def set_register(self, index: QTableWidgetItem) -> None:
        if guiutils.check_inferior_running(self):
            return
        current_row = index.row()
        if self.currentWidget() == self.FPU:
            current_table_widget = self.tableWidget_FPU
        elif self.currentWidget() == self.XMM:
            current_table_widget = self.tableWidget_XMM
        else:
            raise Exception("Current widget is invalid: " + str(self.currentWidget().objectName()))
        current_register = current_table_widget.item(current_row, NAME_COL).text()
        current_value = current_table_widget.item(current_row, VALUE_COL).text()
        label_text = tr.ENTER_REGISTER_VALUE.format(current_register.upper())
        register_dialog = utilwidgets.InputDialog(self, [(label_text, current_value)])
        if register_dialog.exec():
            if guiutils.check_inferior_running(self):
                return
            if self.currentWidget() == self.XMM:
                current_register += ".v4_float"
            debugcore.set_convenience_variable(current_register, register_dialog.get_values()[0])
            self.update_registers()
