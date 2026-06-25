from PyQt6.QtWidgets import QWidget, QMenu, QMessageBox, QListWidgetItem, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QContextMenuEvent, QTextCursor
from PyQt6.QtCore import Qt, QModelIndex
from GUI.Utils import guiutils
from GUI.Widgets.ExamineReferrers.Form.ExamineReferrersWidget import Ui_Form
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import re


class ExamineReferrersWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget, int_address: int) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.splitter.setStretchFactor(0, 1)
        self.textBrowser_DisasInfo.resize(600, self.textBrowser_DisasInfo.height())
        self.referenced_hex = hex(int_address)
        self.collect_referrer_data()
        self.refresh_table()
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        self.listWidget_Referrers.selectionModel().currentChanged.connect(self.listWidget_Referrers_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        guiutils.center_to_parent(self)

    def collect_referrer_data(self) -> None:
        jmp_dict, call_dict = debugcore.get_dissect_code_data(False, True, True)
        self.referrer_data = []
        try:
            try:
                jmp_referrers = jmp_dict[self.referenced_hex]
            except KeyError:
                pass
            else:
                jmp_referrers = [hex(item) for item in jmp_referrers]
                self.referrer_data.extend([item.all for item in debugcore.examine_expressions(jmp_referrers) if item.all])
            try:
                call_referrers = call_dict[self.referenced_hex]
            except KeyError:
                pass
            else:
                call_referrers = [hex(item) for item in call_referrers]
                self.referrer_data.extend([item.all for item in debugcore.examine_expressions(call_referrers) if item.all])
        finally:
            jmp_dict.close()
            call_dict.close()

    def refresh_table(self) -> None:
        searched_str = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        if enable_regex:
            try:
                if case_sensitive:
                    regex = re.compile(searched_str)
                else:
                    regex = re.compile(searched_str, re.IGNORECASE)
            except:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
                return
        self.listWidget_Referrers.setSortingEnabled(False)
        self.listWidget_Referrers.clear()
        for row, item in enumerate(self.referrer_data):
            if enable_regex:
                if not regex.search(item):
                    continue
            else:
                if case_sensitive:
                    if item.find(searched_str) == -1:
                        continue
                else:
                    if item.lower().find(searched_str.lower()) == -1:
                        continue
            self.listWidget_Referrers.addItem(item)
        self.listWidget_Referrers.setSortingEnabled(True)
        self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)

    def listWidget_Referrers_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        if QModelIndex_current.row() < 0:
            return
        self.textBrowser_DisasInfo.clear()
        address = utils.extract_hex_address(self.listWidget_Referrers.item(QModelIndex_current.row()).text())
        disas_data = debugcore.disassemble(address, "+200")
        for address_info, _, instr in disas_data:
            self.textBrowser_DisasInfo.append(address_info + instr)
        cursor = self.textBrowser_DisasInfo.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.textBrowser_DisasInfo.setTextCursor(cursor)
        self.textBrowser_DisasInfo.ensureCursorVisible()

    def listWidget_Referrers_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.parent().disassemble_expression(utils.extract_hex_address(item.text()))

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
