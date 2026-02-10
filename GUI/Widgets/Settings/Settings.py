from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog, QApplication
from PyQt6.QtCore import Qt, QSettings, QSignalBlocker
from PyQt6.QtGui import QKeyEvent, QIcon, QPixmap, QStandardItemModel, QStandardItem
from GUI.States import states
from GUI.Settings import settings, themes
from GUI.Utils import guiutils, utilwidgets
from GUI.Widgets.Settings.Form.SettingsDialog import Ui_Dialog
from GUI.Widgets.HandleSignals.HandleSignals import HandleSignalsDialog
from tr.tr import TranslationConstants as tr
from tr.tr import language_list
from libpince import debugcore, utils, typedefs
from keyboard import KeyboardEvent, _pressed_events
from keyboard._nixkeyboard import to_name
import os, signal, json, re


class SettingsDialog(QDialog, Ui_Dialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.settings = QSettings()
        self.hotkey_to_value = {}  # Dict[str:str]-->Dict[Hotkey.name:settings_value]
        self.handle_signals_data = ""
        icons_directory = guiutils.get_icons_directory()
        self.pushButton_GDBPath.setIcon(QIcon(QPixmap(icons_directory + "/folder.png")))
        locale_model = QStandardItemModel()
        for loc, name in language_list.items():
            item = QStandardItem()
            item.setData(name, Qt.ItemDataRole.DisplayRole)
            item.setData(loc, Qt.ItemDataRole.UserRole)
            locale_model.appendRow(item)
        self.comboBox_Language.setModel(locale_model)
        self.comboBox_InterruptSignal.addItem("SIGINT")
        self.comboBox_InterruptSignal.addItems([f"SIG{x}" for x in range(signal.SIGRTMIN, signal.SIGRTMAX + 1)])
        self.comboBox_InterruptSignal.setStyleSheet("combobox-popup: 0;")  # maxVisibleItems doesn't work otherwise
        self.comboBox_Theme.addItems(themes.theme_strings.values())
        logo_directory = utils.get_logo_directory()
        logo_list = utils.search_files(logo_directory, r"\.(png|jpg|jpeg|svg)$")
        for logo in logo_list:
            self.comboBox_Logo.addItem(QIcon(os.path.join(logo_directory, logo)), logo)
        for hotkey in states.hotkeys.get_hotkeys():
            self.listWidget_Functions.addItem(hotkey.desc)
        self.config_gui()

        self.listWidget_Options.currentRowChanged.connect(self.change_display)
        self.listWidget_Functions.currentRowChanged.connect(self.listWidget_Functions_current_row_changed)
        self.pushButton_ClearHotkey.clicked.connect(self.pushButton_ClearHotkey_clicked)
        self.pushButton_ResetSettings.clicked.connect(self.pushButton_ResetSettings_clicked)
        self.pushButton_GDBPath.clicked.connect(self.pushButton_GDBPath_clicked)
        self.checkBox_AutoUpdateAddressTable.stateChanged.connect(self.checkBox_AutoUpdateAddressTable_state_changed)
        self.checkBox_AutoAttachRegex.stateChanged.connect(self.checkBox_AutoAttachRegex_state_changed)
        self.comboBox_Logo.currentIndexChanged.connect(self.comboBox_Logo_current_index_changed)
        self.comboBox_Theme.currentIndexChanged.connect(self.comboBox_Theme_current_index_changed)
        self.pushButton_HandleSignals.clicked.connect(self.pushButton_HandleSignals_clicked)
        self.lineEdit_Hotkey.keyPressEvent = self.lineEdit_Hotkey_key_pressed_event
        guiutils.center_to_parent(self)

    def accept(self):
        self.settings.setValue("General/auto_update_address_table", self.checkBox_AutoUpdateAddressTable.isChecked())
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.settings.setValue("General/address_table_update_interval", self.spinBox_UpdateInterval.value())
        self.settings.setValue("General/freeze_interval", self.spinBox_FreezeInterval.value())
        output_mode = [
            self.checkBox_OutputModeAsync.isChecked(),
            self.checkBox_OutputModeCommand.isChecked(),
            self.checkBox_OutputModeCommandInfo.isChecked(),
        ]
        self.settings.setValue("General/gdb_output_mode", json.dumps(output_mode))
        if self.checkBox_AutoAttachRegex.isChecked():
            try:
                re.compile(self.lineEdit_AutoAttach.text())
            except:
                QMessageBox.information(self, tr.ERROR, tr.IS_INVALID_REGEX.format(self.lineEdit_AutoAttach.text()))
                return
        self.settings.setValue("General/auto_attach", self.lineEdit_AutoAttach.text())
        self.settings.setValue("General/auto_attach_regex", self.checkBox_AutoAttachRegex.isChecked())
        new_locale = self.comboBox_Language.currentData(Qt.ItemDataRole.UserRole)
        current_locale = self.settings.value("General/locale", type=str)
        if new_locale != current_locale:
            QMessageBox.information(self, tr.INFO, tr.LANG_RESET)
        self.settings.setValue("General/locale", new_locale)
        self.settings.setValue("General/logo_path", self.comboBox_Logo.currentText())
        self.settings.setValue("General/theme", list(themes.Themes)[self.comboBox_Theme.currentIndex()].value)
        for hotkey in states.hotkeys.get_hotkeys():
            self.settings.setValue("Hotkeys/" + hotkey.name, self.hotkey_to_value[hotkey.name])
        if self.radioButton_SimpleDLopenCall.isChecked():
            injection_method = typedefs.INJECTION_METHOD.DLOPEN
        elif self.radioButton_AdvancedInjection.isChecked():
            injection_method = typedefs.INJECTION_METHOD.ADVANCED
        self.settings.setValue("CodeInjection/code_injection_method", injection_method)
        self.settings.setValue("MemoryView/show_memory_view_on_stop", self.checkBox_ShowMemoryViewOnStop.isChecked())
        self.settings.setValue("MemoryView/instructions_per_scroll", self.spinBox_InstructionsPerScroll.value())
        self.settings.setValue("MemoryView/bytes_per_scroll", self.spinBox_BytesPerScroll.value())
        if not os.environ.get("APPDIR"):
            selected_gdb_path = self.lineEdit_GDBPath.text()
            if selected_gdb_path != states.gdb_path:
                if utilwidgets.InputDialog(self, tr.GDB_RESET).exec():
                    debugcore.init_gdb(selected_gdb_path)
            self.settings.setValue("Debug/gdb_path", selected_gdb_path)
        self.settings.setValue("Debug/gdb_logging", self.checkBox_GDBLogging.isChecked())
        self.settings.setValue("Debug/interrupt_signal", self.comboBox_InterruptSignal.currentText())
        self.settings.setValue("Java/ignore_segfault", self.checkBox_JavaSegfault.isChecked())
        if self.handle_signals_data:
            self.settings.setValue("Debug/handle_signals", self.handle_signals_data)
        settings.apply_settings()
        super().accept()

    def reject(self):
        logo_path = self.settings.value("General/logo_path", type=str)
        QApplication.setWindowIcon(QIcon(os.path.join(utils.get_logo_directory(), logo_path)))
        theme = self.settings.value("General/theme", type=str)
        QApplication.setPalette(themes.get_theme(theme))
        super().reject()

    def config_gui(self):
        self.checkBox_AutoUpdateAddressTable.setChecked(
            self.settings.value("General/auto_update_address_table", type=bool)
        )
        self.spinBox_UpdateInterval.setValue(self.settings.value("General/address_table_update_interval", type=int))
        self.spinBox_FreezeInterval.setValue(self.settings.value("General/freeze_interval", type=int))
        output_mode = json.loads(self.settings.value("General/gdb_output_mode", type=str))
        output_mode = typedefs.gdb_output_mode(*output_mode)
        self.checkBox_OutputModeAsync.setChecked(output_mode.async_output)
        self.checkBox_OutputModeCommand.setChecked(output_mode.command_output)
        self.checkBox_OutputModeCommandInfo.setChecked(output_mode.command_info)
        self.lineEdit_AutoAttach.setText(self.settings.value("General/auto_attach", type=str))
        self.checkBox_AutoAttachRegex.setChecked(self.settings.value("General/auto_attach_regex", type=bool))
        current_locale = self.settings.value("General/locale", type=str)
        self.comboBox_Language.setCurrentText(language_list.get(current_locale, "en_US"))
        with QSignalBlocker(self.comboBox_Theme):
            self.comboBox_Theme.setCurrentText(themes.theme_strings[self.settings.value("General/theme", type=str)])
        with QSignalBlocker(self.comboBox_Logo):
            self.comboBox_Logo.setCurrentText(self.settings.value("General/logo_path", type=str))
        self.hotkey_to_value.clear()
        for hotkey in states.hotkeys.get_hotkeys():
            self.hotkey_to_value[hotkey.name] = self.settings.value("Hotkeys/" + hotkey.name)
        self.listWidget_Functions_current_row_changed(self.listWidget_Functions.currentRow())
        code_injection_method = self.settings.value("CodeInjection/code_injection_method", type=int)
        if code_injection_method == typedefs.INJECTION_METHOD.DLOPEN:
            self.radioButton_SimpleDLopenCall.setChecked(True)
        elif code_injection_method == typedefs.INJECTION_METHOD.ADVANCED:
            self.radioButton_AdvancedInjection.setChecked(True)

        self.checkBox_ShowMemoryViewOnStop.setChecked(
            self.settings.value("MemoryView/show_memory_view_on_stop", type=bool)
        )
        self.spinBox_InstructionsPerScroll.setValue(self.settings.value("MemoryView/instructions_per_scroll", type=int))
        self.spinBox_BytesPerScroll.setValue(self.settings.value("MemoryView/bytes_per_scroll", type=int))
        self.lineEdit_GDBPath.setText(str(self.settings.value("Debug/gdb_path", type=str)))
        if os.environ.get("APPDIR"):
            self.label_GDBPath.setDisabled(True)
            self.label_GDBPath.setToolTip(tr.UNUSED_APPIMAGE_SETTING)
            self.lineEdit_GDBPath.setDisabled(True)
            self.lineEdit_GDBPath.setToolTip(tr.UNUSED_APPIMAGE_SETTING)
            self.pushButton_GDBPath.setDisabled(True)
            self.pushButton_GDBPath.setToolTip(tr.UNUSED_APPIMAGE_SETTING)
        self.checkBox_GDBLogging.setChecked(self.settings.value("Debug/gdb_logging", type=bool))
        self.comboBox_InterruptSignal.setCurrentText(self.settings.value("Debug/interrupt_signal", type=str))
        self.checkBox_JavaSegfault.setChecked(self.settings.value("Java/ignore_segfault", type=bool))

    def change_display(self, index):
        self.stackedWidget.setCurrentIndex(index)

    def listWidget_Functions_current_row_changed(self, index):
        if index == -1:
            self.lineEdit_Hotkey.clear()
        else:
            self.lineEdit_Hotkey.setText(self.hotkey_to_value[states.hotkeys.get_hotkeys()[index].name])

    def pushButton_ClearHotkey_clicked(self):
        self.lineEdit_Hotkey.clear()
        index = self.listWidget_Functions.currentIndex().row()
        if index != -1:
            self.hotkey_to_value[states.hotkeys.get_hotkeys()[index].name] = self.lineEdit_Hotkey.text()

    def pushButton_ResetSettings_clicked(self):
        if utilwidgets.InputDialog(self, tr.RESET_DEFAULT_SETTINGS).exec():
            settings.set_default_settings()
            self.handle_signals_data = ""
            self.config_gui()

    def checkBox_AutoUpdateAddressTable_state_changed(self):
        if self.checkBox_AutoUpdateAddressTable.isChecked():
            self.QWidget_UpdateInterval.setEnabled(True)
        else:
            self.QWidget_UpdateInterval.setEnabled(False)

    def checkBox_AutoAttachRegex_state_changed(self):
        if self.checkBox_AutoAttachRegex.isChecked():
            self.lineEdit_AutoAttach.setPlaceholderText(tr.MOUSE_OVER_EXAMPLES)
            self.lineEdit_AutoAttach.setToolTip(tr.AUTO_ATTACH_TOOLTIP)
        else:
            self.lineEdit_AutoAttach.setPlaceholderText(tr.SEPARATE_PROCESSES_WITH.format(";"))
            self.lineEdit_AutoAttach.setToolTip("")

    def comboBox_Logo_current_index_changed(self):
        logo_path = self.comboBox_Logo.currentText()
        QApplication.setWindowIcon(QIcon(os.path.join(utils.get_logo_directory(), logo_path)))

    def comboBox_Theme_current_index_changed(self, index: int):
        QApplication.setPalette(themes.get_theme(list(themes.Themes)[index].value))

    def pushButton_GDBPath_clicked(self):
        current_path = self.lineEdit_GDBPath.text()
        file_path, _ = QFileDialog.getOpenFileName(self, tr.SELECT_GDB_BINARY, os.path.dirname(current_path))
        if file_path:
            self.lineEdit_GDBPath.setText(file_path)

    def pushButton_HandleSignals_clicked(self):
        if not self.handle_signals_data:
            self.handle_signals_data = self.settings.value("Debug/handle_signals", type=str)
        signal_dialog = HandleSignalsDialog(self, self.handle_signals_data)
        if signal_dialog.exec():
            self.handle_signals_data = signal_dialog.get_values()

    def lineEdit_Hotkey_key_pressed_event(self, event: QKeyEvent):
        """
        Instead of relying on the QT Event, we grab input from keyboard lib directly.
        This reduces the amount of parsing from keys necessary and catches some more edge cases.

        One final caveat exists: system hotkeys or system wide defined hotkeys (xserver)
        take precedence over the keyboard lib and are not caught completely.
        """
        pressed_events: list[KeyboardEvent] = list(_pressed_events.values())
        if len(pressed_events) == 0:
            # the keypress time was so short its not recognized by keyboard lib.
            return
        hotkey_string = ""
        for ev in pressed_events:
            # replacing keys with their respective base key, e.g "!" --> "1"
            ev.name = to_name[(ev.scan_code, ())][-1]
            # keyboard does recognize meta key (win key) as alt, setting manually
            if ev.scan_code == 125 or ev.scan_code == 126:
                ev.name = "windows"
            hotkey_string += ev.name + "+"

        # remove the last plus
        hotkey_string = hotkey_string[:-1]

        # moved from old keySequenceChanged event
        self.lineEdit_Hotkey.setText(hotkey_string)
        index = self.listWidget_Functions.currentIndex().row()
        if index == -1:
            self.lineEdit_Hotkey.clear()
        else:
            self.hotkey_to_value[states.hotkeys.get_hotkeys()[index].name] = self.lineEdit_Hotkey.text()
