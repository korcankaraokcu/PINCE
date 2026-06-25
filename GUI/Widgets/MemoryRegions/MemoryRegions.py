from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QMenu, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QContextMenuEvent
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Widgets.MemoryRegions.Form.MemoryRegionsWidget import Ui_Form
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import os

# represents the index of columns in memory regions table
MEMORY_REGIONS_ADDR_COL = 0
MEMORY_REGIONS_PERM_COL = 1
MEMORY_REGIONS_OFFSET_COL = 2
MEMORY_REGIONS_PATH_COL = 3


class MemoryRegionsWidget(QWidget, Ui_Form):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.refresh_table()
        self.tableWidget_MemoryRegions.contextMenuEvent = self.tableWidget_MemoryRegions_context_menu_event
        self.tableWidget_MemoryRegions.itemDoubleClicked.connect(self.tableWidget_MemoryRegions_item_double_clicked)
        self.lineEdit_Search.textChanged.connect(self.filter_table)
        self.shortcut_refresh = QShortcut(QKeySequence("R"), self)
        self.shortcut_refresh.activated.connect(self.refresh_table)
        guiutils.center_to_parent(self)

    def refresh_table(self) -> None:
        memory_regions = utils.get_regions(debugcore.currentpid)
        region_dict = utils.get_region_dict(debugcore.currentpid)
        self.tableWidget_MemoryRegions.setRowCount(0)
        self.tableWidget_MemoryRegions.setRowCount(len(memory_regions))
        # The shown [index] is this region's position within get_region_dict's per name list, matching
        # utils.get_region_info so it lines up with the index bookmarks store and resolve against.
        for row, (start, end, perms, offset, _, _, path) in enumerate(memory_regions):
            file_name = os.path.split(path)[1]
            address_list = region_dict.get(file_name, [])
            try:
                region_index = address_list.index("0x" + start)
            except ValueError:
                region_index = 0
            address = start + "-" + end
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PERM_COL, QTableWidgetItem(perms))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_OFFSET_COL, QTableWidgetItem(offset))
            self.tableWidget_MemoryRegions.setItem(row, MEMORY_REGIONS_PATH_COL, QTableWidgetItem(path + f"[{region_index}]"))

        guiutils.resize_to_contents(self.tableWidget_MemoryRegions)
        self.filter_table()

    def filter_table(self) -> None:
        search_text = self.lineEdit_Search.text().lower()
        for row in range(self.tableWidget_MemoryRegions.rowCount()):
            path = self.tableWidget_MemoryRegions.item(row, MEMORY_REGIONS_PATH_COL).text()
            self.tableWidget_MemoryRegions.setRowHidden(row, search_text not in path.lower())

    def tableWidget_MemoryRegions_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            QApplication.clipboard().setText(self.tableWidget_MemoryRegions.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_MemoryRegions)

        menu = QMenu()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        copy_addresses = menu.addAction(tr.COPY_ADDRESSES)
        copy_offset = menu.addAction(tr.COPY_OFFSET)
        copy_path = menu.addAction(tr.COPY_PATH)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_addresses, copy_offset, copy_path])
        font_size = self.tableWidget_MemoryRegions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            refresh: self.refresh_table,
            copy_addresses: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_ADDR_COL),
            copy_offset: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_OFFSET_COL),
            copy_path: lambda: copy_to_clipboard(selected_row, MEMORY_REGIONS_PATH_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_MemoryRegions_item_double_clicked(self, index: QTableWidgetItem) -> None:
        row = index.row()
        address = self.tableWidget_MemoryRegions.item(row, MEMORY_REGIONS_ADDR_COL).text()
        address_int = utils.safe_str_to_int(address.split("-")[0], 16)
        self.parent().hex_dump_address(address_int)
