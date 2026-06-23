from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from GUI.Utils import guiutils
from GUI.Widgets.StackTraceInfo.Form.StackTraceInfoWidget import Ui_Form
from libpince import debugcore


class StackTraceInfoWidget(QWidget, Ui_Form):
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
