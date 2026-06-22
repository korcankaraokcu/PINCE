from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QLabel, QWidget, QMessageBox
from GUI.Widgets.PointerScan.Form.PointerScanWindow import Ui_MainWindow
from GUI.Widgets.PointerScanFilter.PointerScanFilter import PointerScanFilterDialog
from GUI.Widgets.PointerScanSearch.PointerScanSearch import PointerScanSearchDialog
from GUI.AbstractTableModels.PointerScanModel import QPointerScanModel
from GUI.Utils import guiutils, guitypedefs
from GUI.States import states
from libpince import debugcore, typedefs, utils
from libpince.scancore import memscan
from tr.tr import TranslationConstants as tr
import os


class PointerScanWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent: QWidget, default_scan_address: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        states.process_signals.attach.connect(self.on_process_changed)
        states.process_signals.exit.connect(self.on_process_changed)
        self.actionOpen.triggered.connect(self.actionOpen_triggered)
        self.actionSaveAs.triggered.connect(self.actionSaveAs_triggered)
        self.actionScan.triggered.connect(self.scan_triggered)
        self.actionFilter.triggered.connect(self.filter_triggered)
        self.model = QPointerScanModel(self)
        self.tableView.setModel(self.model)
        self.tableView.setSortingEnabled(True)
        self.tableView.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.tableView.doubleClicked.connect(self.tableView_double_clicked)
        # Enter/Return adds every selected row (a double-click collapses multi-selection, so it can't)
        self.add_selected_shortcuts: list[QShortcut] = []
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            shortcut = QShortcut(QKeySequence(key), self.tableView)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(self.add_selected_to_address_table)
            self.add_selected_shortcuts.append(shortcut)
        self.path_count_label = QLabel()
        self.path_count_label.setContentsMargins(0, 0, 6, 0)
        self.menubar.setCornerWidget(self.path_count_label, Qt.Corner.TopRightCorner)
        self.default_scan_address = default_scan_address
        self.load_thread: guitypedefs.InterruptableWorker | None = None
        if debugcore.currentpid == -1:
            self.actionScan.setEnabled(False)
        guiutils.center_to_parent(self)

    def on_process_changed(self) -> None:
        self.actionScan.setEnabled(debugcore.currentpid != -1)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.load_thread is not None:
            self.load_thread.terminate()
            self.load_thread.wait()
        self.model.clear()
        return super().closeEvent(event)

    def actionOpen_triggered(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), tr.FILE_TYPES_POINTER_MAP
        )
        if file_path != "":
            self.load_map(file_path)

    def load_map(self, file_path: str) -> None:
        if self.load_thread is not None:
            self.load_thread.terminate()
            self.load_thread.wait()
        self.model.clear()
        self.tableView.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.load_thread = guitypedefs.InterruptableWorker(self._read_pointer_map, file_path)
        self.load_thread.signals.finished.connect(self._on_map_loaded)
        self.load_thread.signals.error.connect(self._on_map_error)
        self.load_thread.start()

    @staticmethod
    def _read_pointer_map(file_path: str) -> tuple[list[tuple[str, list[int]]], int]:
        rows = []
        offset_columns = 0
        for base, offsets in memscan.iter_pointer_map(file_path):
            rows.append((base, offsets))
            if len(offsets) > offset_columns:
                offset_columns = len(offsets)
        return rows, offset_columns

    def _on_map_loaded(self, result: tuple[list[tuple[str, list[int]]], int]) -> None:
        self.load_thread.wait()
        self.load_thread = None
        rows, offset_columns = result
        self.model.set_data(rows, offset_columns)
        self.tableView.resizeColumnsToContents()
        self.path_count_label.setText(tr.POINTER_PATH_COUNT.format(len(rows)))
        # Re-set widget to re-align it after text change.
        self.menubar.setCornerWidget(self.path_count_label, Qt.Corner.TopRightCorner)

    def _on_map_error(self, error: Exception) -> None:
        self.load_thread.wait()
        self.load_thread = None
        QMessageBox.information(self, tr.ERROR, str(error))

    def actionSaveAs_triggered(self) -> None:
        with guiutils.save_dialog_as_user(self, tr.SELECT_POINTER_MAP, os.path.expanduser("~"), "") as file_path:
            if file_path:
                with open(file_path, "w") as file:
                    file.write("".join(self.model.format_row(row) + "\n" for row in range(self.model.rowCount())))

    def tableView_double_clicked(self, index: QModelIndex) -> None:
        self.add_rows_to_address_table([index.row()])

    def add_selected_to_address_table(self) -> None:
        selected_rows = sorted({index.row() for index in self.tableView.selectionModel().selectedRows()})
        self.add_rows_to_address_table(selected_rows)

    def add_rows_to_address_table(self, rows: list[int]) -> None:
        if not rows:
            return
        main_window = self.parent()
        for row in rows:
            request = self.model.pointer_chain_request(row)
            main_window.add_entry_to_addresstable(tr.NO_DESCRIPTION, request, typedefs.ValueType())
        main_window.update_address_table()

    def scan_triggered(self) -> None:
        dialog = PointerScanSearchDialog(self, self.default_scan_address)
        if dialog.exec() and dialog.result_map_path:
            self.load_map(dialog.result_map_path)

    def filter_triggered(self) -> None:
        dialog = PointerScanFilterDialog(self)
        if dialog.exec() and dialog.result_map_path:
            self.load_map(dialog.result_map_path)
