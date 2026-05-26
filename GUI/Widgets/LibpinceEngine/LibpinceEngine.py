import builtins, contextlib, io, os, traceback

from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from GUI.Utils import guiutils
from GUI.Widgets.LibpinceEngine.Form.LibpinceEngineWindow import Ui_MainWindow
from GUI.Widgets.LibpinceEngine.ScriptEditor import ScriptEditor
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr


class LibpinceScriptApi:
    """Class to 'alias' certain libpince functions for easier user experience."""

    int_index_by_size = {
        1: typedefs.VALUE_INDEX.INT8,
        2: typedefs.VALUE_INDEX.INT16,
        4: typedefs.VALUE_INDEX.INT32,
        8: typedefs.VALUE_INDEX.INT64,
    }
    string_index_by_encoding = {
        "ascii": typedefs.VALUE_INDEX.STRING_ASCII,
        "utf8": typedefs.VALUE_INDEX.STRING_UTF8,
        "utf-8": typedefs.VALUE_INDEX.STRING_UTF8,
        "utf16": typedefs.VALUE_INDEX.STRING_UTF16,
        "utf-16": typedefs.VALUE_INDEX.STRING_UTF16,
        "utf32": typedefs.VALUE_INDEX.STRING_UTF32,
        "utf-32": typedefs.VALUE_INDEX.STRING_UTF32,
    }

    def address(self, expression) -> int:
        """Return an integer address from an int, hex string, register, symbol, or GDB expression."""
        if isinstance(expression, int):
            return expression
        if not isinstance(expression, str):
            raise TypeError("address expects int or str")
        try:
            return int(expression, 0)
        except ValueError:
            pass
        info = debugcore.examine_expression(expression)
        for value in (info.address, info.all):
            if not value:
                continue
            extracted = utils.extract_hex_address(value)
            if extracted:
                return int(extracted, 16)
            try:
                return int(value, 0)
            except ValueError:
                pass
        raise ValueError(f"Could not resolve address expression: {expression}")

    def read_int(self, address, size=4, signed=False):
        """Read an integer. size can be 1, 2, 4, or 8."""
        value_index = self.int_index_by_size[int(size)]
        value_repr = typedefs.VALUE_REPR.SIGNED if signed else typedefs.VALUE_REPR.UNSIGNED
        return debugcore.read_memory(self.address(address), value_index, value_repr=value_repr)

    def write_int(self, value, address, size=4):
        """Write an integer. size can be 1, 2, 4, or 8."""
        value_index = self.int_index_by_size[int(size)]
        debugcore.write_memory(self.address(address), value_index, int(value))

    def read_float(self, address, double=False):
        """Read a 32-bit float, or a 64-bit float when double=True."""
        value_index = typedefs.VALUE_INDEX.FLOAT64 if double else typedefs.VALUE_INDEX.FLOAT32
        return debugcore.read_memory(self.address(address), value_index)

    def write_float(self, value, address, double=False):
        """Write a 32-bit float, or a 64-bit float when double=True."""
        value_index = typedefs.VALUE_INDEX.FLOAT64 if double else typedefs.VALUE_INDEX.FLOAT32
        debugcore.write_memory(self.address(address), value_index, float(value))

    def read_string(self, address, length=128, encoding="utf8", zero_terminate=True):
        """Read a string using ascii, utf8, utf16, or utf32."""
        value_index = self.string_index_by_encoding[encoding.lower()]
        return debugcore.read_memory(self.address(address), value_index, int(length), zero_terminate=zero_terminate)

    def write_string(self, value, address, encoding="utf8", zero_terminate=True):
        """Write a string using ascii, utf8, utf16, or utf32."""
        value_index = self.string_index_by_encoding[encoding.lower()]
        debugcore.write_memory(self.address(address), value_index, str(value), zero_terminate=zero_terminate)

    def read_bytes(self, address, length):
        """Read bytes from the inferior and return a bytes object."""
        aob = debugcore.read_memory(self.address(address), typedefs.VALUE_INDEX.AOB, int(length))
        return bytes.fromhex(aob) if aob else b""

    def write_bytes(self, data, address):
        """Write bytes where data can be bytes, bytearray, list[int], or a hex string."""
        data = self._bytes(data)
        debugcore.write_memory(self.address(address), typedefs.VALUE_INDEX.AOB, data.hex(" "))

    def patch(self, data, address, expected=None):
        """Patch instruction bytes, optionally verifying the original bytes first.
           Can be restored using restore(address).
        """
        data = self._bytes(data)
        address = self.address(address)
        if expected is not None:
            original = self.read_bytes(address, len(data))
            if original != self._bytes(expected):
                raise RuntimeError(f"Patch mismatch at {address:#x}: expected {expected}, found {original.hex(' ')}")
        debugcore.modify_instruction(address, data.hex(" "))

    def nop(self, address, length):
        """Replace length bytes at address with NOP instructions.
           Can be restored using restore(address).
        """
        debugcore.nop_instruction(self.address(address), int(length))

    def restore(self, address):
        """Restore bytes previously changed through nop_instruction (nop) or modify_instruction (patch)."""
        debugcore.restore_instruction(self.address(address))

    def alloc(self, size, name=None):
        """Allocate executable memory in the inferior and return its address."""
        return debugcore.allocate_memory(int(size), name)

    def dealloc(self, name):
        """Free memory allocated with alloc(size, name)."""
        return debugcore.free_memory(str(name))

    def assemble(self, instructions, address=0):
        """Assemble instructions at address and return bytes."""
        result = utils.assemble(str(instructions), self.address(address) if address else 0, debugcore.inferior_arch)
        return bytes(result[0]) if result else b""

    def disassemble_bytes(self, data, address=0):
        """Disassemble bytes and return a semicolon-separated instruction string."""
        return utils.disassemble(self._bytes(data).hex(" "), self.address(address) if address else 0, debugcore.inferior_arch)

    def module_base(self, name):
        """Return the first mapped base address for a module by basename (e.g. 'libc.so.6')."""
        if debugcore.currentpid == -1:
            raise RuntimeError("No process is attached!")
        needle = str(name).lower()
        return next(
            (int(start, 16) for start, *_, path in utils.get_regions(debugcore.currentpid)
             if path and os.path.basename(path).lower() == needle),
            None,
        )

    def regs(self):
        """Return current general-purpose registers."""
        return debugcore.read_registers()

    def reg(self, name):
        """Read one register from read_registers(), with or without a leading '$'."""
        registers = self.regs()
        raw = str(name)
        return registers.get(raw) or registers.get(raw.lstrip("$")) or registers.get("$" + raw.lstrip("$"))

    def set_reg(self, name, value):
        """Set a register through GDB."""
        return debugcore.send_command(f"set ${str(name).lstrip('$')} = {value}", cli_output=True)

    def gdb(self, command, cli_output=True):
        """Run a GDB command and return its output."""
        return debugcore.send_command(str(command), cli_output=cli_output)

    def aobscan_first(self, pattern, writable=None, executable=None):
        """Return the first address matching an AOB pattern, or None."""
        matches = self.aobscan(pattern, writable=writable, executable=executable, limit=1)
        return matches[0] if matches else None

    def aobscan(self, pattern, writable=None, executable=None, limit=1000):
        """Scan readable maps for an AOB pattern. Wildcards can be '?' or '??'."""
        if debugcore.currentpid == -1:
            raise RuntimeError("No process is attached!")
        return debugcore.aob_scan(str(pattern), writable=writable, executable=executable, limit=limit)

    def _bytes(self, data):
        if isinstance(data, str):
            return bytes.fromhex(data.replace(" ", ""))
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        return bytes(int(item) & 0xFF for item in data)


class LibpinceEngineWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.configure_editor(self.scriptEditor)
        index = self.tabWidget.indexOf(self.plusTab)
        tab_bar = self.tabWidget.tabBar()
        tab_bar.setTabButton(index, tab_bar.ButtonPosition.LeftSide, None)
        tab_bar.setTabButton(index, tab_bar.ButtonPosition.RightSide, None)

        for action in (
            self.actionCode_injection,
            self.actionAOB_scan_nop,
            self.actionAOB_scan_patch,
            self.actionRead_write_address,
        ):
            action.triggered.connect(lambda checked=False, a=action: self.insert_template(a.property("data")))
        self.tabWidget.tabBarClicked.connect(self.handle_tab_click)
        self.tabWidget.tabCloseRequested.connect(self.close_tab)
        self.actionOpen.triggered.connect(self.open_file)
        self.actionSave.triggered.connect(self.save_file)
        self.actionLibpince.triggered.connect(self.actionLibpince_triggered)
        self.actionRun_current_script.triggered.connect(self.run_current_script)
        self.actionRun_selection.triggered.connect(self.run_selection)
        self.actionClear_output.triggered.connect(self.outputEdit.clear)
        if parent is not None:
            guiutils.center_to_parent(self)

    def configure_editor(self, editor):
        editor.bind_tab_widget(self.tabWidget)
        editor.set_namespace(self.create_script_namespace())
        editor.update_line_number_area_width()

    def create_script_namespace(self):
        api = LibpinceScriptApi()
        namespace = {
            "__builtins__": builtins,
            "__name__": "__libpince_engine__",
            "api": api,
            "debugcore": debugcore,
            "typedefs": typedefs,
            "utils": utils,
            "VALUE_INDEX": typedefs.VALUE_INDEX,
            "VALUE_REPR": typedefs.VALUE_REPR,
        }
        for name in dir(api):
            function = getattr(api, name)
            if not name.startswith("_") and callable(function):
                namespace[name] = function
        return namespace

    def create_new_tab(self):
        new_tab = QWidget()
        layout = QVBoxLayout(new_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        text_editor = ScriptEditor(new_tab)
        text_editor.setFont(self.scriptEditor.font())
        text_editor.setLineWrapMode(self.scriptEditor.lineWrapMode())
        text_editor.setTabStopDistance(self.scriptEditor.tabStopDistance())
        self.configure_editor(text_editor)
        layout.addWidget(text_editor)
        index = self.tabWidget.indexOf(self.plusTab)
        self.tabWidget.insertTab(index, new_tab, tr.UNTITLED)
        self.tabWidget.setCurrentIndex(index)
        return text_editor

    def get_current_editor(self):
        current_tab = self.tabWidget.currentWidget()
        return current_tab.findChild(ScriptEditor) if current_tab else None

    def handle_tab_click(self, index: int):
        if index == self.tabWidget.count() - 1:
            self.create_new_tab()

    def close_tab(self, index: int):
        if index == self.tabWidget.count() - 1:
            return
        editor = self.tabWidget.widget(index).findChild(ScriptEditor)
        if editor and editor.is_modified:
            result = QMessageBox.question(
                self,
                tr.UNSAVED_SCRIPT,
                tr.SAVE_SCRIPT_CHANGES.format(self.tabWidget.tabText(index).rstrip("*")),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Cancel:
                return
            if result == QMessageBox.StandardButton.Save:
                self.tabWidget.setCurrentIndex(index)
                self.save_file()
                if editor.is_modified:
                    return
        current_index = self.tabWidget.currentIndex()
        self.tabWidget.removeTab(index)
        if index == current_index and index > 0:
            self.tabWidget.setCurrentIndex(index - 1)

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr.OPEN_SCRIPT_FILE, "", tr.FILE_TYPES_SCRIPT)
        if not file_path:
            return
        editor = self.create_new_tab()
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            editor.setPlainText(content)
            editor.file_path = file_path
            editor.saved_content = content
            editor.is_modified = False
            editor.update_tab_title()
        except Exception as e:
            QMessageBox.critical(self, tr.ERROR, str(e))

    def save_file(self):
        editor = self.get_current_editor()
        if not editor:
            return
        if not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(self, tr.SAVE_SCRIPT_FILE, "", tr.FILE_TYPES_SCRIPT)
            if not file_path:
                return
            if not file_path.lower().endswith(".py"):
                file_path += ".py"
            editor.file_path = file_path
        try:
            with open(editor.file_path, "w", encoding="utf-8") as file:
                content = editor.toPlainText()
                file.write(content)
            editor.saved_content = content
            editor.is_modified = False
            editor.update_tab_title()
        except Exception as e:
            QMessageBox.critical(self, tr.ERROR, str(e))

    def run_current_script(self):
        editor = self.get_current_editor()
        if editor:
            self.run_script(editor, editor.toPlainText())

    def run_selection(self):
        editor = self.get_current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        script = cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else editor.toPlainText()
        self.run_script(editor, script)

    def run_script(self, editor, script_content):
        if not script_content.strip():
            return
        filename = editor.file_path or f"<Libpince Engine: {self.tabWidget.tabText(self.tabWidget.currentIndex())}>"
        namespace = editor.namespace or self.create_script_namespace()
        namespace["__file__"] = filename
        stdout = io.StringIO()
        stderr = io.StringIO()
        self.append_output("\n" + tr.SCRIPT_RUNNING.format(filename))
        try:
            compiled = compile(script_content, filename, "exec")
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compiled, namespace, namespace)
        except Exception:
            self.append_output(stdout.getvalue())
            self.append_output(stderr.getvalue())
            self.append_output(traceback.format_exc())
            self.statusbar.showMessage(tr.SCRIPT_FAILED, 3000)
            return
        finally:
            editor.set_namespace(namespace)
        self.append_output(stdout.getvalue())
        self.append_output(stderr.getvalue())
        self.append_output(tr.SCRIPT_FINISHED)
        self.statusbar.showMessage(tr.SCRIPT_FINISHED, 3000)

    def append_output(self, text):
        if not text:
            return
        self.outputEdit.moveCursor(QTextCursor.MoveOperation.End)
        self.outputEdit.insertPlainText(text if text.endswith("\n") else text + "\n")
        self.outputEdit.moveCursor(QTextCursor.MoveOperation.End)

    def insert_template(self, template):
        editor = self.get_current_editor()
        if editor:
            editor.textCursor().insertText(template)
            editor.setFocus()

    def actionLibpince_triggered(self):
        utils.execute_command_as_user('python3 -m webbrowser "https://korcankaraokcu.github.io/PINCE/"')
