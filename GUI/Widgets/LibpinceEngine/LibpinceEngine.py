from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QPlainTextEdit,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
    QTabWidget,
)
from PyQt6.QtGui import QKeySequence
from GUI.Utils import guiutils
from GUI.Widgets.LibpinceEngine.Form.LibpinceEngineWindow import Ui_MainWindow
from tr.tr import TranslationConstants as tr
from libpince import utils
import os


class ScriptEditor(QPlainTextEdit):
    """Custom text editor that tracks modifications"""

    def __init__(self, tab_widget: QTabWidget):
        super().__init__()
        self.file_path = None
        self.saved_content = ""
        self.is_modified = False
        self.tab_widget = tab_widget
        self.textChanged.connect(self.handle_text_changed)

    def handle_text_changed(self):
        """Check if content differs from saved content and update tab title"""
        current_content = self.toPlainText()
        new_modified_state = current_content != self.saved_content

        if new_modified_state != self.is_modified:
            self.is_modified = new_modified_state
            self.update_tab_title()

    def update_tab_title(self):
        """Updates the tab title based on modification state"""
        parent_tab = self.parent()
        if parent_tab:
            index = self.tab_widget.indexOf(parent_tab)
            if self.file_path:
                base_title = os.path.basename(self.file_path)
                title = f"{base_title}*" if self.is_modified else base_title
            else:
                title = tr.UNTITLED
            self.tab_widget.setTabText(index, title)


class LibpinceEngineWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)

        # Remove the default tab
        self.tabWidget.removeTab(0)
        self.create_new_tab()
        self.add_plus_tab()

        self.actionOpen.setShortcut(QKeySequence("Ctrl+O"))
        self.actionSave.setShortcut(QKeySequence("Ctrl+S"))
        self.actionRun_current_script.setShortcut(QKeySequence("Ctrl+R"))

        self.tabWidget.tabBarClicked.connect(self.handle_tab_click)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.actionOpen.triggered.connect(self.open_file)
        self.actionSave.triggered.connect(self.save_file)
        self.actionLibpince.triggered.connect(self.actionLibpince_triggered)
        self.actionRun_current_script.triggered.connect(self.run_current_script)
        guiutils.center_to_parent(self)

    def add_plus_tab(self):
        """Adds the "+" tab at the end of the tab widget"""
        plus_tab = QWidget()
        index = self.tabWidget.addTab(plus_tab, "+")
        # Remove close button for the "+" tab
        self.tabWidget.tabBar().setTabButton(index, self.tabWidget.tabBar().ButtonPosition.RightSide, None)

    def create_new_tab(self):
        """Creates a new tab with a text editor"""
        new_tab = QWidget()
        layout = QVBoxLayout(new_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        text_editor = ScriptEditor(self.tabWidget)
        layout.addWidget(text_editor)

        # Add the new tab before the "+" tab
        index = self.tabWidget.count() - 1 if self.tabWidget.count() > 0 else 0
        self.tabWidget.insertTab(index, new_tab, tr.UNTITLED)

        # Select the new tab
        self.tabWidget.setCurrentIndex(index)

        return text_editor

    def get_current_editor(self) -> ScriptEditor | None:
        """Gets the text editor of the current tab"""
        current_tab = self.tabWidget.currentWidget()
        if current_tab:
            return current_tab.findChild(ScriptEditor)
        return None

    def handle_tab_click(self, index: int):
        """Handles tab clicks, creates new tab when "+" is clicked"""
        if index == self.tabWidget.count() - 1:  # If "+" tab is clicked
            self.create_new_tab()

    def close_tab(self, index: int):
        """Handles tab closing, prevents closing the "+" tab"""
        if index != self.tabWidget.count() - 1:  # Don't close "+" tab
            current_index = self.tabWidget.currentIndex()
            self.tabWidget.removeTab(index)

            # Switch to previous tab if we're closing the current tab
            if index == current_index and index > 0:
                self.tabWidget.setCurrentIndex(index - 1)

    def open_file(self):
        """Opens a Python script file in a new tab"""
        file_path, _ = QFileDialog.getOpenFileName(self, tr.OPEN_SCRIPT_FILE, "", tr.FILE_TYPES_SCRIPT)

        if file_path:
            editor = self.create_new_tab()

            try:
                with open(file_path, "r") as file:
                    content = file.read()
                    editor.setPlainText(content)
                    editor.file_path = file_path
                    editor.saved_content = content
                    editor.is_modified = False
                    editor.update_tab_title()
            except Exception as e:
                QMessageBox.critical(self, tr.ERROR, str(e))

    def save_file(self):
        """Saves the current tab's content to a file"""
        editor = self.get_current_editor()
        if not editor:
            return

        # If file hasn't been saved before, ask for location
        if not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, tr.SAVE_SCRIPT_FILE, "", tr.FILE_TYPES_SCRIPT)
            if not file_path:
                return

            # Ensure .py extension
            if not file_path.lower().endswith(".py"):
                file_path += ".py"

            editor.file_path = file_path

        try:
            with open(editor.file_path, "w") as file:
                content = editor.toPlainText()
                file.write(content)
                editor.saved_content = content
                editor.is_modified = False
                editor.update_tab_title()
        except Exception as e:
            QMessageBox.critical(self, tr.ERROR, str(e))

    def run_current_script(self):
        """Runs the current tab's script content"""
        editor = self.get_current_editor()
        if not editor:
            return

        try:
            script_content = editor.toPlainText()
            if not script_content.strip():
                return

            # Execute the script with full access to current context
            exec(script_content, globals(), locals())
        except Exception as e:
            QMessageBox.critical(self, tr.ERROR, f"{tr.SCRIPT_FAILED}\n{str(e)}")

    def actionLibpince_triggered(self):
        utils.execute_command_as_user('python3 -m webbrowser "https://korcankaraokcu.github.io/PINCE/"')
