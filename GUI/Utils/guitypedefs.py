from PyQt6.QtCore import QThread, QRunnable, pyqtSignal, QObject
from keyboard import add_hotkey, remove_hotkey
from typing import Callable
from tr.tr import TranslationConstants as tr
from libpince import debugcore, typedefs
import queue

# Docstrings of pyqtSignal causes Sphinx to throw a warning about inline emphasis strings
# The hack below overwrites the docstrings of pyqtSignal so we avoid the warnings
# TODO: Wait for Qt to fix this issue or find a better way of handling this

pyqtSignal.__doc__ = "pyqtSignal"


class SettingSignals(QObject):
    changed = pyqtSignal()


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


class Hotkey:
    def __init__(self, name="", desc="", default="", func=None, custom="", handle=None) -> None:
        self.name = name
        self.desc = desc
        self.default = default
        self.func = func
        self.custom = custom
        if default == "" or func is None:
            self.handle = handle
        else:
            self.handle = add_hotkey(default, func)

    def change_key(self, custom: str) -> None:
        if self.handle is not None:
            remove_hotkey(self.handle)
            self.handle = None
        self.custom = custom
        if custom == "":
            return
        self.handle = add_hotkey(custom.lower(), self.func)

    def change_func(self, func: Callable) -> None:
        self.func = func
        if self.handle is not None:
            remove_hotkey(self.handle)
        if self.custom != "":
            self.handle = add_hotkey(self.custom, func)
        elif self.default != "":
            self.handle = add_hotkey(self.default, func)

    def get_active_key(self) -> str:
        if self.custom == "":
            return self.default
        return self.custom


class Hotkeys:
    def __init__(self) -> None:
        self.pause_hotkey = Hotkey("pause_hotkey", tr.PAUSE_HOTKEY, "F1")
        self.break_hotkey = Hotkey("break_hotkey", tr.BREAK_HOTKEY, "F2")
        self.continue_hotkey = Hotkey("continue_hotkey", tr.CONTINUE_HOTKEY, "F3")
        self.toggle_attach_hotkey = Hotkey("toggle_attach_hotkey", tr.TOGGLE_ATTACH_HOTKEY, "Shift+F10")
        self.exact_scan_hotkey = Hotkey("exact_scan_hotkey", tr.EXACT_SCAN_HOTKEY, "")
        self.not_scan_hotkey = Hotkey("not_scan_hotkey", tr.NOT_SCAN_HOTKEY, "")
        self.increased_scan_hotkey = Hotkey("increased_scan_hotkey", tr.INC_SCAN_HOTKEY, "")
        self.increased_by_scan_hotkey = Hotkey("increased_by_scan_hotkey", tr.INC_BY_SCAN_HOTKEY, "")
        self.decreased_scan_hotkey = Hotkey("decreased_scan_hotkey", tr.DEC_SCAN_HOTKEY, "")
        self.decreased_by_scan_hotkey = Hotkey("decreased_by_scan_hotkey", tr.DEC_BY_SCAN_HOTKEY, "")
        self.less_scan_hotkey = Hotkey("less_scan_hotkey", tr.LESS_SCAN_HOTKEY, "")
        self.more_scan_hotkey = Hotkey("more_scan_hotkey", tr.MORE_SCAN_HOTKEY, "")
        self.between_scan_hotkey = Hotkey("between_scan_hotkey", tr.BETWEEN_SCAN_HOTKEY, "")
        self.changed_scan_hotkey = Hotkey("changed_scan_hotkey", tr.CHANGED_SCAN_HOTKEY, "")
        self.unchanged_scan_hotkey = Hotkey("unchanged_scan_hotkey", tr.UNCHANGED_SCAN_HOTKEY, "")

    def get_hotkeys(self) -> list[Hotkey]:
        hotkey_list = []
        for _, value in vars(self).items():
            if isinstance(value, Hotkey):
                hotkey_list.append(value)
        return hotkey_list
