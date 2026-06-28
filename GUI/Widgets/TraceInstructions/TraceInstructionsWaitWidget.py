from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QMovie, QCloseEvent
from PyQt6.QtCore import Qt, QTimer, QByteArray, QSize, pyqtSignal
from GUI.Utils import guitypedefs, guiutils
from GUI.States import states
from GUI.Widgets.TraceInstructions.Form.TraceInstructionsWaitWidget import Ui_Form
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr
from time import sleep


class TraceInstructionsWaitWidget(QWidget, Ui_Form):
    widget_closed = pyqtSignal()

    def __init__(self, parent: QWidget, address: str, tracer: debugcore.Tracer) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.status_to_text = {
            typedefs.TRACE_STATUS.IDLE: tr.WAITING_FOR_BREAKPOINT,
            typedefs.TRACE_STATUS.FINISHED: tr.TRACING_COMPLETED,
        }
        self.setWindowFlags(Qt.WindowType.Window)
        self.address = address
        self.tracer = tracer
        media_directory = utils.get_media_directory()
        self.movie = QMovie(media_directory + "/TraceInstructionsWaitWidget/ajax-loader.gif", QByteArray())
        self.label_Animated.setMovie(self.movie)
        self.movie.setScaledSize(QSize(215, 100))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.setSpeed(100)
        self.movie.start()
        self.pushButton_Cancel.clicked.connect(self.close)
        tracer_thread = guitypedefs.Worker(tracer.tracer_loop)
        tracer_thread.signals.finished.connect(self.close)
        states.threadpool.start(tracer_thread)
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(50)
        self.status_timer.timeout.connect(self.change_status)
        self.status_timer.start()
        guiutils.center_to_parent(self)

    def change_status(self) -> None:
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.label_StatusText.setText(f"{self.tracer.current_trace_count} / {self.tracer.max_trace_count}")
        else:
            self.label_StatusText.setText(self.status_to_text[self.tracer.trace_status])
        QApplication.processEvents()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.status_timer.stop()
        self.label_StatusText.setText(tr.TRACING_COMPLETED)
        self.pushButton_Cancel.setVisible(False)
        self.adjustSize()
        QApplication.processEvents()
        if self.tracer.trace_status == typedefs.TRACE_STATUS.TRACING:
            self.tracer.cancel_trace()
            while self.tracer.trace_status != typedefs.TRACE_STATUS.FINISHED:
                sleep(0.1)
                QApplication.processEvents()
        self.widget_closed.emit()
        super().closeEvent(event)
