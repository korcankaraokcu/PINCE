from PyQt6.QtWidgets import QMainWindow, QTableWidgetItem, QTreeWidgetItem, QTreeWidgetItemIterator, QMenu, QMessageBox, QCheckBox, QApplication
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon, QPixmap, QBrush, QColor, QKeyEvent, QMouseEvent, QContextMenuEvent, QCloseEvent
from PyQt6.QtCore import Qt, QTimer, QSettings, QKeyCombination, pyqtSignal
from GUI.Session.session import SessionDataChanged, SessionManager, StructureManager
from GUI.Settings import settings
from GUI.States import states
from GUI.Utils import guitypedefs, guiutils, update_check, utilwidgets
from GUI.Widgets.About.About import AboutWidget
from GUI.Widgets.Console.Console import ConsoleWidget
from GUI.Widgets.EditType.EditType import EditTypeDialog
from GUI.Widgets.LibpinceEngine.LibpinceEngine import LibpinceEngineWindow, create_script_namespace, parse_script_sections, run_script_code
from GUI.Widgets.MainWindow.Form.MainWindow import Ui_MainWindow
from GUI.Widgets.ManageScanRegions.ManageScanRegions import ManageScanRegionsDialog
from GUI.Widgets.ManualAddress.ManualAddress import ManualAddressDialog
from GUI.Widgets.MemoryView.MemoryView import MemoryViewWindow
from GUI.Widgets.PointerScan.PointerScan import PointerScanWindow
from GUI.Widgets.PointerScanSearch.PointerScanSearch import PointerScanSearchDialog
from GUI.Widgets.SelectProcess.SelectProcess import SelectProcessWindow
from GUI.Widgets.SessionNotes.SessionNotes import SessionNotesWidget
from GUI.Widgets.Settings.Settings import SettingsDialog
from GUI.Widgets.Structures.StructuresWindow import StructuresWindow
from GUI.Widgets.Structures.StructureViewDialog import StructureViewDialog
from GUI.Widgets.TrackSelector.TrackSelector import TrackSelectorDialog
from GUI.Widgets.TrackWatchpoint.TrackWatchpoint import TrackWatchpointWidget
from libpince import debugcore, monocore, scancore, speedhack, typedefs, utils
from libpince.libmemscan.memscan import DataType, BytePattern
from libpince.scancore import memscan
from libpince.utils import logger
from tr.tr import TranslationConstants as tr
from typing import Any
import ast, collections, copy, os, re, sys, traceback

# represents the index of columns in address table
FROZEN_COL = 0  # Frozen
DESC_COL = 1  # Description
ADDR_COL = 2  # Address
TYPE_COL = 3  # Type
VALUE_COL = 4  # Value

# represents the index of columns in search results table
SEARCH_TABLE_ADDRESS_COL = 0
SEARCH_TABLE_VALUE_COL = 1
SEARCH_TABLE_PREVIOUS_COL = 2


class MainWindow(QMainWindow, Ui_MainWindow):
    # Workaround to avoid race condition with temporary interrupt execution decorator.
    # Routes speedhack hotkeys from the keyboard thread back onto the Qt main thread.
    # Payload is the step delta: -1 = down, 0 = toggle, +1 = up.
    speedhack_action_requested = pyqtSignal(int)

    # Payload is the toggle_attach() result (a typedefs.TOGGLE_ATTACH member or None on failure).
    attach_toggled = pyqtSignal(object)

    # Payload is the requested SCAN_TYPE
    nextscan_requested = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.doubleSpinBox_Speedhack.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.update_check_thread: update_check.UpdateCheckThread | None = None
        self.show_update_check_result = True
        self.deleted_regions: list[int] = []
        self.is_wine_process = False
        self.speedhack: speedhack.LinuxSpeedhack | speedhack.WineSpeedhack | None = None
        self.speedhack_action_requested.connect(self.on_speedhack_hotkey_action)
        self.attach_toggled.connect(self.on_attach_toggled)
        self.nextscan_requested.connect(self.on_nextscan_requested)
        self.checkBox_Speedhack.toggled.connect(self.apply_speedhack)
        self.doubleSpinBox_Speedhack.valueChanged.connect(self.apply_speedhack)
        hotkey_to_func = {
            states.hotkeys.pause_hotkey: self.pause_hotkey_pressed,
            states.hotkeys.break_hotkey: self.break_hotkey_pressed,
            states.hotkeys.continue_hotkey: self.continue_hotkey_pressed,
            states.hotkeys.cancel_hotkey: self.cancel_hotkey_pressed,
            states.hotkeys.toggle_attach_hotkey: self.toggle_attach_hotkey_pressed,
            states.hotkeys.speedhack_toggle_hotkey: self.speedhack_toggle_hotkey_pressed,
            states.hotkeys.speedhack_speed_up_hotkey: self.speedhack_speed_up_hotkey_pressed,
            states.hotkeys.speedhack_speed_down_hotkey: self.speedhack_speed_down_hotkey_pressed,
            states.hotkeys.exact_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.EXACT),
            states.hotkeys.not_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.NOT),
            states.hotkeys.increased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.INCREASED),
            states.hotkeys.increased_by_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.INCREASED_BY),
            states.hotkeys.decreased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.DECREASED),
            states.hotkeys.decreased_by_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.DECREASED_BY),
            states.hotkeys.less_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.LESS),
            states.hotkeys.more_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.MORE),
            states.hotkeys.between_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.BETWEEN),
            states.hotkeys.changed_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.CHANGED),
            states.hotkeys.unchanged_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.UNCHANGED),
        }
        for hotkey, func in hotkey_to_func.items():
            hotkey.change_func(func)
        self.treeWidget_AddressTable.setColumnWidth(FROZEN_COL, 50)
        self.treeWidget_AddressTable.setColumnWidth(DESC_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(ADDR_COL, 150)
        self.treeWidget_AddressTable.setColumnWidth(TYPE_COL, 150)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_ADDRESS_COL, 120)
        self.tableWidget_valuesearchtable.setColumnWidth(SEARCH_TABLE_VALUE_COL, 80)
        self.tableWidget_valuesearchtable.horizontalHeader().setSortIndicatorClearable(True)
        self.await_exit_thread = guitypedefs.AwaitProcessExit()
        self.auto_attach_timer = QTimer(self, timeout=self.auto_attach_loop)

        settings.init_settings()
        self.settings_changed()
        self.memory_view_window = MemoryViewWindow(self)
        self.session_notes = SessionNotesWidget(None)

        if os.environ.get("APPDIR"):
            gdb_path = utils.get_default_gdb_path()
        else:
            gdb_path = states.gdb_path
        if debugcore.init_gdb(gdb_path):
            settings.apply_after_init()
        else:
            utilwidgets.InputDialog(self, tr.GDB_INIT_ERROR, cancel_button=False).exec()
        self.await_exit_thread.process_exited.connect(self.on_inferior_exit)
        self.await_exit_thread.start()
        states.status_thread.process_stopped.connect(self.on_status_stopped)
        states.status_thread.process_running.connect(self.on_status_running)
        states.setting_signals.changed.connect(self.settings_changed)
        self.address_table_timer = QTimer(self, timeout=self.address_table_loop, singleShot=True)
        self.address_table_timer.start()
        self.search_table_timer = QTimer(self, timeout=self.search_table_loop, singleShot=True)
        self.search_table_timer.start()
        self.freeze_timer = QTimer(self, timeout=self.freeze_loop, singleShot=True)
        self.freeze_timer.start()
        self.shortcut_open_file = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_open_file.activated.connect(SessionManager.load_session)
        guiutils.append_shortcut_to_tooltip(self.pushButton_Open, self.shortcut_open_file)
        self.shortcut_save_file = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save_file.activated.connect(SessionManager.save_session)
        guiutils.append_shortcut_to_tooltip(self.pushButton_Save, self.shortcut_save_file)

        # Saving the original function because super() doesn't work when we override functions like this
        self.treeWidget_AddressTable_mouseReleaseEvent_original = self.treeWidget_AddressTable.mouseReleaseEvent
        self.treeWidget_AddressTable.mouseReleaseEvent = self.treeWidget_AddressTable_mouse_release_event
        self.treeWidget_AddressTable_keyPressEvent_original = self.treeWidget_AddressTable.keyPressEvent
        self.treeWidget_AddressTable.keyPressEvent = self.treeWidget_AddressTable_key_press_event
        self.treeWidget_AddressTable.contextMenuEvent = self.treeWidget_AddressTable_context_menu_event
        self.pushButton_AttachProcess.clicked.connect(self.pushButton_AttachProcess_clicked)
        self.pushButton_Open.clicked.connect(SessionManager.load_session)
        self.pushButton_Save.clicked.connect(SessionManager.save_session)
        states.session_signals.on_save.connect(self.on_session_save)
        states.session_signals.on_load.connect(self.on_session_loaded)
        states.session_signals.new_session.connect(self.on_new_session)
        self.session = SessionManager.get_session()
        self.pushButton_CheckForUpdates.clicked.connect(lambda: self.check_for_updates())
        if os.environ.get("APPDIR"):
            self._set_update_button_enabled(True)
            self.update_check_timer = QTimer(self, timeout=self.check_for_updates_on_startup, singleShot=True)
            self.update_check_timer.start(500)
        else:
            self.pushButton_CheckForUpdates.hide()
        self.libpince_engine_window: LibpinceEngineWindow | None = None
        self.structures_window: StructuresWindow | None = None
        self.pushButton_NewFirstScan.clicked.connect(self.pushButton_NewFirstScan_clicked)
        self.pushButton_UndoScan.clicked.connect(self.pushButton_UndoScan_clicked)
        self.pushButton_CancelScan.clicked.connect(self.pushButton_CancelScan_clicked)
        self.pushButton_NextScan.clicked.connect(self.pushButton_NextScan_clicked)
        self.pushButton_ScanRegions.clicked.connect(self.pushButton_ScanRegions_clicked)
        self.scan_mode = typedefs.SCAN_MODE.NEW
        self.pushButton_NewFirstScan_clicked()
        self.comboBox_ScanScope_init()
        self.comboBox_ValueType_init()
        guiutils.fill_endianness_combobox(self.comboBox_Endianness)
        guiutils.fill_alignment_combobox(self.comboBox_Alignment)
        self.comboBox_Endianness.currentIndexChanged.connect(self.on_endianness_changed)
        self.comboBox_Alignment.currentIndexChanged.connect(self.comboBox_Alignment_current_index_changed)
        self.checkBox_Hex.stateChanged.connect(self.checkBox_Hex_stateChanged)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int"))
        self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int"))
        self.lineEdit_Scan_keyPressEvent_original = self.lineEdit_Scan.keyPressEvent
        self.lineEdit_Scan2_keyPressEvent_original = self.lineEdit_Scan2.keyPressEvent
        self.lineEdit_Scan.keyPressEvent = self.lineEdit_Scan_on_key_press_event
        self.lineEdit_Scan2.keyPressEvent = self.lineEdit_Scan2_on_key_press_event
        self.comboBox_ScanType.currentIndexChanged.connect(self.comboBox_ScanType_current_index_changed)
        self.comboBox_ScanType_current_index_changed()
        self.pushButton_Settings.clicked.connect(self.pushButton_Settings_clicked)
        self.pushButton_Console.clicked.connect(self.pushButton_Console_clicked)
        self.pushButton_Wiki.clicked.connect(self.pushButton_Wiki_clicked)
        self.pushButton_About.clicked.connect(self.pushButton_About_clicked)
        self.pushButton_AddAddressManually.clicked.connect(self.pushButton_AddAddressManually_clicked)
        self.pushButton_MemoryView.clicked.connect(self.pushButton_MemoryView_clicked)
        self.pushButton_RefreshAddressTable.clicked.connect(self.pushButton_RefreshAddressTable_clicked)
        self.pushButton_CopyToAddressTable.clicked.connect(self.copy_to_address_table)
        self.pushButton_CleanAddressTable.clicked.connect(self.clear_address_table)
        self.tableWidget_valuesearchtable.cellDoubleClicked.connect(self.tableWidget_valuesearchtable_cell_double_clicked)
        self.tableWidget_valuesearchtable_keyPressEvent_original = self.tableWidget_valuesearchtable.keyPressEvent
        self.tableWidget_valuesearchtable.keyPressEvent = self.tableWidget_valuesearchtable_key_press_event
        self.tableWidget_valuesearchtable.contextMenuEvent = self.tableWidget_valuesearchtable_context_menu_event
        self.treeWidget_AddressTable.itemDoubleClicked.connect(self.treeWidget_AddressTable_item_double_clicked)
        self.treeWidget_AddressTable.expanded.connect(self.resize_address_table)
        self.treeWidget_AddressTable.collapsed.connect(self.resize_address_table)
        self.treeWidget_AddressTable.header().setSortIndicatorClearable(True)
        self.treeWidget_AddressTable.header().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)  # Clear sort indicator
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_AttachProcess.setIcon(QIcon(QPixmap(icons_directory + "/monitor.png")))
        self.pushButton_Open.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        self.pushButton_Save.setIcon(QIcon(QPixmap(icons_directory + "/disk.png")))
        self.pushButton_CheckForUpdates.setIcon(QIcon(QPixmap(icons_directory + "/arrow_refresh.png")))
        self.pushButton_Settings.setIcon(QIcon(QPixmap(icons_directory + "/wrench.png")))
        self.pushButton_CopyToAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/arrow_down.png")))
        self.pushButton_CleanAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/bin_closed.png")))
        self.pushButton_RefreshAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/table_refresh.png")))
        self.pushButton_Console.setIcon(QIcon(QPixmap(icons_directory + "/application_xp_terminal.png")))
        self.pushButton_Wiki.setIcon(QIcon(QPixmap(icons_directory + "/book_open.png")))
        self.pushButton_About.setIcon(QIcon(QPixmap(icons_directory + "/information.png")))
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.pushButton_CancelScan.setEnabled(False)
        self.flashAttachButton = True
        self.flashAttachButtonTimer = QTimer(self)
        self.flashAttachButtonTimer.timeout.connect(self.flash_attach_button)
        self.flashAttachButton_gradientState = 0
        self.flashAttachButtonTimer.start(100)
        self.is_scanning = False
        self.undo_scan_available = False

        self.pushButton_Notes.clicked.connect(self.session_notes.toggle_visibility)
        guiutils.center(self)

    def settings_changed(self) -> None:
        if states.auto_attach:
            self.auto_attach_timer.start(100)
        else:
            self.auto_attach_timer.stop()

    # Check if any process should be attached to automatically
    # Patterns at former positions have higher priority if regex is off
    def auto_attach_loop(self) -> None:
        if debugcore.currentpid != -1:
            return
        if states.auto_attach_regex:
            try:
                compiled_re = re.compile(states.auto_attach)
            except:
                logger.exception(f"Auto-attach failed: {states.auto_attach} isn't a valid regex")
                return
            for pid, _, name in utils.get_process_list():
                if compiled_re.search(name):
                    self.attach_to_pid(int(pid))
                    return
        else:
            for target in filter(None, map(str.strip, states.auto_attach.split(";"))):
                for pid, _, name in utils.get_process_list():
                    if name.find(target) != -1:
                        self.attach_to_pid(int(pid))
                        return

    # Keyboard package has an issue with exceptions, any trigger function that throws an exception stops the event loop
    # Writing a custom event loop instead of ignoring exceptions could work as well but honestly, this looks cleaner
    # Keyboard package does not play well with Qt, do not use anything Qt related with hotkeys
    # Instead of using Qt functions, try to use their signals to prevent crashes
    @utils.ignore_exceptions
    def pause_hotkey_pressed(self) -> None:
        if not debugcore.driving_inferior:
            debugcore.interrupt_inferior(typedefs.STOP_REASON.PAUSE)

    @utils.ignore_exceptions
    def break_hotkey_pressed(self) -> None:
        if not debugcore.driving_inferior:
            debugcore.interrupt_inferior()

    @utils.ignore_exceptions
    def continue_hotkey_pressed(self) -> None:
        if not (debugcore.currentpid == -1 or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING or debugcore.driving_inferior):
            debugcore.continue_inferior()

    @utils.ignore_exceptions
    def cancel_hotkey_pressed(self) -> None:
        if debugcore.cancel_ongoing_command():
            logger.info("Cancelled the ongoing GDB command")

    @utils.ignore_exceptions
    def toggle_attach_hotkey_pressed(self) -> None:
        self.prepare_detach()
        self.attach_toggled.emit(debugcore.toggle_attach())

    def prepare_detach(self) -> None:
        if debugcore.currentpid == -1 or not debugcore.is_attached():
            return
        self.cleanup_speedhack()

    def sync_attach_state(self) -> None:
        if debugcore.currentpid == -1:
            return
        self.on_attach_toggled(typedefs.TOGGLE_ATTACH.ATTACHED if debugcore.is_attached() else typedefs.TOGGLE_ATTACH.DETACHED)

    def on_attach_toggled(self, result: int | None) -> None:
        if not result:
            logger.error("Unable to toggle attach")
        elif result == typedefs.TOGGLE_ATTACH.DETACHED:
            self.on_status_detached()
            self.pushButton_MemoryView.setEnabled(False)
            self.memory_view_window.close()
        else:
            self.pushButton_MemoryView.setEnabled(True)
            # Attaching back doesn't update the status if the process is already stopped before detachment
            with debugcore.status_changed_condition:
                debugcore.status_changed_condition.notify_all()

    def speedhack_toggle_hotkey_pressed(self) -> None:
        self.speedhack_action_requested.emit(0)

    def speedhack_speed_up_hotkey_pressed(self) -> None:
        self.speedhack_action_requested.emit(1)

    def speedhack_speed_down_hotkey_pressed(self) -> None:
        self.speedhack_action_requested.emit(-1)

    def cleanup_speedhack(self) -> None:
        if self.speedhack is not None:
            if self.speedhack.is_installed():
                self.speedhack.set_speed(speedhack.DEFAULT_SPEED)
            self.speedhack.reset()
        self.reset_speedhack_widgets()

    def on_speedhack_hotkey_action(self, delta: int) -> None:
        # We drive the widgets and let their signals run apply_speedhack, so hotkeys and clicks share the same code path.
        if debugcore.currentpid == -1 or self.speedhack is None:
            return
        if delta == 0:
            self.checkBox_Speedhack.toggle()
        else:
            # Up/Down also turns the hack on with the spinbox value becoming the live speed.
            if not self.checkBox_Speedhack.isChecked():
                self.checkBox_Speedhack.setChecked(True)
            self.doubleSpinBox_Speedhack.setValue(self.doubleSpinBox_Speedhack.value() + delta * speedhack.STEP)

    def apply_speedhack(self, *_: Any) -> None:
        # Both widget signals and the hotkeys (via on_speedhack_hotkey_action) funnel through here.
        if debugcore.currentpid == -1 or self.speedhack is None:
            return
        enabled = self.checkBox_Speedhack.isChecked()
        self.doubleSpinBox_Speedhack.setEnabled(enabled)
        # The hooks stay installed across toggles and we just change the speed, so we patch only once per session.
        # Doing so means we avoid racing thread RIPs sitting in the prologue that we'd be overwriting on every keypress,
        # which can cause freezes during rapid toggling.
        if enabled:
            # A failure here is usually a Wine inferior whose ntdll exports couldn't be resolved.
            if not self.speedhack.set_speed(self.doubleSpinBox_Speedhack.value()):
                QMessageBox.information(self, tr.INFO, tr.SPEEDHACK_UNAVAILABLE)
                self.reset_speedhack_widgets()
        # Only restore the default speed if the hooks already exist otherwise set_speed would install them.
        elif self.speedhack.is_installed():
            self.speedhack.set_speed(speedhack.DEFAULT_SPEED)

    def reset_speedhack_widgets(self) -> None:
        self.checkBox_Speedhack.blockSignals(True)
        self.doubleSpinBox_Speedhack.blockSignals(True)
        self.checkBox_Speedhack.setChecked(False)
        self.doubleSpinBox_Speedhack.setValue(speedhack.DEFAULT_SPEED)
        self.doubleSpinBox_Speedhack.setEnabled(False)
        self.checkBox_Speedhack.blockSignals(False)
        self.doubleSpinBox_Speedhack.blockSignals(False)

    def nextscan_hotkey_pressed(self, index: int) -> None:
        self.nextscan_requested.emit(index)

    def on_nextscan_requested(self, index: int) -> None:
        if self.scan_mode == typedefs.SCAN_MODE.NEW or self.is_scanning:
            return
        row = self.comboBox_ScanType.findData(index)
        if row == -1:
            return
        self.comboBox_ScanType.setCurrentIndex(row)
        self.pushButton_NextScan.clicked.emit()

    def treeWidget_AddressTable_context_menu_event(self, event: QContextMenuEvent) -> None:
        current_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        current_address = self._resolved_address(current_row) if current_row else None
        header = self.treeWidget_AddressTable.headerItem()
        menu = QMenu()
        delete_record = menu.addAction(f"{tr.DELETE}[Del]")
        edit_menu = menu.addMenu(tr.EDIT)
        edit_desc = edit_menu.addAction(f"{header.text(DESC_COL)}[Ctrl+Enter]")
        edit_address = edit_menu.addAction(f"{header.text(ADDR_COL)}[Ctrl+Alt+Enter]")
        edit_type = edit_menu.addAction(f"{header.text(TYPE_COL)}[Alt+Enter]")
        edit_value = edit_menu.addAction(f"{header.text(VALUE_COL)}[Enter]")
        edit_script = menu.addAction(tr.EDIT_SCRIPT)
        view_as_struct_menu = menu.addMenu(tr.VIEW_AS_STRUCT)
        structure_names = StructureManager.list_names()
        structure_actions = {}
        for name in structure_names:
            structure_actions[view_as_struct_menu.addAction(name)] = name
        show_hex = menu.addAction(tr.SHOW_HEX)
        show_dec = menu.addAction(tr.SHOW_DEC)
        show_unsigned = menu.addAction(tr.SHOW_UNSIGNED)
        show_signed = menu.addAction(tr.SHOW_SIGNED)
        toggle_record = menu.addAction(f"{tr.TOGGLE}[Space]")
        toggle_children = menu.addAction(f"{tr.TOGGLE_CHILDREN}[Ctrl+Space]")
        menu.addSeparator()
        browse_region = menu.addAction(f"{tr.BROWSE_MEMORY_REGION}[Ctrl+B]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        pointer_scanner = menu.addAction(tr.POINTER_SCANNER)
        pointer_scan = menu.addAction(tr.POINTER_SCAN)
        menu.addSeparator()
        what_writes = menu.addAction(tr.WHAT_WRITES)
        what_reads = menu.addAction(tr.WHAT_READS)
        what_accesses = menu.addAction(tr.WHAT_ACCESSES)
        menu.addSeparator()
        cut_record = menu.addAction(f"{tr.CUT}[Ctrl+X]")
        copy_record = menu.addAction(f"{tr.COPY}[Ctrl+C]")
        paste_record = menu.addAction(f"{tr.PASTE}[Ctrl+V]")
        paste_inside = menu.addAction(f"{tr.PASTE_INSIDE}[V]")
        menu.addSeparator()
        add_group = menu.addAction(tr.ADD_GROUP)
        create_group = menu.addAction(tr.CREATE_GROUP)
        if current_row is None:
            deletion_list = [
                edit_menu.menuAction(),
                edit_script,
                view_as_struct_menu.menuAction(),
                show_hex,
                show_dec,
                show_unsigned,
                show_signed,
                toggle_record,
                toggle_children,
                browse_region,
                disassemble,
                pointer_scan,
                what_writes,
                what_reads,
                what_accesses,
                cut_record,
                copy_record,
                paste_inside,
                delete_record,
                add_group,
            ]
            guiutils.delete_menu_entries(menu, deletion_list)
        elif self.get_script_entry(current_row) is not None:
            # A script entry only edits its description and script, the rest is address oriented
            script_deletion = [
                edit_address,
                edit_type,
                edit_value,
                view_as_struct_menu.menuAction(),
                show_hex,
                show_dec,
                show_unsigned,
                show_signed,
                browse_region,
                disassemble,
                pointer_scanner,
                pointer_scan,
                what_writes,
                what_reads,
                what_accesses,
            ]
            if current_row.childCount() == 0:
                script_deletion.append(toggle_children)
            guiutils.delete_menu_entries(menu, script_deletion)
        else:
            guiutils.delete_menu_entries(menu, [edit_script])
            if not structure_names:
                guiutils.delete_menu_entries(menu, [view_as_struct_menu.menuAction()])
            value_type = current_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            if self._is_struct_row(current_row):  # struct rows have no editable value or type, only an address.
                guiutils.delete_menu_entries(
                    menu,
                    [edit_value, edit_type, view_as_struct_menu.menuAction(), what_writes, what_reads, what_accesses],
                )
            if isinstance(value_type, (typedefs.IntegerValueType, typedefs.BitFieldValueType)):
                if value_type.value_repr is typedefs.VALUE_REPR.HEX:
                    guiutils.delete_menu_entries(menu, [show_unsigned, show_signed, show_hex])
                elif value_type.value_repr is typedefs.VALUE_REPR.UNSIGNED:
                    guiutils.delete_menu_entries(menu, [show_unsigned, show_dec])
                elif value_type.value_repr is typedefs.VALUE_REPR.SIGNED:
                    guiutils.delete_menu_entries(menu, [show_signed, show_dec])
            else:
                guiutils.delete_menu_entries(menu, [show_hex, show_dec, show_unsigned, show_signed])
            if current_row.childCount() == 0:
                guiutils.delete_menu_entries(menu, [toggle_children])
            guiutils.delete_menu_entries(menu, [pointer_scanner])
            if debugcore.currentpid == -1:
                browse_region.setEnabled(False)
                disassemble.setEnabled(False)
                pointer_scan.setEnabled(False)
            if not debugcore.is_attached():
                what_writes.setEnabled(False)
                what_reads.setEnabled(False)
                what_accesses.setEnabled(False)
        font_size = self.treeWidget_AddressTable.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            delete_record: self.delete_records,
            edit_desc: self.treeWidget_AddressTable_edit_desc,
            edit_address: self.treeWidget_AddressTable_edit_address,
            edit_type: self.treeWidget_AddressTable_edit_type,
            edit_value: self.treeWidget_AddressTable_edit_value,
            edit_script: lambda: self.open_script_entry_in_engine(current_row, self.get_script_entry(current_row)),
            show_hex: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.HEX),
            show_dec: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.UNSIGNED),
            show_unsigned: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.UNSIGNED),
            show_signed: lambda: self.treeWidget_AddressTable_change_repr(typedefs.VALUE_REPR.SIGNED),
            toggle_record: self.toggle_records,
            toggle_children: lambda: self.toggle_records(True),
            browse_region: lambda: self.browse_region_for_address(current_address),
            disassemble: lambda: self.disassemble_for_address(current_address),
            pointer_scanner: self.exec_pointer_scanner,
            pointer_scan: self.exec_pointer_scan,
            what_writes: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.WRITE_ONLY),
            what_reads: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.READ_ONLY),
            what_accesses: lambda: self.exec_track_watchpoint_widget(typedefs.WATCHPOINT_TYPE.BOTH),
            cut_record: self.cut_records,
            copy_record: self.copy_records,
            paste_record: self.paste_records,
            paste_inside: lambda: self.paste_records(True),
            add_group: self.group_records,
            create_group: self.create_group,
        }
        for struct_action, struct_name in structure_actions.items():
            actions[struct_action] = lambda n=struct_name: self._view_struct_at_row(current_row, n)
        try:
            actions[action]()
        except KeyError:
            pass

    def _view_struct_at_row(self, row: QTreeWidgetItem, structure_name: str) -> None:
        if row is None:
            return
        resolved_address = self._resolved_address(row)
        view = StructureViewDialog(self, structure_name, resolved_address)
        view.add_to_table_requested.connect(self._add_structure_records_to_table)
        view.show()

    def exec_pointer_scanner(self) -> None:
        pointer_window = PointerScanWindow(self, "0x0")
        pointer_window.show()

    def exec_pointer_scan(self) -> None:
        selected_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not selected_row:
            return
        address = self._resolved_address(selected_row)
        pointer_window = PointerScanWindow(self, address)
        pointer_window.show()
        dialog = PointerScanSearchDialog(pointer_window, address)
        if dialog.exec() and dialog.result_map_path:
            pointer_window.load_map(dialog.result_map_path)

    def exec_track_watchpoint_widget(self, watchpoint_type: int) -> None:
        selected_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not selected_row:
            return
        address = self._resolved_address(selected_row)
        value_type = selected_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        if isinstance(value_type, typedefs.StringValueType):
            value_text = selected_row.text(VALUE_COL)
            errors = "surrogateescape" if value_type.encoding == "utf-8" else "replace"
            byte_len = len(value_text.encode(value_type.encoding, errors))
        else:
            byte_len = value_type.read_size
        address_data = selected_row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
        if isinstance(address_data, typedefs.PointerChainRequest):
            selection_dialog = TrackSelectorDialog(self)
            selection_dialog.exec()
            if not selection_dialog.selection:
                return
            if selection_dialog.selection == "pointer":
                address = address_data.get_base_address_as_str()
                parent = selected_row.parent()
                if address.startswith(("+", "-")) and parent:
                    address = (parent.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1) or "") + address
                byte_len = 4 if debugcore.effective_arch == typedefs.INFERIOR_ARCH.ARCH_32 else 8
        TrackWatchpointWidget(self, address, byte_len, watchpoint_type)

    def browse_region_for_address(self, address: str) -> None:
        address = utils.safe_str_to_int((address or "").removeprefix("P->"), 16)
        if address:
            self.memory_view_window.hex_dump_address(address)
            self.memory_view_window.show()
            self.memory_view_window.activateWindow()

    def disassemble_for_address(self, address: str) -> None:
        if address and self.memory_view_window.disassemble_expression(address.removeprefix("P->")):
            self.memory_view_window.show()
            self.memory_view_window.activateWindow()

    def change_freeze_type(self, freeze_type: int | None = None, row: QTreeWidgetItem | None = None) -> None:
        if freeze_type is None:
            # No type has been specified, iterate through the freeze types
            # This usually happens if user clicks the freeze type text instead of the checkbox
            frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            if not isinstance(frozen, typedefs.Frozen):  # script entries have no freeze type
                return
            if frozen.freeze_type == typedefs.FREEZE_TYPE.ALLOW_DECREMENT:
                # Decrement is the last freeze type
                freeze_type = typedefs.FREEZE_TYPE.DEFAULT
            else:
                freeze_type = frozen.freeze_type + 1
        rows = [row] if row else self.treeWidget_AddressTable.selectedItems()
        for row in rows:
            frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            if not isinstance(frozen, typedefs.Frozen):  # skip script entries
                continue
            if row.checkState(FROZEN_COL) == Qt.CheckState.Checked:
                frozen.freeze_type = freeze_type
                if freeze_type == typedefs.FREEZE_TYPE.DEFAULT:
                    row.setText(FROZEN_COL, "")
                    row.setForeground(FROZEN_COL, QBrush())
                elif freeze_type == typedefs.FREEZE_TYPE.ALLOW_INCREMENT:
                    row.setText(FROZEN_COL, "▲")
                    row.setForeground(FROZEN_COL, QBrush(QColor(0, 255, 0)))
                elif freeze_type == typedefs.FREEZE_TYPE.ALLOW_DECREMENT:
                    row.setText(FROZEN_COL, "▼")
                    row.setForeground(FROZEN_COL, QBrush(QColor(255, 0, 0)))
            else:
                frozen.freeze_type = typedefs.FREEZE_TYPE.DEFAULT
                row.setText(FROZEN_COL, "")
                row.setForeground(FROZEN_COL, QBrush())

    def toggle_records(self, toggle_children: bool = False) -> None:
        selected_items = self.treeWidget_AddressTable.selectedItems()
        for row in selected_items:
            check_state = row.checkState(FROZEN_COL)
            new_state = Qt.CheckState.Checked if check_state == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
            self.handle_freeze_change(row, new_state)
            if toggle_children:
                for index in range(row.childCount()):
                    child = row.child(index)
                    child_old_state = child.checkState(FROZEN_COL)
                    child_new_state = Qt.CheckState.Checked if child_old_state == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked
                    self.handle_freeze_change(child, child_new_state)

    def cut_records(self) -> None:
        self.copy_records()
        self.delete_records()

    def copy_records(self) -> None:
        # Recursive copy
        items = self.treeWidget_AddressTable.selectedItems()

        def index_of(item: QTreeWidgetItem) -> list[int]:
            """Returns the index used to access the given QTreeWidgetItem
            as a list of ints."""
            result = []
            while True:
                parent = item.parent()
                if parent:
                    result.append(parent.indexOfChild(item))
                    item = parent
                else:
                    result.append(item.treeWidget().indexOfTopLevelItem(item))
                    return result[::-1]

        # First, order the items by their indices in the tree widget.
        # Store the indices for later usage.
        index_items = [(index_of(item), item) for item in items]
        index_items.sort(key=lambda x: x[0])  # sort by index

        # Now filter any selected items that is a descendant of another selected items.
        items = []
        last_index = [-1]  # any invalid list of indices are fine
        for index, item in index_items:
            if index[: len(last_index)] == last_index:
                continue  # this item is a descendant of the last item
            items.append(item)
            last_index = index

        QApplication.clipboard().setText(repr([self._read_for_copy(item) for item in items]))

    def _read_for_copy(self, row: QTreeWidgetItem) -> tuple:
        record = self.read_address_table_recursively(row)
        if self.get_script_entry(row) is not None:  # scripts carry no address to absolutize
            return record
        desc, address_expr, vt, *rest = record
        return (desc, self._absolutize_root(row, address_expr), vt, *rest)

    def _absolutize_root(self, row: QTreeWidgetItem, address_expr: str | tuple) -> str | tuple:
        # Rewrite a relative (+/-) address into an absolute one using the parent's resolved address,
        # so a row copied out of its group still points somewhere when pasted alone.
        # Pointer chains keep their offsets, only the base is absolutized.
        parent = row.parent()
        if not parent:
            return address_expr
        parent_resolved = parent.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1)
        if not parent_resolved:
            return address_expr
        if isinstance(address_expr, str) and address_expr.startswith(("+", "-")):
            return row.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1) or parent_resolved + address_expr
        if isinstance(address_expr, (list, tuple)) and address_expr:
            base = address_expr[0]
            if isinstance(base, str) and base.startswith(("+", "-")):
                return (parent_resolved + base, *address_expr[1:])
        return address_expr

    def insert_records(self, records: list, parent_row: QTreeWidgetItem, insert_index: int) -> None:
        # parent_row should be a QTreeWidgetItem in treeWidget_AddressTable
        # records should be an iterable of valid output of read_address_table_recursively
        assert isinstance(parent_row, QTreeWidgetItem)
        for rec in records:
            row = QTreeWidgetItem()
            row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)

            # A 5 element record carries an extra dict before its children (see read_address_table_recursively)
            extra = rec[3] if len(rec) == 5 else None
            if isinstance(extra, dict) and "script" in extra:
                self.init_script_row(row, rec[0], typedefs.ScriptEntry(extra["script"]))
            else:
                frozen = typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT)
                row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
                # Deserialize address_expr and value_type from rec
                if isinstance(rec[1], (list, tuple)):
                    address_expr = typedefs.PointerChainRequest(*rec[1])
                else:
                    address_expr = rec[1]
                value_type = typedefs.ValueType.deserialize(rec[2])
                self.change_address_table_entries(row, rec[0], address_expr, value_type)

            # Insert the row at the current insert_index
            parent_row.insertChild(insert_index, row)
            insert_index += 1

            # Recursively insert children of this row
            self.insert_records(rec[-1], row, 0)
        self.mark_address_tree_changed()

    def paste_records(self, insert_inside: bool = False) -> None:
        try:
            records = ast.literal_eval(QApplication.clipboard().text())
        except (SyntaxError, ValueError, MemoryError, RecursionError):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return
        if not isinstance(records, list):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return

        insert_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        root = self.treeWidget_AddressTable.invisibleRootItem()
        try:
            if not insert_row:  # this is common when the treeWidget_AddressTable is empty
                self.insert_records(records, root, self.treeWidget_AddressTable.topLevelItemCount())
            elif insert_inside:
                self.insert_records(records, insert_row, 0)
            else:
                parent = insert_row.parent() or root
                self.insert_records(records, parent, parent.indexOfChild(insert_row) + 1)
        except (TypeError, ValueError, IndexError, KeyError, AttributeError):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return
        self.update_address_table()

    def group_records(self) -> None:
        selected_items = self.treeWidget_AddressTable.selectedItems()
        for item in selected_items.copy():
            parent = item.parent()
            while parent:
                if parent in selected_items:
                    selected_items.remove(item)
                    break
                parent = parent.parent()
        group = self.create_group()
        if group:
            for item in selected_items:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.treeWidget_AddressTable.indexOfTopLevelItem(item)
                    self.treeWidget_AddressTable.takeTopLevelItem(index)
                group.addChild(item)
            self.treeWidget_AddressTable.setCurrentItem(group)
            group.setExpanded(True)

    def create_group(self) -> QTreeWidgetItem | None:
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_DESCRIPTION, tr.GROUP)])
        if dialog.exec():
            desc = dialog.get_values()[0]
            return self.add_entry_to_addresstable(desc, "0x0")
        return None

    def script_entries_in(self, item: QTreeWidgetItem):
        # Yields the script entries of item and all its descendants
        entry = self.get_script_entry(item)
        if entry is not None:
            yield entry
        for index in range(item.childCount()):
            yield from self.script_entries_in(item.child(index))

    def delete_records(self) -> None:
        selected_items = self.treeWidget_AddressTable.selectedItems()
        if self.libpince_engine_window:  # close any bound tabs before their rows go away
            for item in selected_items:
                for entry in self.script_entries_in(item):
                    self.libpince_engine_window.close_script_entry(entry)
        root = self.treeWidget_AddressTable.invisibleRootItem()
        for item in selected_items:
            (item.parent() or root).removeChild(item)
        if selected_items:
            self.mark_address_tree_changed()

    def treeWidget_AddressTable_mouse_release_event(self, event: QMouseEvent) -> None:
        item = self.treeWidget_AddressTable.itemAt(event.pos())
        column = self.treeWidget_AddressTable.columnAt(event.pos().x())
        if item and column == FROZEN_COL:
            old_state = item.checkState(FROZEN_COL)
            self.treeWidget_AddressTable_mouseReleaseEvent_original(event)
            new_state = item.checkState(FROZEN_COL)
            if old_state != new_state:
                self.handle_freeze_change(item, new_state)
            elif new_state == Qt.CheckState.Checked:
                self.change_freeze_type(row=item)
                frozen = item.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                if isinstance(frozen, typedefs.Frozen):
                    self.change_freeze_type(frozen.freeze_type, item)
        else:
            self.treeWidget_AddressTable_mouseReleaseEvent_original(event)

    def treeWidget_AddressTable_key_press_event(self, event: QKeyEvent) -> None:
        current_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        current_address = self._resolved_address(current_row) if current_row else None
        actions = {
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete): self.delete_records,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B): lambda: self.browse_region_for_address(current_address),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): lambda: self.disassemble_for_address(current_address),
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R): self.pushButton_RefreshAddressTable_clicked,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space): self.toggle_records,
            QKeyCombination(Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Space): self.toggle_records,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Space): lambda: self.toggle_records(True),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_X): self.cut_records,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C): self.copy_records,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V): self.paste_records,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_V): lambda: self.paste_records(True),
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return): self.treeWidget_AddressTable_edit_value,
            QKeyCombination(Qt.KeyboardModifier.KeypadModifier, Qt.Key.Key_Enter): self.treeWidget_AddressTable_edit_value,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Return): self.treeWidget_AddressTable_edit_desc,
            QKeyCombination(
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return
            ): self.treeWidget_AddressTable_edit_address,
            QKeyCombination(Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return): self.treeWidget_AddressTable_edit_type,
        }
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.treeWidget_AddressTable_keyPressEvent_original(event)

    def invalidate_address_expression_cache(self, refresh: bool = False) -> None:
        states.exp_cache.clear()
        if refresh:
            self.update_address_table()

    def update_address_table(self) -> None:
        if debugcore.currentpid == -1 or self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        with debugcore.memory_handle() as mem_handle:
            basic_math_exp = re.compile(r"^[0-9a-fA-F][/*+\-0-9a-fA-FxX]+$")
            while True:
                row = it.value()
                if not row:
                    break
                it += 1
                if self.get_script_entry(row) is not None:  # script entries have no address/value to refresh
                    continue
                address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
                if isinstance(address_data, typedefs.PointerChainRequest):
                    expression = address_data.get_base_address_as_str()
                else:
                    expression = address_data
                parent = row.parent()
                if parent and expression.startswith(("+", "-")):
                    parent_resolved = parent.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1)
                    if parent_resolved:
                        expression = parent_resolved + expression
                if expression in states.exp_cache:
                    address = states.exp_cache[expression]
                elif expression.startswith(("+", "-")):
                    address = None
                elif basic_math_exp.match(expression.replace(" ", "")) and "**" not in expression.replace(" ", ""):
                    try:
                        address = hex(eval(expression))
                        states.exp_cache[expression] = address
                    except:
                        address = debugcore.examine_expression(expression).address
                        if address is not None:
                            states.exp_cache[expression] = address
                else:
                    address = debugcore.examine_expression(expression).address
                    if address is not None:
                        states.exp_cache[expression] = address
                vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                is_struct_child = parent and self._is_struct_row(parent)
                if isinstance(address_data, typedefs.PointerChainRequest):
                    # The original base could be a symbol so we have to save it
                    # This little hack avoids the unnecessary examine_expression call
                    # TODO: Consider implementing exp_cache inside libpince so we don't need this hack
                    pointer_chain_req = address_data
                    if address:
                        old_base = pointer_chain_req.base_address  # save the old base
                        pointer_chain_req.base_address = address
                        try:
                            pointer_chain_result = debugcore.read_pointer_chain(pointer_chain_req)
                        finally:
                            address_data.base_address = old_base  # then set it back
                        if pointer_chain_result and pointer_chain_result.get_final_address():
                            address = pointer_chain_result.get_final_address_as_hex()
                        else:
                            address = None
                        if address:
                            row.setText(ADDR_COL, address_data.get_base_address_as_str() if is_struct_child else f"P->{address}")
                        else:
                            row.setText(ADDR_COL, "P->??")
                    else:
                        row.setText(ADDR_COL, "P->??")
                else:
                    if address:
                        if is_struct_child and isinstance(address_data, str) and address_data.startswith(("+", "-")):
                            row.setText(ADDR_COL, address_data)
                        else:
                            row.setText(ADDR_COL, address)
                    elif expression.startswith(("+", "-")):
                        row.setText(ADDR_COL, "???")
                    else:
                        row.setText(ADDR_COL, address_data)
                address = "" if not address else address
                row.setData(ADDR_COL, Qt.ItemDataRole.UserRole + 1, address)
                value = debugcore.read_memory(address, vt, mem_handle=mem_handle)
                value = "" if value is None else str(value)
                row.setText(VALUE_COL, value)

    def update_scan_box_state(self) -> None:
        if self.is_scanning == True:
            self.pushButton_CancelScan.setEnabled(True)
            self.pushButton_NewFirstScan.setEnabled(False)
            self.pushButton_NextScan.setEnabled(False)
            self.pushButton_UndoScan.setEnabled(False)
            self.widget_ScanOptions.setEnabled(False)
            self.widget_ScanFields.setEnabled(False)
        else:
            is_new_scan = self.scan_mode == typedefs.SCAN_MODE.NEW
            self.pushButton_CancelScan.setEnabled(False)
            self.pushButton_NewFirstScan.setEnabled(True)
            self.pushButton_NextScan.setEnabled(not is_new_scan)
            self.pushButton_UndoScan.setEnabled(self.undo_scan_available)
            self.widget_ScanOptions.setEnabled(True)
            self.comboBox_ScanType_current_index_changed()
            self.comboBox_ScanScope.setEnabled(is_new_scan)
            self.comboBox_ValueType.setEnabled(is_new_scan)
            self.comboBox_Endianness.setEnabled(is_new_scan)
            self.comboBox_Alignment.setEnabled(is_new_scan)
            self.pushButton_ScanRegions.setEnabled(is_new_scan)

    # Create properly typed values for memscan
    def validate_search_values(self, search_for: str, search_for2: str) -> tuple[int | float | str | BytePattern | None, int | float | None]:
        # Manually fix an edge case in number validators
        if search_for == "-":
            search_for = ""
        if search_for2 == "-":
            search_for2 = ""

        if search_for == "":
            return None, None

        value_2 = None

        # none of these should be possible to be true at the same time
        scan_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        if scan_index >= typedefs.SCAN_INDEX.FLOAT_ANY and scan_index <= typedefs.SCAN_INDEX.ANY:
            # Manually fix an edge case in float_number validator
            if search_for[-1] in {"e", "E"}:
                search_for += "0"
            if len(search_for2) != 0 and search_for2[-1] in {"e", "E"}:
                search_for2 += "0"
            # Python's float() only accepts '.' as the decimal separator, so always normalize to '.'
            search_for = search_for.replace(",", ".")
            search_for2 = search_for2.replace(",", ".")
            try:
                value_1 = float(search_for)
                value_2 = float(search_for2) if search_for2 != "" else None
            except ValueError:
                return None, None
        elif scan_index == typedefs.SCAN_INDEX.STRING:
            value_1 = search_for
        elif scan_index == typedefs.SCAN_INDEX.AOB:
            value_1 = BytePattern.from_string(search_for)
        else:  # Integers
            if self.checkBox_Hex.isChecked():
                if not search_for.startswith(("0x", "-0x")):
                    negative_str = "-" if search_for.startswith("-") else ""
                    search_for = negative_str + "0x" + search_for.lstrip("-")
                if search_for in {"0x", "-0x"}:
                    return None, None
                if search_for2 != "":
                    if not search_for2.startswith(("0x", "-0x")):
                        negative_str = "-" if search_for2.startswith("-") else ""
                        search_for2 = negative_str + "0x" + search_for2.lstrip("-")
                    if search_for2 in {"0x", "-0x"}:
                        search_for2 = ""
                value_1 = int(search_for, 16)
                value_2 = int(search_for2, 16) if search_for2 != "" else None
            else:
                value_1 = int(search_for)
                value_2 = int(search_for2) if search_for2 != "" else None

        return value_1, value_2

    def scan_values(self) -> None:
        if debugcore.currentpid == -1:
            return
        is_next_scan = self.scan_mode == typedefs.SCAN_MODE.ONGOING
        type_index = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        if type_index == typedefs.SCAN_TYPE.UNKNOWN:
            scan_thread = guitypedefs.Worker(memscan.snapshot)
        else:
            value_1, value_2 = None, None
            if self.widget_ScanFields.isEnabled():
                search_for2 = self.lineEdit_Scan2.text() if type_index == typedefs.SCAN_TYPE.BETWEEN else ""
                try:
                    value_1, value_2 = self.validate_search_values(self.lineEdit_Scan.text(), search_for2)
                except ValueError:
                    return
                if value_1 == None:
                    return
            scan_type = scancore.scan_type_to_memscan_dict[type_index]
            scan_thread = guitypedefs.Worker(memscan.scan, scan_type, value_1, value_2)
        self.progressBar.setValue(0)
        self.progress_bar_timer = QTimer(self, timeout=self.update_progress_bar)
        self.progress_bar_timer.start(100)
        scan_thread.signals.finished.connect(lambda _: self.scan_callback(is_next_scan))
        scan_thread.signals.error.connect(lambda error: self.scan_error(error, not is_next_scan))
        self.is_scanning = True
        self.undo_scan_available = False
        self.update_scan_box_state()
        states.threadpool.start(scan_thread)

    def resize_address_table(self) -> None:
        self.treeWidget_AddressTable.resizeColumnToContents(FROZEN_COL)

    # gets the information from the dialog then adds it to addresstable
    def pushButton_AddAddressManually_clicked(self) -> None:
        manual_address_dialog = ManualAddressDialog(self)
        if manual_address_dialog.exec():
            desc, address_expr, vt = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(desc, address_expr, vt)
            self.update_address_table()

    def pushButton_RefreshAddressTable_clicked(self) -> None:
        self.invalidate_address_expression_cache(refresh=True)

    def pushButton_MemoryView_clicked(self) -> None:
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def pushButton_Wiki_clicked(self) -> None:
        utils.execute_command_as_user('python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def pushButton_About_clicked(self) -> None:
        about_widget = AboutWidget(self)
        about_widget.show()
        about_widget.activateWindow()

    def check_for_updates_on_startup(self) -> None:
        if not os.environ.get("APPDIR"):
            return
        settings_instance = QSettings()
        if not settings_instance.contains(settings.CHECK_UPDATES_ON_STARTUP):
            message_box = QMessageBox(self)
            message_box.setIcon(QMessageBox.Icon.Question)
            message_box.setWindowTitle(tr.INFO)
            message_box.setText(tr.UPDATE_CHECK_ON_STARTUP_PROMPT)
            checkbox = QCheckBox(tr.CHECK_FOR_UPDATES_ON_STARTUP)
            message_box.setCheckBox(checkbox)
            message_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            message_box.exec()
            settings_instance.setValue(settings.CHECK_UPDATES_ON_STARTUP, checkbox.isChecked())
        if settings_instance.value(settings.CHECK_UPDATES_ON_STARTUP, False, type=bool):
            self.check_for_updates(show_result=False)

    def check_for_updates(self, show_result: bool = True) -> None:
        if self.update_check_thread and self.update_check_thread.isRunning():
            return
        self.show_update_check_result = show_result
        self._set_update_button_enabled(False)
        self.update_check_thread = update_check.UpdateCheckThread(self)
        self.update_check_thread.finished.connect(self._on_update_check_thread_finished)
        self.update_check_thread.start()

    def _on_update_check_thread_finished(self) -> None:
        self._set_update_button_enabled(True)
        thread = self.update_check_thread
        self.update_check_thread = None
        if thread:
            self.on_update_check_finished(thread.result, self.show_update_check_result)
            thread.deleteLater()
        self.show_update_check_result = True

    def _set_update_button_enabled(self, enabled: bool) -> None:
        self.pushButton_CheckForUpdates.setEnabled(enabled and bool(os.environ.get("APPDIR")))

    def on_update_check_finished(self, result: update_check.UpdateCheckResult, show_result: bool = True) -> None:
        status = result.status
        if status == update_check.UpdateCheckStatus.UPDATE_AVAILABLE:
            QMessageBox.information(self, tr.INFO, tr.UPDATE_AVAILABLE_MESSAGE)
        elif show_result and status == update_check.UpdateCheckStatus.UP_TO_DATE:
            QMessageBox.information(self, tr.INFO, tr.UPDATE_NOT_AVAILABLE)
        elif status == update_check.UpdateCheckStatus.ERROR:
            logger.warning("Update check failed: %s", result.message)
            if show_result:
                QMessageBox.information(self, tr.ERROR, tr.UPDATE_CHECK_FAILED)

    def pushButton_Settings_clicked(self) -> None:
        SettingsDialog(self).exec()

    def pushButton_Console_clicked(self) -> None:
        console_widget = ConsoleWidget(self)
        console_widget.gdb_command_sent.connect(lambda: self.invalidate_address_expression_cache(refresh=True))
        console_widget.phase_out_request.connect(self.prepare_detach)
        console_widget.attach_state_changed.connect(self.sync_attach_state)
        console_widget.showMaximized()

    def checkBox_Hex_stateChanged(self, state: int) -> None:
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            # allows only things that are hex, can also start with 0x
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int_hex"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int_hex"))
            base, converter = 10, hex
        else:
            # sets it back to integers only
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int"))
            base, converter = 16, str
        if self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) <= typedefs.SCAN_INDEX.INT64:
            for line_edit in (self.lineEdit_Scan, self.lineEdit_Scan2):
                try:
                    line_edit.setText(converter(int(line_edit.text(), base)))
                except ValueError:
                    pass

    def pushButton_NewFirstScan_clicked(self) -> None:
        if debugcore.currentpid == -1:
            self.comboBox_ScanType_init()
            return
        if self.scan_mode == typedefs.SCAN_MODE.ONGOING:
            self.reset_scan()
            for region_id in self.deleted_regions:
                scancore.memscan.remove_region_by_id(int(region_id))
        else:
            self.scan_values()
            if self.is_scanning == True:
                self.scan_mode = typedefs.SCAN_MODE.ONGOING
                self.pushButton_NewFirstScan.setText(tr.NEW_SCAN)
        self.comboBox_ScanType_init()

    def handle_line_edit_scan_key_press_event(self, event: QKeyEvent) -> None:
        valid_keys = [Qt.Key.Key_Return, Qt.Key.Key_Enter]
        if event.key() in valid_keys and Qt.KeyboardModifier.ControlModifier in event.modifiers():
            self.pushButton_NewFirstScan_clicked()
            return

        if event.key() in valid_keys:
            if self.scan_mode == typedefs.SCAN_MODE.ONGOING:
                self.pushButton_NextScan_clicked()
            else:
                self.pushButton_NewFirstScan_clicked()
            return

    def lineEdit_Scan_on_key_press_event(self, event: QKeyEvent) -> None:
        self.handle_line_edit_scan_key_press_event(event)
        self.lineEdit_Scan_keyPressEvent_original(event)

    def lineEdit_Scan2_on_key_press_event(self, event: QKeyEvent) -> None:
        self.handle_line_edit_scan_key_press_event(event)
        self.lineEdit_Scan2_keyPressEvent_original(event)

    def pushButton_UndoScan_clicked(self) -> None:
        if debugcore.currentpid == -1:
            return
        undo_thread = guitypedefs.Worker(memscan.undo_scan)
        undo_thread.signals.finished.connect(lambda _: self.scan_callback(False))
        undo_thread.signals.error.connect(self.scan_error)
        self.is_scanning = True
        self.undo_scan_available = False
        self.update_scan_box_state()
        self.pushButton_CancelScan.setEnabled(False)
        states.threadpool.start(undo_thread)

    def pushButton_CancelScan_clicked(self) -> None:
        if debugcore.currentpid == -1:
            return
        memscan.set_stop_flag(True)
        self.pushButton_CancelScan.setEnabled(False)

    def comboBox_ScanType_current_index_changed(self) -> None:
        hidden_types = [
            typedefs.SCAN_TYPE.INCREASED,
            typedefs.SCAN_TYPE.DECREASED,
            typedefs.SCAN_TYPE.CHANGED,
            typedefs.SCAN_TYPE.UNCHANGED,
            typedefs.SCAN_TYPE.UNKNOWN,
        ]
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) in hidden_types:
            self.widget_ScanFields.setEnabled(False)
        else:
            self.widget_ScanFields.setEnabled(True)
        if self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole) == typedefs.SCAN_TYPE.BETWEEN:
            self.label_Between.setVisible(True)
            self.lineEdit_Scan2.setVisible(True)
        else:
            self.label_Between.setVisible(False)
            self.lineEdit_Scan2.setVisible(False)

    def comboBox_ScanType_init(self) -> None:
        scan_type_text = {
            typedefs.SCAN_TYPE.EXACT: tr.EXACT,
            typedefs.SCAN_TYPE.NOT: tr.NOT,
            typedefs.SCAN_TYPE.INCREASED: tr.INCREASED,
            typedefs.SCAN_TYPE.INCREASED_BY: tr.INCREASED_BY,
            typedefs.SCAN_TYPE.DECREASED: tr.DECREASED,
            typedefs.SCAN_TYPE.DECREASED_BY: tr.DECREASED_BY,
            typedefs.SCAN_TYPE.LESS: tr.LESS_THAN,
            typedefs.SCAN_TYPE.MORE: tr.MORE_THAN,
            typedefs.SCAN_TYPE.BETWEEN: tr.BETWEEN,
            typedefs.SCAN_TYPE.CHANGED: tr.CHANGED,
            typedefs.SCAN_TYPE.UNCHANGED: tr.UNCHANGED,
            typedefs.SCAN_TYPE.UNKNOWN: tr.UNKNOWN_VALUE,
        }
        current_type = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        value_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        self.comboBox_ScanType.clear()
        items = typedefs.SCAN_TYPE.get_list(self.scan_mode, value_type)
        for type_index in items:
            self.comboBox_ScanType.addItem(scan_type_text[type_index], type_index)
        idx = self.comboBox_ScanType.findData(current_type)
        if idx >= 0:
            self.comboBox_ScanType.setCurrentIndex(idx)
        else:
            self.comboBox_ScanType.setCurrentIndex(0)

    def comboBox_ScanScope_init(self) -> None:
        guiutils.fill_scope_combobox(self.comboBox_ScanScope)
        self.comboBox_ScanScope.currentIndexChanged.connect(self.on_scan_scope_changed)

    def on_scan_scope_changed(self) -> None:
        self.deleted_regions.clear()
        scan_level = self.comboBox_ScanScope.currentData(Qt.ItemDataRole.UserRole)
        memscan.set_scan_level(scan_level)
        memscan.reset()

    def comboBox_Alignment_current_index_changed(self) -> None:
        alignment = self.comboBox_Alignment.currentData(Qt.ItemDataRole.UserRole)
        memscan.set_alignment(alignment)

    def on_endianness_changed(self) -> None:
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        if endian == typedefs.ENDIANNESS.HOST:
            memscan.set_reverse_endianness(False)
        elif endian == typedefs.ENDIANNESS.LITTLE:
            memscan.set_reverse_endianness(sys.byteorder != "little")
        elif endian == typedefs.ENDIANNESS.BIG:
            memscan.set_reverse_endianness(sys.byteorder != "big")

    def comboBox_ValueType_init(self) -> None:
        self.comboBox_ValueType.clear()
        for value_index, value_text in typedefs.scan_index_to_text_dict.items():
            self.comboBox_ValueType.addItem(value_text, value_index)
        self.comboBox_ValueType.setCurrentIndex(self.comboBox_ValueType.findData(typedefs.SCAN_INDEX.INT32))
        self.comboBox_ValueType_current_index_changed()

    def pushButton_NextScan_clicked(self) -> None:
        self.scan_values()

    def pushButton_ScanRegions_clicked(self) -> None:
        scan_regions_dialog = ManageScanRegionsDialog(self)
        if scan_regions_dialog.exec():
            self.deleted_regions.extend(scan_regions_dialog.get_values())

    def scan_error(self, error: Exception, first_scan: bool = False) -> None:
        self.is_scanning = False
        self.undo_scan_available = False
        self.progress_bar_timer.stop()
        if first_scan:
            self.scan_mode = typedefs.SCAN_MODE.NEW
            self.pushButton_NewFirstScan.setText(tr.FIRST_SCAN)
            self.comboBox_ScanType_init()
        self.update_scan_box_state()
        QMessageBox.information(self, tr.ERROR, str(error))

    def scan_callback(self, undo_available: bool) -> None:
        self.is_scanning = False
        self.undo_scan_available = undo_available and self.scan_mode == typedefs.SCAN_MODE.ONGOING
        self.progress_bar_timer.stop()
        self.progressBar.setValue(100)
        self.update_scan_box_state()
        matches = memscan.matches()
        self.update_match_count()
        self.tableWidget_valuesearchtable.setRowCount(0)
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        scan_text = self.lineEdit_Scan.text()
        length = (
            len(scan_text.split()) if current_type == typedefs.SCAN_INDEX.AOB else len(scan_text) if current_type == typedefs.SCAN_INDEX.STRING else 0
        )
        hex_values = self.checkBox_Hex.isChecked()
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        with debugcore.memory_handle() as mem_handle:
            row = 0
            self.tableWidget_valuesearchtable.setSortingEnabled(False)
            for match in matches:
                address = hex(match.address)
                match_info = match.match_info
                if match_info.raw_bits == 0:
                    # Ignore unknown entries (no match flags), should not happen as every received match is valid
                    logger.error("Found invalid/unknown match! Skipping...")
                    continue
                # This is technically wrong because we can have multiple possible value types through a match
                # but we'll go with the lowest matching value type
                if hex_values:
                    value_repr = typedefs.VALUE_REPR.HEX
                else:
                    value_repr = typedefs.VALUE_REPR.SIGNED if match_info.is_signed_integer_only() else typedefs.VALUE_REPR.UNSIGNED
                if match.is_string_match():
                    value_type = typedefs.StringValueType("utf-8", length=length, endian=endian)
                elif match.is_bytearray_match():
                    value_type = typedefs.ByteArrayValueType(length)
                elif match_info.has_int8() or match_info.has_uint8():
                    value_type = typedefs.IntegerValueType(8, value_repr=value_repr, endian=endian)
                elif match_info.has_int16() or match_info.has_uint16():
                    value_type = typedefs.IntegerValueType(16, value_repr=value_repr, endian=endian)
                elif match_info.has_int32() or match_info.has_uint32():
                    value_type = typedefs.IntegerValueType(32, value_repr=value_repr, endian=endian)
                elif match_info.has_int64() or match_info.has_uint64():
                    value_type = typedefs.IntegerValueType(64, value_repr=value_repr, endian=endian)
                elif match_info.has_float32():
                    value_type = typedefs.FloatValueType(32, endian=endian)
                elif match_info.has_float64():
                    value_type = typedefs.FloatValueType(64, endian=endian)
                else:
                    logger.error("Passed invalid match to value type retrieval! Shouldn't be possible!")
                    continue
                current_item = QTableWidgetItem(address)
                current_item.setData(Qt.ItemDataRole.UserRole, value_type)
                # TODO: Change GDB reading to memscan
                value = debugcore.read_memory(address, value_type, mem_handle=mem_handle)
                value = "" if value is None else str(value)
                stored_value = match.stored_value
                if stored_value is None:
                    previous_value = ""
                elif isinstance(value_type, (typedefs.ByteArrayValueType, typedefs.StringValueType)):
                    previous_value = value_type.decode(bytes(stored_value))
                elif isinstance(value_type, typedefs.IntegerValueType):
                    prefix = "int" if value_type.value_repr == typedefs.VALUE_REPR.SIGNED else "uint"
                    number = getattr(stored_value.data, f"{prefix}{value_type.bits}_value")
                    previous_value = hex(number) if value_type.value_repr == typedefs.VALUE_REPR.HEX else str(number)
                elif isinstance(value_type, typedefs.FloatValueType):
                    previous_value = str(getattr(stored_value.data, f"float{value_type.bits}_value"))
                else:
                    previous_value = ""
                if debugcore.is_address_static(address):
                    current_item.setForeground(QColor(0, 136, 85))
                self.tableWidget_valuesearchtable.insertRow(row)
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_ADDRESS_COL, current_item)
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_VALUE_COL, QTableWidgetItem(value))
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_PREVIOUS_COL, QTableWidgetItem(previous_value))
                row += 1
                if row == 5000:
                    break
        self.tableWidget_valuesearchtable.resizeColumnsToContents()
        self.tableWidget_valuesearchtable.setSortingEnabled(True)

    def update_match_count(self) -> None:
        match_count = memscan.get_match_count()
        if match_count > 5000:
            self.label_MatchCount.setText(tr.MATCH_COUNT_LIMITED.format(match_count, 5000))
        else:
            self.label_MatchCount.setText(tr.MATCH_COUNT.format(match_count))

    def tableWidget_valuesearchtable_cell_double_clicked(self, row: int, col: int) -> None:
        current_item = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL)
        vt = copy.copy(current_item.data(Qt.ItemDataRole.UserRole))
        self.add_entry_to_addresstable(tr.NO_DESCRIPTION, current_item.text(), vt)
        self.update_address_table()

    def tableWidget_valuesearchtable_key_press_event(self, event: QKeyEvent) -> None:
        current_item = self.tableWidget_valuesearchtable.currentItem()
        if debugcore.currentpid == -1 or not current_item:
            return
        current_address = self.tableWidget_valuesearchtable.item(current_item.row(), SEARCH_TABLE_ADDRESS_COL).text()
        actions = {
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C): self.copy_valuesearchtable_selection,
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B): lambda: self.browse_region_for_address(current_address),
            QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D): lambda: self.disassemble_for_address(current_address),
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete): self.delete_valuesearchtable_selection,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return): self.copy_to_address_table,
            QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Enter): self.copy_to_address_table,
        }
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.tableWidget_valuesearchtable_keyPressEvent_original(event)

    def tableWidget_valuesearchtable_context_menu_event(self, event: QContextMenuEvent) -> None:
        selected_indexes = self.tableWidget_valuesearchtable.selectionModel().selectedRows()
        if debugcore.currentpid == -1 or not selected_indexes:
            return
        current_item = self.tableWidget_valuesearchtable.currentItem()
        if current_item is None:
            return
        current_row = current_item.row()
        address = self.tableWidget_valuesearchtable.item(current_row, SEARCH_TABLE_ADDRESS_COL).text()
        menu = QMenu()
        if len(selected_indexes) > 1:
            copy_selection = menu.addAction(f"{tr.COPY_ADDRESSES}[Ctrl+C]")
        else:
            copy_selection = menu.addAction(f"{tr.COPY_ADDRESS}[Ctrl+C]")
        menu.addSeparator()
        browse_region = menu.addAction(f"{tr.BROWSE_MEMORY_REGION}[Ctrl+B]")
        disassemble = menu.addAction(f"{tr.DISASSEMBLE_ADDRESS}[Ctrl+D]")
        menu.addSeparator()
        delete_selection = menu.addAction(f"{tr.DELETE_SELECTION}[Del]")
        font_size = self.tableWidget_valuesearchtable.font().pointSize()
        menu.setStyleSheet(f"font-size: {font_size}pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_selection: self.copy_valuesearchtable_selection,
            browse_region: lambda: self.browse_region_for_address(address),
            disassemble: lambda: self.disassemble_for_address(address),
            delete_selection: self.delete_valuesearchtable_selection,
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def copy_valuesearchtable_selection(self) -> None:
        selected_indexes = self.tableWidget_valuesearchtable.selectionModel().selectedRows()
        address_list = []
        for index in selected_indexes:
            row = index.row()
            address = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL).text()
            address_list.append(address)
        QApplication.clipboard().setText(" ".join(address_list))

    def delete_valuesearchtable_selection(self) -> None:
        selected_rows = self.tableWidget_valuesearchtable.selectedItems()
        if not selected_rows:
            return

        # get the row indexes
        rows = set()
        for item in selected_rows:
            rows.add(item.row())

        # remove the rows from the table - removing in reverse sorted order to avoid index issues
        for row in sorted(rows, reverse=True):
            address = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL).text()
            memscan.remove_match_by_address(utils.safe_str_to_int(address, 16))
            self.tableWidget_valuesearchtable.removeRow(row)
        self.update_match_count()

    def comboBox_ValueType_current_index_changed(self) -> None:
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        memscan_type = scancore.scan_index_to_memscan_dict[current_type]
        match memscan_type:
            case DataType.ANYINTEGER | DataType.INTEGER8 | DataType.INTEGER16 | DataType.INTEGER32 | DataType.INTEGER64:
                validator_str = "int"
            case DataType.ANYNUMBER | DataType.ANYFLOAT | DataType.FLOAT32 | DataType.FLOAT64:
                validator_str = "float"
            case DataType.STRING:
                validator_str = "string"
            case DataType.BYTEARRAY:
                validator_str = "bytearray"

        # TODO this can probably be made to look nicer, though it doesn't really matter
        if "int" in validator_str:
            validator_str = "int"
            self.checkBox_Hex.setEnabled(True)
            # keep hex validator if hex is checked
            if self.checkBox_Hex.isChecked():
                validator_str = "int_hex"
        else:
            self.checkBox_Hex.setChecked(False)
            self.checkBox_Hex.setEnabled(False)

        self.comboBox_ScanType_init()
        self.lineEdit_Scan.setValidator(guiutils.validator_map[validator_str])
        self.lineEdit_Scan2.setValidator(guiutils.validator_map[validator_str])
        memscan.set_data_type(memscan_type)
        # according to memscan instructions you should always do `reset` after changing type
        memscan.reset()

    def pushButton_AttachProcess_clicked(self) -> None:
        self.processwindow = SelectProcessWindow(self)
        self.processwindow.show()

    def on_session_save(self) -> None:
        content = [
            self.read_address_table_recursively(self.treeWidget_AddressTable.topLevelItem(i))
            for i in range(self.treeWidget_AddressTable.topLevelItemCount())
        ]
        SessionManager.get_session().pct_address_tree = content

    def on_session_loaded(self) -> None:
        self.clear_address_table()
        self.insert_records(
            SessionManager.get_session().pct_address_tree,
            self.treeWidget_AddressTable.invisibleRootItem(),
            self.treeWidget_AddressTable.topLevelItemCount(),
        )

    def on_new_session(self) -> None:
        self.session = SessionManager.get_session()
        self.clear_address_table()

    # Returns: a bool value indicates whether the operation succeeded.
    def attach_to_pid(self, pid: int) -> bool:
        self.cleanup_speedhack()
        if os.environ.get("APPDIR"):
            gdb_path = utils.get_default_gdb_path()
        else:
            gdb_path = states.gdb_path
        attach_result = debugcore.attach(pid, gdb_path)
        if attach_result == typedefs.ATTACH_RESULT.SUCCESSFUL:
            settings.apply_after_init()
            memscan.detach()
            memscan.attach(pid)
            self.on_new_process()
            SessionManager.on_process_changed()
            states.process_signals.attach.emit()

            # TODO: This makes PINCE call on_process_stop twice when attaching
            # TODO: Signal design might have to change to something like mutexes eventually
            self.memory_view_window.on_process_stop()
            debugcore.continue_inferior()
            return True
        else:
            if attach_result == typedefs.ATTACH_RESULT.ALREADY_TRACED:
                message = tr.ALREADY_TRACED.format(utils.is_traced(pid))
            else:
                messages = {
                    typedefs.ATTACH_RESULT.ATTACH_SELF: tr.SMARTASS,  # easter egg
                    typedefs.ATTACH_RESULT.PROCESS_NOT_VALID: tr.PROCESS_NOT_VALID,
                    typedefs.ATTACH_RESULT.ALREADY_DEBUGGING: tr.ALREADY_DEBUGGING,
                    typedefs.ATTACH_RESULT.PERM_DENIED: tr.PERM_DENIED,
                }
                message = messages.get(attach_result, tr.GDB_INIT_ERROR)
            QMessageBox.information(QApplication.focusWidget(), tr.ERROR, message)
            return False

    # Returns: a bool value indicates whether the operation succeeded.
    def create_new_process(self, file_path: str, args: str, ld_preload_path: str) -> bool:
        self.cleanup_speedhack()
        if debugcore.create_process(file_path, args, ld_preload_path):
            settings.apply_after_init()
            memscan.detach()
            memscan.attach(debugcore.currentpid)
            self.on_new_process()
            SessionManager.on_process_changed()
            states.process_signals.attach.emit()
            return True
        else:
            QMessageBox.information(QApplication.focusWidget(), tr.ERROR, tr.CREATE_PROCESS_ERROR)
            self.on_inferior_exit()
            return False

    # Changes appearance whenever a new process is created or attached
    def on_new_process(self) -> None:
        monocore.reset()
        name = utils.get_process_name(debugcore.currentpid)
        self.label_SelectedProcess.setText(str(debugcore.currentpid) + " - " + name)
        self.is_wine_process = utils.is_wine_process(debugcore.currentpid)
        self.speedhack = speedhack.WineSpeedhack() if self.is_wine_process else speedhack.LinuxSpeedhack()

        # enable scan GUI
        self.lineEdit_Scan.setPlaceholderText(tr.SCAN_FOR)
        self.widget_Scanbox.setEnabled(True)
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.pushButton_CancelScan.setEnabled(False)
        self.pushButton_AddAddressManually.setEnabled(True)
        self.pushButton_MemoryView.setEnabled(True)

        # stop flashing attach button, timer will stop automatically on false value
        self.flashAttachButton = False

    def clear_address_table(self) -> None:
        if self.treeWidget_AddressTable.topLevelItemCount() == 0:
            return
        if self.libpince_engine_window:
            for entry in self.script_entries_in(self.treeWidget_AddressTable.invisibleRootItem()):
                self.libpince_engine_window.close_script_entry(entry)
        self.treeWidget_AddressTable.clear()
        self.mark_address_tree_changed()

    def copy_to_address_table(self) -> None:
        selected_indexes = self.tableWidget_valuesearchtable.selectionModel().selectedRows()
        for index in selected_indexes:
            address_item = self.tableWidget_valuesearchtable.item(index.row(), SEARCH_TABLE_ADDRESS_COL)
            vt = copy.copy(address_item.data(Qt.ItemDataRole.UserRole))
            self.add_entry_to_addresstable(tr.NO_DESCRIPTION, address_item.text(), vt)
        self.update_address_table()
        self.mark_address_tree_changed()

    def reset_scan(self, inferior_exit: bool = False) -> None:
        if inferior_exit:
            memscan.detach()
        else:
            memscan.reset()
        self.scan_mode = typedefs.SCAN_MODE.NEW
        self.undo_scan_available = False
        self.pushButton_NewFirstScan.setText(tr.FIRST_SCAN)
        self.tableWidget_valuesearchtable.setRowCount(0)
        self.update_scan_box_state()
        self.progressBar.setValue(0)
        self.label_MatchCount.setText(tr.MATCH_COUNT.format(0))

    def on_inferior_exit(self) -> None:
        monocore.reset()
        if debugcore.currentpid == -1:
            self.memory_view_window.close()
        if self.speedhack is not None:
            self.speedhack.reset()
            self.speedhack = None
        self.reset_speedhack_widgets()
        self.pushButton_MemoryView.setEnabled(False)
        self.pushButton_AddAddressManually.setEnabled(False)
        self.widget_Scanbox.setEnabled(False)
        self.lineEdit_Scan.setText("")
        self.reset_scan(inferior_exit=True)
        self.on_status_running()
        self.flashAttachButton = True
        self.flashAttachButtonTimer.start(100)
        self.label_SelectedProcess.setText(tr.NO_PROCESS_SELECTED)
        self.memory_view_window.setWindowTitle(tr.NO_PROCESS_SELECTED)
        if os.environ.get("APPDIR"):
            gdb_path = utils.get_default_gdb_path()
        else:
            gdb_path = states.gdb_path
        if debugcore.init_gdb(gdb_path):
            settings.apply_after_init()
        SessionManager.on_process_changed()
        states.process_signals.exit.emit()

    def on_status_detached(self) -> None:
        self.label_SelectedProcess.setStyleSheet("color: blue")
        self.label_InferiorStatus.setText(tr.STATUS_DETACHED)
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: blue")

    def on_status_stopped(self) -> None:
        self.invalidate_address_expression_cache()
        self.label_SelectedProcess.setStyleSheet("color: red")
        self.label_InferiorStatus.setText(tr.STATUS_STOPPED)
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: red")

    def on_status_running(self) -> None:
        self.label_SelectedProcess.setStyleSheet("")
        self.label_InferiorStatus.setVisible(False)

    # closes all windows on exit
    def closeEvent(self, event: QCloseEvent) -> None:
        # you can no longer emit events at this point.
        SessionManager.get_session().pre_exit(event)
        if not event.isAccepted():
            # user cancelled the exit
            return

        if hasattr(self, "update_check_timer"):
            self.update_check_timer.stop()
        self.await_exit_thread.request_shutdown()
        self.await_exit_thread.wait(1000)
        self.cleanup_speedhack()
        debugcore.detach()
        memscan.close()
        QApplication.closeAllWindows()
        logger.info("All PINCE windows closed")

    # Call update_address_table manually after this
    def add_entry_to_addresstable(
        self,
        description: str,
        address_expr: str | typedefs.PointerChainRequest,
        value_type: typedefs.ValueType | None = None,
    ) -> QTreeWidgetItem:
        current_row = QTreeWidgetItem()
        current_row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        frozen = typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT)
        current_row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
        value_type = typedefs.IntegerValueType() if not value_type else value_type
        self.treeWidget_AddressTable.addTopLevelItem(current_row)
        self.change_address_table_entries(current_row, description, address_expr, value_type)
        self.show()  # In case of getting called from elsewhere
        self.activateWindow()
        self.mark_address_tree_changed()
        return current_row

    def get_script_entry(self, row: QTreeWidgetItem | None) -> typedefs.ScriptEntry | None:
        # A row is a script entry when its frozen slot holds a ScriptEntry instead of a Frozen.
        if row is None:
            return None
        data = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
        return data if isinstance(data, typedefs.ScriptEntry) else None

    def init_script_row(self, row: QTreeWidgetItem, description: str, entry: typedefs.ScriptEntry) -> None:
        row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, entry)
        row.setText(DESC_COL, description or tr.SCRIPT)
        row.setText(TYPE_COL, tr.SCRIPT)

    def add_script_entry_to_table(self, title: str, entry: typedefs.ScriptEntry) -> None:
        # entry comes from the engine already bound to its tab so the row and tab share one object.
        row = QTreeWidgetItem()
        row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        self.init_script_row(row, title, entry)
        self.treeWidget_AddressTable.addTopLevelItem(row)
        self.mark_address_tree_changed()

    def open_script_entry_in_engine(self, row: QTreeWidgetItem, entry: typedefs.ScriptEntry) -> None:
        self.show_libpince_engine().open_script_entry(entry, row.text(DESC_COL) or tr.SCRIPT)

    def show_libpince_engine(self) -> LibpinceEngineWindow:
        # A single window is reused so table script entries can be reopened in their existing tab.
        if not self.libpince_engine_window:
            self.libpince_engine_window = LibpinceEngineWindow(self)
            self.libpince_engine_window.send_to_table.connect(self.add_script_entry_to_table)
            self.libpince_engine_window.entry_modified.connect(self.mark_address_tree_changed)
            self.libpince_engine_window.script_executed.connect(lambda: self.invalidate_address_expression_cache(refresh=True))
        self.libpince_engine_window.show()
        self.libpince_engine_window.activateWindow()
        return self.libpince_engine_window

    def show_structures_window(self) -> StructuresWindow:
        if not self.structures_window:
            self.structures_window = StructuresWindow(self)
            self.structures_window.add_to_table_requested.connect(self._add_structure_records_to_table)
        self.structures_window.refresh()
        self.structures_window.show()
        self.structures_window.activateWindow()
        return self.structures_window

    def _add_structure_records_to_table(self, records: list) -> None:
        self.insert_records(records, self.treeWidget_AddressTable.invisibleRootItem(), 0)
        self.update_address_table()

    def mark_address_tree_changed(self) -> None:
        self.session.data_changed |= SessionDataChanged.ADDRESS_TREE

    def toggle_script_entry(self, row: QTreeWidgetItem, entry: typedefs.ScriptEntry, check_state: Qt.CheckState) -> None:
        is_enable = check_state == Qt.CheckState.Checked
        row.setCheckState(FROZEN_COL, check_state)
        enable_code, disable_code = parse_script_sections(entry.script)
        code = enable_code if is_enable else disable_code
        if code is None:  # tagless script or no [DISABLE]: nothing to run when toggling off.
            return
        entry.namespace = entry.namespace or create_script_namespace()
        succeeded, output = run_script_code(code, entry.namespace, f"<{row.text(DESC_COL) or tr.SCRIPT}>")
        if not succeeded and is_enable:  # don't leave a failed enable looking active
            row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        self.invalidate_address_expression_cache(refresh=True)
        if succeeded:
            return
        QMessageBox.information(self, tr.ERROR, tr.SCRIPT_RUN_FAILED.format(output))

    def treeWidget_AddressTable_item_double_clicked(self, row: QTreeWidgetItem, column: int) -> None:
        entry = self.get_script_entry(row)
        if entry is not None:
            self.open_script_entry_in_engine(row, entry)
            return
        action_for_column = {
            VALUE_COL: self.treeWidget_AddressTable_edit_value,
            DESC_COL: self.treeWidget_AddressTable_edit_desc,
            ADDR_COL: self.treeWidget_AddressTable_edit_address,
            TYPE_COL: self.treeWidget_AddressTable_edit_type,
        }
        action_for_column = collections.defaultdict(lambda *args: lambda: None, action_for_column)
        action_for_column[column]()

    # ----------------------------------------------------
    # QTimer loops

    def update_progress_bar(self) -> None:
        value = int(round(memscan.get_scan_progress() * 100))
        self.progressBar.setValue(value)

    # Loop restarts itself to wait for function execution, same for the functions below
    def address_table_loop(self) -> None:
        if states.update_table and not states.exiting:
            try:
                self.update_address_table()
            except:
                traceback.print_exc()
        self.address_table_timer.start(states.table_update_interval)

    def search_table_loop(self) -> None:
        if not states.exiting:
            try:
                self.update_search_table()
            except:
                traceback.print_exc()
        self.search_table_timer.start(500)

    def freeze_loop(self) -> None:
        if not states.exiting:
            try:
                self.freeze()
            except:
                traceback.print_exc()
        self.freeze_timer.start(states.freeze_interval)

    # ----------------------------------------------------

    def update_search_table(self) -> None:
        if debugcore.currentpid == -1:
            return
        row_count = self.tableWidget_valuesearchtable.rowCount()
        if row_count > 0:
            self.tableWidget_valuesearchtable.setSortingEnabled(False)
            try:
                with debugcore.memory_handle() as mem_handle:
                    for row_index in range(row_count):
                        address_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_ADDRESS_COL)
                        value_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_VALUE_COL)
                        previous_text = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_PREVIOUS_COL).text()
                        address = address_item.text()
                        value_type = address_item.data(Qt.ItemDataRole.UserRole)
                        new_value = debugcore.read_memory(address, value_type, mem_handle=mem_handle)
                        new_value = "" if new_value is None else str(new_value)
                        if new_value != previous_text:
                            value_item.setForeground(QBrush(QColor(255, 0, 0)))
                        value_item.setText(new_value)
            finally:
                self.tableWidget_valuesearchtable.setSortingEnabled(True)

    def freeze(self) -> None:
        if debugcore.currentpid == -1:
            return
        it = QTreeWidgetItemIterator(self.treeWidget_AddressTable)
        while True:
            row = it.value()
            if not row:
                break
            it += 1
            if self.get_script_entry(row) is not None:  # script entries toggle on the checkbox, nothing to freeze
                continue
            if row.checkState(FROZEN_COL) == Qt.CheckState.Checked:
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                address = self._resolved_address(row)
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                value = frozen.value
                if value is None:  # nothing valid was captured (e.g. frozen while unreadable) so we skip.
                    continue
                freeze_type = frozen.freeze_type
                if isinstance(vt, (typedefs.IntegerValueType, typedefs.FloatValueType, typedefs.BitFieldValueType)):
                    # Freeze comparisons need the stored number, not a signed/hex display value.
                    read_type = copy.copy(vt)
                    if isinstance(vt, typedefs.IntegerValueType) or getattr(vt, "value_repr", None) == typedefs.VALUE_REPR.HEX:
                        read_type.value_repr = typedefs.VALUE_REPR.UNSIGNED
                    new_value = debugcore.read_memory(address, read_type)
                    if new_value is None:
                        continue
                    compare_value, compare_new_value = value, new_value
                    if isinstance(vt, typedefs.IntegerValueType) and vt.value_repr == typedefs.VALUE_REPR.SIGNED:
                        limit = 1 << vt.bits
                        compare_value -= limit if compare_value >= limit // 2 else 0
                        compare_new_value -= limit if compare_new_value >= limit // 2 else 0
                    if (
                        freeze_type == typedefs.FREEZE_TYPE.ALLOW_INCREMENT
                        and compare_new_value > compare_value
                        or freeze_type == typedefs.FREEZE_TYPE.ALLOW_DECREMENT
                        and compare_new_value < compare_value
                    ):
                        frozen.value = new_value
                        debugcore.write_memory(address, vt, new_value)
                        continue
                debugcore.write_memory(address, vt, value)

    def _frozen_value_for_type(self, row: QTreeWidgetItem, frozen: typedefs.Frozen, new_type: typedefs.ValueType) -> Any | None:
        old_type: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        value = frozen.value
        if not frozen.enabled or value is None:
            return value
        if not isinstance(old_type, typedefs.BitFieldValueType) and not isinstance(new_type, typedefs.BitFieldValueType):
            return value
        numeric_types = (typedefs.IntegerValueType, typedefs.FloatValueType, typedefs.BitFieldValueType)
        if not isinstance(old_type, numeric_types) or not isinstance(new_type, numeric_types):
            return
        if (
            isinstance(old_type, typedefs.BitFieldValueType)
            and isinstance(new_type, typedefs.BitFieldValueType)
            and (old_type.bits, old_type.start_bit) == (new_type.bits, new_type.start_bit)
        ):
            limit = 1 << new_type.bits
            value %= limit
            return value - limit if new_type.value_repr == typedefs.VALUE_REPR.SIGNED and value >= limit // 2 else value
        if isinstance(old_type, typedefs.IntegerValueType):
            value = old_type.parse(str(value))
            if value is None:
                return
            if old_type.value_repr == typedefs.VALUE_REPR.SIGNED and value >= 1 << (old_type.bits - 1):
                value -= 1 << old_type.bits
        return new_type.parse(str(value))

    def handle_freeze_change(self, row: QTreeWidgetItem, check_state: Qt.CheckState) -> None:
        entry = self.get_script_entry(row)
        if entry is not None:
            self.toggle_script_entry(row, entry, check_state)
            return
        if self._is_struct_row(row):
            row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
            return
        frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
        is_checked = check_state == Qt.CheckState.Checked
        frozen_state_toggled = (is_checked and not frozen.enabled) or (not is_checked and frozen.enabled)
        row.setCheckState(FROZEN_COL, check_state)
        # this helps determine whether the user clicked checkbox or the text
        # if the user clicked the text, change the freeze type

        if frozen_state_toggled:
            if is_checked:
                frozen.enabled = True
                # reapply the freeze type, to reflect the current freeze type in the UI
                # otherwise the UI will show DEFAULT freeze type after enabling instead of the actual type
                self.change_freeze_type(frozen.freeze_type, row)
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                frozen.value = vt.parse(row.text(VALUE_COL))
            else:
                frozen.enabled = False  # it has just been toggled off
                self.change_freeze_type(typedefs.FREEZE_TYPE.DEFAULT, row)

    def treeWidget_AddressTable_change_repr(self, new_repr: int) -> None:
        for row in self.treeWidget_AddressTable.selectedItems():
            if self.get_script_entry(row) is not None:
                continue
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            if isinstance(value_type, (typedefs.IntegerValueType, typedefs.BitFieldValueType)):
                value_type.value_repr = new_repr
                if isinstance(value_type, typedefs.BitFieldValueType):
                    frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                    frozen.value = self._frozen_value_for_type(row, frozen, value_type)
                row.setText(TYPE_COL, value_type.text())
        self.update_address_table()
        self.mark_address_tree_changed()

    def _is_struct_row(self, row: QTreeWidgetItem) -> bool:
        # Only carries an address, has no readable value or editable type.
        vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        return isinstance(vt, typedefs.StructValueType)

    def _resolved_address(self, row: QTreeWidgetItem) -> str:
        # The displayed address can be relative (struct children show "+0x4") or "P->…" for pointers,
        # so the resolved absolute kept in UserRole+1 is the source of truth for reads/writes.
        # If nothing useful is in UserRole+1, fall back to text.
        return row.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1) or row.text(ADDR_COL).removeprefix("P->")

    def treeWidget_AddressTable_edit_value(self) -> None:
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row or self.get_script_entry(row) is not None or self._is_struct_row(row):
            return
        value = row.text(VALUE_COL)
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_VALUE, value)])
        if dialog.exec():
            new_value = dialog.get_values()[0]
            parsed_rows = [
                (row, row.data(TYPE_COL, Qt.ItemDataRole.UserRole).parse(new_value))
                for row in self.treeWidget_AddressTable.selectedItems()
                if self.get_script_entry(row) is None and not self._is_struct_row(row)
            ]
            if any(parsed_value is None for _, parsed_value in parsed_rows):
                QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                return
            length_changed = False
            for row, parsed_value in parsed_rows:
                address = self._resolved_address(row)
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                if isinstance(vt, (typedefs.StringValueType, typedefs.ByteArrayValueType)):
                    if vt.length != len(parsed_value):
                        length_changed = True
                    vt.length = len(parsed_value)
                    row.setText(TYPE_COL, vt.text())
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen.value = parsed_value
                debugcore.write_memory(address, vt, parsed_value)
            self.update_address_table()
            if length_changed:
                self.mark_address_tree_changed()

    def treeWidget_AddressTable_edit_desc(self) -> None:
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row:
            return
        description = row.text(DESC_COL)
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_DESCRIPTION, description)])
        if dialog.exec():
            description_text = dialog.get_values()[0]
            for row in self.treeWidget_AddressTable.selectedItems():
                row.setText(DESC_COL, description_text)
                entry = self.get_script_entry(row)
                if entry is not None and self.libpince_engine_window:
                    self.libpince_engine_window.rename_script_entry(entry, description_text)
            self.mark_address_tree_changed()

    def treeWidget_AddressTable_edit_address(self) -> None:
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row or self.get_script_entry(row) is not None:
            return
        if self._is_struct_row(row):
            self._edit_struct_address(row)
            return
        desc, address_expr, vt = self.read_address_table_entries(row)
        parent = row.parent()
        # Pass the parent's resolved base so the dialog can preview relative ("+0x4") children
        relative_base = parent.data(ADDR_COL, Qt.ItemDataRole.UserRole + 1) if parent else ""
        manual_address_dialog = ManualAddressDialog(self, desc, address_expr, vt, relative_base)
        manual_address_dialog.setWindowTitle(tr.EDIT_ADDRESS)
        if manual_address_dialog.exec():
            desc, address_expr, new_type = manual_address_dialog.get_values()
            frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
            frozen_value = self._frozen_value_for_type(row, frozen, new_type)
            if frozen_value is None and frozen.value is not None:
                QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                return
            self.change_address_table_entries(row, desc, address_expr, new_type)
            frozen.value = frozen_value
            self.update_address_table()
            self.mark_address_tree_changed()

    def _edit_struct_address(self, row: QTreeWidgetItem) -> None:
        # Struct rows only carry an address so skip the full manual add dialog and just ask for a new address.
        desc, address_expr, vt = self.read_address_table_entries(row)
        if isinstance(address_expr, typedefs.PointerChainRequest):
            current = address_expr.get_base_address_as_str()
        else:
            current = address_expr or ""
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_ADDRESS, current)])
        if dialog.exec():
            new_address = dialog.get_values()[0].strip()
            if not new_address:
                return
            if isinstance(address_expr, typedefs.PointerChainRequest):  # keep the deref, only the base changed
                new_address = typedefs.PointerChainRequest(new_address, address_expr.offsets_list)
            self.change_address_table_entries(row, desc, new_address, vt)
            self.update_address_table()
            self.mark_address_tree_changed()

    def treeWidget_AddressTable_edit_type(self) -> None:
        row = guiutils.get_current_item(self.treeWidget_AddressTable)
        if not row or self.get_script_entry(row) is not None or self._is_struct_row(row):
            return
        vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        dialog = EditTypeDialog(self, vt)
        if dialog.exec():
            vt = dialog.get_values()
            type_text = vt.text()
            changes = []
            for row in self.treeWidget_AddressTable.selectedItems():
                if self.get_script_entry(row) is not None or self._is_struct_row(row):
                    continue
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen_value = self._frozen_value_for_type(row, frozen, vt)
                if frozen_value is None and frozen.value is not None:
                    QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                    return
                changes.append((row, frozen, frozen_value))
            for row, frozen, frozen_value in changes:
                row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, copy.copy(vt))
                row.setText(TYPE_COL, type_text)
                frozen.value = frozen_value
            self.update_address_table()
            self.mark_address_tree_changed()

    # Changes the column values of the given row
    def change_address_table_entries(
        self,
        row: QTreeWidgetItem,
        description: str,
        address_expr: str | typedefs.PointerChainRequest = "",
        vt: typedefs.ValueType | None = None,
    ) -> None:
        assert isinstance(row, QTreeWidgetItem)
        address_expr = "" if address_expr is None else address_expr
        row.setText(DESC_COL, description)
        row.setData(ADDR_COL, Qt.ItemDataRole.UserRole, address_expr)
        if utils.extract_hex_address(address_expr) and debugcore.is_address_static(address_expr):
            row.setForeground(ADDR_COL, QColor(0, 136, 85))
        else:
            row.setForeground(ADDR_COL, self.palette().text().color())
        row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, vt)
        row.setText(TYPE_COL, vt.text())

    # Returns the column values of the given row
    def read_address_table_entries(self, row: QTreeWidgetItem, serialize: bool = False) -> tuple[str, Any, Any]:
        description = row.text(DESC_COL)
        if serialize:
            address_data = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            if isinstance(address_data, typedefs.PointerChainRequest):
                address_expr = address_data.serialize()
            else:
                address_expr = address_data
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).serialize()
        else:
            address_expr = row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        return description, address_expr, value_type

    # Returns the values inside the given row and all of its descendants.
    # A script entry adds an extra dict before them so it stays backward compatible with plain rows,
    # which insert_records tells apart by length.
    def read_address_table_recursively(self, row: QTreeWidgetItem) -> tuple:
        children = [self.read_address_table_recursively(row.child(i)) for i in range(row.childCount())]
        entry = self.get_script_entry(row)
        if entry is not None:
            return row.text(DESC_COL), "", typedefs.IntegerValueType().serialize(), {"script": entry.script}, children
        return self.read_address_table_entries(row, True) + (children,)

    # Flashing Attach Button when the process is not attached
    def flash_attach_button(self) -> None:
        if not self.flashAttachButton:
            self.flashAttachButtonTimer.stop()
            self.pushButton_AttachProcess.setStyleSheet("")
            return

        case = self.flashAttachButton_gradientState % 32

        if case < 16:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str(case / 16) + ");}"
        else:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str((32 - case) / 16) + ");}"

        self.pushButton_AttachProcess.setStyleSheet(borderstring)
        self.flashAttachButton_gradientState += 1
        if self.flashAttachButton_gradientState > 768:  # 32*24
            self.flashAttachButton_gradientState = 0
