from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QTextCursor, QCloseEvent
from PyQt6.QtCore import Qt, QTimer
from GUI.Utils import guiutils
from GUI.States import states
from GUI.Widgets.LogFile.Form.LogFileWidget import Ui_Form
from libpince import debugcore, utils
from tr.tr import TranslationConstants as tr
import io


class LogFileWidget(QWidget, Ui_Form):
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
