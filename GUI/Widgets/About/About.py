from PyQt6.QtWidgets import QTabWidget, QWidget
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Widgets.About.Form.AboutWidget import Ui_TabWidget
from libpince import utils


class AboutWidget(QTabWidget, Ui_TabWidget):
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
