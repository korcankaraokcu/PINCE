from PyQt6.QtCore import QThread, QRunnable, pyqtSignal, QObject
from libpince import debugcore, typedefs
import queue

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


# Await async output from gdb
class AwaitAsyncOutput(QThread):
    async_output_ready = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue_active = True

    def run(self):
        async_output_queue = debugcore.gdb_async_output.register_queue()
        while self.queue_active:
            try:
                async_output = async_output_queue.get(timeout=5)
            except queue.Empty:
                pass
            else:
                self.async_output_ready.emit(async_output)
        debugcore.gdb_async_output.delete_queue(async_output_queue)

    def stop(self):
        self.queue_active = False


# Checks if the inferior has been terminated
class AwaitProcessExit(QThread):
    process_exited = pyqtSignal()

    def run(self):
        while True:
            with debugcore.process_exited_condition:
                debugcore.process_exited_condition.wait()
            self.process_exited.emit()


# Checks if the inferior is running or stopped
class CheckInferiorStatus(QThread):
    process_stopped = pyqtSignal()
    process_running = pyqtSignal()

    def run(self):
        while True:
            with debugcore.status_changed_condition:
                debugcore.status_changed_condition.wait()
            if debugcore.inferior_status == typedefs.INFERIOR_STATUS.STOPPED:
                self.process_stopped.emit()
            elif debugcore.inferior_status == typedefs.INFERIOR_STATUS.RUNNING:
                self.process_running.emit()
