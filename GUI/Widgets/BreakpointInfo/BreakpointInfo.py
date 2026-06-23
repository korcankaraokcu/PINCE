from PyQt6.QtWidgets import QTabWidget, QWidget, QTableWidgetItem, QMenu, QMessageBox
from PyQt6.QtGui import QKeyEvent, QContextMenuEvent
from PyQt6.QtCore import Qt, QKeyCombination
from GUI.Utils import guiutils, utilwidgets
from GUI.States import states
from GUI.Widgets.BreakpointInfo.Form.BreakpointInfoWidget import Ui_TabWidget
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr

# represents the index of columns in breakpoint table
BREAK_NUM_COL = 0
BREAK_TYPE_COL = 1
BREAK_DISP_COL = 2
BREAK_ENABLED_COL = 3
BREAK_ADDR_COL = 4
BREAK_SIZE_COL = 5
BREAK_ON_HIT_COL = 6
BREAK_HIT_COUNT_COL = 7
BREAK_COND_COL = 8


class BreakpointInfoWidget(QTabWidget, Ui_TabWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_BreakpointInfo.contextMenuEvent = self.tableWidget_BreakpointInfo_context_menu_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_BreakpointInfo.keyPressEvent_original = self.tableWidget_BreakpointInfo.keyPressEvent
        self.tableWidget_BreakpointInfo.keyPressEvent = self.tableWidget_BreakpointInfo_key_press_event
        self.tableWidget_BreakpointInfo.itemDoubleClicked.connect(self.tableWidget_BreakpointInfo_double_clicked)
        self.refresh()
        states.backend_signals.breakpoints_changed.connect(self.refresh)
        guiutils.center_to_parent(self)

    def refresh(self) -> None:
        break_info = debugcore.get_breakpoint_info()
        self.tableWidget_BreakpointInfo.setRowCount(0)
        self.tableWidget_BreakpointInfo.setRowCount(len(break_info))
        for row, item in enumerate(break_info):
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_NUM_COL, QTableWidgetItem(item.number))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_TYPE_COL, QTableWidgetItem(item.breakpoint_type))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_DISP_COL, QTableWidgetItem(item.disp))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ENABLED_COL, QTableWidgetItem(item.enabled))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ADDR_COL, QTableWidgetItem(item.address or ""))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_SIZE_COL, QTableWidgetItem(str(item.size)))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_ON_HIT_COL, QTableWidgetItem(item.on_hit))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_HIT_COUNT_COL, QTableWidgetItem(item.hit_count))
            self.tableWidget_BreakpointInfo.setItem(row, BREAK_COND_COL, QTableWidgetItem(item.condition))
        guiutils.resize_to_contents(self.tableWidget_BreakpointInfo)
        self.textBrowser_BreakpointInfo.clear()
        self.textBrowser_BreakpointInfo.setText(debugcore.send_command("info break", cli_output=True))
        self.repaint()

    def delete_breakpoint(self, breakpoint_num: int | None) -> None:
        if breakpoint_num is not None:
            debugcore.delete_breakpoint(breakpoint_num)
            self.refresh_all()

    def tableWidget_BreakpointInfo_key_press_event(self, event: QKeyEvent) -> None:
        selected_row = guiutils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            breakpoint_num = utils.safe_int_cast(self.tableWidget_BreakpointInfo.item(selected_row, BREAK_NUM_COL).text())
        else:
            breakpoint_num = None

        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete),
                    lambda: self.delete_breakpoint(breakpoint_num),
                ),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_BreakpointInfo.keyPressEvent_original(event)

    def exec_enable_count_dialog(self, breakpoint_number: int) -> None:
        hit_count_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_HIT_COUNT.format(1), "")])
        if hit_count_dialog.exec():
            count = hit_count_dialog.get_values()[0]
            try:
                count = int(count)
            except ValueError:
                QMessageBox.information(self, tr.ERROR, tr.HIT_COUNT_ASSERT_INT)
            else:
                if count < 1:
                    QMessageBox.information(self, tr.ERROR, tr.HIT_COUNT_ASSERT_LT.format(1))
                else:
                    debugcore.modify_breakpoint(breakpoint_number, typedefs.BREAKPOINT_MODIFY.ENABLE_COUNT, count=count)

    def tableWidget_BreakpointInfo_context_menu_event(self, event: QContextMenuEvent) -> None:
        selected_row = guiutils.get_current_row(self.tableWidget_BreakpointInfo)
        if selected_row != -1:
            bp_num = utils.safe_int_cast(self.tableWidget_BreakpointInfo.item(selected_row, BREAK_NUM_COL).text())
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            if current_address:
                current_address_int = utils.safe_str_to_int(current_address, 16)
            else:
                current_address_int = None
        else:
            bp_num = None
            current_address_int = None

        menu = QMenu()
        change_condition = menu.addAction(tr.CHANGE_CONDITION)
        enable = menu.addAction(tr.ENABLE)
        disable = menu.addAction(tr.DISABLE)
        enable_once = menu.addAction(tr.DISABLE_AFTER_HIT)
        enable_count = menu.addAction(tr.DISABLE_AFTER_COUNT)
        enable_delete = menu.addAction(tr.DELETE_AFTER_HIT)
        menu.addSeparator()
        delete_breakpoint = menu.addAction(f"{tr.DELETE}[Del]")
        menu.addSeparator()
        if bp_num is None:
            deletion_list = [
                change_condition,
                enable,
                disable,
                enable_once,
                enable_count,
                enable_delete,
                delete_breakpoint,
            ]
            guiutils.delete_menu_entries(menu, deletion_list)
        if current_address_int is None:
            deletion_list = [
                change_condition,
            ]
            guiutils.delete_menu_entries(menu, deletion_list)
        font_size = self.tableWidget_BreakpointInfo.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            change_condition: lambda: self.parent().add_breakpoint_condition(current_address_int),
            enable: lambda: debugcore.modify_breakpoint(bp_num, typedefs.BREAKPOINT_MODIFY.ENABLE),
            disable: lambda: debugcore.modify_breakpoint(bp_num, typedefs.BREAKPOINT_MODIFY.DISABLE),
            enable_once: lambda: debugcore.modify_breakpoint(bp_num, typedefs.BREAKPOINT_MODIFY.ENABLE_ONCE),
            enable_count: lambda: self.exec_enable_count_dialog(bp_num),
            enable_delete: lambda: debugcore.modify_breakpoint(bp_num, typedefs.BREAKPOINT_MODIFY.ENABLE_DELETE),
            delete_breakpoint: lambda: debugcore.delete_breakpoint(bp_num),
        }
        try:
            actions[action]()
        except KeyError:
            pass
        if action != -1 and action is not None:
            self.refresh_all()

    def refresh_all(self) -> None:
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        self.refresh()

    def tableWidget_BreakpointInfo_double_clicked(self, index: QTableWidgetItem) -> None:
        current_address_text = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        if current_address is None:
            # Catchpoints won't have an address, we don't need to change conditions or hex_dump
            return
        current_address_int = utils.safe_str_to_int(current_address, 16)

        if index.column() == BREAK_COND_COL:
            self.parent().add_breakpoint_condition(current_address_int)
            self.refresh_all()
        else:
            current_breakpoint_type = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_TYPE_COL).text()
            if "breakpoint" in current_breakpoint_type:
                self.parent().disassemble_expression(current_address)
            else:
                self.parent().hex_dump_address(current_address_int)
