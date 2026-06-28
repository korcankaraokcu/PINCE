from PyQt6.QtWidgets import QMainWindow, QWidget, QMessageBox, QMenu, QFileDialog, QTreeWidgetItem
from PyQt6.QtGui import QCloseEvent, QContextMenuEvent
from GUI.Utils import guiutils
from GUI.Widgets.TraceInstructions.Form.TraceInstructionsWindow import Ui_MainWindow
from GUI.Widgets.TraceInstructions.TraceInstructionsPromptDialog import TraceInstructionsPromptDialog
from GUI.Widgets.TraceInstructions.TraceInstructionsWaitWidget import TraceInstructionsWaitWidget
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import copy
import os


class TraceInstructionsWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent: QWidget, address: str = "", prompt_dialog: bool = True) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.address = address
        self.tracer = debugcore.Tracer()
        self.treeWidget_InstructionInfo.currentItemChanged.connect(self.display_collected_data)
        self.treeWidget_InstructionInfo.itemDoubleClicked.connect(self.treeWidget_InstructionInfo_item_double_clicked)
        self.treeWidget_InstructionInfo.contextMenuEvent = self.treeWidget_InstructionInfo_context_menu_event
        self.actionOpen.triggered.connect(self.load_file)
        self.actionSave.triggered.connect(self.save_file)
        self.splitter.setStretchFactor(0, 1)
        guiutils.center_to_parent(self)
        if not prompt_dialog:
            self.showMaximized()
            return
        prompt_dialog = TraceInstructionsPromptDialog(self)
        if prompt_dialog.exec():
            params = (address,) + prompt_dialog.get_values()
            breakpoint = self.tracer.set_breakpoint(*params)
            if not breakpoint:
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(address))
                self.close()
                return
            self.showMaximized()
            self.wait_dialog = TraceInstructionsWaitWidget(self, address, self.tracer)
            self.wait_dialog.widget_closed.connect(self.show_trace_info)
            self.wait_dialog.show()
        else:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        wait_dialog = getattr(self, "wait_dialog", None)
        if wait_dialog is not None:
            wait_dialog.close()
        super().closeEvent(event)

    def display_collected_data(self, QTreeWidgetItem_current: QTreeWidgetItem) -> None:
        if QTreeWidgetItem_current is None:
            return
        self.textBrowser_RegisterInfo.clear()
        current_dict = QTreeWidgetItem_current.trace_data[1]
        if current_dict:
            for key in current_dict:
                self.textBrowser_RegisterInfo.append(str(key) + " = " + str(current_dict[key]))
            self.textBrowser_RegisterInfo.verticalScrollBar().setValue(self.textBrowser_RegisterInfo.verticalScrollBar().minimum())

    def show_trace_info(self) -> None:
        self.treeWidget_InstructionInfo.setStyleSheet("QTreeWidget::item{ height: 16px; }")
        parent = QTreeWidgetItem(self.treeWidget_InstructionInfo)
        self.treeWidget_InstructionInfo.setRootIndex(self.treeWidget_InstructionInfo.indexFromItem(parent))
        trace_tree, current_root_index = copy.deepcopy(self.tracer.trace_data)
        while current_root_index is not None:
            try:
                current_index = trace_tree[current_root_index][2][0]  # Get the first child
                current_item = trace_tree[current_index][0]
                del trace_tree[current_root_index][2][0]  # Delete it
            except IndexError:  # We've depleted the children
                current_root_index = trace_tree[current_root_index][1]  # traverse upwards
                parent = parent.parent()
                continue
            child = QTreeWidgetItem(parent)
            child.trace_data = current_item
            child.setText(0, current_item[0])
            if trace_tree[current_index][2]:  # If current item has children, traverse them
                current_root_index = current_index  # traverse downwards
                parent = child
        self.treeWidget_InstructionInfo.expandAll()

    def save_file(self) -> None:
        with guiutils.save_dialog_as_user(self, tr.SAVE_TRACE_FILE, os.path.expanduser("~"), tr.FILE_TYPES_TRACE, "trace") as file_path:
            if file_path and not utils.save_file(self.tracer.trace_data, file_path):
                QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    def load_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.OPEN_TRACE_FILE, os.path.expanduser("~"), tr.FILE_TYPES_TRACE)
        if file_path:
            content = utils.load_file(file_path)
            if content is None:
                QMessageBox.information(self, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
                return
            self.treeWidget_InstructionInfo.clear()
            self.tracer.trace_data = content
            self.show_trace_info()

    def treeWidget_InstructionInfo_context_menu_event(self, event: QContextMenuEvent) -> None:
        menu = QMenu()
        expand_all = menu.addAction(tr.EXPAND_ALL)
        collapse_all = menu.addAction(tr.COLLAPSE_ALL)
        font_size = self.treeWidget_InstructionInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            expand_all: self.treeWidget_InstructionInfo.expandAll,
            collapse_all: self.treeWidget_InstructionInfo.collapseAll,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def treeWidget_InstructionInfo_item_double_clicked(self, index: QTreeWidgetItem) -> None:
        current_item = guiutils.get_current_item(self.treeWidget_InstructionInfo)
        if not current_item:
            return
        address = utils.extract_hex_address(current_item.trace_data[0])
        if address:
            self.parent().disassemble_expression(address)
