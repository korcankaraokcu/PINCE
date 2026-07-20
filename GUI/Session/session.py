import os
from enum import IntFlag, auto
from typing import Any

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QCheckBox, QFileDialog, QMessageBox

from GUI.Settings import settings
from GUI.States import states
from GUI.Utils import guiutils
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr


class SessionDataChanged(IntFlag):
    NONE = 0
    ADDRESS_TREE = auto()
    BOOKMARKS = auto()
    NOTES = auto()
    PROCESS_NAME = auto()
    STRUCTURES = auto()


LATEST_VERSION = 3


def _legacy_to_v1(content: list) -> dict[str, Any]:
    utils.logger.info("Migrating legacy session data to version 1")
    return {"version": 1, "notes": "", "bookmarks": {}, "address_tree": content, "process_name": ""}


def _v1_to_v2(content: dict[str, Any]) -> dict[str, Any]:
    # v2 added script entry rows which are told apart by length so no row transform is needed
    utils.logger.info("Migrating version 1 session data to version 2")
    content["version"] = 2
    return content


def _v2_to_v3(content: dict[str, Any]) -> dict[str, Any]:
    # v3 added saved structures
    utils.logger.info("Migrating version 2 session data to version 3")
    content["version"] = 3
    content.setdefault("structures", {})
    return content


def migrate_version(content: Any) -> dict[str, Any]:
    if not hasattr(content, "version") and type(content) == list:
        content = _legacy_to_v1(content)
    if isinstance(content, dict) and content.get("version") == 1:
        content = _v1_to_v2(content)
    if isinstance(content, dict) and content.get("version") == 2:
        content = _v2_to_v3(content)
    return content


def is_valid_session_data(content: dict[str, Any]) -> bool:
    if not isinstance(content, dict):
        return False
    keys = ["version", "notes", "bookmarks", "address_tree", "process_name"]
    for key in keys:
        if key not in content:
            return False
    if not isinstance(content["bookmarks"], dict):
        return False
    for addr, value in content["bookmarks"].items():
        try:
            int(addr)
        except (TypeError, ValueError):
            return False
        if not isinstance(value, dict):
            return False
        for field in ("comment", "symbol", "address_region_details"):
            if field not in value:
                return False
        details = value["address_region_details"]
        if not isinstance(details, dict):
            return False
        for field in ("region_name", "offset_in_region", "region_index"):
            if field not in details:
                return False
        if not isinstance(details["region_index"], int):
            return False
    if not isinstance(content.get("structures", {}), dict):
        return False
    return True


class Session:
    def __init__(self) -> None:
        # Anything labled with pct should be saved to the session file
        self.pct_notes: str = ""
        self.pct_bookmarks: dict[int, dict] = {}
        self.pct_version: int = LATEST_VERSION
        self.pct_address_tree: list = []
        self.pct_process_name: str = ""
        self.pct_structures: dict[str, tuple] = {}
        self.data_changed = SessionDataChanged.NONE
        self.file_path: str = os.path.expanduser("~")
        self.last_file_name: str = ""  # process name or file name
        self.file_backed: bool = False

    def save_session(self) -> bool:
        """
        Save the current session to a file.

        Args:
            None
        Returns:
            bool: True if the session was saved successfully, False otherwise.
        """
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
            "structures": self.pct_structures,
        }
        if self.file_backed:
            file_path = os.path.join(self.file_path, self.last_file_name)
            if not utils.save_file(session, file_path):
                QMessageBox.information(None, tr.ERROR, tr.FILE_SAVE_ERROR)
                return False
            guiutils.own_path_as_user(file_path)
            self.data_changed = SessionDataChanged.NONE
            return True

        with guiutils.save_dialog_as_user(None, tr.SAVE_PCT_FILE, self.file_path + "/" + self.last_file_name, tr.FILE_TYPES_PCT, "pct") as file_path:
            if not file_path:
                return False
            if not utils.save_file(session, file_path):
                QMessageBox.information(None, tr.ERROR, tr.FILE_SAVE_ERROR)
                return False
            self.file_path = os.path.dirname(file_path)
            self.last_file_name = os.path.basename(file_path)
            self.file_backed = True
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

    def load_session(self, file_path: str | None = None) -> bool:
        """
        Load a pct session file from passed argument, otherwise, opens the file picker. Will check for unsaved changes and prompt
        the user to save them before loading a new session.
        If the user chooses to cancel, the function will return False.
        Will also attempt to migrate the session data to the latest version.

        Args:
            file_path: Optional absolute path to load a session file
        Returns:
            bool: True if the session was loaded successfully, False otherwise.

        """

        unsaved_changes_result = self.check_unsaved_changes()
        if unsaved_changes_result == QMessageBox.StandardButton.Cancel:
            return False
        elif unsaved_changes_result == QMessageBox.StandardButton.Yes:
            if not self.save_session():
                return False

        if file_path is None or not isinstance(file_path, str):
            file_path, _ = QFileDialog.getOpenFileName(None, tr.OPEN_PCT_FILE, self.file_path + "/" + self.last_file_name, tr.FILE_TYPES_PCT)

            if not file_path:
                return False

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

        # Load bookmarks with symbol resolution
        self.pct_bookmarks = {int(addr): value for addr, value in content["bookmarks"].items()}

        if utils.is_process_valid(debugcore.currentpid):
            self.recalculate_bookmarks()

        self.pct_address_tree = content["address_tree"]
        self.pct_process_name = content["process_name"]
        self.pct_structures = content.get("structures", {})

        self.file_path = os.path.dirname(file_path)
        self.last_file_name = os.path.basename(file_path)
        self.file_backed = True

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

        settings_instance = QSettings()
        if settings_instance.contains(settings.SAVE_SESSION_ON_EXIT):
            if not settings_instance.value(settings.SAVE_SESSION_ON_EXIT, type=bool):
                return close_event.accept()

            if not self.save_session():
                return close_event.ignore()

            return close_event.accept()

        unsaved_changes = QMessageBox()
        remember_choice = QCheckBox(tr.REMEMBER_MY_DECISION)
        unsaved_changes.setCheckBox(remember_choice)
        unsaved_changes.setWindowTitle(tr.SAVE_SESSION_QUESTION_TITLE)
        unsaved_changes.setText(tr.SAVE_SESSION_QUESTION_PROMPT)
        unsaved_changes.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
        result = QMessageBox.StandardButton(unsaved_changes.exec())

        if result == QMessageBox.StandardButton.Cancel:
            return close_event.ignore()

        if remember_choice.isChecked():
            settings_instance.setValue(settings.SAVE_SESSION_ON_EXIT, result == QMessageBox.StandardButton.Yes)
            settings_instance.sync()

        if result == QMessageBox.StandardButton.Yes:
            if self.save_session():
                close_event.accept()
            else:
                close_event.ignore()
        else:
            close_event.accept()

    def recalculate_bookmarks(self) -> None:
        """
        Recalculate all bookmarks to update their addresses based on their symbols or region info.
        This is useful when the process has changed and the addresses may have shifted.
        Will not mark session as changed.

        Args:
            None
        Returns:
            None
        """

        region_dict = utils.get_region_dict(debugcore.currentpid)

        new_bookmarks: dict[int, dict] = {}
        for addr, value in self.pct_bookmarks.items():
            comment = value["comment"]
            symbol = value["symbol"]
            address_region_details = value["address_region_details"]
            new_addr = addr

            # We used to resolve the symbol first but parentheses in symbols causes the functions to be called
            # For instance, main() won't be resolved to main but rather the function main() will be called
            # Because of this behavior, we rely on resolving via regions
            # Resolving via regions is more reliable unless the binary has been changed
            # TODO: Resolving via symbols could be re-addressed if this behavior were fixed

            # resolve via region details
            region_name = address_region_details["region_name"]
            offset = address_region_details["offset_in_region"]
            region_index = address_region_details["region_index"]
            region = region_dict.get(region_name, None)
            if region is None:
                utils.logger.warning(f"Could not find region with name: {region_name}")
                continue
            if region_index < 0 or region_index >= len(region):
                utils.logger.warning(
                    f"Region '{region_name}' now has {len(region)} mapping(s). " f"Bookmark expected index {region_index}, dropping it..."
                )
                continue
            new_addr = utils.safe_str_to_int(region[region_index], 16) + utils.safe_str_to_int(offset, 16)
            if new_addr == 0:
                continue

            new_bookmarks[new_addr] = {
                "symbol": symbol,
                "comment": comment,
                "address_region_details": address_region_details,
            }

        self.pct_bookmarks = new_bookmarks


class SessionManager:
    session = Session()

    @staticmethod
    def get_session() -> Session:
        return SessionManager.session

    @staticmethod
    def reset_session() -> None:
        session = SessionManager.get_session()
        unsaved_changes_result = session.check_unsaved_changes()
        if unsaved_changes_result == QMessageBox.StandardButton.Cancel:
            return
        if unsaved_changes_result == QMessageBox.StandardButton.Yes:
            if not session.save_session():
                return
        SessionManager.session = Session()
        states.session_signals.new_session.emit()
        SessionManager.session.data_changed = SessionDataChanged.NONE

    @staticmethod
    def save_session() -> None:
        SessionManager.get_session().save_session()

    @staticmethod
    def load_session(file_path: str | None = None) -> None:
        SessionManager.get_session().load_session(file_path)

    @staticmethod
    def on_process_changed() -> None:
        if debugcore.currentpid == -1:
            return

        if states.exiting:
            return

        process_name = utils.get_process_name(debugcore.currentpid)
        session = SessionManager.get_session()

        if session.pct_process_name == process_name:
            # process is the same as last one, probably process restarted / reattached
            session.recalculate_bookmarks()
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
                session = SessionManager.get_session()
                session.pct_process_name = process_name
                session.last_file_name = utils.append_file_extension(process_name, "pct")


class StructureManager:
    @staticmethod
    def _registry() -> dict[str, tuple]:
        return SessionManager.get_session().pct_structures

    @staticmethod
    def list_names() -> list[str]:
        return sorted(StructureManager._registry().keys())

    @staticmethod
    def get(name: str) -> typedefs.Structure | None:
        data = StructureManager._registry().get(name)
        return typedefs.Structure.deserialize(data) if data is not None else None

    @staticmethod
    def add(structure: typedefs.Structure) -> bool:
        registry = StructureManager._registry()
        if structure.name in registry:
            return False
        registry[structure.name] = structure.serialize()
        StructureManager._mark_changed()
        return True

    @staticmethod
    def update(structure: typedefs.Structure) -> None:
        StructureManager._registry()[structure.name] = structure.serialize()
        StructureManager._mark_changed()

    @staticmethod
    def rename(old: str, new: str) -> bool:
        registry = StructureManager._registry()
        if old not in registry or new in registry:
            return False
        registry[new] = registry.pop(old)
        StructureManager._mark_changed()
        return True

    @staticmethod
    def delete(name: str) -> None:
        if StructureManager._registry().pop(name, None) is not None:
            StructureManager._mark_changed()

    @staticmethod
    def _mark_changed() -> None:
        SessionManager.get_session().data_changed |= SessionDataChanged.STRUCTURES
