import os
from enum import IntFlag, auto

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from GUI.Session.Version import is_valid_session_data, migrate_version
from GUI.States import states
from libpince import utils, debugcore
from tr.tr import TranslationConstants as tr


class SessionDataChanged(IntFlag):
    NONE = auto()
    ADDRESS_TREE = auto()
    BOOKMARKS = auto()
    NOTES = auto()
    PROCESS_NAME = auto()


class Session:
    def __init__(self) -> None:
        # Anything labled with pct should be saved to the session file
        self.pct_notes: str = ""
        self.pct_bookmarks: dict[int, str] = {}
        self.pct_version: int = 1
        self.pct_address_tree: list = []
        self.pct_process_name: str = ""
        self.data_changed = SessionDataChanged.NONE
        self.file_path: str = os.path.expanduser("~/.config/PINCE/PINCE_USER_FILES/CheatTables")
        self.last_file_name: str = ""  # process name or file name

    def save_session(self) -> bool:
        """
        Save the current session to a file.
        If there is nothing to save, the function will return False.

        Args:
            None
        Returns:
            bool: True if the session was saved successfully, False otherwise.
        """
        if self.data_changed == SessionDataChanged.NONE:
            return False

        file_path, _ = QFileDialog.getSaveFileName(
            None, tr.SAVE_PCT_FILE, self.file_path + "/" + self.last_file_name, tr.FILE_TYPES_PCT
        )
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
            "process_name": self.pct_process_name,
        }

        file_path = utils.append_file_extension(file_path, "pct")
        if not utils.save_file(session, file_path):
            QMessageBox.information(None, tr.ERROR, tr.FILE_SAVE_ERROR)
            return False

        self.file_path = os.path.dirname(file_path)
        self.last_file_name = os.path.basename(file_path)
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
        """
        Load a pct session file. Will check for unsaved changes and prompt
        the user to save them before loading a new session.
        If the user chooses to cancel, the function will return False.
        Will also attempt to migrate the session data to the latest version.

        Args:
            None
        Returns:
            bool: True if the session was loaded successfully, False otherwise.

        """

        unsaved_changes_result = self.check_unsaved_changes()
        if unsaved_changes_result == QMessageBox.StandardButton.Cancel:
            return False
        elif unsaved_changes_result == QMessageBox.StandardButton.Yes:
            if not self.save_session():
                return False

        file_path, _ = QFileDialog.getOpenFileName(
            None, tr.OPEN_PCT_FILE, self.file_path + "/" + self.last_file_name, tr.FILE_TYPES_PCT
        )
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

        self.file_path = os.path.dirname(file_path)
        print(self.file_path)
        self.last_file_name = os.path.basename(file_path)
        print(self.last_file_name)

        states.session_signals.on_load.emit()
        self.data_changed = SessionDataChanged.NONE
        return True

    def pre_exit(self, close_event: QCloseEvent) -> None:
        """
        Event handler for the close event of the application.
        If there are unsaved changes, prompt the user to save them.
        Accepts or ignores the close event based on the user's choice.

        Args:
            close_event (QCloseEvent): The close event to be handled.
        Returns:
            None
        """

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
    def get_session() -> Session:
        return SessionManager.session

    @staticmethod
    def reset_session() -> None:
        session = SessionManager.get_session()
        # User has one last chance to save the session before resetting
        # result is ignored, because the session is going to be reset anyway
        session.check_unsaved_changes()
        SessionManager.session = Session()
        states.session_signals.new_session.emit()
        # Reset the session data changed flag
        session.data_changed = SessionDataChanged.NONE

    @staticmethod
    def save_session() -> None:
        SessionManager.get_session().save_session()

    @staticmethod
    def load_session() -> None:
        SessionManager.get_session().load_session()

    @staticmethod
    def on_process_changed() -> None:
        if debugcore.currentpid == -1:
            return
        process_name = utils.get_process_name(debugcore.currentpid)
        session = SessionManager.get_session()

        if session.last_file_name == utils.append_file_extension(process_name, "pct"):
            return

        if session.pct_process_name == "":
            # silently set the process name and file name if necessary
            session.pct_process_name = process_name
            if session.last_file_name == "":
                session.last_file_name = utils.append_file_extension(process_name, "pct")
            return

        if session.pct_process_name != process_name:
            # Ask if the user wants to keep the session
            keep_session_result = QMessageBox.question(
                None,
                tr.SESSION_PROCESS_CHANGED_TITLE,
                tr.SESSION_PROCESS_CHANGED_PROMPT,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if keep_session_result == QMessageBox.StandardButton.Yes:
                session.pct_process_name = process_name
            else:
                SessionManager.reset_session()
                session.pct_process_name = process_name
                session.last_file_name = utils.append_file_extension(process_name, "pct")
