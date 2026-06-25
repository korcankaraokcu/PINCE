from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMenu, QMessageBox, QListWidgetItem, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QContextMenuEvent
from PyQt6.QtCore import Qt, QModelIndex
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.DissectCode.DissectCode import DissectCodeDialog
from GUI.Widgets.ReferencedCalls.Form.ReferencedCallsWidget import Ui_Form
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr

# represents the index of columns in referenced calls table
REF_CALL_ADDR_COL = 0
REF_CALL_COUNT_COL = 1


class ReferencedCallsWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_CALL_ADDR_COL, 480)
        self.splitter.setStretchFactor(0, 1)
        self.listWidget_Referrers.resize(400, self.listWidget_Referrers.height())
        guiutils.center_to_parent(self)
        self.hex_len = 16 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else 8
        str_dict, jmp_dict, call_dict = debugcore.get_dissect_code_data()
        try:
            str_dict_len, jmp_dict_len, call_dict_len = len(str_dict), len(jmp_dict), len(call_dict)
        finally:
            str_dict.close()
            jmp_dict.close()
            call_dict.close()
        if str_dict_len == 0 and jmp_dict_len == 0 and call_dict_len == 0:
            if utilwidgets.InputDialog(self, tr.DISSECT_CODE).exec():
                dissect_code_dialog = DissectCodeDialog(self)
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_CALL_ADDR_COL, Qt.SortOrder.AscendingOrder)
        self.tableWidget_References.selectionModel().currentChanged.connect(self.tableWidget_References_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.tableWidget_References.itemDoubleClicked.connect(self.tableWidget_References_item_double_clicked)
        self.tableWidget_References.contextMenuEvent = self.tableWidget_References_context_menu_event
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)

    def pad_hex(self, hex_str: str) -> str:
        index = hex_str.find(" ")
        if index == -1:
            self_len = 0
        else:
            self_len = len(hex_str) - index
        return "0x" + hex_str[2:].zfill(self.hex_len + self_len)

    def refresh_table(self) -> None:
        item_list = debugcore.search_referenced_calls(
            self.lineEdit_Regex.text(), self.checkBox_CaseSensitive.isChecked(), self.checkBox_Regex.isChecked()
        )
        if item_list is None:
            QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_CALL_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_CALL_COUNT_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        call_dict = debugcore.get_dissect_code_data(False, False, True)[0]
        try:
            addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_CALL_ADDR_COL).text()
            referrers = call_dict.get(hex(int(utils.extract_hex_address(addr), 16)))
            if referrers is None:
                return
            addrs = [hex(address) for address in referrers]
            self.listWidget_Referrers.addItems([self.pad_hex(item.all) for item in debugcore.examine_expressions(addrs) if item.all])
            self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        finally:
            call_dict.close()

    def tableWidget_References_item_double_clicked(self, index: QTableWidgetItem) -> None:
        row = index.row()
        address = self.tableWidget_References.item(row, REF_CALL_ADDR_COL).text()
        self.parent().disassemble_expression(utils.extract_hex_address(address))

    def listWidget_Referrers_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.parent().disassemble_expression(utils.extract_hex_address(item.text()))

    def tableWidget_References_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            QApplication.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row, REF_CALL_ADDR_COL)}
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int) -> None:
            QApplication.clipboard().setText(self.listWidget_Referrers.item(row).text())

        selected_row = guiutils.get_current_row(self.listWidget_Referrers)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address])
        font_size = self.listWidget_Referrers.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_address: lambda: copy_to_clipboard(selected_row)}
        try:
            actions[action]()
        except KeyError:
            pass
