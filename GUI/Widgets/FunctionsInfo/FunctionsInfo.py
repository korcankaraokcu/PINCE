from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMenu, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QColor, QColorConstants, QContextMenuEvent
from PyQt6.QtCore import Qt, QModelIndex
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.FunctionsInfo.Form.FunctionsInfoWidget import Ui_Form
from GUI.Widgets.LoadingDialog.LoadingDialog import LoadingDialog
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr

# represents the index of columns in function info table
ADDR_COL = 0
SYMBOL_COL = 1


class FunctionsInfoWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.textBrowser_AddressInfo.setFixedHeight(100)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_SymbolInfo.selectionModel().currentChanged.connect(self.tableWidget_SymbolInfo_current_changed)
        self.tableWidget_SymbolInfo.itemDoubleClicked.connect(self.tableWidget_SymbolInfo_item_double_clicked)
        self.tableWidget_SymbolInfo.contextMenuEvent = self.tableWidget_SymbolInfo_context_menu_event
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        guiutils.center_to_parent(self)

    def refresh_table(self) -> None:
        input_text = self.lineEdit_SearchInput.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        self.loading_dialog = LoadingDialog(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(input_text, case_sensitive)
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(self, gdb_input: str, case_sensitive: bool) -> list:
        return debugcore.search_functions(gdb_input, case_sensitive)

    def apply_data(self, output: list) -> None:
        if output is None:
            return
        self.tableWidget_SymbolInfo.setSortingEnabled(False)
        self.tableWidget_SymbolInfo.setRowCount(0)
        self.tableWidget_SymbolInfo.setRowCount(len(output))
        defined_color = QColor(QColorConstants.Green)
        defined_color.setAlpha(96)
        for row, item in enumerate(output):
            address = item[0]
            if address:
                address_item = QTableWidgetItem(address)
            else:
                address_item = QTableWidgetItem(tr.DEFINED)
                address_item.setBackground(defined_color)
            self.tableWidget_SymbolInfo.setItem(row, ADDR_COL, address_item)
            self.tableWidget_SymbolInfo.setItem(row, SYMBOL_COL, QTableWidgetItem(item[1]))
        self.tableWidget_SymbolInfo.setSortingEnabled(True)
        guiutils.resize_to_contents(self.tableWidget_SymbolInfo)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        self.textBrowser_AddressInfo.clear()
        current_row = QModelIndex_current.row()
        if current_row < 0:
            return
        address = self.tableWidget_SymbolInfo.item(current_row, ADDR_COL).text()
        if utils.extract_hex_address(address):
            symbol = self.tableWidget_SymbolInfo.item(current_row, SYMBOL_COL).text()
            for item in utils.split_symbol(symbol):
                info = debugcore.get_symbol_info(item)
                self.textBrowser_AddressInfo.append(info)
        else:
            self.textBrowser_AddressInfo.append(tr.DEFINED_SYMBOL)

    def tableWidget_SymbolInfo_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            QApplication.clipboard().setText(self.tableWidget_SymbolInfo.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_SymbolInfo)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_symbol = menu.addAction(tr.COPY_SYMBOL)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_symbol])
        font_size = self.tableWidget_SymbolInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, ADDR_COL),
            copy_symbol: lambda: copy_to_clipboard(selected_row, SYMBOL_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_SymbolInfo_item_double_clicked(self, index: QTableWidgetItem) -> None:
        address = self.tableWidget_SymbolInfo.item(index.row(), ADDR_COL).text()
        if address == tr.DEFINED:
            return
        self.parent().disassemble_expression(address)

    def pushButton_Help_clicked(self) -> None:
        utilwidgets.InputDialog(self, tr.FUNCTIONS_INFO_HELPER, Qt.AlignmentFlag.AlignLeft, False).exec()
