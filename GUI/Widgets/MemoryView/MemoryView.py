from PyQt6.QtWidgets import QMainWindow, QWidget, QTableWidgetItem, QMenu, QMessageBox, QFileDialog, QAbstractItemView, QAbstractSlider, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QKeyEvent, QWheelEvent, QContextMenuEvent, QColor, QColorConstants
from PyQt6.QtCore import Qt, QEvent, QObject, QTimer, QKeyCombination, QSignalBlocker, QItemSelection, QItemSelectionModel
from GUI.AbstractTableModels.AsciiModel import AsciiModel
from GUI.AbstractTableModels.HexModel import HexModel
from GUI.Labels.RegisterLabel import RegisterLabel
from GUI.Overlays.DisassembleArrowOverlay import DisassembleArrowOverlay
from GUI.Session.session import SessionDataChanged, SessionManager, StructureManager
from GUI.States import states
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.Bookmark.Bookmark import BookmarkWidget
from GUI.Widgets.BreakpointInfo.BreakpointInfo import BreakpointInfoWidget
from GUI.Widgets.DissectCode.DissectCode import DissectCodeDialog
from GUI.Widgets.EditInstruction.EditInstruction import EditInstructionDialog
from GUI.Widgets.ExamineReferrers.ExamineReferrers import ExamineReferrersWidget
from GUI.Widgets.FloatRegister.FloatRegister import FloatRegisterWidget
from GUI.Widgets.FunctionsInfo.FunctionsInfo import FunctionsInfoWidget
from GUI.Widgets.HexEdit.HexEdit import HexEditDialog
from GUI.Widgets.LogFile.LogFile import LogFileWidget
from GUI.Widgets.ManualAddress.ManualAddress import ManualAddressDialog
from GUI.Widgets.MemoryRegions.MemoryRegions import MemoryRegionsWidget
from GUI.Widgets.MemoryView.Form.MemoryViewWindow import Ui_MainWindow_MemoryView
from GUI.Widgets.MonoDissect.MonoDissect import MonoDissectDialog
from GUI.Widgets.ReferencedCalls.ReferencedCalls import ReferencedCallsWidget
from GUI.Widgets.ReferencedStrings.ReferencedStrings import ReferencedStringsWidget
from GUI.Widgets.RestoreInstructions.RestoreInstructions import RestoreInstructionsWidget
from GUI.Widgets.SearchInstructions.SearchInstructions import SearchInstructionsWidget
from GUI.Widgets.StackTraceInfo.StackTraceInfo import StackTraceInfoWidget
from GUI.Widgets.Structures import mono_export
from GUI.Widgets.Structures.StructureEditorDialog import StructureEditorDialog
from GUI.Widgets.Structures.StructureViewDialog import StructureViewDialog
from GUI.Widgets.TraceInstructions.TraceInstructionsWindow import TraceInstructionsWindow
from GUI.Widgets.TrackBreakpoint.TrackBreakpoint import TrackBreakpointWidget
from libpince import debugcore, monocore, typedefs, utils
from libpince.utils import logger
from tr.tr import TranslationConstants as tr
from time import time
import os

# row colors for disassemble qtablewidget
PC_COLOR = QColorConstants.Blue
BOOKMARK_COLOR = QColorConstants.Cyan
BREAKPOINT_COLOR = QColorConstants.Red

# jmp/call references are drawn as arrows overlaid left of the instruction column (see DisassembleArrowOverlay)
DISAS_MAX_REFS_PER_TARGET = 12  # cap referrer arrows converging on a single visible target to avoid clutter
DISAS_MAX_ARROWS = 240  # overall safety cap on the number of arrows drawn for one view
DISAS_BYTES_PER_ROW = 15  # maximum x86 instruction length

# represents the index of columns in disassemble table
DISAS_ADDR_COL = 0
DISAS_OPCODES_COL = 1
DISAS_INSTR_COL = 2
DISAS_COMMENT_COL = 3

# represents the index of columns in stacktrace table
STACKTRACE_RETURN_ADDRESS_COL = 0
STACKTRACE_FRAME_ADDRESS_COL = 1

# represents the index of columns in stack table
STACK_POINTER_ADDRESS_COL = 0
STACK_VALUE_COL = 1
STACK_POINTS_TO_COL = 2

# represents row and column counts of Hex table
HEX_VIEW_COL_COUNT = 16
HEX_VIEW_ROW_COUNT = 42  # J-JUST A COINCIDENCE, I SWEAR!


class MemoryViewWindow(QMainWindow, Ui_MainWindow_MemoryView):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.updating_memoryview = False
        self.stack_from_base_pointer = False
        self.stacktrace_info_widget = StackTraceInfoWidget(self)
        self.float_registers_widget = FloatRegisterWidget(self)
        # Created lazily on first open and reused afterwards, so we don't leak on each open.
        self.bookmark_widget = None
        self.breakpoint_widget = None
        self.functions_info_widget = None
        self.memory_regions_widget = None
        self.restore_instructions_widget = None
        states.status_thread.process_stopped.connect(self.on_process_stop)
        states.status_thread.process_running.connect(self.on_process_running)
        states.setting_signals.changed.connect(self.set_dynamic_debug_hotkeys)
        states.session_signals.new_session.connect(self.on_new_session)
        self.session = SessionManager.get_session()
        self.set_debug_menu_shortcuts()
        self.set_dynamic_debug_hotkeys()
        self.initialize_file_context_menu()
        self.initialize_view_context_menu()
        self.initialize_debug_context_menu()
        self.initialize_tools_context_menu()
        self.initialize_help_context_menu()
        self.initialize_disassemble_view()
        self.initialize_register_view()
        self.initialize_stack_view()
        self.initialize_hex_view()

        self.label_HexView_Information.contextMenuEvent = self.label_HexView_Information_context_menu_event

        self.splitter_Disassemble_Registers.setStretchFactor(0, 1)
        # Keep the disassembler/registers pane and the hex/stack pane at a 3:2 ratio, both on first show and on later window resizes.
        self.splitter_MainMiddle.setStretchFactor(0, 3)
        self.splitter_MainMiddle.setStretchFactor(1, 2)
        self.splitter_MainMiddle.setSizes([3000, 2000])
        self.widget_StackView.resize(660, self.widget_StackView.height())
        self.widget_Registers.resize(330, self.widget_Registers.height())
        guiutils.center(self)

    def set_dynamic_debug_hotkeys(self) -> None:
        self.actionBreak.setText(tr.BREAK.format(states.hotkeys.break_hotkey.get_active_key()))
        self.actionRun.setText(tr.RUN.format(states.hotkeys.continue_hotkey.get_active_key()))
        self.actionToggle_Attach.setText(tr.TOGGLE_ATTACH.format(states.hotkeys.toggle_attach_hotkey.get_active_key()))

    def set_debug_menu_shortcuts(self) -> None:
        self.shortcut_step = QShortcut(QKeySequence("F7"), self)
        self.shortcut_step.activated.connect(self.step_instruction)
        self.shortcut_step_over = QShortcut(QKeySequence("F8"), self)
        self.shortcut_step_over.activated.connect(self.step_over_instruction)
        self.shortcut_execute_till_return = QShortcut(QKeySequence("Shift+F8"), self)
        self.shortcut_execute_till_return.activated.connect(self.execute_till_return)
        self.shortcut_toggle_breakpoint = QShortcut(QKeySequence("F5"), self)
        self.shortcut_toggle_breakpoint.activated.connect(self.toggle_breakpoint)
        self.shortcut_set_address = QShortcut(QKeySequence("Shift+F4"), self)
        self.shortcut_set_address.activated.connect(self.set_address)

    def initialize_file_context_menu(self) -> None:
        self.actionLoad_Trace.triggered.connect(self.show_trace_window)

    def initialize_debug_context_menu(self) -> None:
        self.actionBreak.triggered.connect(debugcore.interrupt_inferior)
        self.actionRun.triggered.connect(debugcore.continue_inferior)
        self.actionToggle_Attach.triggered.connect(lambda: self.parent().toggle_attach_hotkey_pressed())
        self.actionStep.triggered.connect(self.step_instruction)
        self.actionStep_Over.triggered.connect(self.step_over_instruction)
        self.actionExecute_Till_Return.triggered.connect(self.execute_till_return)

        # Ignore the "checked" bool param as we don't make use of it
        self.actionToggle_Breakpoint.triggered.connect(lambda checked: self.toggle_breakpoint())
        self.actionSet_Address.triggered.connect(self.set_address)

    def initialize_view_context_menu(self) -> None:
        self.actionBookmarks.triggered.connect(self.actionBookmarks_triggered)
        self.actionStackTrace_Info.triggered.connect(self.actionStackTrace_Info_triggered)
        self.actionBreakpoints.triggered.connect(self.actionBreakpoints_triggered)
        self.actionFunctions.triggered.connect(self.actionFunctions_triggered)
        self.actionGDB_Log_File.triggered.connect(self.actionGDB_Log_File_triggered)
        self.actionMemory_Regions.triggered.connect(self.actionMemory_Regions_triggered)
        self.actionRestore_Instructions.triggered.connect(self.actionRestore_Instructions_triggered)
        self.actionReferenced_Strings.triggered.connect(self.actionReferenced_Strings_triggered)
        self.actionReferenced_Calls.triggered.connect(self.actionReferenced_Calls_triggered)

    def initialize_tools_context_menu(self) -> None:
        self.actionInject_so_file.triggered.connect(self.actionInject_so_file_triggered)
        self.actionInject_DLL_file.triggered.connect(self.actionInject_DLL_file_triggered)
        self.actionCall_Function.triggered.connect(self.actionCall_Function_triggered)
        self.actionSearch_Instructions.triggered.connect(self.actionSearch_Instructions_triggered)
        self.actionDissect_Code.triggered.connect(self.actionDissect_Code_triggered)
        self.actionDissect_Mono.triggered.connect(self.actionDissect_Mono_triggered)
        self.actionStructures.triggered.connect(self.actionStructures_triggered)
        self.actionLibpince_Engine.triggered.connect(self.actionLibpince_Engine_triggered)

    def initialize_help_context_menu(self) -> None:
        self.actionLibpince.triggered.connect(self.actionLibpince_triggered)

    def initialize_register_view(self) -> None:
        self.pushButton_ShowFloatRegisters.clicked.connect(self.pushButton_ShowFloatRegisters_clicked)
        for register_label in self.findChildren(RegisterLabel):
            register_label.hex_view_requested.connect(lambda address: self.hex_dump_address(utils.safe_str_to_int(address, 16)))
            register_label.disassemble_requested.connect(self.disassemble_expression)
        if guiutils.check_inferior_running(self, show_message=False):
            self.pushButton_ShowFloatRegisters.setEnabled(False)

    def initialize_stack_view(self) -> None:
        self.stackedWidget_StackScreens.setCurrentWidget(self.StackTrace)
        self.tableWidget_StackTrace.setColumnWidth(STACKTRACE_RETURN_ADDRESS_COL, 350)

        self.tableWidget_Stack.contextMenuEvent = self.tableWidget_Stack_context_menu_event
        self.tableWidget_StackTrace.contextMenuEvent = self.tableWidget_StackTrace_context_menu_event
        self.tableWidget_Stack.itemDoubleClicked.connect(self.tableWidget_Stack_double_click)
        self.tableWidget_StackTrace.itemDoubleClicked.connect(self.tableWidget_StackTrace_double_click)

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Stack_keyPressEvent_original = self.tableWidget_Stack.keyPressEvent
        self.tableWidget_Stack.keyPressEvent = self.tableWidget_Stack_key_press_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_StackTrace_keyPressEvent_original = self.tableWidget_StackTrace.keyPressEvent
        self.tableWidget_StackTrace.keyPressEvent = self.tableWidget_StackTrace_key_press_event

    def initialize_disassemble_view(self) -> None:
        self.tableWidget_Disassemble.setColumnWidth(DISAS_ADDR_COL, 400)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_OPCODES_COL, 350)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_INSTR_COL, 450)

        # Draw jmp/call references as arrows overlaid on the left of the instruction column.
        self.disassemble_arrow_overlay = DisassembleArrowOverlay(self.tableWidget_Disassemble, DISAS_INSTR_COL)
        self.disassemble_arrow_overlay.follow_requested.connect(self.disassemble_arrow_follow)
        # The most rows any viewport could ever need, computed once from the desktop resolution.
        # Sizing for the largest possible screen keeps a later resize or splitter drag from underfilling the table.
        row_height = max(1, self.tableWidget_Disassemble.verticalHeader().defaultSectionSize())
        screen_height = max(screen.size().height() for screen in QApplication.screens())
        self.disassemble_screen_rows = max(20, screen_height // row_height)

        self.disassemble_last_selected_address_int = 0
        self.disassemble_selected_addresses: set[int] = set()
        self.disassemble_currently_displayed_address = "0"
        self.widget_Disassemble.wheelEvent = self.widget_Disassemble_wheel_event

        self.bDisassemblyScrolling = False  # rejects new scroll requests while scrolling
        self.tableWidget_Disassemble_wheelEvent_original = self.tableWidget_Disassemble.wheelEvent
        self.tableWidget_Disassemble.wheelEvent = QEvent.ignore
        self.verticalScrollBar_Disassemble.wheelEvent = QEvent.ignore
        self.verticalScrollBar_Disassemble.sliderChange = self.disassemble_scrollbar_sliderchanged
        guiutils.center_scroll_bar(self.verticalScrollBar_Disassemble)

        # Format: [address1, address2, ...]
        self.tableWidget_Disassemble.travel_history = []

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_Disassemble_keyPressEvent_original = self.tableWidget_Disassemble.keyPressEvent
        self.tableWidget_Disassemble.keyPressEvent = self.tableWidget_Disassemble_key_press_event
        self.tableWidget_Disassemble.contextMenuEvent = self.tableWidget_Disassemble_context_menu_event

        self.tableWidget_Disassemble.itemDoubleClicked.connect(self.tableWidget_Disassemble_item_double_clicked)
        self.tableWidget_Disassemble.itemSelectionChanged.connect(self.tableWidget_Disassemble_item_selection_changed)

    def initialize_hex_view(self) -> None:
        # Determines where selection starts and ends
        self.hex_selection_start = 0
        self.hex_selection_end = 0
        # Actual start and end addresses of the selection
        self.hex_selection_address_begin = 0
        self.hex_selection_address_end = 0
        self.hex_view_current_region = typedefs.tuple_region_info(0, 0, None, None, None)
        # Number of rows shown is recomputed from the viewport height (see adjust_hex_view_rows).
        self.hex_row_count = HEX_VIEW_ROW_COUNT
        self.hex_model = HexModel(self.hex_row_count, HEX_VIEW_COL_COUNT)
        self.ascii_model = AsciiModel(self.hex_row_count, HEX_VIEW_COL_COUNT)
        self.tableView_HexView_Hex.setModel(self.hex_model)
        self.tableView_HexView_Ascii.setModel(self.ascii_model)
        # Adjust cell sizes after setting model to ensure correct size
        self.tableView_HexView_Hex.adjust_cell_size(2)
        self.tableView_HexView_Ascii.adjust_cell_size(1)

        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        # Saving the original function because super() doesn't work when we override functions like this
        self.widget_HexView_keyPressEvent_original = self.widget_HexView.keyPressEvent
        self.widget_HexView.keyPressEvent = self.widget_HexView_key_press_event

        self.tableView_HexView_Hex.contextMenuEvent = self.widget_HexView_context_menu_event
        self.tableView_HexView_Ascii.contextMenuEvent = self.widget_HexView_context_menu_event

        self.bHexViewScrolling = False  # rejects new scroll requests while scrolling
        self.verticalScrollBar_HexView.wheelEvent = QEvent.ignore
        self.verticalScrollBar_HexView.sliderChange = self.hex_view_scrollbar_sliderchanged
        guiutils.center_scroll_bar(self.verticalScrollBar_HexView)

        self.tableWidget_HexView_Address.wheelEvent = QEvent.ignore
        self.tableWidget_HexView_Address.setAutoScroll(False)
        self.tableWidget_HexView_Address.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)

        self.tableView_HexView_Hex.selectionModel().selectionChanged.connect(self.hex_view_selection_changed)
        self.tableView_HexView_Ascii.selectionModel().selectionChanged.connect(self.hex_view_selection_changed)
        self.tableView_HexView_Hex.scroll_requested.connect(self.hex_view_scroll_by_row)
        self.tableView_HexView_Ascii.scroll_requested.connect(self.hex_view_scroll_by_row)
        self.tableView_HexView_Hex.page_scroll_requested.connect(self.hex_view_page_scroll)
        self.tableView_HexView_Ascii.page_scroll_requested.connect(self.hex_view_page_scroll)

        self.scrollArea_Hex.viewport().installEventFilter(self)
        self.scrollArea_Hex.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_Hex.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tableWidget_HexView_Address.verticalHeader().setMinimumSectionSize(self.tableView_HexView_Hex.verticalHeader().minimumSectionSize())
        self.tableWidget_HexView_Address.verticalHeader().setDefaultSectionSize(self.tableView_HexView_Hex.verticalHeader().defaultSectionSize())
        self.tableWidget_HexView_Address.verticalHeader().setMaximumSectionSize(self.tableView_HexView_Hex.verticalHeader().maximumSectionSize())

        self.hex_update_timer = QTimer(self, timeout=self.hex_update_loop)
        self.hex_update_timer.start(200)

    def show_trace_window(self) -> None:
        TraceInstructionsWindow(self, prompt_dialog=False)

    def step_instruction(self) -> None:
        if not (
            debugcore.currentpid == -1
            or debugcore.driving_inferior
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.step_instruction()

    def step_over_instruction(self) -> None:
        if not (
            debugcore.currentpid == -1
            or debugcore.driving_inferior
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.step_over_instruction()

    def execute_till_return(self) -> None:
        if not (
            debugcore.currentpid == -1
            or debugcore.driving_inferior
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or self.updating_memoryview
        ):
            debugcore.execute_till_return()

    def get_disassemble_row(self, no_selection_row: int = -1) -> int:
        selected_rows = self.tableWidget_Disassemble.selectionModel().selectedRows()
        if not selected_rows:
            return no_selection_row
        return selected_rows[0].row() if len(selected_rows) == 1 else -1

    def set_address(self) -> None:
        if guiutils.check_inferior_running(self):
            return
        selected_row = self.get_disassemble_row()
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        debugcore.set_convenience_variable("pc", current_address)
        self.refresh_disassemble_view()

    def edit_instruction(self) -> None:
        selected_row = self.get_disassemble_row()
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        bytes_aob = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        EditInstructionDialog(self, current_address, bytes_aob).exec()

    def nop_instruction(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = self.get_disassemble_row()
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = utils.safe_str_to_int(current_address, 16)
        if current_address_int == 0:
            return
        array_of_bytes = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        debugcore.nop_instruction(current_address_int, len(array_of_bytes.split()))
        self.refresh_disassemble_view()

    def toggle_breakpoint(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = self.get_disassemble_row()
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = utils.safe_str_to_int(current_address, 16)
        if current_address_int == 0:
            return
        breakpoints = debugcore.get_breakpoints_in_range(current_address_int)
        if breakpoints:
            for breakpoint in breakpoints:
                debugcore.delete_breakpoint(utils.safe_int_cast(breakpoint.number))
        else:
            if not debugcore.add_breakpoint(current_address):
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(current_address))
        self.refresh_disassemble_view()

    def toggle_watchpoint(self, address: int, length: int, watchpoint_type: int = typedefs.WATCHPOINT_TYPE.BOTH) -> None:
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(address, length)
        if not breakpoints:
            created_watchpoints = debugcore.add_watchpoint(hex(address), length, watchpoint_type)
            if not created_watchpoints:
                QMessageBox.information(self, tr.ERROR, tr.WATCHPOINT_FAILED.format(hex(address)))
        else:
            for bp in breakpoints:
                debugcore.delete_breakpoint(utils.safe_int_cast(bp.number))
        self.refresh_hex_view()

    def label_HexView_Information_context_menu_event(self, event: QContextMenuEvent) -> None:
        if debugcore.currentpid == -1:
            return

        def copy_to_clipboard() -> None:
            QApplication.clipboard().setText(self.label_HexView_Information.text())

        menu = QMenu()
        copy_label = menu.addAction(tr.COPY_CLIPBOARD)
        font_size = self.label_HexView_Information.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {copy_label: copy_to_clipboard}
        try:
            actions[action]()
        except KeyError:
            pass

    def widget_HexView_context_menu_event(self, event: QContextMenuEvent) -> None:
        if debugcore.currentpid == -1:
            return
        addr = self.hex_selection_address_begin
        length = self.get_hex_selection_length()
        menu = QMenu()
        edit = menu.addAction(tr.EDIT)
        menu.addSeparator()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        add_address = menu.addAction(f"{tr.ADD_TO_ADDRESS_LIST}[Ctrl+A]")
        menu.addSeparator()
        copy_selection = menu.addAction(f"{tr.COPY}[Ctrl+C]")
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        watchpoint_menu = menu.addMenu(tr.SET_WATCHPOINT)
        watchpoint_write = watchpoint_menu.addAction(tr.WRITE_ONLY)
        watchpoint_read = watchpoint_menu.addAction(tr.READ_ONLY)
        watchpoint_both = watchpoint_menu.addAction(tr.BOTH)
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        delete_breakpoint = menu.addAction(tr.DELETE_BREAKPOINT)
        if not debugcore.get_breakpoints_in_range(addr, length):
            guiutils.delete_menu_entries(menu, [add_condition, delete_breakpoint])
        else:
            guiutils.delete_menu_entries(menu, [watchpoint_menu.menuAction()])
        font_size = self.widget_HexView.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            edit: self.exec_hex_view_edit_dialog,
            go_to: self.exec_hex_view_go_to_dialog,
            disassemble: lambda: self.disassemble_expression(hex(addr)),
            add_address: self.exec_hex_view_add_address_dialog,
            copy_selection: self.copy_hex_view_selection,
            refresh: self.refresh_hex_view,
            watchpoint_write: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.WRITE_ONLY),
            watchpoint_read: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.READ_ONLY),
            watchpoint_both: lambda: self.toggle_watchpoint(addr, length, typedefs.WATCHPOINT_TYPE.BOTH),
            add_condition: lambda: self.add_breakpoint_condition(addr, length),
            delete_breakpoint: lambda: self.toggle_watchpoint(addr, length),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def exec_hex_view_edit_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        HexEditDialog(self, self.hex_selection_address_begin, self.get_hex_selection_length()).exec()
        self.refresh_hex_view()

    def exec_hex_view_go_to_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        go_to_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_EXPRESSION, hex(self.hex_selection_address_begin))])
        if go_to_dialog.exec():
            expression = go_to_dialog.get_values()[0]
            dest_address = debugcore.examine_expression(expression).address
            if not dest_address:
                QMessageBox.information(self, tr.ERROR, tr.INVALID.format(expression))
                return
            self.hex_dump_address(int(dest_address, 16))

    def exec_hex_view_add_address_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        vt = typedefs.ByteArrayValueType(self.get_hex_selection_length())
        address_dialog = ManualAddressDialog(self, address=hex(self.hex_selection_address_begin), value_type=vt)
        if address_dialog.exec():
            desc, address, vt = address_dialog.get_values()
            self.parent().add_entry_to_addresstable(desc, address, vt)
            self.parent().update_address_table()

    def copy_hex_view_selection(self) -> None:
        data = debugcore.hex_dump(self.hex_selection_address_begin, self.get_hex_selection_length())
        if self.focusWidget() == self.tableView_HexView_Ascii:
            display_text = utils.aob_to_str(data)
        else:
            display_text = " ".join(data)
        QApplication.clipboard().setText(display_text)

    def hex_view_scroll_up(self) -> None:
        self.verticalScrollBar_HexView.setValue(self.verticalScrollBar_HexView.minimum())

    def hex_view_scroll_down(self) -> None:
        self.verticalScrollBar_HexView.setValue(self.verticalScrollBar_HexView.maximum())

    def hex_view_page_scroll(self, direction: int) -> None:
        if direction < 0:
            self.hex_view_scroll_up()
        else:
            self.hex_view_scroll_down()

    def hex_view_scroll_by_row(self, direction: int) -> None:
        if debugcore.currentpid == -1:
            return
        offset = direction * HEX_VIEW_COL_COUNT
        self.hex_selection_start += offset
        self.hex_selection_end += offset
        self.hex_selection_address_begin += offset
        self.hex_selection_address_end += offset
        self.hex_dump_address(self.hex_model.current_address + offset)

    def hex_view_scrollbar_sliderchanged(self, event: QAbstractSlider.SliderChange) -> None:
        if self.bHexViewScrolling:
            return
        self.bHexViewScrolling = True
        maximum = self.verticalScrollBar_HexView.maximum()
        minimum = self.verticalScrollBar_HexView.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_HexView.value()
        current_address = self.hex_model.current_address
        if current_value < midst:
            next_address = current_address - states.bytes_per_scroll
        else:
            next_address = current_address + states.bytes_per_scroll
        self.hex_dump_address(next_address)
        guiutils.center_scroll_bar(self.verticalScrollBar_HexView)
        self.bHexViewScrolling = False

    def disassemble_scroll_up(self) -> None:
        self.verticalScrollBar_Disassemble.setValue(self.verticalScrollBar_Disassemble.minimum())

    def disassemble_scroll_down(self) -> None:
        self.verticalScrollBar_Disassemble.setValue(self.verticalScrollBar_Disassemble.maximum())

    def disassemble_scrollbar_sliderchanged(self, even: QAbstractSlider.SliderChange) -> None:
        if self.bDisassemblyScrolling:
            return
        self.bDisassemblyScrolling = True
        maximum = self.verticalScrollBar_Disassemble.maximum()
        minimum = self.verticalScrollBar_Disassemble.minimum()
        midst = (maximum + minimum) / 2
        current_value = self.verticalScrollBar_Disassemble.value()
        if current_value < midst:
            self.tableWidget_Disassemble_scroll("previous", states.instructions_per_scroll)
        else:
            self.tableWidget_Disassemble_scroll("next", states.instructions_per_scroll)
        guiutils.center_scroll_bar(self.verticalScrollBar_Disassemble)
        self.bDisassemblyScrolling = False

    def hex_view_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        sender_selection_model: QItemSelectionModel = self.sender()
        sender_selection = sorted([(idx.row(), idx.column()) for idx in sender_selection_model.selectedIndexes()])
        if not sender_selection:
            return
        first_selection = sender_selection[0]
        last_selection = sender_selection[-1]
        hex_start = self.address_to_hex_point(self.hex_selection_start)
        hex_end = self.address_to_hex_point(self.hex_selection_end)
        hex_start, hex_end = self.fix_selection_at_borders(hex_start, hex_end)
        if len(sender_selection) == 1:
            hex_start = first_selection
            hex_end = first_selection
        else:
            # Selection ends in top left
            if last_selection == hex_start:
                hex_end = first_selection
            # Selection ends in top right
            elif last_selection[0] == hex_start[0]:
                hex_end = (first_selection[0], last_selection[1])
            # Selection ends in bottom left
            elif last_selection[1] == hex_start[1]:
                hex_end = (last_selection[0], first_selection[1])
            # Selection ends in bottom right
            else:
                hex_end = last_selection
        if hex_start < hex_end:
            address_begin = hex_start
            address_end = hex_end
        else:
            address_begin = hex_end
            address_end = hex_start
        self.hex_selection_start = self.hex_point_to_address(hex_start)
        self.hex_selection_end = self.hex_point_to_address(hex_end)
        self.hex_selection_address_begin = self.hex_point_to_address(address_begin)
        self.hex_selection_address_end = self.hex_point_to_address(address_end)
        self.handle_hex_selection()

    def handle_hex_selection(self) -> None:
        hex_view = self.tableView_HexView_Hex
        ascii_view = self.tableView_HexView_Ascii
        addr_view = self.tableWidget_HexView_Address
        hex_enabled = hex_view.updatesEnabled()
        ascii_enabled = ascii_view.updatesEnabled()
        addr_enabled = addr_view.updatesEnabled()
        hex_view.setUpdatesEnabled(False)
        ascii_view.setUpdatesEnabled(False)
        addr_view.setUpdatesEnabled(False)
        hex_selection_model = hex_view.selectionModel()
        ascii_selection_model = ascii_view.selectionModel()
        start_point = self.address_to_hex_point(self.hex_selection_address_begin)
        end_point = self.address_to_hex_point(self.hex_selection_address_end)
        with QSignalBlocker(hex_selection_model), QSignalBlocker(ascii_selection_model):
            hex_selection_model.clearSelection()
            ascii_selection_model.clearSelection()
            addr_view.clearSelection()
            if start_point or end_point:
                start_point, end_point = self.fix_selection_at_borders(start_point, end_point)
                model = hex_selection_model.model()
                selection = QItemSelection()
                if start_point[0] == end_point[0]:
                    selection.select(model.index(*start_point), model.index(*end_point))
                else:
                    # First line
                    selection.select(model.index(*start_point), model.index(start_point[0], HEX_VIEW_COL_COUNT - 1))
                    # Middle
                    if end_point[0] - start_point[0] > 1:
                        selection.select(
                            model.index(start_point[0] + 1, 0),
                            model.index(end_point[0] - 1, HEX_VIEW_COL_COUNT - 1),
                        )
                    # Last line
                    selection.select(model.index(end_point[0], 0), model.index(*end_point))
                hex_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                ascii_selection_model.select(selection, QItemSelectionModel.SelectionFlag.Select)
                addr_view.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
                for row in range(start_point[0], end_point[0] + 1):
                    addr_view.selectRow(row)
                addr_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        hex_view.setUpdatesEnabled(hex_enabled)
        ascii_view.setUpdatesEnabled(ascii_enabled)
        addr_view.setUpdatesEnabled(addr_enabled)

    def hex_point_to_address(self, point: tuple[int, int]) -> int:
        address = self.hex_model.current_address + point[0] * HEX_VIEW_COL_COUNT + point[1]
        return utils.modulo_address(address, debugcore.inferior_arch)

    def address_to_hex_point(self, address: int) -> tuple[int, int] | None:
        diff = address - self.hex_model.current_address
        if 0 <= diff < self.hex_row_count * HEX_VIEW_COL_COUNT:
            return diff // HEX_VIEW_COL_COUNT, diff % HEX_VIEW_COL_COUNT

    def get_hex_selection_length(self) -> int:
        return self.hex_selection_address_end - self.hex_selection_address_begin + 1

    def fix_selection_at_borders(
        self, start_point: tuple[int, int] | None, end_point: tuple[int, int] | None
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        if not start_point:
            start_point = (0, 0)
        if not end_point:
            end_point = (self.hex_row_count - 1, HEX_VIEW_COL_COUNT - 1)
        return start_point, end_point

    def eventFilter(self, obj: QObject | None, event: QEvent | None) -> bool:
        if obj is self.scrollArea_Hex.viewport() and event.type() == QEvent.Type.Resize:
            self.adjust_hex_view_rows()
        return super().eventFilter(obj, event)

    def adjust_hex_view_rows(self) -> None:
        row_height = self.tableView_HexView_Hex.verticalHeader().defaultSectionSize()
        if row_height <= 0:
            return
        available = self.scrollArea_Hex.viewport().height() - self.tableView_HexView_Hex.y()
        new_count = max(1, available // row_height)
        if new_count == self.hex_row_count:
            return
        self.hex_row_count = new_count
        self.hex_model.set_row_count(new_count)
        self.ascii_model.set_row_count(new_count)
        self.hex_dump_address(self.hex_model.current_address)

    def hex_update_loop(self) -> None:
        offset = self.hex_row_count * HEX_VIEW_COL_COUNT
        if debugcore.currentpid == -1 or states.exiting:
            updated_array = ["??"] * offset
        else:
            updated_array = debugcore.hex_dump(self.hex_model.current_address, offset)
        self.hex_model.update_loop(updated_array)
        self.ascii_model.update_loop(updated_array)

    # TODO: Consider merging HexView_Address, HexView_Hex and HexView_Ascii into one UI class
    # TODO: Move this function to that class if that happens
    # TODO: Also consider moving shared fields of HexView and HexModel to that class(such as HexModel.current_address)
    def hex_dump_address(self, int_address: int, offset: int | None = None) -> None:
        if debugcore.currentpid == -1:
            return
        if offset is None:
            offset = self.hex_row_count * HEX_VIEW_COL_COUNT
        self.tableView_HexView_Hex.setUpdatesEnabled(False)
        self.tableView_HexView_Ascii.setUpdatesEnabled(False)
        self.tableWidget_HexView_Address.setUpdatesEnabled(False)
        int_address = utils.modulo_address(int_address, debugcore.inferior_arch)
        if not (self.hex_view_current_region.start <= int_address < self.hex_view_current_region.end):
            info = utils.get_region_info(debugcore.currentpid, int_address)
            if info:
                self.hex_view_current_region = info
                self.label_HexView_Information.setText(tr.REGION_INFO.format(info.perms, hex(info.start), hex(info.end), info.file_name))
            else:
                self.hex_view_current_region = typedefs.tuple_region_info(0, 0, None, None, None)
                self.label_HexView_Information.setText(tr.INVALID_REGION)
        self.tableWidget_HexView_Address.setRowCount(0)
        self.tableWidget_HexView_Address.setRowCount(self.hex_row_count)
        for row, current_offset in enumerate(range(self.hex_row_count)):
            row_address = hex(utils.modulo_address(int_address + current_offset * 16, debugcore.inferior_arch))
            self.tableWidget_HexView_Address.setItem(row, 0, QTableWidgetItem(utils.upper_hex(row_address)))
        tableWidget_HexView_column_size = self.tableWidget_HexView_Address.sizeHintForColumn(0) + 5
        self.tableWidget_HexView_Address.setMaximumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setMinimumWidth(tableWidget_HexView_column_size)
        self.tableWidget_HexView_Address.setColumnWidth(0, tableWidget_HexView_column_size)
        data_array = debugcore.hex_dump(int_address, offset)
        breakpoint_info = debugcore.get_breakpoint_info()
        self.hex_model.refresh(int_address, offset, data_array, breakpoint_info)
        self.ascii_model.refresh(int_address, offset, data_array, breakpoint_info)
        self.handle_hex_selection()
        self.tableWidget_HexView_Address.setUpdatesEnabled(True)
        self.tableView_HexView_Ascii.setUpdatesEnabled(True)
        self.tableView_HexView_Hex.setUpdatesEnabled(True)

    def refresh_hex_view(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.tableWidget_HexView_Address.rowCount() == 0:
            entry_point = debugcore.find_entry_point()
            if not entry_point:
                # **Shrugs**
                entry_point = "0x00400000"
            self.hex_dump_address(int(entry_point, 16))
            self.tableView_HexView_Hex.resize_to_contents()
            self.tableView_HexView_Ascii.resize_to_contents()
        else:
            self.hex_dump_address(self.hex_model.current_address)

    # returns True if the given expression is disassembled correctly, False if not
    def disassemble_expression(self, expression: str, append_history: bool = True) -> bool | None:
        if debugcore.currentpid == -1:
            return
        # We ask for a generous byte span that decodes to at least a screenful of rows at any instruction density,
        # because gdb sizes disassembly by byte length, not by row count.
        # One forward call spares us find_closest counting rows, keeps the target on row 0 and lets disas_data[0] double as the examine_expression.
        span = self.disassemble_screen_rows * DISAS_BYTES_PER_ROW
        disas_data = debugcore.disassemble(expression, "+" + str(span))
        if not disas_data:
            QMessageBox.information(QApplication.focusWidget(), tr.ERROR, tr.EXPRESSION_ACCESS_ERROR.format(expression))
            return False
        # In dense code that span decodes to many more rows than fit.
        # We keep only screen_rows, the most any viewport could show, to avoid building rows that would never be visible.
        disas_data = disas_data[: self.disassemble_screen_rows]
        program_counter = debugcore.examine_expression("$pc").address
        program_counter_int = int(program_counter, 16) if program_counter else None
        row_color = {}
        breakpoint_info = debugcore.get_breakpoint_info()

        # TODO: Change this nonsense when the huge refactorization happens
        current_first_address = utils.extract_hex_address(disas_data[0][0])  # address of first list entry
        try:
            previous_first_address = utils.extract_hex_address(self.tableWidget_Disassemble.item(0, DISAS_ADDR_COL).text())
        except AttributeError:
            previous_first_address = current_first_address

        jmp_dict, call_dict = debugcore.get_dissect_code_data(False, True, True)
        # Reference arrows are only meaningful within a local range, so we bound the endpoints to the displayed window
        # and let DisassembleArrowOverlay clamp what's off-screen.
        window_first_int = utils.safe_str_to_int(current_first_address, 16)
        window_last_int = utils.safe_str_to_int(utils.extract_hex_address(disas_data[-1][0]), 16)
        arrow_span = max(window_last_int - window_first_int, 0)
        near_lo = window_first_int - arrow_span - 1
        near_hi = window_last_int + arrow_span + 1
        arrows: set[tuple[int, int, str]] = set()  # (source_address, target_address, kind)
        address_to_row: dict[int, int] = {}
        self.tableWidget_Disassemble.blockSignals(True)
        try:
            self.tableWidget_Disassemble.setRowCount(0)
            self.tableWidget_Disassemble.setRowCount(len(disas_data))
            self.tableWidget_Disassemble.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            for row, (address_info, bytes_aob, instruction) in enumerate(disas_data):
                comment = ""
                current_address_str = utils.extract_hex_address(address_info)
                current_address = utils.safe_str_to_int(current_address_str, 16)
                address_to_row[current_address] = row
                # dissect stores keys as unpadded hex but extract_hex_address keeps gdb's leading zeros, normalize first
                referrer_key = hex(current_address)
                jmp_ref_exists = False
                call_ref_exists = False
                try:
                    jmp_referrers = jmp_dict[referrer_key]
                    jmp_ref_exists = True
                except KeyError:
                    pass
                try:
                    call_referrers = call_dict[referrer_key]
                    call_ref_exists = True
                except KeyError:
                    pass
                if jmp_ref_exists or call_ref_exists:
                    tooltip_text = f"{tr.REFERENCED_BY}\n"
                    ref_count = 0
                    if jmp_ref_exists:
                        for referrer in jmp_referrers:
                            if ref_count > 30:
                                break
                            tooltip_text += "\n" + hex(referrer) + "(" + jmp_referrers[referrer] + ")"
                            ref_count += 1
                    if call_ref_exists:
                        for referrer in call_referrers:
                            if ref_count > 30:
                                break
                            tooltip_text += "\n" + hex(referrer) + "(call)"
                            ref_count += 1
                    if ref_count > 30:
                        tooltip_text += "\n..."
                    tooltip_text += f"\n\n{tr.SEE_REFERRERS}"
                    # An arrow is drawn from each nearby referrer (caller) into this row (the target).
                    # Referrers that are out of sight get clamped to the viewport edge by DisassembleArrowOverlay.
                    arrow_refs = 0
                    if jmp_ref_exists:
                        for referrer in jmp_referrers:
                            if arrow_refs >= DISAS_MAX_REFS_PER_TARGET:
                                break
                            if near_lo <= referrer <= near_hi:
                                arrows.add((referrer, current_address, "jmp"))
                                arrow_refs += 1
                    if call_ref_exists:
                        for referrer in call_referrers:
                            if arrow_refs >= DISAS_MAX_REFS_PER_TARGET:
                                break
                            if near_lo <= referrer <= near_hi:
                                arrows.add((referrer, current_address, "call"))
                                arrow_refs += 1
                    real_ref_count = 0
                    if jmp_ref_exists:
                        real_ref_count += len(jmp_referrers)
                    if call_ref_exists:
                        real_ref_count += len(call_referrers)
                    address_info = "{" + str(real_ref_count) + "}" + address_info
                # An arrow is also drawn from this row (the caller) to its target when the instruction is a direct jmp/call.
                # The target may be out of sight, the overlay clamps it to an edge if so.
                followed_address = utils.instruction_follow_address(instruction)
                if followed_address:
                    target_int = utils.safe_str_to_int(followed_address, 16)
                    if target_int != current_address and near_lo <= target_int <= near_hi:
                        arrows.add((current_address, target_int, "call" if instruction.startswith("call") else "jmp"))
                if current_address == program_counter_int:
                    address_info = ">>>" + address_info
                    try:
                        row_color[row].append(PC_COLOR)
                    except KeyError:
                        row_color[row] = [PC_COLOR]

                for bookmark_item in self.session.pct_bookmarks.keys():
                    if current_address == bookmark_item:
                        try:
                            row_color[row].append(BOOKMARK_COLOR)
                        except KeyError:
                            row_color[row] = [BOOKMARK_COLOR]
                        address_info = "(M)" + address_info
                        comment = self.session.pct_bookmarks[bookmark_item]["comment"]
                        break
                for breakpoint in breakpoint_info:
                    # Catchpoints won't have an address
                    if type(breakpoint.address) != str:
                        continue
                    int_breakpoint_address = utils.safe_str_to_int(breakpoint.address, 16)
                    if current_address == int_breakpoint_address:
                        try:
                            row_color[row].append(BREAKPOINT_COLOR)
                        except KeyError:
                            row_color[row] = [BREAKPOINT_COLOR]
                        breakpoint_mark = "(B"
                        if breakpoint.enabled == "n":
                            breakpoint_mark += "-disabled"
                        else:
                            if breakpoint.disp != "keep":
                                breakpoint_mark += "-" + breakpoint.disp
                            if breakpoint.enable_count:
                                breakpoint_mark += "-" + breakpoint.enable_count
                        breakpoint_mark += ")"
                        address_info = breakpoint_mark + address_info
                        break
                if current_address in self.disassemble_selected_addresses:
                    self.tableWidget_Disassemble.selectRow(row)
                addr_item = QTableWidgetItem(address_info)
                bytes_item = QTableWidgetItem(bytes_aob)
                instruction_item = QTableWidgetItem(instruction)
                comment_item = QTableWidgetItem(comment)
                if jmp_ref_exists or call_ref_exists:
                    addr_item.setToolTip(tooltip_text)
                    bytes_item.setToolTip(tooltip_text)
                    instruction_item.setToolTip(tooltip_text)
                    comment_item.setToolTip(tooltip_text)
                self.tableWidget_Disassemble.setItem(row, DISAS_ADDR_COL, addr_item)
                self.tableWidget_Disassemble.setItem(row, DISAS_OPCODES_COL, bytes_item)
                self.tableWidget_Disassemble.setItem(row, DISAS_INSTR_COL, instruction_item)
                self.tableWidget_Disassemble.setItem(row, DISAS_COMMENT_COL, comment_item)
        finally:
            jmp_dict.close()
            call_dict.close()
            self.tableWidget_Disassemble.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            self.tableWidget_Disassemble.blockSignals(False)
        self.handle_colors(row_color)
        # Sorting keeps the per-arrow shade assignment stable across repaints and groups nearby paths.
        sorted_arrows = sorted(arrows)[:DISAS_MAX_ARROWS]
        self.disassemble_arrow_overlay.set_arrows(sorted_arrows, address_to_row, window_first_int, window_last_int)

        # We append the old record to travel history as last action because we wouldn't like to see unnecessary
        # addresses in travel history if any error occurs while displaying the next location
        if append_history:
            self.tableWidget_Disassemble.travel_history.append(previous_first_address)
        self.disassemble_currently_displayed_address = current_first_address
        return True

    def refresh_disassemble_view(self) -> None:
        if debugcore.currentpid == -1:
            return
        self.disassemble_expression(self.disassemble_currently_displayed_address, append_history=False)

    # Set color of a row if a specific address is encountered(e.g $pc, a bookmarked address etc.)
    def handle_colors(self, row_color: dict[int, list[QColor]]) -> None:
        if debugcore.currentpid == -1:
            return
        for row in row_color:
            current_row = row_color[row]
            if PC_COLOR in current_row:
                if BREAKPOINT_COLOR in current_row:
                    color = QColorConstants.Green
                elif BOOKMARK_COLOR in current_row:
                    color = QColorConstants.Yellow
                else:
                    color = PC_COLOR
                self.set_row_color(row, color)
                continue
            if BREAKPOINT_COLOR in current_row:
                if BOOKMARK_COLOR in current_row:
                    color = QColorConstants.Magenta
                else:
                    color = BREAKPOINT_COLOR
                self.set_row_color(row, color)
                continue
            if BOOKMARK_COLOR in current_row:
                self.set_row_color(row, BOOKMARK_COLOR)

    def set_row_color(self, row: int, color: QColor) -> None:
        if debugcore.currentpid == -1:
            return
        for col in range(self.tableWidget_Disassemble.columnCount()):
            color = QColor(color)
            color.setAlpha(96)
            self.tableWidget_Disassemble.item(row, col).setData(Qt.ItemDataRole.BackgroundRole, color)

    def on_process_stop(self) -> None:
        if debugcore.stop_reason == typedefs.STOP_REASON.PAUSE:
            self.setWindowTitle(tr.MV_PAUSED)
            return
        self.updating_memoryview = True
        try:
            time0 = time()
            self.setWindowTitle(tr.MV_DEBUGGING.format(debugcore.get_thread_info()))
            self.disassemble_expression("$pc", append_history=False)
            self.update_registers()
            if self.stackedWidget_StackScreens.currentWidget() == self.StackTrace:
                self.update_stacktrace()
            elif self.stackedWidget_StackScreens.currentWidget() == self.Stack:
                self.update_stack()

            # These tableWidgets are never emptied but initially both are empty, so this runs only once
            if self.tableWidget_StackTrace.rowCount() == 0:
                self.update_stacktrace()
            if self.tableWidget_Stack.rowCount() == 0:
                self.update_stack()
            self.refresh_hex_view()
            if states.show_memory_view_on_stop:
                self.showMaximized()
                self.activateWindow()
            if self.stacktrace_info_widget.isVisible():
                self.stacktrace_info_widget.update_stacktrace()
            self.pushButton_ShowFloatRegisters.setEnabled(True)
            if self.float_registers_widget.isVisible():
                self.float_registers_widget.update_registers()
            QApplication.processEvents()
            time1 = time()
            logger.debug(f"Updated memory view in: {str(time1 - time0)}")
        finally:
            self.updating_memoryview = False

    def on_process_running(self) -> None:
        self.setWindowTitle(tr.MV_RUNNING)
        self.pushButton_ShowFloatRegisters.setEnabled(False)

    def add_breakpoint_condition(self, int_address: int, length: int = 1, dialog_parent: QWidget | None = None) -> None:
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(int_address, length)
        if breakpoints:
            condition_line_edit_text = breakpoints[0].condition
        else:
            condition_line_edit_text = ""
        items = [(tr.ENTER_BP_CONDITION, condition_line_edit_text)]
        condition_dialog = utilwidgets.InputDialog(dialog_parent or self, items, Qt.AlignmentFlag.AlignLeft)
        if condition_dialog.exec():
            condition = condition_dialog.get_values()[0]
            for bp in breakpoints:
                if not debugcore.modify_breakpoint(utils.safe_int_cast(bp.number), typedefs.BREAKPOINT_MODIFY.CONDITION, condition):
                    QMessageBox.information(QApplication.focusWidget(), tr.ERROR, tr.BP_CONDITION_FAILED.format(bp.address))

    def update_registers(self) -> None:
        if debugcore.currentpid == -1:
            return
        registers = debugcore.read_registers()
        if not registers:
            return
        if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64:
            self.stackedWidget.setCurrentWidget(self.registers_64)
            self.RAX.set_value(registers["rax"])
            self.RBX.set_value(registers["rbx"])
            self.RCX.set_value(registers["rcx"])
            self.RDX.set_value(registers["rdx"])
            self.RSI.set_value(registers["rsi"])
            self.RDI.set_value(registers["rdi"])
            self.RBP.set_value(registers["rbp"])
            self.RSP.set_value(registers["rsp"])
            self.RIP.set_value(registers["rip"])
            self.R8.set_value(registers["r8"])
            self.R9.set_value(registers["r9"])
            self.R10.set_value(registers["r10"])
            self.R11.set_value(registers["r11"])
            self.R12.set_value(registers["r12"])
            self.R13.set_value(registers["r13"])
            self.R14.set_value(registers["r14"])
            self.R15.set_value(registers["r15"])
        elif debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_32:
            self.stackedWidget.setCurrentWidget(self.registers_32)
            self.EAX.set_value(registers["eax"])
            self.EBX.set_value(registers["ebx"])
            self.ECX.set_value(registers["ecx"])
            self.EDX.set_value(registers["edx"])
            self.ESI.set_value(registers["esi"])
            self.EDI.set_value(registers["edi"])
            self.EBP.set_value(registers["ebp"])
            self.ESP.set_value(registers["esp"])
            self.EIP.set_value(registers["eip"])
        self.CF.set_value(registers["cf"])
        self.PF.set_value(registers["pf"])
        self.AF.set_value(registers["af"])
        self.ZF.set_value(registers["zf"])
        self.SF.set_value(registers["sf"])
        self.TF.set_value(registers["tf"])
        self.IF.set_value(registers["if"])
        self.DF.set_value(registers["df"])
        self.OF.set_value(registers["of"])
        self.CS.set_value(registers["cs"])
        self.SS.set_value(registers["ss"])
        self.DS.set_value(registers["ds"])
        self.ES.set_value(registers["es"])
        self.GS.set_value(registers["gs"])
        self.FS.set_value(registers["fs"])

    def update_stacktrace(self) -> None:
        if guiutils.check_inferior_running(self, show_message=False):
            return
        stack_trace_info = debugcore.get_stacktrace_info()
        self.tableWidget_StackTrace.setRowCount(0)
        self.tableWidget_StackTrace.setRowCount(len(stack_trace_info))
        for row, item in enumerate(stack_trace_info):
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_RETURN_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_StackTrace.setItem(row, STACKTRACE_FRAME_ADDRESS_COL, QTableWidgetItem(item[1]))

    def set_stack_widget(self, stack_widget: QWidget) -> None:
        if debugcore.currentpid == -1:
            return
        self.stackedWidget_StackScreens.setCurrentWidget(stack_widget)
        if stack_widget == self.Stack:
            self.update_stack()
        elif stack_widget == self.StackTrace:
            self.update_stacktrace()

    def tableWidget_StackTrace_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            item = self.tableWidget_StackTrace.item(row, column)
            if item is None:
                return
            QApplication.clipboard().setText(item.text())

        selected_row = guiutils.get_current_row(self.tableWidget_StackTrace)
        menu = QMenu()
        switch_to_stack = menu.addAction(tr.FULL_STACK)
        menu.addSeparator()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_return = clipboard_menu.addAction(tr.COPY_RETURN_ADDRESS)
        copy_frame = clipboard_menu.addAction(tr.COPY_FRAME_ADDRESS)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [clipboard_menu.menuAction()])
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        if guiutils.check_inferior_running(self, show_message=False):
            refresh.setEnabled(False)
        if debugcore.currentpid == -1:
            menu.clear()
            menu.addMenu(clipboard_menu)
        font_size = self.tableWidget_StackTrace.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            switch_to_stack: lambda: self.set_stack_widget(self.Stack),
            copy_return: lambda: copy_to_clipboard(selected_row, STACKTRACE_RETURN_ADDRESS_COL),
            copy_frame: lambda: copy_to_clipboard(selected_row, STACKTRACE_FRAME_ADDRESS_COL),
            refresh: self.update_stacktrace,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def update_stack(self) -> None:
        if guiutils.check_inferior_running(self, show_message=False):
            return
        stack_info: list[str] = debugcore.get_stack_info(from_base_pointer=self.stack_from_base_pointer)
        self.tableWidget_Stack.setRowCount(0)
        self.tableWidget_Stack.setRowCount(len(stack_info))
        for row, item in enumerate(stack_info):
            self.tableWidget_Stack.setItem(row, STACK_POINTER_ADDRESS_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Stack.setItem(row, STACK_VALUE_COL, QTableWidgetItem(item[1]))
            self.tableWidget_Stack.setItem(row, STACK_POINTS_TO_COL, QTableWidgetItem(item[2]))
        self.tableWidget_Stack.resizeColumnToContents(STACK_POINTER_ADDRESS_COL)
        self.tableWidget_Stack.resizeColumnToContents(STACK_VALUE_COL)

    def toggle_stack_from_sp_bp(self) -> None:
        self.stack_from_base_pointer = not self.stack_from_base_pointer
        self.update_stack()

    def tableWidget_Stack_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if selected_row == -1:
            actions = {QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.update_stack}
        else:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_hex_address(current_address_text)

            actions = {
                QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.update_stack,
                QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): lambda: self.disassemble_expression(current_address),
                QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H): lambda: self.hex_dump_address(
                    utils.safe_str_to_int(current_address, 16)
                ),
            }
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Stack_keyPressEvent_original(event)

    def tableWidget_Stack_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            item = self.tableWidget_Stack.item(row, column)
            if item is None:
                return
            QApplication.clipboard().setText(item.text())

        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if selected_row == -1:
            current_address = None
        else:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
        menu = QMenu()
        switch_to_stacktrace = menu.addAction(tr.STACKTRACE)
        toggle_stack_pointer = menu.addAction(tr.TOGGLE_STACK_FROM_SP_BP)
        if guiutils.check_inferior_running(self, show_message=False):
            toggle_stack_pointer.setEnabled(False)
        menu.addSeparator()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_address = clipboard_menu.addAction(tr.COPY_ADDRESS)
        copy_value = clipboard_menu.addAction(tr.COPY_VALUE)
        copy_points_to = clipboard_menu.addAction(tr.COPY_POINTS_TO)
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        if guiutils.check_inferior_running(self, show_message=False):
            refresh.setEnabled(False)
        menu.addSeparator()
        show_in_disas = menu.addAction(f"{tr.DISASSEMBLE_VALUE_POINTER}[Ctrl+D]")
        show_in_hex = menu.addAction(f"{tr.HEXVIEW_VALUE_POINTER}[Ctrl+H]")
        if selected_row == -1 or current_address is None:
            guiutils.delete_menu_entries(menu, [clipboard_menu.menuAction(), show_in_disas, show_in_hex])
        if debugcore.currentpid == -1:
            menu.clear()
            menu.addMenu(clipboard_menu)
        font_size = self.tableWidget_Stack.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            switch_to_stacktrace: lambda: self.set_stack_widget(self.StackTrace),
            toggle_stack_pointer: self.toggle_stack_from_sp_bp,
            copy_address: lambda: copy_to_clipboard(selected_row, STACK_POINTER_ADDRESS_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, STACK_VALUE_COL),
            copy_points_to: lambda: copy_to_clipboard(selected_row, STACK_POINTS_TO_COL),
            refresh: self.update_stack,
            show_in_disas: lambda: self.disassemble_expression(current_address),
            show_in_hex: lambda: self.hex_dump_address(utils.safe_str_to_int(current_address, 16)),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_Stack_double_click(self, index: QTableWidgetItem) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Stack)
        if index.column() == STACK_POINTER_ADDRESS_COL:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_POINTER_ADDRESS_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            self.hex_dump_address(utils.safe_str_to_int(current_address, 16))
        else:
            points_to_text = self.tableWidget_Stack.item(selected_row, STACK_POINTS_TO_COL).text()
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            if points_to_text.startswith("(str)"):
                self.hex_dump_address(utils.safe_str_to_int(current_address, 16))
            else:
                self.disassemble_expression(current_address)

    def tableWidget_StackTrace_double_click(self, index: QTableWidgetItem) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_StackTrace)
        if index.column() == STACKTRACE_RETURN_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_RETURN_ADDRESS_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            self.disassemble_expression(current_address)
        if index.column() == STACKTRACE_FRAME_ADDRESS_COL:
            current_address_text = self.tableWidget_StackTrace.item(selected_row, STACKTRACE_FRAME_ADDRESS_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            self.hex_dump_address(utils.safe_str_to_int(current_address, 16))

    def tableWidget_StackTrace_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        actions = {QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.update_stacktrace}
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_StackTrace_keyPressEvent_original(event)

    def widget_Disassemble_wheel_event(self, event: QWheelEvent) -> None:
        steps = event.angleDelta()
        if steps.x() != 0:
            self.tableWidget_Disassemble_wheelEvent_original(event)
        if debugcore.currentpid == -1:
            return
        if steps.y() > 0:
            self.tableWidget_Disassemble_scroll("previous", states.instructions_per_scroll)
        elif steps.y() < 0:
            self.tableWidget_Disassemble_scroll("next", states.instructions_per_scroll)

    def disassemble_check_viewport(self, where: str, instruction_count: int) -> None:
        if debugcore.currentpid == -1:
            return
        current_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if current_row == -1:
            return
        current_row_height = self.tableWidget_Disassemble.rowViewportPosition(current_row)
        row_height = self.tableWidget_Disassemble.verticalHeader().defaultSectionSize()
        max_height = self.tableWidget_Disassemble.maximumViewportSize().height()
        # visible_height = max_height - row_height
        height = max_height - row_height * 3  # lets us see the next 2 instructions after the last visible row
        if current_row_height > max_height:
            last_visible_row = 0
            for row in range(self.tableWidget_Disassemble.rowCount()):
                if self.tableWidget_Disassemble.rowViewportPosition(row) > height:
                    break
                last_visible_row += 1
            current_address = utils.extract_hex_address(self.tableWidget_Disassemble.item(current_row, DISAS_ADDR_COL).text())
            new_address = debugcore.find_closest_instruction_address(current_address, "previous", last_visible_row)
            if not new_address:
                return
            self.disassemble_expression(new_address, append_history=False)
        elif (where == "previous" and current_row == 0) or (where == "next" and current_row_height > height):
            self.tableWidget_Disassemble_scroll(where, instruction_count)

    def tableWidget_Disassemble_scroll(self, where: str, instruction_count: int) -> None:
        if debugcore.currentpid == -1:
            return
        current_address = self.disassemble_currently_displayed_address
        new_address = debugcore.find_closest_instruction_address(current_address, where, instruction_count)
        if not new_address:
            return
        self.disassemble_expression(new_address, append_history=False)

    def widget_HexView_wheel_event(self, event: QWheelEvent) -> None:
        if debugcore.currentpid == -1:
            return
        steps = event.angleDelta()
        current_address = self.hex_model.current_address
        if steps.y() > 0:
            next_address = current_address - states.bytes_per_scroll
        else:
            next_address = current_address + states.bytes_per_scroll
        self.hex_dump_address(next_address)

    def widget_HexView_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        actions = {
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G): self.exec_hex_view_go_to_dialog,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): lambda: self.disassemble_expression(
                hex(self.hex_selection_address_begin)
            ),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_A): self.exec_hex_view_add_address_dialog,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C): self.copy_hex_view_selection,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.refresh_hex_view,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp): self.hex_view_scroll_up,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown): self.hex_view_scroll_down,
        }
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.widget_HexView_keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        if event.matches(QKeySequence.StandardKey.SelectAll):
            last_row = self.tableWidget_Disassemble.rowAt(self.tableWidget_Disassemble.viewport().height() - 1)
            if last_row == -1:
                last_row = self.tableWidget_Disassemble.rowCount() - 1
            model = self.tableWidget_Disassemble.model()
            selection = QItemSelection(model.index(0, 0), model.index(last_row, self.tableWidget_Disassemble.columnCount() - 1))
            self.tableWidget_Disassemble.selectionModel().select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
            return
        selected_row = self.get_disassemble_row(no_selection_row=0)
        if selected_row == -1:
            return self.tableWidget_Disassemble_keyPressEvent_original(event)
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = utils.safe_str_to_int(current_address, 16)

        actions = {
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space): lambda: self.follow_instruction(selected_row),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_E): lambda: self.exec_examine_referrers_widget(current_address_text),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G): self.exec_disassemble_go_to_dialog,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H): lambda: self.hex_dump_address(current_address_int),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B): lambda: self.bookmark_address(current_address_int),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): self.dissect_current_region,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_T): self.exec_trace_instructions_dialog,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.refresh_disassemble_view,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down): lambda: self.disassemble_check_viewport("next", 1),
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up): lambda: self.disassemble_check_viewport("previous", 1),
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp): self.disassemble_scroll_up,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown): self.disassemble_scroll_down,
        }
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Disassemble_keyPressEvent_original(event)

    def tableWidget_Disassemble_item_double_clicked(self, index: QTableWidgetItem) -> None:
        if debugcore.currentpid == -1:
            return
        if index.column() == DISAS_COMMENT_COL:
            selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
            if selected_row == -1:
                return
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = utils.safe_str_to_int(utils.extract_hex_address(current_address_text), 16)
            if current_address in self.session.pct_bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def tableWidget_Disassemble_item_selection_changed(self) -> None:
        if debugcore.currentpid == -1:
            return
        try:
            selected_rows = self.tableWidget_Disassemble.selectionModel().selectedRows()
            address_texts = [self.tableWidget_Disassemble.item(index.row(), DISAS_ADDR_COL).text() for index in selected_rows]
            self.disassemble_selected_addresses = {utils.safe_str_to_int(utils.extract_hex_address(text), 16) for text in address_texts}
            selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
            selected_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            self.disassemble_last_selected_address_int = int(utils.extract_hex_address(selected_address_text), 16)
        except (TypeError, ValueError, AttributeError):
            pass

    # Search the item in given row for location changing instructions
    # Go to the address pointed by that instruction if it contains any
    def follow_instruction(self, selected_row: int) -> None:
        if debugcore.currentpid == -1:
            return
        address = utils.instruction_follow_address(self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text())
        if address:
            self.disassemble_expression(address)

    # Follows a clicked reference arrow.
    # Normally jumps to the target address, but if the target is already the selected row we follow the caller instead so the arrow acts as a toggle.
    def disassemble_arrow_follow(self, source: int, target: int) -> None:
        if debugcore.currentpid == -1:
            return
        follow_address = source if self.disassemble_last_selected_address_int == target else target
        # Select the followed address so repeated clicks keep toggling between caller and target.
        self.disassemble_last_selected_address_int = follow_address
        self.disassemble_selected_addresses = {follow_address}
        self.disassemble_expression(hex(follow_address))

    def disassemble_go_back(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.tableWidget_Disassemble.travel_history:
            last_location = self.tableWidget_Disassemble.travel_history[-1]
            self.disassemble_expression(last_location, append_history=False)
            self.tableWidget_Disassemble.travel_history.pop()

    def tableWidget_Disassemble_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(*columns: int, extract_address: bool = False) -> None:
            rows = ["\t".join(self.tableWidget_Disassemble.item(row, column).text() for column in columns) for row in selected_rows]
            QApplication.clipboard().setText("\n".join(utils.extract_hex_address(text) if extract_address else text for text in rows))

        selected_rows = sorted({index.row() for index in self.tableWidget_Disassemble.selectionModel().selectedRows()})
        if not selected_rows:
            return
        selected_row = selected_rows[0]
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = utils.safe_str_to_int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        back = menu.addAction(tr.BACK)
        show_in_hex_view = menu.addAction(f"{tr.HEXVIEW_ADDRESS}[Ctrl+H]")
        menu.addSeparator()
        followable = utils.instruction_follow_address(self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text())
        follow = menu.addAction(f"{tr.FOLLOW}[Space]")
        if not followable:
            guiutils.delete_menu_entries(menu, [follow])
        examine_referrers = menu.addAction(f"{tr.EXAMINE_REFERRERS}[Ctrl+E]")
        if not guiutils.contains_reference_mark(current_address_text):
            guiutils.delete_menu_entries(menu, [examine_referrers])
        bookmark = menu.addAction(f"{tr.BOOKMARK_ADDRESS}[Ctrl+B]")
        delete_bookmark = menu.addAction(tr.DELETE_BOOKMARK)
        change_comment = menu.addAction(tr.CHANGE_COMMENT)
        is_bookmarked = current_address_int in self.session.pct_bookmarks
        if not is_bookmarked:
            guiutils.delete_menu_entries(menu, [delete_bookmark, change_comment])
        else:
            guiutils.delete_menu_entries(menu, [bookmark])
        go_to_bookmark = menu.addMenu(tr.GO_TO_BOOKMARK_ADDRESS)
        address_list = [hex(address) for address in self.session.pct_bookmarks.keys()]
        bookmark_actions = [go_to_bookmark.addAction(item.all) for item in debugcore.examine_expressions(address_list)]
        menu.addSeparator()
        toggle_breakpoint = menu.addAction(f"{tr.TOGGLE_BREAKPOINT}[F5]")
        add_condition = menu.addAction(tr.CHANGE_BREAKPOINT_CONDITION)
        if not debugcore.get_breakpoints_in_range(current_address_int):
            guiutils.delete_menu_entries(menu, [add_condition])
        menu.addSeparator()
        edit_instruction = menu.addAction(tr.EDIT_INSTRUCTION)
        nop_instruction = menu.addAction(tr.REPLACE_WITH_NOPS)
        if self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text() == "90":
            guiutils.delete_menu_entries(menu, [nop_instruction])
        menu.addSeparator()
        track_breakpoint = menu.addAction(tr.WHAT_ACCESSES_INSTRUCTION)
        trace_instructions = menu.addAction(f"{tr.TRACE_INSTRUCTION}[Ctrl+T]")
        dissect_region = menu.addAction(f"{tr.DISSECT_REGION}[Ctrl+D]")
        menu.addSeparator()
        refresh = menu.addAction(f"{tr.REFRESH}[R]")
        menu.addSeparator()
        if debugcore.currentpid == -1:
            menu.clear()
        clipboard_menu = menu.addMenu(tr.COPY_CLIPBOARD)
        copy_address = clipboard_menu.addAction(tr.COPY_ADDRESS)
        copy_bytes = clipboard_menu.addAction(tr.COPY_BYTES)
        copy_instr = clipboard_menu.addAction(tr.COPY_INSTR)
        copy_comment = clipboard_menu.addAction(tr.COPY_COMMENT)
        copy_all = clipboard_menu.addAction(tr.COPY_ALL)
        if len(selected_rows) > 1:
            for entry in menu.actions():
                entry.setEnabled(entry.menu() is not None or entry in (go_to, back, dissect_region, refresh))
        font_size = self.tableWidget_Disassemble.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            go_to: self.exec_disassemble_go_to_dialog,
            back: self.disassemble_go_back,
            show_in_hex_view: lambda: self.hex_dump_address(current_address_int),
            follow: lambda: self.follow_instruction(selected_row),
            examine_referrers: lambda: self.exec_examine_referrers_widget(current_address_text),
            bookmark: lambda: self.bookmark_address(current_address_int),
            delete_bookmark: lambda: self.delete_bookmark(current_address_int),
            change_comment: lambda: self.change_bookmark_comment(current_address_int),
            toggle_breakpoint: self.toggle_breakpoint,
            add_condition: lambda: self.add_breakpoint_condition(current_address_int),
            edit_instruction: self.edit_instruction,
            nop_instruction: self.nop_instruction,
            track_breakpoint: self.exec_track_breakpoint_dialog,
            trace_instructions: self.exec_trace_instructions_dialog,
            dissect_region: self.dissect_current_region,
            refresh: self.refresh_disassemble_view,
            copy_address: lambda: copy_to_clipboard(DISAS_ADDR_COL, extract_address=True),
            copy_bytes: lambda: copy_to_clipboard(DISAS_OPCODES_COL),
            copy_instr: lambda: copy_to_clipboard(DISAS_INSTR_COL),
            copy_comment: lambda: copy_to_clipboard(DISAS_COMMENT_COL),
            copy_all: lambda: copy_to_clipboard(*range(self.tableWidget_Disassemble.columnCount())),
        }
        try:
            actions[action]()
        except KeyError:
            pass
        if action in bookmark_actions:
            self.disassemble_expression(utils.extract_hex_address(action.text()))

    def dissect_current_region(self) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        dissect_code_dialog = DissectCodeDialog(self, utils.safe_str_to_int(current_address, 16))
        dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def exec_examine_referrers_widget(self, current_address_text: str) -> None:
        if debugcore.currentpid == -1:
            return
        if not guiutils.contains_reference_mark(current_address_text):
            return
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = utils.safe_str_to_int(current_address, 16)
        examine_referrers_widget = ExamineReferrersWidget(self, current_address_int)
        examine_referrers_widget.show()

    def exec_trace_instructions_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        selected_row = self.get_disassemble_row(no_selection_row=0)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        TraceInstructionsWindow(self, current_address)

    def exec_track_breakpoint_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = self.get_disassemble_row()
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_instruction = self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text()
        register_expression_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_TRACK_BP_EXPRESSION, "")])
        if register_expression_dialog.exec():
            exp = register_expression_dialog.get_values()[0]
            TrackBreakpointWidget(self, current_address, current_instruction, exp)

    def exec_disassemble_go_to_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)

        go_to_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_EXPRESSION, current_address)])
        if go_to_dialog.exec():
            traveled_exp = go_to_dialog.get_values()[0]
            self.disassemble_expression(traveled_exp)

    def bookmark_address(self, address: int) -> None:
        if debugcore.currentpid == -1:
            return
        if address in self.session.pct_bookmarks:
            QMessageBox.information(QApplication.focusWidget(), tr.ERROR, tr.ALREADY_BOOKMARKED)
            return
        comment_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_BOOKMARK_COMMENT, "")])
        if comment_dialog.exec():
            comment_data = comment_dialog.get_values()
            comment = comment_data[0] if comment_data else ""
        else:
            return
        exam_result = debugcore.examine_expression(hex(address))
        symbol = utils.extract_symbol_name(exam_result.symbol) if exam_result.symbol else ""

        region_info = utils.get_region_info(debugcore.currentpid, address)

        if not region_info:
            logger.error("Address does not belong to any mapped region, aborting")
            return

        if region_info.file_name == "[heap]" or region_info.file_name == "[stack]":
            logger.warning("Address belongs to the heap or stack, cannot bookmark")
            return

        address_region_details = {
            "region_name": region_info.file_name,
            "offset_in_region": hex(address - region_info.start),
            "region_index": region_info.region_index,
        }
        self.session.pct_bookmarks[address] = {
            "symbol": symbol,
            "comment": comment,
            "address_region_details": address_region_details,
        }
        self.session.data_changed |= SessionDataChanged.BOOKMARKS
        states.session_signals.bookmarks_changed.emit()
        logger.info(self.session.pct_bookmarks)
        self.refresh_disassemble_view()

    def change_bookmark_comment(self, address: int) -> None:
        if debugcore.currentpid == -1:
            return
        current_comment = self.session.pct_bookmarks[address]["comment"]
        comment_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_BOOKMARK_COMMENT, current_comment)])
        if comment_dialog.exec():
            new_comment = comment_dialog.get_values()[0]
        else:
            return
        self.session.pct_bookmarks[address]["comment"] = new_comment
        self.session.data_changed |= SessionDataChanged.BOOKMARKS
        states.session_signals.bookmarks_changed.emit()
        self.refresh_disassemble_view()

    def delete_bookmark(self, address: int) -> None:
        if debugcore.currentpid == -1:
            return
        if address in self.session.pct_bookmarks:
            del self.session.pct_bookmarks[address]
            self.session.data_changed |= SessionDataChanged.BOOKMARKS
            states.session_signals.bookmarks_changed.emit()
            self.refresh_disassemble_view()

    def actionBookmarks_triggered(self) -> None:
        if self.bookmark_widget is None:
            self.bookmark_widget = BookmarkWidget(self)
            self.bookmark_widget.bookmarked.connect(self.bookmark_address)
            self.bookmark_widget.comment_changed.connect(self.change_bookmark_comment)
            self.bookmark_widget.double_clicked.connect(self.disassemble_expression)
            self.bookmark_widget.deleted.connect(self.delete_bookmark)
        else:
            self.bookmark_widget.refresh_table()
        self.bookmark_widget.show()
        self.bookmark_widget.activateWindow()

    def actionStackTrace_Info_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        self.stacktrace_info_widget.update_stacktrace()
        guiutils.center_to_parent(self.stacktrace_info_widget)
        self.stacktrace_info_widget.show()
        self.stacktrace_info_widget.activateWindow()

    def actionBreakpoints_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.breakpoint_widget is None:
            self.breakpoint_widget = BreakpointInfoWidget(self)
        else:
            self.breakpoint_widget.refresh()
        self.breakpoint_widget.show()
        self.breakpoint_widget.activateWindow()

    def actionFunctions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.functions_info_widget is None:
            self.functions_info_widget = FunctionsInfoWidget(self)
        self.functions_info_widget.show()

    def actionGDB_Log_File_triggered(self) -> None:
        log_file_widget = LogFileWidget(self)
        log_file_widget.showMaximized()

    def actionMemory_Regions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.memory_regions_widget is None:
            self.memory_regions_widget = MemoryRegionsWidget(self)
        else:
            self.memory_regions_widget.refresh_table()
        self.memory_regions_widget.show()

    def actionRestore_Instructions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.restore_instructions_widget is None:
            self.restore_instructions_widget = RestoreInstructionsWidget(self)
            self.restore_instructions_widget.restored.connect(self.refresh_hex_view)
            self.restore_instructions_widget.restored.connect(self.refresh_disassemble_view)
            self.restore_instructions_widget.double_clicked.connect(self.disassemble_expression)
        else:
            self.restore_instructions_widget.refresh()
        self.restore_instructions_widget.show()
        self.restore_instructions_widget.activateWindow()

    def actionReferenced_Strings_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        ref_str_widget = ReferencedStringsWidget(self)
        ref_str_widget.show()

    def actionReferenced_Calls_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        ref_call_widget = ReferencedCallsWidget(self)
        ref_call_widget.show()

    def actionInject_so_file_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_SO_FILE, os.path.expanduser("~"), tr.SHARED_OBJECT_TYPE)
        if file_path:
            if debugcore.inject_so(file_path):
                QMessageBox.information(self, tr.SUCCESS, tr.SO_INJECTED)
            else:
                QMessageBox.information(self, tr.ERROR, tr.SO_INJECT_FAILED)

    def actionInject_DLL_file_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if not utils.is_wine_process(debugcore.currentpid):
            QMessageBox.information(self, tr.ERROR, tr.DLL_INJECT_WINE_ONLY)
            return
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_DLL_FILE, os.path.expanduser("~"), tr.DLL_TYPE)
        if file_path:
            if debugcore.inject_dll(file_path):
                QMessageBox.information(self, tr.SUCCESS, tr.DLL_INJECT_STARTED)
            else:
                QMessageBox.information(self, tr.ERROR, tr.DLL_INJECT_FAILED)

    def actionCall_Function_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        call_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_CALL_EXPRESSION, "")])
        if call_dialog.exec():
            result = debugcore.call_function_from_inferior(call_dialog.get_values()[0])
            if result[0]:
                QMessageBox.information(self, tr.SUCCESS, result[0] + " = " + result[1])
            else:
                QMessageBox.information(self, tr.ERROR, tr.CALL_EXPRESSION_FAILED.format(call_dialog.get_values()[0]))

    def actionSearch_Instructions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        start_address = utils.safe_str_to_int(self.disassemble_currently_displayed_address, 16)
        end_address = start_address + 0x30000
        region_info = utils.get_region_info(debugcore.currentpid, start_address)
        if region_info:
            start_address = region_info.start
            end_address = region_info.end
        search_instr_widget = SearchInstructionsWidget(self, hex(start_address), hex(end_address))
        search_instr_widget.show()

    def actionDissect_Code_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        dissect_code_dialog = DissectCodeDialog(self)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def actionDissect_Mono_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        info = monocore.detect_runtime(debugcore.currentpid)
        if info is None:
            QMessageBox.information(self, tr.ERROR, tr.MONO_NO_RUNTIME)
            return
        if not monocore.init_mono():
            QMessageBox.information(self, tr.ERROR, tr.MONO_NOT_READY)
            return
        mono_dialog = MonoDissectDialog(self)
        mono_dialog.disassemble_requested.connect(lambda address: self.disassemble_expression(hex(int(address))))
        mono_dialog.breakpoint_requested.connect(self._mono_breakpoint)
        mono_dialog.add_to_table_requested.connect(lambda description, address: self.parent().add_entry_to_addresstable(description, address))
        mono_dialog.export_structure_requested.connect(self._export_mono_structure)
        mono_dialog.view_structure_requested.connect(self._view_mono_structure)
        mono_dialog.show()

    def _mono_breakpoint(self, address: object) -> None:
        if not debugcore.add_breakpoint(hex(int(address))):
            QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(hex(int(address))))
        self.refresh_disassemble_view()

    def _export_mono_structure(self, class_data: object) -> None:
        client = monocore.get_client()
        if client is None:
            return
        existing = set(StructureManager.list_names())
        try:
            struct = mono_export.structure_from_class(client, class_data)
        except monocore.MonoError:
            QMessageBox.information(self, tr.ERROR, tr.MONO_NOT_READY)
            return
        created = set(StructureManager.list_names()) - existing
        if not StructureEditorDialog(self, struct.name).exec():
            for name in created:
                StructureManager.delete(name)
        if self.parent().structures_window:
            self.parent().structures_window.refresh()

    def _view_mono_structure(self, structure_name: str, address: object) -> None:
        view = StructureViewDialog(self, structure_name, hex(int(address)))
        view.add_to_table_requested.connect(self.parent()._add_structure_records_to_table)
        view.show()
        if self.parent().structures_window:
            self.parent().structures_window.refresh()

    def actionLibpince_Engine_triggered(self) -> None:
        # The engine is owned by the main form since it integrates with the address table
        self.parent().show_libpince_engine()

    def actionStructures_triggered(self) -> None:
        self.parent().show_structures_window()

    def actionLibpince_triggered(self) -> None:
        utils.execute_command_as_user('python3 -m webbrowser "https://korcankaraokcu.github.io/PINCE/"')

    def pushButton_ShowFloatRegisters_clicked(self) -> None:
        if guiutils.check_inferior_running(self):
            return
        self.float_registers_widget.update_registers()
        guiutils.center_to_parent(self.float_registers_widget)
        self.float_registers_widget.show()
        self.float_registers_widget.activateWindow()

    def on_new_session(self) -> None:
        self.session = SessionManager.get_session()
