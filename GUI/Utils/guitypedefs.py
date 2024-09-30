from PyQt6.QtCore import QThread, QRunnable, pyqtSignal, QObject

# Docstrings of pyqtSignal causes Sphinx to throw a warning about inline emphasis strings
# The hack below overwrites the docstrings of pyqtSignal so we avoid the warnings
# TODO: Wait for Qt to fix this issue or find a better way of handling this

pyqtSignal.__doc__ = "pyqtSignal"


class WorkerSignals(QObject):
    finished = pyqtSignal()


class ProcessSignals(QObject):
    attach = pyqtSignal()
    exit = pyqtSignal()


class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()


class InterruptableWorker(QThread):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()

    def stop(self):
        self.terminate()
