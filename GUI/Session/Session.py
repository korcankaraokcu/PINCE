import os
from enum import IntFlag, auto

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from GUI.Session.Version import is_valid_session_data, migrate_version
from GUI.States import states
from libpince import utils
from tr.tr import TranslationConstants as tr


class SessionDataChanged(IntFlag):
    NONE = auto()
    ADDRESS_TREE = auto()
    BOOKMARKS = auto()
    NOTES = auto()


class Session(QObject):
    def __init__(self) -> None:
        self.pct_notes: str = ""
        self.pct_bookmarks: dict[int, str] = {}
        self.pct_version: int = 1
        self.pct_address_tree: list = []
        self.data_changed = SessionDataChanged.NONE
        self.file_path: str = os.path.expanduser("~/.config/PINCE/PINCE_USER_FILES/CheatTables/")

    def save_session(self) -> bool:
        if self.data_changed == SessionDataChanged.NONE:
            return False

        file_path, _ = QFileDialog.getSaveFileName(None, tr.SAVE_PCT_FILE, self.file_path, tr.FILE_TYPES_PCT)
        if not file_path:
            return False

        # until address tree is model view and properly read from this new session object,
        # address tree must save its data to the session object via signal
        if self.data_changed & SessionDataChanged.ADDRESS_TREE:
            states.session_signals.on_save.emit()

        session = {
            "version": self.pct_version,
            "notes": self.pct_notes,
            "bookmarks": self.pct_bookmarks,
            "address_tree": self.pct_address_tree,
        }

        file_path = utils.append_file_extension(file_path, "pct")
        if not utils.save_file(session, file_path):
            QMessageBox.information(None, tr.ERROR, tr.FILE_SAVE_ERROR)
            return False

        self.file_path = file_path
        self.data_changed = SessionDataChanged.NONE
        return True

    def check_unsaved_changes(self) -> QMessageBox.StandardButton:
        if self.data_changed == SessionDataChanged.NONE:
            return QMessageBox.StandardButton.No

        unsaved_changes_result = QMessageBox.question(
            None,
            tr.SAVE_SESSION_QUESTION_TITLE,
            tr.SAVE_SESSION_QUESTION_PROMPT,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        return unsaved_changes_result

    def load_session(self) -> bool:

        unsaved_changes_result = self.check_unsaved_changes()
        if unsaved_changes_result == QMessageBox.StandardButton.Cancel:
            return False
        elif unsaved_changes_result == QMessageBox.StandardButton.Yes:
            if not self.save_session():
                return False

        file_path, _ = QFileDialog.getOpenFileName(None, tr.OPEN_PCT_FILE, self.file_path, tr.FILE_TYPES_PCT)
        if not file_path:
            return False

        print(file_path)
        content = utils.load_file(file_path)
        if content is None:
            QMessageBox.information(None, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
            return False
        content = migrate_version(content)
        if not is_valid_session_data(content):
            QMessageBox.information(None, tr.ERROR, tr.FILE_LOAD_ERROR.format(file_path))
            return False

        self.pct_version = content["version"]
        self.pct_notes = content["notes"]
        self.pct_bookmarks = content["bookmarks"]
        # bookmarks are saved as int string keys, convert them back to int
        self.pct_bookmarks = {int(k): v for k, v in self.pct_bookmarks.items()}
        self.pct_address_tree = content["address_tree"]
        self.file_path = file_path

        states.session_signals.on_load.emit()
        self.data_changed = SessionDataChanged.NONE
        return True

    def pre_exit(self, close_event: QCloseEvent) -> None:
        print("Pre-Exit event, checking for unsaved Data.")
        if self.data_changed == SessionDataChanged.NONE:
            close_event.accept()
            return

        pre_exit_unsaved_changes_result = self.check_unsaved_changes()
        if pre_exit_unsaved_changes_result == QMessageBox.StandardButton.Yes:
            self.save_session()
            close_event.accept()

        elif pre_exit_unsaved_changes_result == QMessageBox.StandardButton.Cancel:
            close_event.ignore()
        else:
            close_event.accept()


class SessionManager:
    session = Session()

    @staticmethod
    def get_session():
        return SessionManager.session

    @staticmethod
    def reset_session():
        SessionManager.session = Session()
        states.session_signals.new_session.emit()

    @staticmethod
    def save_session():
        SessionManager.get_session().save_session()

    @staticmethod
    def load_session():
        SessionManager.get_session().load_session()
