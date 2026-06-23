from PyQt6.QtWidgets import QDialog, QWidget
from PyQt6.QtGui import QCloseEvent, QMovie
from PyQt6.QtCore import QEvent, QByteArray, QSize, QThread, pyqtSignal
from GUI.Utils import guiutils
from GUI.Widgets.LoadingDialog.Form.LoadingDialog import Ui_Dialog
from libpince import debugcore, utils
from libpince.utils import logger
from typing import Any
import traceback


class LoadingDialog(QDialog, Ui_Dialog):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags())
        self.keyPressEvent = QEvent.ignore

        # Make use of this background_thread when you spawn a LoadingDialog
        # Warning: overrided_func() can only return one value, so if your overridden function returns more than one
        # value, refactor your overriden function to return only one object(convert tuple to list etc.)
        # Check refresh_table method of FunctionsInfoWidget for exemplary usage
        self.background_thread = self.BackgroundThread()
        self.background_thread.output_ready.connect(self.accept)
        self.pushButton_Cancel.clicked.connect(self.close)
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/LoadingDialog/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(25, 25))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        guiutils.center_to_parent(self)

    # TODO: This function only cancels the last command sent, redesign this if it's needed to cancel non-gdb functions
    def cancel_thread(self) -> None:
        debugcore.cancel_ongoing_command()
        self.background_thread.wait()

    def exec(self) -> None:
        self.background_thread.start()
        super().exec()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_thread()
        super().closeEvent(event)

    class BackgroundThread(QThread):
        output_ready = pyqtSignal(object)

        def __init__(self) -> None:
            super().__init__()

        # Unhandled exceptions in this thread freezes PINCE
        def run(self) -> None:
            try:
                output = self.overrided_func()
            except:
                traceback.print_exc()
                output = None
            self.output_ready.emit(output)

        def overrided_func(self) -> Any:
            logger.debug("Override this function")
            return 0
