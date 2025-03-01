from GUI.Widgets.SessionNotes.Form.SessionNotes import Ui_SessionNotes as SessionNotesForm
from GUI.Session.Session import SessionManager, SessionDataChanged
from PyQt6.QtWidgets import QWidget
from GUI.States import states

class SessionNotesWidget(QWidget, SessionNotesForm):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.textEdit_Notes.textChanged.connect(self.on_textEdit_notes_textChanged)
        states.session_signals.on_load.connect(self.on_load)
        states.session_signals.new_session.connect(self.on_new_session)
        self.session = SessionManager.get_session()

    def on_new_session(self):
        self.textEdit_Notes.clear()
        self.session = SessionManager.get_session()

    def on_load(self):
        self.textEdit_Notes.setText(SessionManager.session.pct_notes)
    
    def on_textEdit_notes_textChanged(self):
        SessionManager.session.pct_notes = self.textEdit_Notes.toPlainText()
        SessionManager.session.data_changed |= SessionDataChanged.NOTES

    def toggle_visibility(self):
        self.setVisible(not self.isVisible())