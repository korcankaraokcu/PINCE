from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMenu, QMessageBox, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QContextMenuEvent
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.LoadingDialog.LoadingDialog import LoadingDialog
from GUI.Widgets.SearchInstructions.Form.SearchInstructionsWidget import Ui_Form
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import re

# represents the index of columns in search instructions table
ADDR_COL = 0
INSTR_COL = 1


class SearchInstructionsWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget, start: str = "", end: str = "") -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.lineEdit_Start.setText(start)
        self.lineEdit_End.setText(end)
        self.tableWidget_Instructions.setColumnWidth(ADDR_COL, 250)
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_Instructions.itemDoubleClicked.connect(self.tableWidget_Instructions_item_double_clicked)
        self.tableWidget_Instructions.contextMenuEvent = self.tableWidget_Instructions_context_menu_event
        guiutils.center_to_parent(self)

    def refresh_table(self) -> None:
        start_address = self.lineEdit_Start.text()
        end_address = self.lineEdit_End.text()
        regex = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        if enable_regex:
            try:
                re.compile(regex) if case_sensitive else re.compile(regex, re.IGNORECASE)
            except re.error:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
                return
        self.loading_dialog = LoadingDialog(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(regex, start_address, end_address, case_sensitive, enable_regex)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, regex: str, start_address: str, end_address: str, case_sensitive: bool, enable_regex: bool) -> list | None:
        return debugcore.search_instr(regex, start_address, end_address, case_sensitive, enable_regex)

    def apply_data(self, disas_data: list | None) -> None:
        if disas_data is None:
            return
        self.tableWidget_Instructions.setSortingEnabled(False)
        self.tableWidget_Instructions.setRowCount(0)
        self.tableWidget_Instructions.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            self.tableWidget_Instructions.setItem(row, ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Instructions.setItem(row, INSTR_COL, QTableWidgetItem(item[1]))
        self.tableWidget_Instructions.setSortingEnabled(True)

    def pushButton_Help_clicked(self) -> None:
        utilwidgets.InputDialog(self, tr.SEARCH_INSTR_HELPER, Qt.AlignmentFlag.AlignLeft, False).exec()

    def tableWidget_Instructions_item_double_clicked(self, index: QTableWidgetItem) -> None:
        row = index.row()
        address = self.tableWidget_Instructions.item(row, ADDR_COL).text()
        self.parent().disassemble_expression(utils.extract_hex_address(address))

    def tableWidget_Instructions_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            QApplication.clipboard().setText(self.tableWidget_Instructions.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_Instructions)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_instr = menu.addAction(tr.COPY_INSTR)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_instr])
        font_size = self.tableWidget_Instructions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, ADDR_COL),
            copy_instr: lambda: copy_to_clipboard(selected_row, INSTR_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass
