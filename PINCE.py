#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2016-2017 Korcan Karaokçu <korcankaraokcu@gmail.com>
Copyright (C) 2016-2017 Çağrı Ulaş <cagriulas@gmail.com>
Copyright (C) 2016-2017 Jakob Kreuze <jakob@memeware.net>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import ast
import collections
import copy
import importlib
import io
import os
import re
import signal
import sys
import traceback
from time import sleep, time
from types import FrameType, ModuleType, TracebackType
from typing import Any

# Must precede the imports below in case any of the PyQt and other imports want to create bytecodes.
if os.geteuid() == 0:
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # For GDB and other processes that will inherit environ.

from PyQt6.QtCore import (
    QByteArray,
    QEvent,
    QItemSelection,
    QItemSelectionModel,
    QKeyCombination,
    QLibraryInfo,
    QLocale,
    QModelIndex,
    QObject,
    QSettings,
    QSignalBlocker,
    QSize,
    QStringListModel,
    Qt,
    QThread,
    QTimer,
    QTranslator,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QColorConstants,
    QContextMenuEvent,
    QCursor,
    QIcon,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QMovie,
    QPixmap,
    QShortcut,
    QTextCursor,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractSlider,
    QApplication,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QWidget,
)

from GUI.AboutWidget import Ui_TabWidget as AboutWidget
from GUI.AbstractTableModels.AsciiModel import QAsciiModel
from GUI.AbstractTableModels.HexModel import QHexModel
from GUI.AddAddressManuallyDialog import Ui_Dialog as ManualAddressDialog
from GUI.BreakpointInfoWidget import Ui_TabWidget as BreakpointInfoWidget
from GUI.ConsoleWidget import Ui_Form as ConsoleWidget
from GUI.DissectCodeDialog import Ui_Dialog as DissectCodeDialog
from GUI.EditInstructionDialog import Ui_Dialog as EditInstructionDialog
from GUI.EditTypeDialog import Ui_Dialog as EditTypeDialog
from GUI.ExamineReferrersWidget import Ui_Form as ExamineReferrersWidget
from GUI.FloatRegisterWidget import Ui_TabWidget as FloatRegisterWidget
from GUI.FunctionsInfoWidget import Ui_Form as FunctionsInfoWidget
from GUI.HexEditDialog import Ui_Dialog as HexEditDialog
from GUI.LoadingDialog import Ui_Dialog as LoadingDialog
from GUI.LogFileWidget import Ui_Form as LogFileWidget
from GUI.MainWindow import Ui_MainWindow as MainWindow
from GUI.ManualAddressDialogUtils.PointerChainOffset import PointerChainOffset
from GUI.MemoryRegionsWidget import Ui_Form as MemoryRegionsWidget

# If you are going to change the name "Ui_MainWindow_MemoryView", review GUI/Labels/RegisterLabel.py as well
from GUI.MemoryViewerWindow import Ui_MainWindow_MemoryView as MemoryViewWindow
from GUI.ReferencedCallsWidget import Ui_Form as ReferencedCallsWidget
from GUI.ReferencedStringsWidget import Ui_Form as ReferencedStringsWidget
from GUI.SearchInstructionsWidget import Ui_Form as SearchInstructionsWidget
from GUI.SelectProcess import Ui_MainWindow as ProcessWindow
from GUI.Session.session import SessionDataChanged, SessionManager, StructureManager
from GUI.Settings import settings, themes
from GUI.StackTraceInfoWidget import Ui_Form as StackTraceInfoWidget
from GUI.States import states
from GUI.TraceInstructionsPromptDialog import Ui_Dialog as TraceInstructionsPromptDialog
from GUI.TraceInstructionsWaitWidget import Ui_Form as TraceInstructionsWaitWidget
from GUI.TraceInstructionsWindow import Ui_MainWindow as TraceInstructionsWindow
from GUI.TrackBreakpointWidget import Ui_Form as TrackBreakpointWidget
from GUI.TrackSelectorDialog import Ui_Dialog as TrackSelectorDialog
from GUI.TrackWatchpointWidget import Ui_Form as TrackWatchpointWidget
from GUI.Utils import guitypedefs, guiutils, utilwidgets
from GUI.Validators.HexValidator import QHexValidator
from GUI.Widgets.Bookmark.Bookmark import BookmarkWidget
from GUI.Widgets.LibpinceEngine.LibpinceEngine import (
    LibpinceEngineWindow,
    create_script_namespace,
    parse_script_sections,
    run_script_code,
)
from GUI.Widgets.ManageScanRegions.ManageScanRegions import ManageScanRegionsDialog
from GUI.Widgets.PointerScan.PointerScan import PointerScanWindow
from GUI.Widgets.PointerScanSearch.PointerScanSearch import PointerScanSearchDialog
from GUI.Widgets.RestoreInstructions.RestoreInstructions import RestoreInstructionsWidget
from GUI.Widgets.SessionNotes.SessionNotes import SessionNotesWidget
from GUI.Widgets.Settings.Settings import SettingsDialog
from GUI.Widgets.MonoDissect.MonoDissect import MonoDissectDialog
from GUI.Widgets.Structures.StructuresWindow import StructuresWindow
from GUI.Widgets.Structures.StructureViewDialog import StructureViewDialog
from GUI.Widgets.Structures.StructureEditorDialog import StructureEditorDialog
from GUI.Widgets.Structures import mono_export
from GUI.Widgets.TextEdit.TextEdit import TextEditDialog
from libpince import debugcore, linux_speedhack, monocore, scancore, typedefs, utils, wine_speedhack
from libpince.libmemscan.memscan import ScanLevel, DataType, MatchView, BytePattern
from libpince.scancore import memscan
from libpince.utils import logger, safe_str_to_int, safe_int_cast
from tr.tr import TranslationConstants as tr
from tr.tr import get_locale

if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("PINCE")
    app.setOrganizationName("PINCE")
    app.setOrganizationDomain("github.io")
    app.setDesktopFileName("io.github.korcankaraokcu.PINCE")
    QSettings.setPath(
        QSettings.Format.NativeFormat, QSettings.Scope.UserScope, utils.get_user_path(typedefs.USER_PATHS.CONFIG)
    )
    settings_instance = QSettings()
    translator = QTranslator()
    qt_translator = QTranslator()
    try:
        locale = settings_instance.value("General/locale", type=str)
    except SystemError:
        # We're reading the settings for the first time here
        # If there's an error due to python objects, clear settings
        settings_instance.clear()
        locale = None
    if not locale:
        locale = get_locale()
    # Load Qt's own translations for standard widget strings (file dialog buttons, message box buttons etc...).
    # Installed before PINCE's catalog so PINCE's strings take precedence on any overlap.
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(QLocale(locale), "qtbase", "_", translations_path):
        app.installTranslator(qt_translator)
    locale_file = utils.get_script_directory() + f"/i18n/qm/{locale}.qm"
    translator.load(locale_file)
    app.installTranslator(translator)
    tr.translate()
    # Reload states after QApplication instance to ensure that variables are correctly initiated
    # Reloading states after translations also ensures that hotkeys are correctly translated
    importlib.reload(states)
    importlib.reload(themes)  # Needed for correct translations, might not be needed after refactorization

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

# row colors for disassemble qtablewidget
PC_COLOR = QColorConstants.Blue
BOOKMARK_COLOR = QColorConstants.Cyan
BREAKPOINT_COLOR = QColorConstants.Red
REF_COLOR = QColorConstants.LightGray

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

# represents the index of columns in disassemble table
DISAS_ADDR_COL = 0
DISAS_OPCODES_COL = 1
DISAS_INSTR_COL = 2
DISAS_COMMENT_COL = 3

# represents the index of columns in floating point table
FLOAT_REGISTERS_NAME_COL = 0
FLOAT_REGISTERS_VALUE_COL = 1

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

# represents the index of columns in track watchpoint table(what accesses this address thingy)
TRACK_WATCHPOINT_COUNT_COL = 0
TRACK_WATCHPOINT_ADDR_COL = 1

# represents the index of columns in track breakpoint table(which addresses this instruction accesses thingy)
TRACK_BREAKPOINT_COUNT_COL = 0
TRACK_BREAKPOINT_ADDR_COL = 1
TRACK_BREAKPOINT_VALUE_COL = 2
TRACK_BREAKPOINT_SOURCE_COL = 3

# represents the index of columns in function info table
FUNCTIONS_INFO_ADDR_COL = 0
FUNCTIONS_INFO_SYMBOL_COL = 1

# represents the index of columns in libpince reference resources table
LIBPINCE_REFERENCE_ITEM_COL = 0
LIBPINCE_REFERENCE_VALUE_COL = 1

# represents the index of columns in search instructions table
SEARCH_INSTR_ADDR_COL = 0
SEARCH_INSTR_INSTR_COL = 1

# represents the index of columns in memory regions table
MEMORY_REGIONS_ADDR_COL = 0
MEMORY_REGIONS_PERM_COL = 1
MEMORY_REGIONS_OFFSET_COL = 2
MEMORY_REGIONS_PATH_COL = 3

# represents the index of columns in dissect code table
DISSECT_CODE_ADDR_COL = 0
DISSECT_CODE_PATH_COL = 1

# represents the index of columns in referenced strings table
REF_STR_ADDR_COL = 0
REF_STR_COUNT_COL = 1
REF_STR_VAL_COL = 2

# represents the index of columns in referenced calls table
REF_CALL_ADDR_COL = 0
REF_CALL_COUNT_COL = 1


def except_hook(exception_type: type[BaseException], value: BaseException, tb: TracebackType | None) -> None:
    focused_widget = app.focusWidget()
    if focused_widget and exception_type == typedefs.GDBInitializeException:
        QMessageBox.information(focused_widget, tr.ERROR, tr.GDB_INIT)
    traceback.print_exception(exception_type, value, tb)


# From version 5.5 and onwards, PyQT calls qFatal() when an exception has been encountered
# So, we must override sys.excepthook to avoid calling of qFatal()
sys.excepthook = except_hook


def signal_handler(signal: int, frame: FrameType | None) -> None:
    with QSignalBlocker(app):
        debugcore.detach()
        memscan.close()
        quit()


signal.signal(signal.SIGINT, signal_handler)


class MainForm(QMainWindow, MainWindow):
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
        self.deleted_regions: list[int] = []
        self.is_wine_process = False
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
            states.hotkeys.increased_by_scan_hotkey: lambda: self.nextscan_hotkey_pressed(
                typedefs.SCAN_TYPE.INCREASED_BY
            ),
            states.hotkeys.decreased_scan_hotkey: lambda: self.nextscan_hotkey_pressed(typedefs.SCAN_TYPE.DECREASED),
            states.hotkeys.decreased_by_scan_hotkey: lambda: self.nextscan_hotkey_pressed(
                typedefs.SCAN_TYPE.DECREASED_BY
            ),
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
        self.memory_view_window = MemoryViewWindowForm(self)
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
        self.treeWidget_AddressTable.mouseReleaseEvent_original = self.treeWidget_AddressTable.mouseReleaseEvent
        self.treeWidget_AddressTable.mouseReleaseEvent = self.treeWidget_AddressTable_mouse_release_event
        self.treeWidget_AddressTable.keyPressEvent_original = self.treeWidget_AddressTable.keyPressEvent
        self.treeWidget_AddressTable.keyPressEvent = self.treeWidget_AddressTable_key_press_event
        self.treeWidget_AddressTable.contextMenuEvent = self.treeWidget_AddressTable_context_menu_event
        self.pushButton_AttachProcess.clicked.connect(self.pushButton_AttachProcess_clicked)
        self.pushButton_Open.clicked.connect(SessionManager.load_session)
        self.pushButton_Save.clicked.connect(SessionManager.save_session)
        states.session_signals.on_save.connect(self.on_session_save)
        states.session_signals.on_load.connect(self.on_session_loaded)
        states.session_signals.new_session.connect(self.on_new_session)
        self.session = SessionManager.get_session()
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
        self.lineEdit_Scan.keyPressEvent_original = self.lineEdit_Scan.keyPressEvent
        self.lineEdit_Scan2.keyPressEvent_original = self.lineEdit_Scan2.keyPressEvent
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
        self.pushButton_RefreshAdressTable.clicked.connect(self.pushButton_RefreshAdressTable_clicked)
        self.pushButton_CopyToAddressTable.clicked.connect(self.copy_to_address_table)
        self.pushButton_CleanAddressTable.clicked.connect(self.clear_address_table)
        self.tableWidget_valuesearchtable.cellDoubleClicked.connect(
            self.tableWidget_valuesearchtable_cell_double_clicked
        )
        self.tableWidget_valuesearchtable.keyPressEvent_original = self.tableWidget_valuesearchtable.keyPressEvent
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
        self.pushButton_Settings.setIcon(QIcon(QPixmap(icons_directory + "/wrench.png")))
        self.pushButton_CopyToAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/arrow_down.png")))
        self.pushButton_CleanAddressTable.setIcon(QIcon(QPixmap(icons_directory + "/bin_closed.png")))
        self.pushButton_RefreshAdressTable.setIcon(QIcon(QPixmap(icons_directory + "/table_refresh.png")))
        self.pushButton_Console.setIcon(QIcon(QPixmap(icons_directory + "/application_xp_terminal.png")))
        self.pushButton_Wiki.setIcon(QIcon(QPixmap(icons_directory + "/book_open.png")))
        self.pushButton_About.setIcon(QIcon(QPixmap(icons_directory + "/information.png")))
        self.pushButton_NextScan.setEnabled(False)
        self.pushButton_UndoScan.setEnabled(False)
        self.pushButton_CancelScan.setEnabled(False)
        self.flashAttachButton = True
        self.flashAttachButtonTimer = QTimer(self)
        self.flashAttachButtonTimer.timeout.connect(self.flash_attach_button)
        self.flashAttachButton_gradiantState = 0
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
            for target in states.auto_attach.split(";"):
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
        if not (
            debugcore.currentpid == -1
            or debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING
            or debugcore.driving_inferior
        ):
            debugcore.continue_inferior()

    @utils.ignore_exceptions
    def cancel_hotkey_pressed(self) -> None:
        if debugcore.cancel_ongoing_command():
            logger.info("Cancelled the ongoing GDB command")

    @utils.ignore_exceptions
    def toggle_attach_hotkey_pressed(self) -> None:
        self.attach_toggled.emit(debugcore.toggle_attach())

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
        # Called when the inferior is being replaced or torn down.
        # uninstall() is best-effort, it restores patched bytes and frees the cave if it can.
        self.speedhack.uninstall()
        self.reset_speedhack_widgets()

    @property
    def speedhack(self) -> ModuleType:
        # WINE/Proton games are scaled at the Wine ntdll layer, native linux ones at the glibc layer.
        return wine_speedhack if self.is_wine_process else linux_speedhack

    def on_speedhack_hotkey_action(self, delta: int) -> None:
        # We drive the widgets and let their signals run apply_speedhack, so hotkeys and clicks share the same code path.
        if debugcore.currentpid == -1:
            return
        if delta == 0:
            self.checkBox_Speedhack.toggle()
        else:
            # Up/Down also turns the hack on with the spinbox value becoming the live speed.
            if not self.checkBox_Speedhack.isChecked():
                self.checkBox_Speedhack.setChecked(True)
            self.doubleSpinBox_Speedhack.setValue(self.doubleSpinBox_Speedhack.value() + delta * self.speedhack.STEP)

    def apply_speedhack(self, *_: Any) -> None:
        # Both widget signals and the hotkeys (via on_speedhack_hotkey_action) funnel through here.
        if debugcore.currentpid == -1:
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
            self.speedhack.set_speed(self.speedhack.DEFAULT_SPEED)

    def reset_speedhack_widgets(self) -> None:
        self.checkBox_Speedhack.blockSignals(True)
        self.doubleSpinBox_Speedhack.blockSignals(True)
        self.checkBox_Speedhack.setChecked(False)
        self.doubleSpinBox_Speedhack.setValue(self.speedhack.DEFAULT_SPEED)
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
            if typedefs.VALUE_INDEX.is_integer(value_type.value_index):
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
        address_data = selected_row.data(ADDR_COL, Qt.ItemDataRole.UserRole)
        if isinstance(address_data, typedefs.PointerChainRequest):
            selection_dialog = TrackSelectorDialogForm(self)
            selection_dialog.exec()
            if not selection_dialog.selection:
                return
            if selection_dialog.selection == "pointer":
                address = address_data.get_base_address_as_str()
        value_type = selected_row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        if typedefs.VALUE_INDEX.is_string(value_type.value_index):
            value_text = selected_row.text(VALUE_COL)
            encoding, option = typedefs.string_index_to_encoding_dict[value_type.value_index]
            byte_len = len(value_text.encode(encoding, option))
        elif value_type.value_index == typedefs.VALUE_INDEX.AOB:
            byte_len = value_type.length
        else:
            byte_len = typedefs.index_to_valuetype_dict[value_type.value_index][0]
        TrackWatchpointWidgetForm(self, address, byte_len, watchpoint_type)

    def browse_region_for_address(self, address: str) -> None:
        if address:
            self.memory_view_window.hex_dump_address(int(address.removeprefix("P->"), 16))
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

        app.clipboard().setText(repr([self._read_for_copy(item) for item in items]))

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
                value_type = typedefs.ValueType(*rec[2])
                self.change_address_table_entries(row, rec[0], address_expr, value_type)

            # Insert the row at the current insert_index
            parent_row.insertChild(insert_index, row)
            insert_index += 1

            # Recursively insert children of this row
            self.insert_records(rec[-1], row, 0)
        self.mark_address_tree_changed()

    def paste_records(self, insert_inside: bool = False) -> None:
        try:
            records = ast.literal_eval(app.clipboard().text())
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
        except (TypeError, IndexError, KeyError, AttributeError):
            QMessageBox.information(self, tr.ERROR, tr.INVALID_CLIPBOARD)
            return
        self.update_address_table()

    def group_records(self) -> None:
        selected_items = self.treeWidget_AddressTable.selectedItems()
        if self.create_group():
            item_count = self.treeWidget_AddressTable.topLevelItemCount()
            last_item = self.treeWidget_AddressTable.topLevelItem(item_count - 1)
            for item in selected_items:
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.treeWidget_AddressTable.indexOfTopLevelItem(item)
                    self.treeWidget_AddressTable.takeTopLevelItem(index)
                last_item.addChild(item)
            self.treeWidget_AddressTable.setCurrentItem(last_item)
            last_item.setExpanded(True)

    def create_group(self) -> bool:
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_DESCRIPTION, tr.GROUP)])
        if dialog.exec():
            desc = dialog.get_values()[0]
            self.add_entry_to_addresstable(desc, "0x0")
            return True
        return False

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
            self.treeWidget_AddressTable.mouseReleaseEvent_original(event)
            new_state = item.checkState(FROZEN_COL)
            if old_state != new_state:
                self.handle_freeze_change(item, new_state)
            elif new_state == Qt.CheckState.Checked:
                self.change_freeze_type(row=item)
                frozen = item.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                if isinstance(frozen, typedefs.Frozen):
                    self.change_freeze_type(frozen.freeze_type, item)
        else:
            self.treeWidget_AddressTable.mouseReleaseEvent_original(event)

    def treeWidget_AddressTable_key_press_event(self, event: QKeyEvent) -> None:
        current_row = guiutils.get_current_item(self.treeWidget_AddressTable)
        current_address = self._resolved_address(current_row) if current_row else None
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete), self.delete_records),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
                    lambda: self.browse_region_for_address(current_address),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                    lambda: self.disassemble_for_address(current_address),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R),
                    self.pushButton_RefreshAdressTable_clicked,
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space), self.toggle_records),
                (QKeyCombination(Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Space), self.toggle_records),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Space),
                    lambda: self.toggle_records(True),
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_X), self.cut_records),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C), self.copy_records),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_V), self.paste_records),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_V), lambda: self.paste_records(True)),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_value,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.KeypadModifier, Qt.Key.Key_Enter),
                    self.treeWidget_AddressTable_edit_value,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_desc,
                ),
                (
                    QKeyCombination(
                        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return
                    ),
                    self.treeWidget_AddressTable_edit_address,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.AltModifier, Qt.Key.Key_Return),
                    self.treeWidget_AddressTable_edit_type,
                ),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.treeWidget_AddressTable.keyPressEvent_original(event)

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
                            row.setText(
                                ADDR_COL, address_data.get_base_address_as_str() if is_struct_child else f"P->{address}"
                            )
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
                value = debugcore.read_memory(
                    address,
                    vt.value_index,
                    vt.length,
                    vt.zero_terminate,
                    vt.value_repr,
                    vt.endian,
                    mem_handle=mem_handle,
                )
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

    # Create properly typed values for memscan
    def validate_search_values(
        self, search_for: str, search_for2: str
    ) -> tuple[int | float | str | BytePattern | None, int | float | None]:
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
        type_index = self.comboBox_ScanType.currentData(Qt.ItemDataRole.UserRole)
        if type_index == typedefs.SCAN_TYPE.UNKNOWN:
            scan_thread = guitypedefs.Worker(memscan.snapshot)
        else:
            value_1, value_2 = self.validate_search_values(self.lineEdit_Scan.text(), self.lineEdit_Scan2.text())
            if self.widget_ScanFields.isEnabled() and value_1 == None:
                return
            scan_type = scancore.scan_type_to_memscan_dict[type_index]
            scan_thread = guitypedefs.Worker(memscan.scan, scan_type, value_1, value_2)
        self.progressBar.setValue(0)
        self.progress_bar_timer = QTimer(self, timeout=self.update_progress_bar)
        self.progress_bar_timer.start(100)
        scan_thread.signals.finished.connect(self.scan_callback)
        states.threadpool.start(scan_thread)
        self.is_scanning = True
        self.update_scan_box_state()

    def resize_address_table(self) -> None:
        self.treeWidget_AddressTable.resizeColumnToContents(FROZEN_COL)

    # gets the information from the dialog then adds it to addresstable
    def pushButton_AddAddressManually_clicked(self) -> None:
        manual_address_dialog = ManualAddressDialogForm(self)
        if manual_address_dialog.exec():
            desc, address_expr, vt = manual_address_dialog.get_values()
            self.add_entry_to_addresstable(desc, address_expr, vt)
            self.update_address_table()

    def pushButton_RefreshAdressTable_clicked(self) -> None:
        states.exp_cache.clear()
        self.update_address_table()

    def pushButton_MemoryView_clicked(self) -> None:
        self.memory_view_window.showMaximized()
        self.memory_view_window.activateWindow()

    def pushButton_Wiki_clicked(self) -> None:
        utils.execute_command_as_user('python3 -m webbrowser "https://github.com/korcankaraokcu/PINCE/wiki"')

    def pushButton_About_clicked(self) -> None:
        about_widget = AboutWidgetForm(self)
        about_widget.show()
        about_widget.activateWindow()

    def pushButton_Settings_clicked(self) -> None:
        SettingsDialog(self).exec()

    def pushButton_Console_clicked(self) -> None:
        console_widget = ConsoleWidgetForm(self)
        console_widget.showMaximized()

    def checkBox_Hex_stateChanged(self, state: int) -> None:
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            # allows only things that are hex, can also start with 0x
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int_hex"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int_hex"))
        else:
            # sets it back to integers only
            self.lineEdit_Scan.setValidator(guiutils.validator_map.get("int"))
            self.lineEdit_Scan2.setValidator(guiutils.validator_map.get("int"))

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
        self.lineEdit_Scan.keyPressEvent_original(event)

    def lineEdit_Scan2_on_key_press_event(self, event: QKeyEvent) -> None:
        self.handle_line_edit_scan_key_press_event(event)
        self.lineEdit_Scan2.keyPressEvent_original(event)

    def pushButton_UndoScan_clicked(self) -> None:
        if debugcore.currentpid == -1:
            return
        undo_thread = guitypedefs.Worker(memscan.undo_scan)
        undo_thread.signals.finished.connect(self.scan_callback)
        states.threadpool.start(undo_thread)
        self.undo_scan_available = False
        self.pushButton_UndoScan.setEnabled(False)  # we can undo once so set it to false and re-enable at next scan

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
        scan_scope_text = [
            (ScanLevel.HEAP_STACK_EXE, tr.BASIC),
            (ScanLevel.HEAP_STACK_EXE_BSS, tr.NORMAL),
            (ScanLevel.ALL_RW, tr.RW),
            (ScanLevel.ALL, tr.FULL),
        ]
        for scope, text in scan_scope_text:
            self.comboBox_ScanScope.addItem(text, scope)
        self.comboBox_ScanScope.setCurrentIndex(self.comboBox_ScanScope.findData(ScanLevel.HEAP_STACK_EXE_BSS))  # NORMAL
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
        self.undo_scan_available = True

    def pushButton_ScanRegions_clicked(self) -> None:
        scan_regions_dialog = ManageScanRegionsDialog(self)
        if scan_regions_dialog.exec():
            self.deleted_regions.extend(scan_regions_dialog.get_values())

    def get_value_index_for_match(self, match: MatchView) -> int:
        if match.is_string_match():
            return typedefs.VALUE_INDEX.STRING_UTF8
        elif match.is_bytearray_match():
            return typedefs.VALUE_INDEX.AOB
        else:
            if match.match_info.has_int8() or match.match_info.has_uint8():
                return typedefs.VALUE_INDEX.INT8
            if match.match_info.has_int16() or match.match_info.has_uint16():
                return typedefs.VALUE_INDEX.INT16
            if match.match_info.has_int32() or match.match_info.has_uint32():
                return typedefs.VALUE_INDEX.INT32
            if match.match_info.has_int64() or match.match_info.has_uint64():
                return typedefs.VALUE_INDEX.INT64
            if match.match_info.has_float32():
                return typedefs.VALUE_INDEX.FLOAT32
            if match.match_info.has_float64():
                return typedefs.VALUE_INDEX.FLOAT64
            logger.error("Passed invalid match to value_index retrieval! Shouldn't be possible!")
            return -1

    def scan_callback(self) -> None:
        self.is_scanning = False
        self.progress_bar_timer.stop()
        self.progressBar.setValue(100)
        matches = memscan.matches()
        self.update_match_count()
        self.tableWidget_valuesearchtable.setRowCount(0)
        current_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = self._scan_to_length(current_type)
        with debugcore.memory_handle() as mem_handle:
            row = 0
            self.tableWidget_valuesearchtable.setSortingEnabled(False)
            for match in matches:
                address = hex(match.address)
                if match.match_info.raw_bits == 0:
                    # Ignore unknown entries (no match flags), should not happen as every received match is valid
                    logger.error("Found invalid/unknown match! Skipping...")
                    continue
                # This is technically wrong because we can have multiple possible value types through a match
                # but we'll go with the lowest matching value type
                value_index = self.get_value_index_for_match(match)
                if self.checkBox_Hex.isChecked():
                    value_repr = typedefs.VALUE_REPR.HEX
                else:
                    value_repr = (
                        typedefs.VALUE_REPR.SIGNED
                        if match.match_info.is_signed_integer_only()
                        else typedefs.VALUE_REPR.UNSIGNED
                    )
                endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
                current_item = QTableWidgetItem(address)
                current_item.setData(Qt.ItemDataRole.UserRole, (value_index, value_repr, endian))
                # TODO: Change GDB reading to memscan
                value = debugcore.read_memory(address, value_index, length, True, value_repr, endian, mem_handle)
                value = "" if value is None else str(value)
                if debugcore.is_address_static(address):
                    current_item.setForeground(QColor(0, 136, 85))
                self.tableWidget_valuesearchtable.insertRow(row)
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_ADDRESS_COL, current_item)
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_VALUE_COL, QTableWidgetItem(value))
                self.tableWidget_valuesearchtable.setItem(row, SEARCH_TABLE_PREVIOUS_COL, QTableWidgetItem(value))
                row += 1
                if row == 1000:
                    break
        self.tableWidget_valuesearchtable.resizeColumnsToContents()
        self.tableWidget_valuesearchtable.setSortingEnabled(True)
        self.update_scan_box_state()

    def _scan_to_length(self, type_index: int) -> int:
        if type_index == typedefs.SCAN_INDEX.AOB:
            return self.lineEdit_Scan.text().count(" ") + 1
        if type_index == typedefs.SCAN_INDEX.STRING:
            return len(self.lineEdit_Scan.text())
        return 0

    def update_match_count(self) -> None:
        match_count = memscan.get_match_count()
        if match_count > 1000:
            self.label_MatchCount.setText(tr.MATCH_COUNT_LIMITED.format(match_count, 1000))
        else:
            self.label_MatchCount.setText(tr.MATCH_COUNT.format(match_count))

    def tableWidget_valuesearchtable_cell_double_clicked(self, row: int, col: int) -> None:
        current_item = self.tableWidget_valuesearchtable.item(row, SEARCH_TABLE_ADDRESS_COL)
        value_index, value_repr, endian = current_item.data(Qt.ItemDataRole.UserRole)
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        vt = typedefs.ValueType(value_index, length, True, value_repr, endian)
        self.add_entry_to_addresstable(tr.NO_DESCRIPTION, current_item.text(), vt)
        self.update_address_table()

    def tableWidget_valuesearchtable_key_press_event(self, event: QKeyEvent) -> None:
        current_item = self.tableWidget_valuesearchtable.currentItem()
        if debugcore.currentpid == -1 or not current_item:
            return
        current_address = self.tableWidget_valuesearchtable.item(current_item.row(), SEARCH_TABLE_ADDRESS_COL).text()
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C),
                    self.copy_valuesearchtable_selection,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
                    lambda: self.browse_region_for_address(current_address),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                    lambda: self.disassemble_for_address(current_address),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Delete),
                    self.delete_valuesearchtable_selection,
                ),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.tableWidget_valuesearchtable.keyPressEvent_original(event)

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
        app.clipboard().setText(" ".join(address_list))

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
            memscan.remove_match_by_address(safe_str_to_int(address, 16))
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
        self.processwindow = ProcessForm(self)
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
                message = messages.get(attach_result, tr.ERROR)
            QMessageBox.information(app.focusWidget(), tr.ERROR, message)
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
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.CREATE_PROCESS_ERROR)
            self.on_inferior_exit()
            return False

    # Changes appearance whenever a new process is created or attached
    def on_new_process(self) -> None:
        monocore.reset()
        name = utils.get_process_name(debugcore.currentpid)
        self.label_SelectedProcess.setText(str(debugcore.currentpid) + " - " + name)
        self.is_wine_process = utils.is_wine_process(debugcore.currentpid)

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
        self.treeWidget_AddressTable.clear()

    def copy_to_address_table(self) -> None:
        length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        selected_indexes = self.tableWidget_valuesearchtable.selectionModel().selectedRows()
        for index in selected_indexes:
            address_item = self.tableWidget_valuesearchtable.item(index.row(), SEARCH_TABLE_ADDRESS_COL)
            value_index, value_repr, endian = address_item.data(Qt.ItemDataRole.UserRole)
            vt = typedefs.ValueType(value_index, length, True, value_repr, endian)
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
        # Inferior is gone, so just drop speedhack state.
        # No need for uninstall as that would only produce noise with errors.
        self.speedhack.reset()
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
        debugcore.init_gdb(gdb_path)
        settings.apply_after_init()
        SessionManager.on_process_changed()
        states.process_signals.exit.emit()

    def on_status_detached(self) -> None:
        self.label_SelectedProcess.setStyleSheet("color: blue")
        self.label_InferiorStatus.setText(tr.STATUS_DETACHED)
        self.label_InferiorStatus.setVisible(True)
        self.label_InferiorStatus.setStyleSheet("color: blue")

    def on_status_stopped(self) -> None:
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

        self.await_exit_thread.request_shutdown()
        self.await_exit_thread.wait(1000)
        self.cleanup_speedhack()
        debugcore.detach()
        memscan.close()
        app.closeAllWindows()
        logger.info("All PINCE windows closed")

    # Call update_address_table manually after this
    def add_entry_to_addresstable(
        self,
        description: str,
        address_expr: str | typedefs.PointerChainRequest,
        value_type: typedefs.ValueType | None = None,
    ) -> None:
        current_row = QTreeWidgetItem()
        current_row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
        frozen = typedefs.Frozen("", typedefs.FREEZE_TYPE.DEFAULT)
        current_row.setData(FROZEN_COL, Qt.ItemDataRole.UserRole, frozen)
        value_type = typedefs.ValueType() if not value_type else value_type
        self.treeWidget_AddressTable.addTopLevelItem(current_row)
        self.change_address_table_entries(current_row, description, address_expr, value_type)
        self.show()  # In case of getting called from elsewhere
        self.activateWindow()
        self.mark_address_tree_changed()

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

    def toggle_script_entry(
        self, row: QTreeWidgetItem, entry: typedefs.ScriptEntry, check_state: Qt.CheckState
    ) -> None:
        is_enable = check_state == Qt.CheckState.Checked
        row.setCheckState(FROZEN_COL, check_state)
        enable_code, disable_code = parse_script_sections(entry.script)
        code = enable_code if is_enable else disable_code
        if code is None:  # tagless script or no [DISABLE]: nothing to run when toggling off.
            return
        entry.namespace = entry.namespace or create_script_namespace()
        succeeded, output = run_script_code(code, entry.namespace, f"<{row.text(DESC_COL) or tr.SCRIPT}>")
        if not succeeded:
            if is_enable:  # don't leave a failed enable looking active
                row.setCheckState(FROZEN_COL, Qt.CheckState.Unchecked)
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
            length = self._scan_to_length(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
            self.tableWidget_valuesearchtable.setSortingEnabled(False)
            try:
                with debugcore.memory_handle() as mem_handle:
                    for row_index in range(row_count):
                        address_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_ADDRESS_COL)
                        value_item = self.tableWidget_valuesearchtable.item(row_index, SEARCH_TABLE_VALUE_COL)
                        previous_text = self.tableWidget_valuesearchtable.item(
                            row_index, SEARCH_TABLE_PREVIOUS_COL
                        ).text()
                        value_index, value_repr, endian = address_item.data(Qt.ItemDataRole.UserRole)
                        address = address_item.text()
                        new_value = debugcore.read_memory(
                            address,
                            value_index,
                            length,
                            value_repr=value_repr,
                            endian=endian,
                            mem_handle=mem_handle,
                        )
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
                if typedefs.VALUE_INDEX.is_number(vt.value_index):
                    new_value = debugcore.read_memory(address, vt.value_index, endian=vt.endian)
                    if new_value is None:
                        continue
                    if (
                        freeze_type == typedefs.FREEZE_TYPE.ALLOW_INCREMENT
                        and new_value > value
                        or freeze_type == typedefs.FREEZE_TYPE.ALLOW_DECREMENT
                        and new_value < value
                    ):
                        frozen.value = new_value
                        debugcore.write_memory(address, vt.value_index, new_value, endian=vt.endian)
                        continue
                debugcore.write_memory(address, vt.value_index, value, vt.zero_terminate, vt.endian)

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
                frozen.value = utils.parse_string(row.text(VALUE_COL), vt.value_index)
            else:
                frozen.enabled = False  # it has just been toggled off
                self.change_freeze_type(typedefs.FREEZE_TYPE.DEFAULT, row)

    def treeWidget_AddressTable_change_repr(self, new_repr: int) -> None:
        for row in self.treeWidget_AddressTable.selectedItems():
            if self.get_script_entry(row) is not None:
                continue
            value_type = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
            value_type.value_repr = new_repr
            row.setText(TYPE_COL, value_type.text())
        self.update_address_table()
        self.mark_address_tree_changed()

    def _is_struct_row(self, row: QTreeWidgetItem) -> bool:
        # Only carries an address, has no readable value or editable type.
        vt = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
        return vt is not None and vt.value_index == typedefs.VALUE_INDEX.STRUCT

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
        value_index = row.data(TYPE_COL, Qt.ItemDataRole.UserRole).value_index
        dialog = utilwidgets.InputDialog(self, [(tr.ENTER_VALUE, value)])
        if dialog.exec():
            new_value = dialog.get_values()[0]
            if utils.parse_string(new_value, value_index) is None:
                QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
                return
            length_changed = False
            for row in self.treeWidget_AddressTable.selectedItems():
                if self.get_script_entry(row) is not None or self._is_struct_row(row):
                    continue
                address = self._resolved_address(row)
                vt: typedefs.ValueType = row.data(TYPE_COL, Qt.ItemDataRole.UserRole)
                parsed_value = utils.parse_string(new_value, vt.value_index)
                if typedefs.VALUE_INDEX.has_length(vt.value_index) and parsed_value is not None:
                    if vt.length != len(parsed_value):
                        length_changed = True
                    vt.length = len(parsed_value)
                    row.setText(TYPE_COL, vt.text())
                frozen: typedefs.Frozen = row.data(FROZEN_COL, Qt.ItemDataRole.UserRole)
                frozen.value = parsed_value
                debugcore.write_memory(address, vt.value_index, parsed_value, vt.zero_terminate, vt.endian)
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
        manual_address_dialog = ManualAddressDialogForm(self, desc, address_expr, vt, relative_base)
        manual_address_dialog.setWindowTitle(tr.EDIT_ADDRESS)
        if manual_address_dialog.exec():
            desc, address_expr, vt = manual_address_dialog.get_values()
            self.change_address_table_entries(row, desc, address_expr, vt)
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
        dialog = EditTypeDialogForm(self, vt)
        if dialog.exec():
            vt = dialog.get_values()
            type_text = vt.text()
            for row in self.treeWidget_AddressTable.selectedItems():
                if self.get_script_entry(row) is not None or self._is_struct_row(row):
                    continue
                row.setData(TYPE_COL, Qt.ItemDataRole.UserRole, copy.copy(vt))
                row.setText(TYPE_COL, type_text)
            self.update_address_table()
            self.mark_address_tree_changed()

    # Changes the column values of the given row
    def change_address_table_entries(
        self,
        row: QTreeWidgetItem,
        description: str = tr.NO_DESCRIPTION,
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
            return row.text(DESC_COL), "", typedefs.ValueType().serialize(), {"script": entry.script}, children
        return self.read_address_table_entries(row, True) + (children,)

    # Flashing Attach Button when the process is not attached
    def flash_attach_button(self) -> None:
        if not self.flashAttachButton:
            self.flashAttachButtonTimer.stop()
            self.pushButton_AttachProcess.setStyleSheet("")
            return

        case = self.flashAttachButton_gradiantState % 32

        if case < 16:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str(case / 16) + ");}"
        else:
            borderstring = "QPushButton {border: 3px solid rgba(0,255,0," + str((32 - case) / 16) + ");}"

        self.pushButton_AttachProcess.setStyleSheet(borderstring)
        self.flashAttachButton_gradiantState += 1
        if self.flashAttachButton_gradiantState > 768:  # 32*24
            self.flashAttachButton_gradiantState = 0


# process select window
class ProcessForm(QMainWindow, ProcessWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.refresh_process_table(self.tableWidget_ProcessTable, utils.get_process_list())
        self.pushButton_Close.clicked.connect(self.close)
        self.pushButton_Open.clicked.connect(self.pushButton_Open_clicked)
        self.pushButton_CreateProcess.clicked.connect(self.pushButton_CreateProcess_clicked)
        self.lineEdit_SearchProcess.textChanged.connect(self.generate_new_list)
        self.tableWidget_ProcessTable.itemDoubleClicked.connect(self.pushButton_Open_clicked)
        guiutils.center_to_parent(self)

    # refreshes process list
    def generate_new_list(self) -> None:
        text = self.lineEdit_SearchProcess.text()
        processlist = utils.search_processes(text)
        self.refresh_process_table(self.tableWidget_ProcessTable, processlist)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.pushButton_Open_clicked()
        elif event.key() == Qt.Key.Key_F1:
            self.pushButton_CreateProcess_clicked()
        else:
            return super().keyPressEvent(event)

    # lists currently working processes to table
    def refresh_process_table(self, tablewidget: QTableWidget, processlist: list[tuple[str, str, str]]) -> None:
        tablewidget.setRowCount(0)
        for pid, user, name in processlist:
            current_row = tablewidget.rowCount()
            tablewidget.insertRow(current_row)
            tablewidget.setItem(current_row, 0, QTableWidgetItem(pid))
            tablewidget.setItem(current_row, 1, QTableWidgetItem(user))
            tablewidget.setItem(current_row, 2, QTableWidgetItem(name))

    # gets the pid out of the selection to attach
    def pushButton_Open_clicked(self) -> None:
        index = self.tableWidget_ProcessTable.currentIndex()
        row_count = self.tableWidget_ProcessTable.rowCount()
        if index.row() == -1 and row_count == 1:
            # autoselect first row if there is only one row
            self.tableWidget_ProcessTable.setCurrentCell(0, 0)

        current_item = self.tableWidget_ProcessTable.item(self.tableWidget_ProcessTable.currentIndex().row(), 0)
        if current_item is None:
            QMessageBox.information(self, tr.ERROR, tr.SELECT_PROCESS)
        else:
            pid = int(current_item.text())
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            if self.parent().attach_to_pid(pid):
                self.close()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def pushButton_CreateProcess_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_BINARY, os.path.expanduser("~"))
        if file_path:
            arg_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_OPTIONAL_ARGS, ""), (tr.LD_PRELOAD_OPTIONAL, "")])
            if arg_dialog.exec():
                args, ld_preload_path = arg_dialog.get_values()
            else:
                return
            self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
            if self.parent().create_new_process(file_path, args, ld_preload_path):
                self.close()
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))


# Add Address Manually Dialog
class ManualAddressDialogForm(QDialog, ManualAddressDialog):
    def __init__(
        self,
        parent: QWidget,
        description: str = tr.NO_DESCRIPTION,
        address: str | typedefs.PointerChainRequest = "0x",
        value_type: typedefs.ValueType | None = None,
        relative_base: str = "",
    ) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.relative_base = relative_base
        self.lineEdit_PtrStartAddress.setFixedWidth(180)
        self.lineEdit_Address.setFixedWidth(180)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(QHexValidator(99, self))
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        self.lineEdit_Description.setText(description)
        self.lineEdit_Description.setFixedWidth(180)
        self.offsetsList: list[PointerChainOffset] = []
        if not isinstance(address, typedefs.PointerChainRequest):
            self.lineEdit_Address.setText(address)
            self.widget_Pointer.hide()
        else:
            self.checkBox_IsPointer.setChecked(True)
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(address.get_base_address_as_str())
            self.create_offsets_list(address)
            self.widget_Pointer.show()
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.comboBox_Endianness.currentIndexChanged.connect(self.update_value)
        self.lineEdit_Length.textChanged.connect(self.update_value)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        self.checkBox_Signed.stateChanged.connect(self.repr_changed)
        self.checkBox_ZeroTerminate.stateChanged.connect(self.update_value)
        self.checkBox_IsPointer.stateChanged.connect(self.checkBox_IsPointer_state_changed)
        self.lineEdit_PtrStartAddress.textChanged.connect(self.update_value)
        self.lineEdit_Address.textChanged.connect(self.update_value)
        self.pushButton_AddOffset.clicked.connect(lambda: self.addOffsetLayout(True))
        self.pushButton_RemoveOffset.clicked.connect(self.removeOffsetLayout)
        self.label_Value.contextMenuEvent = self.label_Value_context_menu_event
        self.update_value()
        guiutils.center_to_parent(self)

    def label_Value_context_menu_event(self, event: QContextMenuEvent) -> None:
        menu = QMenu()
        refresh = menu.addAction(tr.REFRESH)
        font_size = self.label_Value.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {refresh: self.update_value}
        try:
            actions[action]()
        except KeyError:
            pass

    def addOffsetLayout(self, should_update: bool = True) -> None:
        offsetFrame = PointerChainOffset(len(self.offsetsList), self.widget_Pointer)
        self.offsetsList.append(offsetFrame)
        self.verticalLayout_Pointers.insertWidget(0, self.offsetsList[-1])
        offsetFrame.offset_changed_signal.connect(self.update_value)
        if should_update:
            self.update_value()

    def removeOffsetLayout(self) -> None:
        if len(self.offsetsList) == 1:
            return
        frame = self.offsetsList[-1]
        frame.deleteLater()
        self.verticalLayout_Pointers.removeWidget(frame)
        del self.offsetsList[-1]
        self.update_value()

    def update_deref_labels(self, pointer_chain_result: typedefs.PointerChainResult) -> None:
        if pointer_chain_result is not None:
            base_deref = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[0])
            self.label_BaseAddressDeref.setText(f" → {base_deref}")
            for index, offsetFrame in enumerate(self.offsetsList):
                if index + 1 >= len(pointer_chain_result.pointer_chain):
                    offsetFrame.update_deref_label("<font color=red>??</font>")
                    continue
                previousDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index])
                currentDerefText = self.caps_hex_or_error_indicator(pointer_chain_result.pointer_chain[index + 1])
                offsetText = utils.upper_hex(offsetFrame.offsetText.text())
                operationalSign = "" if offsetText.startswith("-") else "+"
                calculation = f"{previousDerefText} {operationalSign} {offsetText}"
                if index + 1 != len(pointer_chain_result.pointer_chain) - 1:
                    offsetFrame.update_deref_label(f" [{calculation}] → {currentDerefText}")
                else:
                    offsetFrame.update_deref_label(f" {calculation} = {currentDerefText}")
        else:
            self.label_BaseAddressDeref.setText(" → <font color=red>??</font>")
            for offsetFrame in self.offsetsList:
                offsetFrame.update_deref_label("<font color=red>??</font>")

    def caps_hex_or_error_indicator(self, address: int) -> str:
        if address == 0:
            return "<font color=red>??</font>"
        return utils.upper_hex(hex(address))

    def _apply_relative_base(self, expression: str) -> str:
        # Prepend the parent base so a relative offset resolves while the stored expression stays relative.
        if self.relative_base and expression.startswith(("+", "-")):
            return self.relative_base + expression
        return expression

    def update_value(self) -> None:
        if self.checkBox_IsPointer.isChecked():
            hex_converted_expr = debugcore.convert_to_hex(
                self._apply_relative_base(self.lineEdit_PtrStartAddress.text())
            )
            pointer_chain_req = typedefs.PointerChainRequest(hex_converted_expr, self.get_offsets_int_list())
            pointer_chain_result = debugcore.read_pointer_chain(pointer_chain_req)
            address = None
            if pointer_chain_result is not None and pointer_chain_result.get_final_address() not in {0, None}:
                address_text = pointer_chain_result.get_final_address_as_hex()
                address = pointer_chain_result.get_final_address()
            else:
                address_text = "??"
            self.lineEdit_Address.setText(address_text)
            self.update_deref_labels(pointer_chain_result)
        else:
            hex_converted_expr = debugcore.convert_to_hex(self._apply_relative_base(self.lineEdit_Address.text()))
            address = debugcore.examine_expression(hex_converted_expr).address
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        address_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = safe_str_to_int(self.lineEdit_Length.text(), 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        value = debugcore.read_memory(address, address_type, length, zero_terminate, value_repr, endian)
        self.label_Value.setText("<font color=red>??</font>" if value is None else str(value))
        old_width = self.width()
        app.processEvents()
        self.adjustSize()
        self.resize(old_width, self.minimumHeight())

    def comboBox_ValueType_current_index_changed(self) -> None:
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        self.update_value()

    def repr_changed(self) -> None:
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)
        self.update_value()

    def checkBox_IsPointer_state_changed(self) -> None:
        if self.checkBox_IsPointer.isChecked():
            self.lineEdit_Address.setReadOnly(True)
            self.lineEdit_PtrStartAddress.setText(self.lineEdit_Address.text())
            if len(self.offsetsList) == 0:
                self.addOffsetLayout(False)
            self.widget_Pointer.show()
        else:
            self.lineEdit_Address.setText(self.lineEdit_PtrStartAddress.text())
            self.lineEdit_PtrStartAddress.setText("")
            self.lineEdit_Address.setReadOnly(False)
            self.widget_Pointer.hide()
        self.update_value()

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self) -> tuple[str, str | typedefs.PointerChainRequest, typedefs.ValueType]:
        description = self.lineEdit_Description.text()
        length = self.lineEdit_Length.text()
        length = safe_str_to_int(length, 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        value_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        vt = typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)
        if self.checkBox_IsPointer.isChecked():
            base_expression = debugcore.convert_to_hex(self.lineEdit_PtrStartAddress.text())
            address = typedefs.PointerChainRequest(base_expression, self.get_offsets_int_list())
        else:
            address = debugcore.convert_to_hex(self.lineEdit_Address.text())
        return description, address, vt

    def get_offsets_int_list(self) -> list[int]:
        offsetsIntList = []
        for frame in self.offsetsList:
            offsetText = frame.layout().itemAt(1).widget().text()
            try:
                offsetValue = int(offsetText, 16)
            except ValueError:
                offsetValue = 0
            offsetsIntList.append(offsetValue)
        return offsetsIntList

    def create_offsets_list(self, pointer_chain_req: typedefs.PointerChainRequest) -> None:
        if not isinstance(pointer_chain_req, typedefs.PointerChainRequest):
            raise TypeError("Passed non-PointerChainRequest type to create_offsets_list!")

        for offset in pointer_chain_req.offsets_list:
            self.addOffsetLayout(False)
            frame = self.offsetsList[-1]
            frame.layout().itemAt(1).widget().setText(hex(offset))

    def get_type_size(self) -> int:
        return typedefs.index_to_valuetype_dict[self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)][0]


class EditTypeDialogForm(QDialog, EditTypeDialog):
    def __init__(self, parent: QWidget, value_type: typedefs.ValueType | None = None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        vt = typedefs.ValueType() if not value_type else value_type
        self.lineEdit_Length.setValidator(QHexValidator(99, self))
        self.lineEdit_Length.setFixedWidth(40)
        guiutils.fill_value_combobox(self.comboBox_ValueType, vt.value_index)
        guiutils.fill_endianness_combobox(self.comboBox_Endianness, vt.endian)
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.show()
            self.checkBox_ZeroTerminate.setChecked(vt.zero_terminate)
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            try:
                length = str(vt.length)
            except:
                length = "10"
            self.lineEdit_Length.setText(length)
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        if vt.value_repr == typedefs.VALUE_REPR.HEX:
            self.checkBox_Hex.setChecked(True)
            self.checkBox_Signed.setEnabled(False)
        elif vt.value_repr == typedefs.VALUE_REPR.SIGNED:
            self.checkBox_Signed.setChecked(True)
        else:
            self.checkBox_Signed.setChecked(False)
        self.comboBox_ValueType.currentIndexChanged.connect(self.comboBox_ValueType_current_index_changed)
        self.checkBox_Hex.stateChanged.connect(self.repr_changed)
        app.processEvents()
        self.adjustSize()
        guiutils.center_to_parent(self)

    def comboBox_ValueType_current_index_changed(self) -> None:
        if typedefs.VALUE_INDEX.is_string(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)):
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.show()
        elif self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole) == typedefs.VALUE_INDEX.AOB:
            self.widget_Length.show()
            self.checkBox_ZeroTerminate.hide()
        else:
            self.widget_Length.hide()
        app.processEvents()
        self.adjustSize()

    def repr_changed(self) -> None:
        if self.checkBox_Hex.isChecked():
            self.checkBox_Signed.setEnabled(False)
        else:
            self.checkBox_Signed.setEnabled(True)

    def reject(self) -> None:
        super().reject()

    def accept(self) -> None:
        if self.label_Length.isVisible():
            length = self.lineEdit_Length.text()
            try:
                length = int(length, 0)
            except:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_NOT_VALID)
                return
            if not length > 0:
                QMessageBox.information(self, tr.ERROR, tr.LENGTH_GT)
                return
        super().accept()

    def get_values(self) -> typedefs.ValueType:
        value_index = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
        length = self.lineEdit_Length.text()
        length = safe_str_to_int(length, 0)
        zero_terminate = self.checkBox_ZeroTerminate.isChecked()
        if self.checkBox_Hex.isChecked():
            value_repr = typedefs.VALUE_REPR.HEX
        elif self.checkBox_Signed.isChecked():
            value_repr = typedefs.VALUE_REPR.SIGNED
        else:
            value_repr = typedefs.VALUE_REPR.UNSIGNED
        endian = self.comboBox_Endianness.currentData(Qt.ItemDataRole.UserRole)
        return typedefs.ValueType(value_index, length, zero_terminate, value_repr, endian)


class TrackSelectorDialogForm(QDialog, TrackSelectorDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.selection = None
        self.pushButton_Pointer.clicked.connect(lambda: self.change_selection("pointer"))
        self.pushButton_Pointed.clicked.connect(lambda: self.change_selection("pointed"))
        guiutils.center_to_parent(self)

    def change_selection(self, selection: str) -> None:
        self.selection = selection
        self.close()


class LoadingDialogForm(QDialog, LoadingDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags())
        self.keyPressEvent = QEvent.ignore

        # Make use of this background_thread when you spawn a LoadingDialogForm
        # Warning: overrided_func() can only return one value, so if your overridden function returns more than one
        # value, refactor your overriden function to return only one object(convert tuple to list etc.)
        # Check refresh_table method of FunctionsInfoWidgetForm for exemplary usage
        self.background_thread = self.BackgroundThread()
        self.background_thread.output_ready.connect(self.accept)
        self.pushButton_Cancel.clicked.connect(self.close)
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/LoadingDialog/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(25, 25))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        guiutils.center_to_parent(self)

    # TODO: This function only cancels the last command sent, redesign this if it's needed to cancel non-gdb functions
    def cancel_thread(self) -> None:
        debugcore.cancel_ongoing_command()
        self.background_thread.wait()

    def exec(self) -> None:
        self.background_thread.start()
        super().exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_thread()
        super().closeEvent(event)

    class BackgroundThread(QThread):
        output_ready = pyqtSignal(object)

        def __init__(self) -> None:
            super().__init__()

        # Unhandled exceptions in this thread freezes PINCE
        def run(self) -> None:
            try:
                output = self.overrided_func()
            except:
                traceback.print_exc()
                output = None
            self.output_ready.emit(output)

        def overrided_func(self) -> Any:
            logger.debug("Override this function")
            return 0


class ConsoleWidgetForm(QWidget, ConsoleWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.completion_model = QStringListModel()
        self.completer = QCompleter()
        self.completer.setModel(self.completion_model)
        self.completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer.setMaxVisibleItems(8)
        self.lineEdit.setCompleter(self.completer)
        self.quit_commands = ("q", "quit", "-gdb-exit")
        self.continue_commands = ("c", "continue", "-exec-continue")
        self.input_history = [""]
        self.current_history_index = -1
        self.await_async_output_thread = guitypedefs.AwaitAsyncOutput()
        self.await_async_output_thread.async_output_ready.connect(self.on_async_output)
        self.await_async_output_thread.start()
        self.pushButton_Send.clicked.connect(self.communicate)
        self.shortcut_send = QShortcut(QKeySequence("Return"), self)
        self.shortcut_send.activated.connect(self.communicate)
        self.shortcut_complete_command = QShortcut(QKeySequence("Tab"), self)
        self.shortcut_complete_command.activated.connect(self.complete_command)
        self.shortcut_multiline_mode = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.shortcut_multiline_mode.activated.connect(self.enter_multiline_mode)
        self.lineEdit.textEdited.connect(self.finish_completion)

        # Saving the original function because super() doesn't work when we override functions like this
        self.lineEdit.keyPressEvent_original = self.lineEdit.keyPressEvent
        self.lineEdit.keyPressEvent = self.lineEdit_key_press_event
        self.reset_console_text()
        guiutils.center_to_parent(self)

    def communicate(self) -> None:
        self.current_history_index = -1
        self.input_history[-1] = ""
        console_input = self.lineEdit.text()
        last_input = self.input_history[-2] if len(self.input_history) > 1 else ""
        if console_input != last_input and console_input != "":
            self.input_history[-1] = console_input
            self.input_history.append("")
        if console_input.lower() == "/clear":
            self.lineEdit.clear()
            self.reset_console_text()
            return
        self.lineEdit.clear()
        stripped = console_input.strip().lower()
        if stripped in self.quit_commands:
            console_output = tr.QUIT_SESSION_CRASH
        elif stripped in self.continue_commands:
            console_output = tr.CONT_SESSION_CRASH
        elif self.radioButton_CLI.isChecked():
            console_output = debugcore.send_command(console_input, cli_output=True)
        else:
            console_output = debugcore.send_command(console_input)
        self.textBrowser.append("-->" + console_input)
        if console_output:
            self.textBrowser.append(console_output)
        self.scroll_to_bottom()

    def reset_console_text(self) -> None:
        self.textBrowser.clear()
        self.textBrowser.append(tr.GDB_CONSOLE_INIT)

    def scroll_to_bottom(self) -> None:
        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.textBrowser.setTextCursor(cursor)
        self.textBrowser.ensureCursorVisible()

    def enter_multiline_mode(self) -> None:
        multiline_dialog = TextEditDialog(self, self.lineEdit.text())
        if multiline_dialog.exec():
            self.lineEdit.setText(multiline_dialog.get_values())
            self.communicate()

    def on_async_output(self, async_output: str) -> None:
        self.textBrowser.append(async_output)
        self.scroll_to_bottom()

    def scroll_backwards_history(self) -> None:
        if self.current_history_index - 1 < -len(self.input_history):
            return
        new_text = self.input_history[self.current_history_index - 1]
        self.input_history[self.current_history_index] = self.lineEdit.text()
        self.current_history_index -= 1
        self.lineEdit.setText(new_text)

    def scroll_forwards_history(self) -> None:
        if self.current_history_index == -1:
            return
        self.input_history[self.current_history_index] = self.lineEdit.text()
        self.current_history_index += 1
        self.lineEdit.setText(self.input_history[self.current_history_index])

    def lineEdit_key_press_event(self, event: QKeyEvent) -> None:
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up), self.scroll_backwards_history),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down), self.scroll_forwards_history),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            self.lineEdit.keyPressEvent_original(event)

    def finish_completion(self) -> None:
        self.completion_model.setStringList([])

    def complete_command(self) -> None:
        if debugcore.gdb_initialized and debugcore.currentpid != -1 and self.lineEdit.text():
            self.completion_model.setStringList(debugcore.complete_command(self.lineEdit.text()))
            self.completer.complete()
        else:
            self.finish_completion()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.await_async_output_thread.stop()


class AboutWidgetForm(QTabWidget, AboutWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        # This section has untranslated text since it's just a placeholder
        pince_dir = utils.get_script_directory()
        with open(f"{pince_dir}/COPYING", encoding="utf-8") as f:
            license_text = f.read()
        with open(f"{pince_dir}/AUTHORS", encoding="utf-8") as f:
            authors_text = f.read()
        with open(f"{pince_dir}/THANKS", encoding="utf-8") as f:
            thanks_text = f.read()
        self.textBrowser_License.setPlainText(license_text)
        self.textBrowser_Contributors.append(
            "This is only a placeholder, this section may look different when the project finishes"
            + "\nIn fact, something like a demo-scene for here would look absolutely fabulous <:"
        )
        self.textBrowser_Contributors.append("\n########")
        self.textBrowser_Contributors.append("#AUTHORS#")
        self.textBrowser_Contributors.append("########\n")
        self.textBrowser_Contributors.append(authors_text)
        self.textBrowser_Contributors.append("\n#######")
        self.textBrowser_Contributors.append("#THANKS#")
        self.textBrowser_Contributors.append("#######\n")
        self.textBrowser_Contributors.append(thanks_text)
        guiutils.center_to_parent(self)


class MemoryViewWindowForm(QMainWindow, MemoryViewWindow):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.updating_memoryview = False
        self.stack_from_base_pointer = False
        self.stacktrace_info_widget = StackTraceInfoWidgetForm(self)
        self.float_registers_widget = FloatRegisterWidgetForm(self)
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
        self.splitter_MainMiddle.setStretchFactor(1, 1)
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
        self.tableWidget_Stack.keyPressEvent_original = self.tableWidget_Stack.keyPressEvent
        self.tableWidget_Stack.keyPressEvent = self.tableWidget_Stack_key_press_event

        # Saving the original function because super() doesn't work when we override functions like this
        self.tableWidget_StackTrace.keyPressEvent_original = self.tableWidget_StackTrace.keyPressEvent
        self.tableWidget_StackTrace.keyPressEvent = self.tableWidget_StackTrace_key_press_event

    def initialize_disassemble_view(self) -> None:
        self.tableWidget_Disassemble.setColumnWidth(DISAS_ADDR_COL, 300)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_OPCODES_COL, 150)
        self.tableWidget_Disassemble.setColumnWidth(DISAS_INSTR_COL, 400)

        self.disassemble_last_selected_address_int = 0
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
        self.tableWidget_Disassemble.keyPressEvent_original = self.tableWidget_Disassemble.keyPressEvent
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
        self.hex_model = QHexModel(self.hex_row_count, HEX_VIEW_COL_COUNT)
        self.ascii_model = QAsciiModel(self.hex_row_count, HEX_VIEW_COL_COUNT)
        self.tableView_HexView_Hex.setModel(self.hex_model)
        self.tableView_HexView_Ascii.setModel(self.ascii_model)
        # Adjust cell sizes after setting model to ensure correct size
        self.tableView_HexView_Hex.adjust_cell_size(2)
        self.tableView_HexView_Ascii.adjust_cell_size(1)

        self.widget_HexView.wheelEvent = self.widget_HexView_wheel_event
        # Saving the original function because super() doesn't work when we override functions like this
        self.widget_HexView.keyPressEvent_original = self.widget_HexView.keyPressEvent
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
        self.tableWidget_HexView_Address.verticalHeader().setMinimumSectionSize(
            self.tableView_HexView_Hex.verticalHeader().minimumSectionSize()
        )
        self.tableWidget_HexView_Address.verticalHeader().setDefaultSectionSize(
            self.tableView_HexView_Hex.verticalHeader().defaultSectionSize()
        )
        self.tableWidget_HexView_Address.verticalHeader().setMaximumSectionSize(
            self.tableView_HexView_Hex.verticalHeader().maximumSectionSize()
        )

        self.hex_update_timer = QTimer(self, timeout=self.hex_update_loop)
        self.hex_update_timer.start(200)

    def show_trace_window(self) -> None:
        TraceInstructionsWindowForm(self, prompt_dialog=False)

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

    def set_address(self) -> None:
        if guiutils.check_inferior_running(self):
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        debugcore.set_convenience_variable("pc", current_address)
        self.refresh_disassemble_view()

    def edit_instruction(self) -> None:
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        bytes_aob = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        EditInstructionDialogForm(self, current_address, bytes_aob).exec()

    def nop_instruction(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = safe_str_to_int(current_address, 16)
        if current_address_int == 0:
            return
        array_of_bytes = self.tableWidget_Disassemble.item(selected_row, DISAS_OPCODES_COL).text()
        debugcore.nop_instruction(current_address_int, len(array_of_bytes.split()))
        self.refresh_disassemble_view()

    def toggle_breakpoint(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = safe_str_to_int(current_address, 16)
        if current_address_int == 0:
            return
        breakpoints = debugcore.get_breakpoints_in_range(current_address_int)
        if breakpoints:
            for breakpoint in breakpoints:
                debugcore.delete_breakpoint(safe_int_cast(breakpoint.number))
        else:
            if not debugcore.add_breakpoint(current_address):
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(current_address))
        self.refresh_disassemble_view()

    def toggle_watchpoint(
        self, address: int, length: int, watchpoint_type: int = typedefs.WATCHPOINT_TYPE.BOTH
    ) -> None:
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(address, length)
        if not breakpoints:
            created_watchpoints = debugcore.add_watchpoint(hex(address), length, watchpoint_type)
            if not created_watchpoints:
                QMessageBox.information(self, tr.ERROR, tr.WATCHPOINT_FAILED.format(hex(address)))
        else:
            for bp in breakpoints:
                debugcore.delete_breakpoint(safe_int_cast(bp.number))
        self.refresh_hex_view()

    def label_HexView_Information_context_menu_event(self, event: QContextMenuEvent) -> None:
        if debugcore.currentpid == -1:
            return

        def copy_to_clipboard() -> None:
            app.clipboard().setText(self.label_HexView_Information.text())

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
        HexEditDialogForm(self, self.hex_selection_address_begin, self.get_hex_selection_length()).exec()
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
        vt = typedefs.ValueType(typedefs.VALUE_INDEX.AOB, self.get_hex_selection_length())
        address_dialog = ManualAddressDialogForm(self, address=hex(self.hex_selection_address_begin), value_type=vt)
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
        app.clipboard().setText(display_text)

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
                self.label_HexView_Information.setText(
                    tr.REGION_INFO.format(info.perms, hex(info.start), hex(info.end), info.file_name)
                )
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

    # offset can also be an address as hex str
    # returns True if the given expression is disassembled correctly, False if not
    def disassemble_expression(self, expression: str, offset: str = "+200", append_history: bool = True) -> bool | None:
        if debugcore.currentpid == -1:
            return
        disas_data = debugcore.disassemble(expression, offset)
        if not disas_data:
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.EXPRESSION_ACCESS_ERROR.format(expression))
            return False
        program_counter = debugcore.examine_expression("$pc").address
        program_counter_int = int(program_counter, 16) if program_counter else None
        row_color = {}
        breakpoint_info = debugcore.get_breakpoint_info()

        # TODO: Change this nonsense when the huge refactorization happens
        current_first_address = utils.extract_hex_address(disas_data[0][0])  # address of first list entry
        try:
            previous_first_address = utils.extract_hex_address(
                self.tableWidget_Disassemble.item(0, DISAS_ADDR_COL).text()
            )
        except AttributeError:
            previous_first_address = current_first_address

        self.tableWidget_Disassemble.setRowCount(0)
        self.tableWidget_Disassemble.setRowCount(len(disas_data))
        jmp_dict, call_dict = debugcore.get_dissect_code_data(False, True, True)
        try:
            for row, (address_info, bytes_aob, instruction) in enumerate(disas_data):
                comment = ""
                current_address_str = utils.extract_hex_address(address_info)
                current_address = safe_str_to_int(current_address_str, 16)
                jmp_ref_exists = False
                call_ref_exists = False
                try:
                    jmp_referrers = jmp_dict[current_address_str]
                    jmp_ref_exists = True
                except KeyError:
                    pass
                try:
                    call_referrers = call_dict[current_address_str]
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
                    try:
                        row_color[row].append(REF_COLOR)
                    except KeyError:
                        row_color[row] = [REF_COLOR]
                    real_ref_count = 0
                    if jmp_ref_exists:
                        real_ref_count += len(jmp_referrers)
                    if call_ref_exists:
                        real_ref_count += len(call_referrers)
                    address_info = "{" + str(real_ref_count) + "}" + address_info
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
                    int_breakpoint_address = safe_str_to_int(breakpoint.address, 16)
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
                if current_address == self.disassemble_last_selected_address_int:
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
        self.handle_colors(row_color)

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
                continue
            if REF_COLOR in current_row:
                self.set_row_color(row, REF_COLOR)

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
            app.processEvents()
            time1 = time()
            logger.debug(f"Updated memory view in: {str(time1 - time0)}")
        finally:
            self.updating_memoryview = False

    def on_process_running(self) -> None:
        self.setWindowTitle(tr.MV_RUNNING)
        self.pushButton_ShowFloatRegisters.setEnabled(False)

    def add_breakpoint_condition(self, int_address: int, length: int = 1) -> None:
        if debugcore.currentpid == -1:
            return
        breakpoints = debugcore.get_breakpoints_in_range(int_address, length)
        if breakpoints:
            condition_line_edit_text = breakpoints[0].condition
        else:
            condition_line_edit_text = ""
        items = [(tr.ENTER_BP_CONDITION, condition_line_edit_text)]
        condition_dialog = utilwidgets.InputDialog(self, items, Qt.AlignmentFlag.AlignLeft)
        if condition_dialog.exec():
            condition = condition_dialog.get_values()[0]
            for bp in breakpoints:
                if not debugcore.modify_breakpoint(
                    safe_int_cast(bp.number), typedefs.BREAKPOINT_MODIFY.CONDITION, condition
                ):
                    QMessageBox.information(app.focusWidget(), tr.ERROR, tr.BP_CONDITION_FAILED.format(bp.address))

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
            app.clipboard().setText(item.text())

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
            actions = typedefs.KeyboardModifiersTupleDict(
                [(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stack)]
            )
        else:
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_hex_address(current_address_text)

            actions = typedefs.KeyboardModifiersTupleDict(
                [
                    (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stack),
                    (
                        QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                        lambda: self.disassemble_expression(current_address),
                    ),
                    (
                        QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
                        lambda: self.hex_dump_address(safe_str_to_int(current_address, 16)),
                    ),
                ]
            )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Stack.keyPressEvent_original(event)

    def tableWidget_Stack_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            item = self.tableWidget_Stack.item(row, column)
            if item is None:
                return
            app.clipboard().setText(item.text())

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
            show_in_hex: lambda: self.hex_dump_address(safe_str_to_int(current_address, 16)),
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
            self.hex_dump_address(safe_str_to_int(current_address, 16))
        else:
            points_to_text = self.tableWidget_Stack.item(selected_row, STACK_POINTS_TO_COL).text()
            current_address_text = self.tableWidget_Stack.item(selected_row, STACK_VALUE_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            if points_to_text.startswith("(str)"):
                self.hex_dump_address(safe_str_to_int(current_address, 16))
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
            self.hex_dump_address(safe_str_to_int(current_address, 16))

    def tableWidget_StackTrace_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        actions = typedefs.KeyboardModifiersTupleDict(
            [(QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.update_stacktrace)]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_StackTrace.keyPressEvent_original(event)

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
            current_address = utils.extract_hex_address(
                self.tableWidget_Disassemble.item(current_row, DISAS_ADDR_COL).text()
            )
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
        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G), self.exec_hex_view_go_to_dialog),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D),
                    lambda: self.disassemble_expression(hex(self.hex_selection_address_begin)),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_A),
                    self.exec_hex_view_add_address_dialog,
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_C), self.copy_hex_view_selection),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_hex_view),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.hex_view_scroll_up),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.hex_view_scroll_down),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.widget_HexView.keyPressEvent_original(event)

    def tableWidget_Disassemble_key_press_event(self, event: QKeyEvent) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = safe_str_to_int(current_address, 16)

        actions = typedefs.KeyboardModifiersTupleDict(
            [
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Space),
                    lambda: self.follow_instruction(selected_row),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_E),
                    lambda: self.exec_examine_referrers_widget(current_address_text),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_G),
                    self.exec_disassemble_go_to_dialog,
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_H),
                    lambda: self.hex_dump_address(current_address_int),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_B),
                    lambda: self.bookmark_address(current_address_int),
                ),
                (QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_D), self.dissect_current_region),
                (
                    QKeyCombination(Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_T),
                    self.exec_trace_instructions_dialog,
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_R), self.refresh_disassemble_view),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Down),
                    lambda: self.disassemble_check_viewport("next", 1),
                ),
                (
                    QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_Up),
                    lambda: self.disassemble_check_viewport("previous", 1),
                ),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageUp), self.disassemble_scroll_up),
                (QKeyCombination(Qt.KeyboardModifier.NoModifier, Qt.Key.Key_PageDown), self.disassemble_scroll_down),
            ]
        )
        try:
            actions[QKeyCombination(event.modifiers(), Qt.Key(event.key()))]()
        except KeyError:
            pass
        self.tableWidget_Disassemble.keyPressEvent_original(event)

    def tableWidget_Disassemble_item_double_clicked(self, index: QTableWidgetItem) -> None:
        if debugcore.currentpid == -1:
            return
        if index.column() == DISAS_COMMENT_COL:
            selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
            if selected_row == -1:
                return
            current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
            current_address = safe_str_to_int(utils.extract_hex_address(current_address_text), 16)
            if current_address in self.session.pct_bookmarks:
                self.change_bookmark_comment(current_address)
            else:
                self.bookmark_address(current_address)

    def tableWidget_Disassemble_item_selection_changed(self) -> None:
        if debugcore.currentpid == -1:
            return
        try:
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
        address = utils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text()
        )
        if address:
            self.disassemble_expression(address)

    def disassemble_go_back(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.tableWidget_Disassemble.travel_history:
            last_location = self.tableWidget_Disassemble.travel_history[-1]
            self.disassemble_expression(last_location, append_history=False)
            self.tableWidget_Disassemble.travel_history.pop()

    def tableWidget_Disassemble_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            item = self.tableWidget_Disassemble.item(row, column)
            if item is None:
                return
            app.clipboard().setText(item.text())

        def copy_all_columns(row: int) -> None:
            copied_string = ""
            for column in range(self.tableWidget_Disassemble.columnCount()):
                item = self.tableWidget_Disassemble.item(row, column)
                if item is not None:
                    copied_string += item.text() + "\t"
            app.clipboard().setText(copied_string)

        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = safe_str_to_int(current_address, 16)

        menu = QMenu()
        go_to = menu.addAction(f"{tr.GO_TO_EXPRESSION}[Ctrl+G]")
        back = menu.addAction(tr.BACK)
        show_in_hex_view = menu.addAction(f"{tr.HEXVIEW_ADDRESS}[Ctrl+H]")
        menu.addSeparator()
        followable = utils.instruction_follow_address(
            self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text()
        )
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
            copy_address: lambda: copy_to_clipboard(selected_row, DISAS_ADDR_COL),
            copy_bytes: lambda: copy_to_clipboard(selected_row, DISAS_OPCODES_COL),
            copy_instr: lambda: copy_to_clipboard(selected_row, DISAS_INSTR_COL),
            copy_comment: lambda: copy_to_clipboard(selected_row, DISAS_COMMENT_COL),
            copy_all: lambda: copy_all_columns(selected_row),
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
        dissect_code_dialog = DissectCodeDialogForm(self, safe_str_to_int(current_address, 16))
        dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
        dissect_code_dialog.exec()
        self.refresh_disassemble_view()

    def exec_examine_referrers_widget(self, current_address_text: str) -> None:
        if debugcore.currentpid == -1:
            return
        if not guiutils.contains_reference_mark(current_address_text):
            return
        current_address = utils.extract_hex_address(current_address_text)
        current_address_int = safe_str_to_int(current_address, 16)
        examine_referrers_widget = ExamineReferrersWidgetForm(self, current_address_int)
        examine_referrers_widget.show()

    def exec_trace_instructions_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        if not self.tableWidget_Disassemble.rowCount():
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            selected_row = 0
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        TraceInstructionsWindowForm(self, current_address)

    def exec_track_breakpoint_dialog(self) -> None:
        if debugcore.currentpid == -1:
            return
        selected_row = guiutils.get_current_row(self.tableWidget_Disassemble)
        if selected_row == -1:
            return
        current_address_text = self.tableWidget_Disassemble.item(selected_row, DISAS_ADDR_COL).text()
        current_address = utils.extract_hex_address(current_address_text)
        current_instruction = self.tableWidget_Disassemble.item(selected_row, DISAS_INSTR_COL).text()
        register_expression_dialog = utilwidgets.InputDialog(self, [(tr.ENTER_TRACK_BP_EXPRESSION, "")])
        if register_expression_dialog.exec():
            exp = register_expression_dialog.get_values()[0]
            TrackBreakpointWidgetForm(self, current_address, current_instruction, exp)

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
            QMessageBox.information(app.focusWidget(), tr.ERROR, tr.ALREADY_BOOKMARKED)
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
            self.breakpoint_widget = BreakpointInfoWidgetForm(self)
        else:
            self.breakpoint_widget.refresh()
        self.breakpoint_widget.show()
        self.breakpoint_widget.activateWindow()

    def actionFunctions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.functions_info_widget is None:
            self.functions_info_widget = FunctionsInfoWidgetForm(self)
        self.functions_info_widget.show()

    def actionGDB_Log_File_triggered(self) -> None:
        log_file_widget = LogFileWidgetForm(self)
        log_file_widget.showMaximized()

    def actionMemory_Regions_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        if self.memory_regions_widget is None:
            self.memory_regions_widget = MemoryRegionsWidgetForm(self)
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
        ref_str_widget = ReferencedStringsWidgetForm(self)
        ref_str_widget.show()

    def actionReferenced_Calls_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        ref_call_widget = ReferencedCallsWidgetForm(self)
        ref_call_widget.show()

    def actionInject_so_file_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr.SELECT_SO_FILE, os.path.expanduser("~"), tr.SHARED_OBJECT_TYPE
        )
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
            success, hmod = debugcore.inject_dll(file_path)
            if success:
                QMessageBox.information(self, tr.SUCCESS, tr.DLL_INJECTED.format(hex(hmod)))
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
        start_address = safe_str_to_int(self.disassemble_currently_displayed_address, 16)
        end_address = start_address + 0x30000
        region_info = utils.get_region_info(debugcore.currentpid, start_address)
        if region_info:
            start_address = region_info.start
            end_address = region_info.end
        search_instr_widget = SearchInstructionsWidgetForm(self, hex(start_address), hex(end_address))
        search_instr_widget.show()

    def actionDissect_Code_triggered(self) -> None:
        if debugcore.currentpid == -1:
            return
        dissect_code_dialog = DissectCodeDialogForm(self)
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
        mono_dialog.add_to_table_requested.connect(
            lambda description, address: self.parent().add_entry_to_addresstable(description, address)
        )
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


class FloatRegisterWidgetForm(QTabWidget, FloatRegisterWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_FPU.itemDoubleClicked.connect(self.set_register)
        self.tableWidget_XMM.itemDoubleClicked.connect(self.set_register)

    def update_registers(self) -> None:
        float_registers = list(debugcore.read_float_registers().items())
        st_registers = float_registers[:8]
        xmm_registers = float_registers[8:]
        self.tableWidget_FPU.setRowCount(len(st_registers))
        self.tableWidget_XMM.setRowCount(len(xmm_registers))
        for row, (name, value) in enumerate(st_registers):
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(name))
            self.tableWidget_FPU.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(value))
        for row, (name, value) in enumerate(xmm_registers):
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_NAME_COL, QTableWidgetItem(name))
            self.tableWidget_XMM.setItem(row, FLOAT_REGISTERS_VALUE_COL, QTableWidgetItem(value))

    def set_register(self, index: QTableWidgetItem) -> None:
        if guiutils.check_inferior_running(self):
            return
        current_row = index.row()
        if self.currentWidget() == self.FPU:
            current_table_widget = self.tableWidget_FPU
        elif self.currentWidget() == self.XMM:
            current_table_widget = self.tableWidget_XMM
        else:
            raise Exception("Current widget is invalid: " + str(self.currentWidget().objectName()))
        current_register = current_table_widget.item(current_row, FLOAT_REGISTERS_NAME_COL).text()
        current_value = current_table_widget.item(current_row, FLOAT_REGISTERS_VALUE_COL).text()
        label_text = tr.ENTER_REGISTER_VALUE.format(current_register.upper())
        register_dialog = utilwidgets.InputDialog(self, [(label_text, current_value)])
        if register_dialog.exec():
            if guiutils.check_inferior_running(self):
                return
            if self.currentWidget() == self.XMM:
                current_register += ".v4_float"
            debugcore.set_convenience_variable(current_register, register_dialog.get_values()[0])
            self.update_registers()


class StackTraceInfoWidgetForm(QWidget, StackTraceInfoWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.listWidget_ReturnAddresses.currentRowChanged.connect(self.update_frame_info)

    def update_stacktrace(self) -> None:
        self.listWidget_ReturnAddresses.clear()
        self.textBrowser_Info.clear()
        error_message = guiutils.check_inferior_running(self, show_message=False)
        if error_message:
            self.textBrowser_Info.setText(error_message)
            return
        return_addresses = debugcore.get_stack_frame_return_addresses()
        self.listWidget_ReturnAddresses.addItems(return_addresses)

    def update_frame_info(self, index: int) -> None:
        self.textBrowser_Info.clear()
        error_message = guiutils.check_inferior_running(self, show_message=False)
        if error_message:
            self.textBrowser_Info.setText(error_message)
            return
        frame_info = debugcore.get_stack_frame_info(index)
        self.textBrowser_Info.setText(frame_info)


class BreakpointInfoWidgetForm(QTabWidget, BreakpointInfoWidget):
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
            breakpoint_num = safe_int_cast(self.tableWidget_BreakpointInfo.item(selected_row, BREAK_NUM_COL).text())
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
            bp_num = safe_int_cast(self.tableWidget_BreakpointInfo.item(selected_row, BREAK_NUM_COL).text())
            current_address_text = self.tableWidget_BreakpointInfo.item(selected_row, BREAK_ADDR_COL).text()
            current_address = utils.extract_hex_address(current_address_text)
            if current_address:
                current_address_int = safe_str_to_int(current_address, 16)
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
        current_address_int = safe_str_to_int(current_address, 16)

        if index.column() == BREAK_COND_COL:
            self.parent().add_breakpoint_condition(current_address_int)
            self.refresh_all()
        else:
            current_breakpoint_type = self.tableWidget_BreakpointInfo.item(index.row(), BREAK_TYPE_COL).text()
            if "breakpoint" in current_breakpoint_type:
                self.parent().disassemble_expression(current_address)
            else:
                self.parent().hex_dump_address(current_address_int)


class TrackWatchpointWidgetForm(QWidget, TrackWatchpointWidget):
    def __init__(self, parent: QWidget, address: str, length: int, watchpoint_type: int) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.update_timer = QTimer(self, timeout=self.update_list)
        self.stopped = False
        self.address = address
        self.info = {}
        self.last_selected_row = 0
        if watchpoint_type == typedefs.WATCHPOINT_TYPE.WRITE_ONLY:
            string = tr.INSTR_WRITING_TO.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.READ_ONLY:
            string = tr.INSTR_READING_FROM.format(address)
        elif watchpoint_type == typedefs.WATCHPOINT_TYPE.BOTH:
            string = tr.INSTR_ACCESSING_TO.format(address)
        else:
            raise Exception("Watchpoint type is invalid: " + str(watchpoint_type))
        self.setWindowTitle(string)
        guiutils.center_to_parent(self)  # Called before the QMessageBox to center its position properly
        self.breakpoints = debugcore.track_watchpoint(address, length, watchpoint_type)
        if not self.breakpoints:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_WATCHPOINT_FAILED.format(address))
            self.close()
            return
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.pushButton_Refresh.clicked.connect(self.update_list)
        self.tableWidget_Addresses.itemDoubleClicked.connect(self.tableWidget_Addresses_item_double_clicked)
        self.tableWidget_Addresses.selectionModel().currentChanged.connect(self.tableWidget_Addresses_current_changed)
        self.update_timer.start(100)
        self.show()

    def update_list(self) -> None:
        info = debugcore.get_track_watchpoint_info(self.breakpoints)
        if not info or self.info == info:
            return
        self.info = info
        self.tableWidget_Addresses.setRowCount(0)
        self.tableWidget_Addresses.setRowCount(len(info))
        for row, key in enumerate(info):
            self.tableWidget_Addresses.setItem(row, TRACK_WATCHPOINT_COUNT_COL, QTableWidgetItem(str(info[key][0])))
            self.tableWidget_Addresses.setItem(row, TRACK_WATCHPOINT_ADDR_COL, QTableWidgetItem(info[key][1]))
        guiutils.resize_to_contents(self.tableWidget_Addresses)
        self.tableWidget_Addresses.selectRow(self.last_selected_row)

    def tableWidget_Addresses_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

        info = self.info
        key_list = list(info)
        if not key_list:
            return
        self.last_selected_row = min(self.last_selected_row, len(key_list) - 1)
        key = key_list[self.last_selected_row]
        self.textBrowser_Info.clear()
        for item in info[key][2]:
            self.textBrowser_Info.append(item + "=" + str(info[key][2][item]))
        self.textBrowser_Info.append(" ")
        for item in info[key][3]:
            self.textBrowser_Info.append(item + "=" + info[key][3][item])
        self.textBrowser_Info.verticalScrollBar().setValue(self.textBrowser_Info.verticalScrollBar().minimum())
        self.textBrowser_Disassemble.setPlainText(info[key][4])

    def tableWidget_Addresses_item_double_clicked(self, index: QTableWidgetItem) -> None:
        self.parent().memory_view_window.disassemble_expression(
            self.tableWidget_Addresses.item(index.row(), TRACK_WATCHPOINT_ADDR_COL).text()
        )
        self.parent().memory_view_window.show()
        self.parent().memory_view_window.activateWindow()

    def pushButton_Stop_clicked(self) -> None:
        if self.stopped:
            self.close()
            return
        # Internal chained breakpoints check will delete the rest from self.breakpoints
        if not debugcore.delete_breakpoint(safe_int_cast(self.breakpoints[0])):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_WATCHPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.update_timer.stop()
        if self.breakpoints:
            if not self.stopped:
                # Internal chained breakpoints check will delete the rest from self.breakpoints
                debugcore.delete_breakpoint(safe_int_cast(self.breakpoints[0]))
            watchpoint_file = utils.get_track_watchpoint_file(debugcore.currentpid, self.breakpoints)
            if os.path.exists(watchpoint_file):
                os.remove(watchpoint_file)
        super().closeEvent(event)


class TrackBreakpointWidgetForm(QWidget, TrackBreakpointWidget):
    def __init__(self, parent: QWidget, address: str, instruction: str, register_expressions: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.update_list_timer = QTimer(self, timeout=self.update_list)
        self.update_values_timer = QTimer(self, timeout=self.update_values)
        self.stopped = False
        self.address = address
        self.info = {}
        self.last_selected_row = 0
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle(tr.ACCESSED_BY_INSTRUCTION.format(instruction))
        guiutils.center_to_parent(self)  # Called before the QMessageBox to center its position properly
        self.breakpoint = debugcore.track_breakpoint(address, register_expressions)
        if not self.breakpoint:
            QMessageBox.information(self, tr.ERROR, tr.TRACK_BREAKPOINT_FAILED.format(address))
            self.close()
            return
        guiutils.fill_value_combobox(self.comboBox_ValueType)
        self.pushButton_Stop.clicked.connect(self.pushButton_Stop_clicked)
        self.tableWidget_TrackInfo.itemDoubleClicked.connect(self.tableWidget_TrackInfo_item_double_clicked)
        self.tableWidget_TrackInfo.selectionModel().currentChanged.connect(self.tableWidget_TrackInfo_current_changed)
        self.comboBox_ValueType.currentIndexChanged.connect(self.update_values)
        self.update_list_timer.start(100)
        self.update_values_timer.start(500)
        self.parent().refresh_disassemble_view()
        self.show()

    def update_list(self) -> None:
        info = debugcore.get_track_breakpoint_info(self.breakpoint)
        if not info:
            return
        if info == self.info:
            return
        self.info = info
        self.tableWidget_TrackInfo.setRowCount(0)
        row = 0
        for register_expression in info:
            for address in info[register_expression]:
                self.tableWidget_TrackInfo.setRowCount(row + 1)
                self.tableWidget_TrackInfo.setItem(
                    row, TRACK_BREAKPOINT_COUNT_COL, QTableWidgetItem(str(info[register_expression][address]))
                )
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_ADDR_COL, QTableWidgetItem(address))
                self.tableWidget_TrackInfo.setItem(
                    row, TRACK_BREAKPOINT_SOURCE_COL, QTableWidgetItem("[" + register_expression + "]")
                )
                row += 1
        self.update_values()

    def update_values(self) -> None:
        with debugcore.memory_handle() as mem_handle:
            value_type = self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole)
            for row in range(self.tableWidget_TrackInfo.rowCount()):
                address = self.tableWidget_TrackInfo.item(row, TRACK_BREAKPOINT_ADDR_COL).text()
                value = debugcore.read_memory(address, value_type, 10, mem_handle=mem_handle)
                value = "" if value is None else str(value)
                self.tableWidget_TrackInfo.setItem(row, TRACK_BREAKPOINT_VALUE_COL, QTableWidgetItem(value))
        guiutils.resize_to_contents(self.tableWidget_TrackInfo)
        self.tableWidget_TrackInfo.selectRow(self.last_selected_row)

    def tableWidget_TrackInfo_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        current_row = QModelIndex_current.row()
        if current_row >= 0:
            self.last_selected_row = current_row

    def tableWidget_TrackInfo_item_double_clicked(self, index: QTableWidgetItem) -> None:
        address = self.tableWidget_TrackInfo.item(index.row(), TRACK_BREAKPOINT_ADDR_COL).text()
        vt = typedefs.ValueType(self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole))
        self.parent().parent().add_entry_to_addresstable(tr.ACCESSED_BY.format(self.address), address, vt)
        self.parent().parent().update_address_table()

    def pushButton_Stop_clicked(self) -> None:
        if self.stopped:
            self.close()
            return
        if not debugcore.delete_breakpoint(safe_int_cast(self.breakpoint)):
            QMessageBox.information(self, tr.ERROR, tr.DELETE_BREAKPOINT_FAILED.format(self.address))
            return
        self.stopped = True
        self.pushButton_Stop.setText(tr.CLOSE)
        self.parent().refresh_disassemble_view()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.update_list_timer.stop()
        self.update_values_timer.stop()
        if self.breakpoint:
            if not self.stopped:
                debugcore.delete_breakpoint(safe_int_cast(self.breakpoint))
            breakpoint_file = utils.get_track_breakpoint_file(debugcore.currentpid, self.breakpoint)
            if os.path.exists(breakpoint_file):
                os.remove(breakpoint_file)
        self.parent().refresh_disassemble_view()
        super().closeEvent(event)


class TraceInstructionsPromptDialogForm(QDialog, TraceInstructionsPromptDialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.center_to_parent(self)

    def get_values(self) -> tuple[int, str, str, int, bool, bool]:
        try:
            max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        except ValueError:
            max_trace_count = 0
        trigger_condition = self.lineEdit_TriggerCondition.text()
        stop_condition = self.lineEdit_StopCondition.text()
        if self.checkBox_StepOver.isChecked():
            step_mode = typedefs.STEP_MODE.STEP_OVER
        else:
            step_mode = typedefs.STEP_MODE.SINGLE_STEP
        stop_after_trace = self.checkBox_StopAfterTrace.isChecked()
        collect_registers = self.checkBox_CollectRegisters.isChecked()
        return max_trace_count, trigger_condition, stop_condition, step_mode, stop_after_trace, collect_registers

    def accept(self) -> None:
        try:
            max_trace_count = int(self.lineEdit_MaxTraceCount.text())
        except ValueError:
            max_trace_count = 0
        if max_trace_count >= 1:
            super().accept()
        else:
            QMessageBox.information(self, tr.ERROR, tr.MAX_TRACE_COUNT_ASSERT_GT.format(1))


class TraceInstructionsWaitWidgetForm(QWidget, TraceInstructionsWaitWidget):
    widget_closed = pyqtSignal()

    def __init__(self, parent: QWidget, address: str, tracer: debugcore.Tracer) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.status_to_text = {
            typedefs.TRACE_STATUS.IDLE: tr.WAITING_FOR_BREAKPOINT,
            typedefs.TRACE_STATUS.FINISHED: tr.TRACING_COMPLETED,
        }
        self.setWindowFlags(Qt.WindowType.Window)
        self.address = address
        self.tracer = tracer
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/TraceInstructionsWaitWidget/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(215, 100))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.pushButton_Cancel.clicked.connect(self.close)
        tracer_thread = guitypedefs.Worker(tracer.tracer_loop)
        tracer_thread.signals.finished.connect(self.close)
        states.threadpool.start(tracer_thread)
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(50)
        self.status_timer.timeout.connect(self.change_status)
        self.status_timer.start()
        guiutils.center_to_parent(self)

    def change_status(self) -> None:
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.label_StatusText.setText(f"{self.tracer.current_trace_count} / {self.tracer.max_trace_count}")
        else:
            self.label_StatusText.setText(self.status_to_text[self.tracer.trace_status])
        app.processEvents()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.status_timer.stop()
        self.label_StatusText.setText(tr.TRACING_COMPLETED)
        self.pushButton_Cancel.setVisible(False)
        self.adjustSize()
        app.processEvents()
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.tracer.cancel_trace()
            while self.tracer.trace_status != typedefs.TRACE_STATUS.FINISHED:
                sleep(0.1)
                app.processEvents()
        self.widget_closed.emit()
        super().closeEvent(event)


class TraceInstructionsWindowForm(QMainWindow, TraceInstructionsWindow):
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
        prompt_dialog = TraceInstructionsPromptDialogForm(self)
        if prompt_dialog.exec():
            params = (address,) + prompt_dialog.get_values()
            breakpoint = self.tracer.set_breakpoint(*params)
            if not breakpoint:
                QMessageBox.information(self, tr.ERROR, tr.BREAKPOINT_FAILED.format(address))
                self.close()
                return
            self.showMaximized()
            self.wait_dialog = TraceInstructionsWaitWidgetForm(self, address, self.tracer)
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
            self.textBrowser_RegisterInfo.verticalScrollBar().setValue(
                self.textBrowser_RegisterInfo.verticalScrollBar().minimum()
            )

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
        with guiutils.save_dialog_as_user(
            self, tr.SAVE_TRACE_FILE, os.path.expanduser("~"), tr.FILE_TYPES_TRACE, "trace"
        ) as file_path:
            if file_path and not utils.save_file(self.tracer.trace_data, file_path):
                QMessageBox.information(self, tr.ERROR, tr.FILE_SAVE_ERROR)

    def load_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr.OPEN_TRACE_FILE, os.path.expanduser("~"), tr.FILE_TYPES_TRACE
        )
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


class FunctionsInfoWidgetForm(QWidget, FunctionsInfoWidget):
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
        self.loading_dialog = LoadingDialogForm(self)
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
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_ADDR_COL, address_item)
            self.tableWidget_SymbolInfo.setItem(row, FUNCTIONS_INFO_SYMBOL_COL, QTableWidgetItem(item[1]))
        self.tableWidget_SymbolInfo.setSortingEnabled(True)
        guiutils.resize_to_contents(self.tableWidget_SymbolInfo)

    def tableWidget_SymbolInfo_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        self.textBrowser_AddressInfo.clear()
        current_row = QModelIndex_current.row()
        if current_row < 0:
            return
        address = self.tableWidget_SymbolInfo.item(current_row, FUNCTIONS_INFO_ADDR_COL).text()
        if utils.extract_hex_address(address):
            symbol = self.tableWidget_SymbolInfo.item(current_row, FUNCTIONS_INFO_SYMBOL_COL).text()
            for item in utils.split_symbol(symbol):
                info = debugcore.get_symbol_info(item)
                self.textBrowser_AddressInfo.append(info)
        else:
            self.textBrowser_AddressInfo.append(tr.DEFINED_SYMBOL)

    def tableWidget_SymbolInfo_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            app.clipboard().setText(self.tableWidget_SymbolInfo.item(row, column).text())

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
            copy_address: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_ADDR_COL),
            copy_symbol: lambda: copy_to_clipboard(selected_row, FUNCTIONS_INFO_SYMBOL_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def tableWidget_SymbolInfo_item_double_clicked(self, index: QTableWidgetItem) -> None:
        address = self.tableWidget_SymbolInfo.item(index.row(), FUNCTIONS_INFO_ADDR_COL).text()
        if address == tr.DEFINED:
            return
        self.parent().disassemble_expression(address)

    def pushButton_Help_clicked(self) -> None:
        utilwidgets.InputDialog(self, tr.FUNCTIONS_INFO_HELPER, Qt.AlignmentFlag.AlignLeft, False).exec()


class EditInstructionDialogForm(QDialog, EditInstructionDialog):
    def __init__(self, parent: QWidget, address: str, bytes_aob: str) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.orig_bytes = bytes_aob
        self.lineEdit_Address.setText(address)
        self.lineEdit_Bytes.setText(bytes_aob)
        self.lineEdit_Bytes_text_edited()
        self.lineEdit_Bytes.textEdited.connect(self.lineEdit_Bytes_text_edited)
        self.lineEdit_Instruction.textEdited.connect(self.lineEdit_Instruction_text_edited)
        guiutils.center_to_parent(self)

    def set_valid(self, valid: bool) -> None:
        if valid:
            self.is_valid = True
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        else:
            self.is_valid = False
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def lineEdit_Bytes_text_edited(self) -> None:
        bytes_aob = self.lineEdit_Bytes.text()
        if utils.parse_string(bytes_aob, typedefs.VALUE_INDEX.AOB):
            address = safe_str_to_int(self.lineEdit_Address.text(), 0)
            instruction = utils.disassemble(bytes_aob, address, debugcore.inferior_arch)
            if instruction:
                self.set_valid(True)
                self.lineEdit_Instruction.setText(instruction)
                return
        self.set_valid(False)
        self.lineEdit_Instruction.setText("??")

    def lineEdit_Instruction_text_edited(self) -> None:
        instruction = self.lineEdit_Instruction.text()
        address = safe_str_to_int(self.lineEdit_Address.text(), 0)
        result = utils.assemble(instruction, address, debugcore.inferior_arch)
        if result:
            byte_list = result[0]
            self.set_valid(True)
            bytes_str = " ".join([format(num, "02x") for num in byte_list])
            self.lineEdit_Bytes.setText(bytes_str)
        else:
            self.set_valid(False)
            self.lineEdit_Bytes.setText("??")

    def accept(self) -> None:
        if not self.is_valid:
            return

        # No need to check for validity since address is not editable and instruction is checked in text_edited
        address = safe_str_to_int(self.lineEdit_Address.text(), 0)
        bytes_aob = self.lineEdit_Bytes.text()
        if bytes_aob != self.orig_bytes:
            new_length = len(bytes_aob.split())
            old_length = len(self.orig_bytes.split())
            if new_length < old_length:
                bytes_aob += " 90" * (old_length - new_length)  # Append NOPs if we are short on bytes
            elif new_length > old_length:
                if not utilwidgets.InputDialog(self, tr.NEW_INSTR.format(new_length, old_length)).exec():
                    return
            debugcore.modify_instruction(address, bytes_aob)
        self.parent().refresh_hex_view()
        self.parent().refresh_disassemble_view()
        super().accept()


class HexEditDialogForm(QDialog, HexEditDialog):
    def __init__(self, parent: QWidget, address: int, length: int = 20) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.lineEdit_Length.setValidator(QHexValidator(999, self))
        self.lineEdit_Address.setText(hex(address))
        self.lineEdit_Length.setText(str(length))
        self.refresh_view()
        self.lineEdit_AsciiView.selectionChanged.connect(self.lineEdit_AsciiView_selection_changed)
        guiutils.center_to_parent(self)

        # TODO: Implement this
        # self.lineEdit_HexView.selectionChanged.connect(self.lineEdit_HexView_selection_changed)
        self.lineEdit_HexView.textEdited.connect(self.lineEdit_HexView_text_edited)
        self.lineEdit_AsciiView.textEdited.connect(self.lineEdit_AsciiView_text_edited)
        self.pushButton_Refresh.pressed.connect(self.refresh_view)
        self.lineEdit_Address.textChanged.connect(self.refresh_view)
        self.lineEdit_Length.textChanged.connect(self.refresh_view)

    def lineEdit_AsciiView_selection_changed(self) -> None:
        length = len(utils.str_to_aob(self.lineEdit_AsciiView.selectedText(), "utf-8"))
        start_index = self.lineEdit_AsciiView.selectionStart()
        start_index = len(utils.str_to_aob(self.lineEdit_AsciiView.text()[0:start_index], "utf-8"))
        if start_index > 0:
            start_index += 1
        self.lineEdit_HexView.deselect()
        self.lineEdit_HexView.setSelection(start_index, length)

    def lineEdit_HexView_selection_changed(self) -> None:
        # TODO: Implement this
        logger.debug("TODO: Implement selectionChanged signal of lineEdit_HexView")
        raise NotImplementedError

    def lineEdit_HexView_text_edited(self) -> None:
        aob_string = self.lineEdit_HexView.text()
        if not utils.parse_string(aob_string, typedefs.VALUE_INDEX.AOB):
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")
            return
        aob_array = aob_string.split()
        try:
            self.lineEdit_AsciiView.setText(utils.aob_to_str(aob_array, "utf-8", replace_unprintable=False))
            self.lineEdit_HexView.setStyleSheet("")  # This should set background color back to QT default
        except ValueError:
            self.lineEdit_HexView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def lineEdit_AsciiView_text_edited(self) -> None:
        ascii_str = self.lineEdit_AsciiView.text()
        try:
            self.lineEdit_HexView.setText(utils.str_to_aob(ascii_str, "utf-8"))
            self.lineEdit_AsciiView.setStyleSheet("")
        except ValueError:
            self.lineEdit_AsciiView.setStyleSheet("QLineEdit {background-color: rgba(255, 0, 0, 96);}")

    def refresh_view(self) -> None:
        self.lineEdit_AsciiView.clear()
        self.lineEdit_HexView.clear()
        address = debugcore.examine_expression(self.lineEdit_Address.text()).address
        if not address:
            return
        length = self.lineEdit_Length.text()
        try:
            length = int(length, 0)
            address = int(address, 0)
        except ValueError:
            return
        aob_array = debugcore.hex_dump(address, length)
        ascii_str = utils.aob_to_str(aob_array, "utf-8", replace_unprintable=False)
        self.lineEdit_AsciiView.setText(ascii_str)
        self.lineEdit_HexView.setText(" ".join(aob_array))

    def accept(self) -> None:
        expression = self.lineEdit_Address.text()
        address = debugcore.examine_expression(expression).address
        if not address:
            QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_EXPRESSION.format(expression))
            return
        value = self.lineEdit_HexView.text()
        parsed = utils.parse_string(value, typedefs.VALUE_INDEX.AOB)
        if parsed is None:
            QMessageBox.information(self, tr.ERROR, tr.PARSE_ERROR)
            return
        debugcore.write_memory(address, typedefs.VALUE_INDEX.AOB, value)
        super().accept()


class LogFileWidgetForm(QWidget, LogFileWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.contents = ""
        self.refresh_contents()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(500)
        self.refresh_timer.timeout.connect(self.refresh_contents)
        self.refresh_timer.start()
        guiutils.center_to_parent(self)

    def refresh_contents(self) -> None:
        log_path = utils.get_logging_file(debugcore.currentpid)
        self.setWindowTitle(tr.LOG_FILE.format(debugcore.currentpid))
        self.label_FilePath.setText(tr.LOG_CONTENTS.format(log_path, 20000))
        log_status = f"<font color=blue>{tr.ON}</font>" if states.gdb_logging else f"<font color=red>{tr.OFF}</font>"
        self.label_LoggingStatus.setText(f"<b>{tr.LOG_STATUS.format(log_status)}</b>")
        try:
            log_file = open(log_path, encoding="utf-8", errors="replace")
        except OSError:
            self.textBrowser_LogContent.clear()
            error_message = tr.LOG_READ_ERROR.format(log_path) + "\n"
            if not states.gdb_logging:
                error_message += tr.SETTINGS_ENABLE_LOG
            self.textBrowser_LogContent.setText(error_message)
            return
        with log_file:
            log_file.seek(0, io.SEEK_END)
            end_pos = log_file.tell()
            truncated = end_pos > 20000
            log_file.seek(end_pos - 20000 if truncated else 0, io.SEEK_SET)
            contents = log_file.read()
            if truncated:
                contents = contents.split("\n", 1)[-1]
        if contents != self.contents:
            self.contents = contents
            self.textBrowser_LogContent.clear()
            self.textBrowser_LogContent.setPlainText(contents)

            # Scrolling to bottom
            cursor = self.textBrowser_LogContent.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.textBrowser_LogContent.setTextCursor(cursor)
            self.textBrowser_LogContent.ensureCursorVisible()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.refresh_timer.stop()
        super().closeEvent(event)


class SearchInstructionsWidgetForm(QWidget, SearchInstructionsWidget):
    def __init__(self, parent: QWidget, start: str = "", end: str = "") -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.lineEdit_Start.setText(start)
        self.lineEdit_End.setText(end)
        self.tableWidget_Instructions.setColumnWidth(SEARCH_INSTR_ADDR_COL, 250)
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_Help.setIcon(QIcon(QPixmap(icons_directory + "/help.png")))
        self.pushButton_Help.clicked.connect(self.pushButton_Help_clicked)
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.shortcut_search = QShortcut(QKeySequence("Return"), self)
        self.shortcut_search.activated.connect(self.refresh_table)
        self.tableWidget_Instructions.itemDoubleClicked.connect(self.tableWidget_Instructions_item_double_clicked)
        self.tableWidget_Instructions.contextMenuEvent = self.tableWidget_Instructions_context_menu_event
        guiutils.center_to_parent(self)

    def refresh_table(self) -> None:
        start_address = self.lineEdit_Start.text()
        end_address = self.lineEdit_End.text()
        regex = self.lineEdit_Regex.text()
        case_sensitive = self.checkBox_CaseSensitive.isChecked()
        enable_regex = self.checkBox_Regex.isChecked()
        if enable_regex:
            try:
                re.compile(regex) if case_sensitive else re.compile(regex, re.IGNORECASE)
            except re.error:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
                return
        self.loading_dialog = LoadingDialogForm(self)
        self.background_thread = self.loading_dialog.background_thread
        self.background_thread.overrided_func = lambda: self.process_data(
            regex, start_address, end_address, case_sensitive, enable_regex
        )
        self.background_thread.output_ready.connect(self.apply_data)
        self.loading_dialog.exec()

    def process_data(
        self, regex: str, start_address: str, end_address: str, case_sensitive: bool, enable_regex: bool
    ) -> list | None:
        return debugcore.search_instr(regex, start_address, end_address, case_sensitive, enable_regex)

    def apply_data(self, disas_data: list | None) -> None:
        if disas_data is None:
            return
        self.tableWidget_Instructions.setSortingEnabled(False)
        self.tableWidget_Instructions.setRowCount(0)
        self.tableWidget_Instructions.setRowCount(len(disas_data))
        for row, item in enumerate(disas_data):
            self.tableWidget_Instructions.setItem(row, SEARCH_INSTR_ADDR_COL, QTableWidgetItem(item[0]))
            self.tableWidget_Instructions.setItem(row, SEARCH_INSTR_INSTR_COL, QTableWidgetItem(item[1]))
        self.tableWidget_Instructions.setSortingEnabled(True)

    def pushButton_Help_clicked(self) -> None:
        utilwidgets.InputDialog(self, tr.SEARCH_INSTR_HELPER, Qt.AlignmentFlag.AlignLeft, False).exec()

    def tableWidget_Instructions_item_double_clicked(self, index: QTableWidgetItem) -> None:
        row = index.row()
        address = self.tableWidget_Instructions.item(row, SEARCH_INSTR_ADDR_COL).text()
        self.parent().disassemble_expression(utils.extract_hex_address(address))

    def tableWidget_Instructions_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            app.clipboard().setText(self.tableWidget_Instructions.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_Instructions)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_instr = menu.addAction(tr.COPY_INSTR)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_instr])
        font_size = self.tableWidget_Instructions.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, SEARCH_INSTR_ADDR_COL),
            copy_instr: lambda: copy_to_clipboard(selected_row, SEARCH_INSTR_INSTR_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass


class MemoryRegionsWidgetForm(QWidget, MemoryRegionsWidget):
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
            self.tableWidget_MemoryRegions.setItem(
                row, MEMORY_REGIONS_PATH_COL, QTableWidgetItem(path + f"[{region_index}]")
            )

        guiutils.resize_to_contents(self.tableWidget_MemoryRegions)
        self.filter_table()

    def filter_table(self) -> None:
        search_text = self.lineEdit_Search.text().lower()
        for row in range(self.tableWidget_MemoryRegions.rowCount()):
            path = self.tableWidget_MemoryRegions.item(row, MEMORY_REGIONS_PATH_COL).text()
            self.tableWidget_MemoryRegions.setRowHidden(row, search_text not in path.lower())

    def tableWidget_MemoryRegions_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            app.clipboard().setText(self.tableWidget_MemoryRegions.item(row, column).text())

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
        address_int = safe_str_to_int(address.split("-")[0], 16)
        self.parent().hex_dump_address(address_int)


class DissectCodeDialogForm(QDialog, DissectCodeDialog):
    scan_finished_signal = pyqtSignal()

    def __init__(self, parent: QWidget, int_address: int = -1) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.init_pre_scan_gui()
        self.update_dissect_results()
        self.show_memory_regions()
        self.splitter.setStretchFactor(0, 1)
        self.pushButton_StartCancel.clicked.connect(self.pushButton_StartCancel_clicked)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(self.refresh_dissect_status)
        if int_address != -1:
            for row in range(self.tableWidget_ExecutableMemoryRegions.rowCount()):
                item = self.tableWidget_ExecutableMemoryRegions.item(row, DISSECT_CODE_ADDR_COL).text()
                start_addr, end_addr = item.split("-")
                if safe_str_to_int(start_addr, 16) <= int_address <= safe_str_to_int(end_addr, 16):
                    self.tableWidget_ExecutableMemoryRegions.clearSelection()
                    self.tableWidget_ExecutableMemoryRegions.selectRow(row)
                    self.pushButton_StartCancel_clicked()
                    break
            else:
                QMessageBox.information(self, tr.ERROR, tr.INVALID_REGION)
        else:
            if self.tableWidget_ExecutableMemoryRegions.rowCount() > 0:
                self.tableWidget_ExecutableMemoryRegions.selectRow(0)
        guiutils.center_to_parent(self)

    class BackgroundThread(QThread):
        output_ready = pyqtSignal()
        is_canceled = False

        def __init__(self, region_list: list, discard_invalid_strings: bool) -> None:
            super().__init__()
            self.region_list = region_list
            self.discard_invalid_strings = discard_invalid_strings

        def run(self) -> None:
            debugcore.dissect_code(self.region_list, self.discard_invalid_strings)
            if not self.is_canceled:
                self.output_ready.emit()

    def init_pre_scan_gui(self) -> None:
        self.is_scanning = False
        self.is_canceled = False
        self.pushButton_StartCancel.setText(tr.START)

    def init_after_scan_gui(self) -> None:
        self.is_scanning = True
        self.label_ScanInfo.setText(tr.CURRENT_SCAN_REGION)
        self.pushButton_StartCancel.setText(tr.CANCEL)

    def refresh_dissect_status(self) -> None:
        region, region_count, range, string_count, jump_count, call_count = debugcore.get_dissect_code_status()
        if not region:
            return
        self.label_RegionInfo.setText(region)
        self.label_RegionCountInfo.setText(region_count)
        self.label_CurrentRange.setText(range)
        self.label_StringReferenceCount.setText(str(string_count))
        self.label_JumpReferenceCount.setText(str(jump_count))
        self.label_CallReferenceCount.setText(str(call_count))

    def update_dissect_results(self) -> None:
        referenced_strings = None
        referenced_jumps = None
        referenced_calls = None
        try:
            referenced_strings, referenced_jumps, referenced_calls = debugcore.get_dissect_code_data()
        except:
            return
        try:
            self.label_StringReferenceCount.setText(str(len(referenced_strings)))
            self.label_JumpReferenceCount.setText(str(len(referenced_jumps)))
            self.label_CallReferenceCount.setText(str(len(referenced_calls)))
        finally:
            for ref_dict in (referenced_strings, referenced_jumps, referenced_calls):
                if ref_dict is not None:
                    ref_dict.close()

    def show_memory_regions(self) -> None:
        executable_regions = utils.filter_regions(debugcore.currentpid, "permissions", "..x.")
        self.region_list = []
        self.tableWidget_ExecutableMemoryRegions.setRowCount(0)
        self.tableWidget_ExecutableMemoryRegions.setRowCount(len(executable_regions))
        for row, (start, end, _, _, _, _, path) in enumerate(executable_regions):
            address = start + "-" + end
            self.region_list.append((start, end))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_ADDR_COL, QTableWidgetItem(address))
            self.tableWidget_ExecutableMemoryRegions.setItem(row, DISSECT_CODE_PATH_COL, QTableWidgetItem(path))
        guiutils.resize_to_contents(self.tableWidget_ExecutableMemoryRegions)

    def scan_finished(self) -> None:
        self.init_pre_scan_gui()
        if not self.is_canceled:
            self.label_ScanInfo.setText(tr.SCAN_FINISHED)
        self.is_canceled = False
        self.refresh_timer.stop()
        self.refresh_dissect_status()
        self.update_dissect_results()
        self.scan_finished_signal.emit()

    def pushButton_StartCancel_clicked(self) -> None:
        if self.is_scanning:
            self.is_canceled = True
            self.background_thread.is_canceled = True
            debugcore.cancel_dissect_code()
            self.refresh_timer.stop()
            self.update_dissect_results()
            self.label_ScanInfo.setText(tr.SCAN_CANCELED)
            self.init_pre_scan_gui()
        else:
            selected_rows = self.tableWidget_ExecutableMemoryRegions.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, tr.ERROR, tr.SELECT_ONE_REGION)
                return
            selected_indexes = [selected_row.row() for selected_row in selected_rows]
            selected_regions = [self.region_list[selected_index] for selected_index in selected_indexes]
            self.background_thread = self.BackgroundThread(
                selected_regions, self.checkBox_DiscardInvalidStrings.isChecked()
            )
            self.background_thread.output_ready.connect(self.scan_finished)
            self.init_after_scan_gui()
            self.refresh_timer.start()
            self.background_thread.start()

    def closeEvent(self, event: QCloseEvent) -> None:
        debugcore.cancel_dissect_code()
        self.refresh_timer.stop()
        if hasattr(self, "background_thread"):
            self.is_canceled = True
            self.background_thread.is_canceled = True
            self.background_thread.wait()
        super().closeEvent(event)


class ReferencedStringsWidgetForm(QWidget, ReferencedStringsWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        guiutils.fill_value_combobox(self.comboBox_ValueType, typedefs.VALUE_INDEX.STRING_UTF8)
        self.setWindowFlags(Qt.WindowType.Window)
        self.tableWidget_References.setColumnWidth(REF_STR_ADDR_COL, 150)
        self.tableWidget_References.setColumnWidth(REF_STR_COUNT_COL, 80)
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
                dissect_code_dialog = DissectCodeDialogForm(self)
                dissect_code_dialog.scan_finished_signal.connect(dissect_code_dialog.accept)
                dissect_code_dialog.exec()
        self.refresh_table()
        self.tableWidget_References.sortByColumn(REF_STR_ADDR_COL, Qt.SortOrder.AscendingOrder)
        self.tableWidget_References.selectionModel().currentChanged.connect(self.tableWidget_References_current_changed)
        self.listWidget_Referrers.itemDoubleClicked.connect(self.listWidget_Referrers_item_double_clicked)
        self.tableWidget_References.itemDoubleClicked.connect(self.tableWidget_References_item_double_clicked)
        self.tableWidget_References.contextMenuEvent = self.tableWidget_References_context_menu_event
        self.listWidget_Referrers.contextMenuEvent = self.listWidget_Referrers_context_menu_event
        self.pushButton_Search.clicked.connect(self.refresh_table)
        self.comboBox_ValueType.currentIndexChanged.connect(self.refresh_table)
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
        item_list = debugcore.search_referenced_strings(
            self.lineEdit_Regex.text(),
            self.comboBox_ValueType.currentData(Qt.ItemDataRole.UserRole),
            self.checkBox_CaseSensitive.isChecked(),
            self.checkBox_Regex.isChecked(),
        )
        if item_list is None:
            QMessageBox.information(self, tr.ERROR, tr.INVALID_REGEX)
            return
        self.tableWidget_References.setSortingEnabled(False)
        self.tableWidget_References.setRowCount(0)
        self.tableWidget_References.setRowCount(len(item_list))
        for row, item in enumerate(item_list):
            self.tableWidget_References.setItem(row, REF_STR_ADDR_COL, QTableWidgetItem(self.pad_hex(item[0])))
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[1])
            self.tableWidget_References.setItem(row, REF_STR_COUNT_COL, table_widget_item)
            table_widget_item = QTableWidgetItem()
            table_widget_item.setData(Qt.ItemDataRole.EditRole, item[2])
            self.tableWidget_References.setItem(row, REF_STR_VAL_COL, table_widget_item)
        self.tableWidget_References.setSortingEnabled(True)

    def tableWidget_References_current_changed(self, QModelIndex_current: QModelIndex) -> None:
        if QModelIndex_current.row() < 0:
            return
        self.listWidget_Referrers.clear()
        str_dict = debugcore.get_dissect_code_data(True, False, False)[0]
        try:
            addr = self.tableWidget_References.item(QModelIndex_current.row(), REF_STR_ADDR_COL).text()
            referrers = str_dict.get(hex(int(addr, 16)))
            if referrers is None:
                return
            addrs = [hex(address) for address in referrers]
            self.listWidget_Referrers.addItems(
                [self.pad_hex(item.all) for item in debugcore.examine_expressions(addrs) if item.all]
            )
            self.listWidget_Referrers.sortItems(Qt.SortOrder.AscendingOrder)
        finally:
            str_dict.close()

    def tableWidget_References_item_double_clicked(self, index: QTableWidgetItem) -> None:
        row = index.row()
        address = self.tableWidget_References.item(row, REF_STR_ADDR_COL).text()
        self.parent().hex_dump_address(safe_str_to_int(address, 16))

    def listWidget_Referrers_item_double_clicked(self, item: QListWidgetItem) -> None:
        self.parent().disassemble_expression(utils.extract_hex_address(item.text()))

    def tableWidget_References_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int, column: int) -> None:
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

        selected_row = guiutils.get_current_row(self.tableWidget_References)

        menu = QMenu()
        copy_address = menu.addAction(tr.COPY_ADDRESS)
        copy_value = menu.addAction(tr.COPY_VALUE)
        if selected_row == -1:
            guiutils.delete_menu_entries(menu, [copy_address, copy_value])
        font_size = self.tableWidget_References.font().pointSize()
        menu.setStyleSheet("font-size: " + str(font_size) + "pt;")
        action = menu.exec(event.globalPos())
        actions = {
            copy_address: lambda: copy_to_clipboard(selected_row, REF_STR_ADDR_COL),
            copy_value: lambda: copy_to_clipboard(selected_row, REF_STR_VAL_COL),
        }
        try:
            actions[action]()
        except KeyError:
            pass

    def listWidget_Referrers_context_menu_event(self, event: QContextMenuEvent) -> None:
        def copy_to_clipboard(row: int) -> None:
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

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


class ReferencedCallsWidgetForm(QWidget, ReferencedCallsWidget):
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
                dissect_code_dialog = DissectCodeDialogForm(self)
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
            self.listWidget_Referrers.addItems(
                [self.pad_hex(item.all) for item in debugcore.examine_expressions(addrs) if item.all]
            )
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
            app.clipboard().setText(self.tableWidget_References.item(row, column).text())

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
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

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


class ExamineReferrersWidgetForm(QWidget, ExamineReferrersWidget):
    def __init__(self, parent: QWidget, int_address: int) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)
        self.splitter.setStretchFactor(0, 1)
        self.textBrowser_DisasInfo.resize(600, self.textBrowser_DisasInfo.height())
        self.referenced_hex = hex(int_address)
        self.hex_len = 16 if debugcore.inferior_arch == typedefs.INFERIOR_ARCH.ARCH_64 else 8
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

    def pad_hex(self, hex_str: str) -> str:
        index = hex_str.find(" ")
        if index == -1:
            self_len = 0
        else:
            self_len = len(hex_str) - index
        return "0x" + hex_str[2:].zfill(self.hex_len + self_len)

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
        disas_data = debugcore.disassemble(
            utils.extract_hex_address(self.listWidget_Referrers.item(QModelIndex_current.row()).text()), "+200"
        )
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
            app.clipboard().setText(self.listWidget_Referrers.item(row).text())

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


def handle_exit() -> None:
    states.exiting = True


if __name__ == "__main__":
    app.aboutToQuit.connect(handle_exit)
    window = MainForm()
    window.show()

    if len(sys.argv) > 1 and sys.argv[1]:
        real_path = os.path.realpath(sys.argv[1])
        SessionManager.load_session(real_path)

    sys.exit(app.exec())
