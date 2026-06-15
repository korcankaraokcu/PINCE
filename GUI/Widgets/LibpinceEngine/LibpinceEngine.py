import builtins, contextlib, io, os, traceback
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from GUI.Utils import guiutils
from GUI.Widgets.LibpinceEngine.Form.LibpinceEngineWindow import Ui_MainWindow
from GUI.Widgets.LibpinceEngine.ScriptEditor import ScriptEditor
from libpince import debugcore, typedefs, utils
from tr.tr import TranslationConstants as tr

# Accepted input for byte-oriented helpers: a hex string, a bytes-like object, or a list of byte values
BytesLike = bytes | bytearray | memoryview | str | list[int]

ENABLE_TAG = "[ENABLE]"
DISABLE_TAG = "[DISABLE]"


def parse_script_sections(script: str) -> tuple[str, str | None]:
    """Split a toggle script into runnable (enable, disable) section code.

    Sections are marked by [ENABLE] or [DISABLE] (case-insensitive, surrounding whitespace ignored).
    Code before the first tag is the prelude and runs before both halves.
    Tag lines and the half that isn't being run are blanked rather than removed
    so traceback line numbers still match the editor.
    A tagless script is returned as (whole script, None) so it keeps running whole.
    """
    lines = script.splitlines()
    enable_line = disable_line = None
    for i, line in enumerate(lines):
        tag = line.strip().upper()
        if tag == ENABLE_TAG and enable_line is None:
            enable_line = i
        elif tag == DISABLE_TAG and disable_line is None:
            disable_line = i
    if enable_line is None or disable_line is None:
        return script, None
    tags = sorted((enable_line, disable_line))
    prelude_end = tags[0]

    def body(tag_line: int) -> str:
        end = next((t for t in tags if t > tag_line), len(lines))
        return "\n".join(ln if i < prelude_end or tag_line < i < end else "" for i, ln in enumerate(lines))

    return body(enable_line), body(disable_line)


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

    def address(self, expression: int | str) -> int:
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

    def read_int(self, address: int | str, size: int = 4, signed: bool = False) -> int | None:
        """Read an integer. size can be 1, 2, 4, or 8."""
        value_index = self.int_index_by_size[int(size)]
        value_repr = typedefs.VALUE_REPR.SIGNED if signed else typedefs.VALUE_REPR.UNSIGNED
        return debugcore.read_memory(self.address(address), value_index, value_repr=value_repr)

    def write_int(self, value: int, address: int | str, size: int = 4) -> None:
        """Write an integer. size can be 1, 2, 4, or 8."""
        value_index = self.int_index_by_size[int(size)]
        debugcore.write_memory(self.address(address), value_index, int(value))

    def read_float(self, address: int | str, double: bool = False) -> float | None:
        """Read a 32-bit float, or a 64-bit float when double=True."""
        value_index = typedefs.VALUE_INDEX.FLOAT64 if double else typedefs.VALUE_INDEX.FLOAT32
        return debugcore.read_memory(self.address(address), value_index)

    def write_float(self, value: float, address: int | str, double: bool = False) -> None:
        """Write a 32-bit float, or a 64-bit float when double=True."""
        value_index = typedefs.VALUE_INDEX.FLOAT64 if double else typedefs.VALUE_INDEX.FLOAT32
        debugcore.write_memory(self.address(address), value_index, float(value))

    def read_string(
        self, address: int | str, length: int = 128, encoding: str = "utf8", zero_terminate: bool = True
    ) -> str | None:
        """Read a string using ascii, utf8, utf16, or utf32."""
        value_index = self.string_index_by_encoding[encoding.lower()]
        return debugcore.read_memory(self.address(address), value_index, int(length), zero_terminate=zero_terminate)

    def write_string(self, value: str, address: int | str, encoding: str = "utf8", zero_terminate: bool = True) -> None:
        """Write a string using ascii, utf8, utf16, or utf32."""
        value_index = self.string_index_by_encoding[encoding.lower()]
        debugcore.write_memory(self.address(address), value_index, str(value), zero_terminate=zero_terminate)

    def read_bytes(self, address: int | str, length: int) -> bytes:
        """Read bytes from the inferior and return a bytes object."""
        aob = debugcore.read_memory(self.address(address), typedefs.VALUE_INDEX.AOB, int(length))
        return bytes.fromhex(aob) if aob else b""

    def write_bytes(self, data: BytesLike, address: int | str) -> None:
        """Write bytes where data can be bytes, bytearray, list[int], or a hex string."""
        data = self._bytes(data)
        debugcore.write_memory(self.address(address), typedefs.VALUE_INDEX.AOB, data.hex(" "))

    def patch(self, data: BytesLike, address: int | str, expected: BytesLike | None = None) -> None:
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

    def nop(self, address: int | str, length: int) -> None:
        """Replace length bytes at address with NOP instructions.
        Can be restored using restore(address).
        """
        debugcore.nop_instruction(self.address(address), int(length))

    def restore(self, address: int | str) -> None:
        """Restore bytes previously changed through nop_instruction (nop) or modify_instruction (patch)."""
        debugcore.restore_instruction(self.address(address))

    def alloc(self, size: int, name: str | None = None) -> int:
        """Allocate executable memory in the inferior and return its address."""
        return debugcore.allocate_memory(int(size), name)

    def dealloc(self, name: str) -> bool:
        """Free memory allocated with alloc(size, name)."""
        return debugcore.free_memory(str(name))

    def assemble(self, instructions: str, address: int | str = 0) -> bytes:
        """Assemble instructions at address and return bytes."""
        result = utils.assemble(str(instructions), self.address(address) if address else 0, debugcore.inferior_arch)
        return bytes(result[0]) if result else b""

    def disassemble_bytes(self, data: BytesLike, address: int | str = 0) -> str | None:
        """Disassemble bytes and return a semicolon-separated instruction string."""
        return utils.disassemble(
            self._bytes(data).hex(" "), self.address(address) if address else 0, debugcore.inferior_arch
        )

    def module_base(self, name: str) -> int | None:
        """Return the first mapped base address for a module by basename (e.g. 'libc.so.6')."""
        if debugcore.currentpid == -1:
            raise RuntimeError("No process is attached!")
        needle = str(name).lower()
        return next(
            (
                int(start, 16)
                for start, *_, path in utils.get_regions(debugcore.currentpid)
                if path and os.path.basename(path).lower() == needle
            ),
            None,
        )

    def regs(self) -> dict[str, str | None]:
        """Return current general-purpose registers."""
        return debugcore.read_registers()

    def reg(self, name: str) -> str | None:
        """Read one register from read_registers(), with or without a leading '$'."""
        registers = self.regs()
        raw = str(name)
        return registers.get(raw) or registers.get(raw.lstrip("$")) or registers.get("$" + raw.lstrip("$"))

    def set_reg(self, name: str, value: Any) -> Any:
        """Set a register through GDB."""
        return debugcore.send_command(f"set ${str(name).lstrip('$')} = {value}", cli_output=True)

    def gdb(self, command: str, cli_output: bool = True) -> Any:
        """Run a GDB command and return its output."""
        return debugcore.send_command(str(command), cli_output=cli_output)

    def aobscan_first(self, pattern: str, writable: bool | None = None, executable: bool | None = None) -> int | None:
        """Return the first address matching an AOB pattern, or None."""
        matches = self.aobscan(pattern, writable=writable, executable=executable, limit=1)
        return matches[0] if matches else None

    def aobscan(
        self, pattern: str, writable: bool | None = None, executable: bool | None = None, limit: int = 1000
    ) -> list[int]:
        """Scan readable maps for an AOB pattern. Wildcards can be '?' or '??'."""
        if debugcore.currentpid == -1:
            raise RuntimeError("No process is attached!")
        return debugcore.aob_scan(str(pattern), writable=writable, executable=executable, limit=limit)

    def _bytes(self, data: BytesLike) -> bytes:
        if isinstance(data, str):
            return bytes.fromhex(data.replace(" ", ""))
        if isinstance(data, (bytes, bytearray, memoryview)):
            return bytes(data)
        return bytes(int(item) & 0xFF for item in data)


def create_script_namespace() -> dict[str, Any]:
    """Build a fresh execution namespace exposing the LibpinceScriptApi helpers."""
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


def run_script_code(script_content: str, namespace: dict[str, Any], filename: str) -> tuple[bool, str]:
    """Compile and exec script_content in namespace, capturing its combined output.

    Returns (succeeded, output).
    Namespace is mutated in place so variables set by an [ENABLE] run survive into a later [DISABLE] run.
    Used by the engine window and any headless caller (e.g. address-table script entries).
    """
    namespace["__file__"] = filename
    output = io.StringIO()
    succeeded = True
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(script_content, filename, "exec"), namespace, namespace)
    except Exception:
        traceback.print_exc(file=output)
        succeeded = False
    return succeeded, output.getvalue()


class LibpinceEngineWindow(QMainWindow, Ui_MainWindow):
    # Emitted with (title, entry) when the user pushes the current editor to the address table
    send_to_table = pyqtSignal(str, object)
    # Emitted when a tab bound to a table script entry is edited, so the session can be marked dirty
    entry_modified = pyqtSignal()

    def __init__(self, parent: QWidget | None) -> None:
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
        self.actionRun_enable.triggered.connect(self.run_enable)
        self.actionRun_disable.triggered.connect(self.run_disable)
        self.actionRun_selection.triggered.connect(self.run_selection)
        self.actionSend_to_table.triggered.connect(self.send_to_cheat_table)
        self.actionClear_output.triggered.connect(self.outputEdit.clear)
        if parent is not None:
            guiutils.center_to_parent(self)

    def configure_editor(self, editor: ScriptEditor) -> None:
        editor.bind_tab_widget(self.tabWidget)
        editor.set_namespace(create_script_namespace())
        editor.update_line_number_area_width()

    def create_new_tab(self) -> ScriptEditor:
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

    def get_current_editor(self) -> ScriptEditor | None:
        current_tab = self.tabWidget.currentWidget()
        return current_tab.findChild(ScriptEditor) if current_tab else None

    def handle_tab_click(self, index: int) -> None:
        if index == self.tabWidget.count() - 1:
            self.create_new_tab()

    def close_tab(self, index: int) -> None:
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

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr.OPEN_SCRIPT_FILE, os.path.expanduser("~"), tr.FILE_TYPES_SCRIPT
        )
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

    def save_file(self) -> None:
        editor = self.get_current_editor()
        if not editor:
            return
        if not editor.file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, tr.SAVE_SCRIPT_FILE, os.path.expanduser("~"), tr.FILE_TYPES_SCRIPT
            )
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

    def run_enable(self) -> None:
        editor = self.get_current_editor()
        if editor:
            enable_code, _ = parse_script_sections(editor.toPlainText())
            self.run_script(editor, enable_code)

    def run_disable(self) -> None:
        editor = self.get_current_editor()
        if not editor:
            return
        _, disable_code = parse_script_sections(editor.toPlainText())
        if disable_code is None:
            self.statusbar.showMessage(tr.SCRIPT_NO_DISABLE, 3000)
            return
        self.run_script(editor, disable_code)

    def run_selection(self) -> None:
        editor = self.get_current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        script = cursor.selectedText().replace("\u2029", "\n") if cursor.hasSelection() else editor.toPlainText()
        self.run_script(editor, script)

    def run_script(self, editor: ScriptEditor, script_content: str) -> None:
        if not script_content.strip():
            return
        filename = editor.file_path or f"<Libpince Engine: {self.tabWidget.tabText(self.tabWidget.currentIndex())}>"
        namespace = editor.namespace or create_script_namespace()
        self.append_output("\n" + tr.SCRIPT_RUNNING.format(filename))
        succeeded, output = run_script_code(script_content, namespace, filename)
        editor.set_namespace(namespace)
        self.append_output(output)
        message = tr.SCRIPT_FINISHED if succeeded else tr.SCRIPT_FAILED
        if succeeded:
            self.append_output(message)
        self.statusbar.showMessage(message, 3000)

    def send_to_cheat_table(self) -> None:
        editor = self.get_current_editor()
        if not editor:
            return
        script = editor.toPlainText()
        if not script.strip():
            return
        default = self.tabWidget.tabText(self.tabWidget.currentIndex()).rstrip("*")
        name, accepted = QInputDialog.getText(self, tr.SEND_TO_TABLE, tr.ENTER_DESCRIPTION, text=default)
        if not accepted:
            return
        entry = typedefs.ScriptEntry(script)
        # Adopt an unsaved scratch tab as the entry's live tab. A file or already-bound tab keeps its identity.
        if editor.script_entry is None and not editor.file_path:
            self._bind_editor(editor, entry, name)
        self.send_to_table.emit(name, entry)
        self.statusbar.showMessage(tr.SENT_TO_TABLE, 3000)

    def _iter_editors(self):
        # Walks every tab's editor. The trailing "+" tab holds none and is skipped.
        for index in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(index)
            editor = tab.findChild(ScriptEditor) if tab else None
            if editor is not None:
                yield editor

    def _editor_for_entry(self, entry: typedefs.ScriptEntry) -> ScriptEditor | None:
        return next((e for e in self._iter_editors() if e.script_entry is entry), None)

    def _scratch_editor(self) -> ScriptEditor | None:
        # An unbound, empty, unsaved tab (e.g. the one a fresh window starts with) an entry can take over
        scratch = (
            e
            for e in self._iter_editors()
            if e.script_entry is None and not e.file_path and not e.is_modified and not e.toPlainText().strip()
        )
        return next(scratch, None)

    def _bind_editor(self, editor: ScriptEditor, entry: typedefs.ScriptEntry, title: str) -> None:
        # Tie editor to a table script entry so its edits mirror back into it. Editor must already hold entry.script.
        editor.script_entry = entry
        editor.display_name = title
        editor.saved_content = entry.script
        editor.is_modified = False
        editor.update_tab_title()
        editor.textChanged.connect(lambda e=editor: self.mirror_script_entry(e))

    def open_script_entry(self, entry: typedefs.ScriptEntry, title: str) -> None:
        """Open or focus if already open, a tab bound to a table script entry.

        The tab shares the entry object so edits mirror straight back into it (see mirror_script_entry).
        """
        editor = self._editor_for_entry(entry)
        if editor is None:
            editor = self._scratch_editor() or self.create_new_tab()
            editor.setPlainText(entry.script)
            self._bind_editor(editor, entry, title)
        self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(editor.parent()))
        editor.setFocus()

    def rename_script_entry(self, entry: typedefs.ScriptEntry, title: str) -> None:
        # Keep an open bound tab's title in sync when the row description is edited from the table
        editor = self._editor_for_entry(entry)
        if editor is not None:
            editor.display_name = title
            editor.update_tab_title()

    def close_script_entry(self, entry: typedefs.ScriptEntry) -> None:
        # Close the bound tab when its table row is deleted so edits can't orphan onto a gone entry
        editor = self._editor_for_entry(entry)
        if editor is not None:
            self.close_tab(self.tabWidget.indexOf(editor.parent()))

    def mirror_script_entry(self, editor: ScriptEditor) -> None:
        entry = editor.script_entry
        if entry is None:
            return
        text = editor.toPlainText()
        entry.script = text
        # Bound tabs are live so keep them unmodified to skip the "*" marker and the close-save prompt
        editor.saved_content = text
        if editor.is_modified:
            editor.is_modified = False
            editor.update_tab_title()
        self.entry_modified.emit()

    def append_output(self, text: str) -> None:
        if not text:
            return
        self.outputEdit.moveCursor(QTextCursor.MoveOperation.End)
        self.outputEdit.insertPlainText(text if text.endswith("\n") else text + "\n")
        self.outputEdit.moveCursor(QTextCursor.MoveOperation.End)

    def insert_template(self, template: str) -> None:
        editor = self.get_current_editor()
        if editor:
            editor.textCursor().insertText(template)
            editor.setFocus()

    def actionLibpince_triggered(self) -> None:
        utils.execute_command_as_user('python3 -m webbrowser "https://korcankaraokcu.github.io/PINCE/"')
