from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QContextMenuEvent
from GUI.States import states
from GUI.Utils import guiutils
from GUI.Widgets.RestoreInstructions.Form.RestoreInstructionsWidget import Ui_Form
from tr.tr import TranslationConstants as tr
from libpince import debugcore, utils

ADDR_COL = 0
AOB_COL = 1
NAME_COL = 2


class RestoreInstructionsWidget(QWidget, Ui_Form):
    restored = pyqtSignal()
    double_clicked = pyqtSignal(str)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.tableWidget_Instructions.contextMenuEvent = self.tableWidget_Instructions_context_menu_event
        self.tableWidget_Instructions.itemDoubleClicked.connect(self.tableWidget_Instructions_double_clicked)
        self.refresh()
        states.backend_signals.instructions_changed.connect(self.refresh)
        guiutils.center_to_parent(self)

    def tableWidget_Instructions_context_menu_event(self, event: QContextMenuEvent) -> None:
        selected_row = guiutils.get_current_row(self.tableWidget_Instructions)
        menu = QMenu()
        restore_instruction = menu.addAction(tr.RESTORE_INSTRUCTION)
        if selected_row != -1:
            selected_address_text = self.tableWidget_Instructions.item(selected_row, ADDR_COL).text()
            selected_address = int(utils.extract_hex_address(selected_address_text), 16)
        else:
            guiutils.delete_menu_entries(menu, [restore_instruction])
            selected_address = None
        menu.addSeparator()
        font_size = self.tableWidget_Instructions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {restore_instruction: lambda: self.restore_instruction(selected_address)}
        try:
            actions[action]()
        except KeyError:
            pass

    def restore_instruction(self, selected_address: int) -> None:
        debugcore.restore_instruction(selected_address)
        self.refresh()
        self.restored.emit()

    def refresh(self) -> None:
        modified_instructions = debugcore.get_modified_instructions()
        self.tableWidget_Instructions.setRowCount(len(modified_instructions))
        for row, (address, aob) in enumerate(modified_instructions.items()):
            self.tableWidget_Instructions.setItem(row, ADDR_COL, QTableWidgetItem(hex(address)))
            self.tableWidget_Instructions.setItem(row, AOB_COL, QTableWidgetItem(aob))
            instr_name = utils.disassemble(aob, address, debugcore.get_inferior_arch())
            if not instr_name:
                instr_name = "??"
            self.tableWidget_Instructions.setItem(row, NAME_COL, QTableWidgetItem(instr_name))
        guiutils.resize_to_contents(self.tableWidget_Instructions)
        self.repaint()

    def tableWidget_Instructions_double_clicked(self, index: QTableWidgetItem) -> None:
        current_address_text = self.tableWidget_Instructions.item(index.row(), ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        self.double_clicked.emit(current_address)
