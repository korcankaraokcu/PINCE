from PyQt6.QtWidgets import QWidget, QMessageBox, QMenu, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QShortcut, QKeySequence
from GUI.States import states
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.Bookmark.Form.BookmarkWidget import Ui_Form
from tr.tr import TranslationConstants as tr
from libpince import debugcore, utils


# This widget is too intertwined with MemoryViewer, it will be need to be reworked if it gets used in anywhere else
class BookmarkWidget(QWidget, Ui_Form):
    bookmarked = pyqtSignal(object)
    comment_changed = pyqtSignal(object)
    double_clicked = pyqtSignal(str)
    deleted = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget.contextMenuEvent = self.listWidget_context_menu_event
        self.listWidget.currentRowChanged.connect(self.change_display)
        self.listWidget.itemDoubleClicked.connect(self.listWidget_item_double_clicked)
        self.shortcut_delete = QShortcut(QKeySequence("Del"), self)
        self.shortcut_delete.activated.connect(self.delete_record)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        self.refresh_table()
        guiutils.center_to_parent(self)

    def refresh_table(self):
        self.listWidget.clear()
        address_list = [hex(address) for address in states.bookmarks.keys()]
        if debugcore.currentpid == -1:
            self.listWidget.addItems(address_list)
        else:
            self.listWidget.addItems([item.all for item in debugcore.examine_expressions(address_list)])

    def change_display(self, row):
        if row == -1:
            return
        current_address = utils.extract_address(self.listWidget.item(row).text())
        if debugcore.currentpid == -1:
            self.lineEdit_Info.clear()
        else:
            self.lineEdit_Info.setText(debugcore.get_address_info(current_address))
        self.lineEdit_Comment.setText(states.bookmarks[int(current_address, 16)])

    def listWidget_item_double_clicked(self, item: QListWidgetItem):
        self.double_clicked.emit(utils.extract_address(item.text()))

    def exec_add_entry_dialog(self):
        entry_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_EXPRESSION, "")])
        if entry_dialog.exec():
            text = entry_dialog.get_values()[0]
            address = debugcore.examine_expression(text).address
            if not address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_EXPRESSION)
                return
            self.bookmarked.emit(int(address, 16))
            self.refresh_table()

    def exec_change_comment_dialog(self, current_address):
        self.comment_changed.emit(current_address)
        self.refresh_table()

    def listWidget_context_menu_event(self, event):
        current_item = guiutils.get_current_item(self.listWidget)
        if current_item:
            current_address = int(utils.extract_address(current_item.text()), 16)
            if current_address not in states.bookmarks:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_ENTRY)
                self.refresh_table()
                return
        else:
            current_address = None
        menu = QMenu()
        add_entry = menu.addAction(tr.ADD_ENTRY)
        change_comment = menu.addAction(tr.CHANGE_COMMENT)
        delete_record = menu.addAction(f"{tr.DELETE}[Del]")
        if current_item is None:
            guiutils.delete_menu_entries(menu, [change_comment, delete_record])
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        font_size = self.listWidget.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            add_entry: self.exec_add_entry_dialog,
            change_comment: lambda: self.exec_change_comment_dialog(current_address),
            delete_record: self.delete_record,
            refresh: self.refresh_table,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def delete_record(self):
        current_item = guiutils.get_current_item(self.listWidget)
        if not current_item:
            return
        current_address = int(utils.extract_address(current_item.text()), 16)
        self.deleted.emit(current_address)
        self.refresh_table()
