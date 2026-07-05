from PyQt6.QtWidgets import QWidget, QCompleter
from PyQt6.QtGui import QShortcut, QKeySequence, QKeyEvent, QCloseEvent, QTextCursor
from PyQt6.QtCore import Qt, QKeyCombination, QStringListModel, pyqtSignal
from GUI.Utils import guitypedefs, guiutils
from GUI.Widgets.Console.Form.ConsoleWidget import Ui_Form
from GUI.Widgets.TextEdit.TextEdit import TextEditDialog
from libpince import debugcore, typedefs
from tr.tr import TranslationConstants as tr


class ConsoleWidget(QWidget, Ui_Form):
    gdb_command_sent = pyqtSignal()

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
        gdb_command_sent = False
        if stripped in self.quit_commands:
            console_output = tr.QUIT_SESSION_CRASH
        elif stripped in self.continue_commands:
            console_output = tr.CONT_SESSION_CRASH
        elif self.radioButton_CLI.isChecked():
            console_output = debugcore.send_command(console_input, cli_output=True)
            gdb_command_sent = bool(console_input.strip())
        else:
            console_output = debugcore.send_command(console_input)
            gdb_command_sent = bool(console_input.strip())
        self.textBrowser.append("-->" + console_input)
        if console_output:
            self.textBrowser.append(console_output)
        self.scroll_to_bottom()
        if gdb_command_sent:
            self.gdb_command_sent.emit()

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
