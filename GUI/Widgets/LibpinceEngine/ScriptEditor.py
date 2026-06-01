import builtins, inspect, keyword, os, re
from typing import Any, Iterator

from PyQt6.QtCore import QModelIndex, QRect, QSize, QStringListModel, Qt
from PyQt6.QtGui import (
    QColor,
    QKeyEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QSyntaxHighlighter,
)
from PyQt6.QtWidgets import QApplication, QCompleter, QPlainTextEdit, QTabWidget, QTextEdit, QToolTip, QWidget

from tr.tr import TranslationConstants as tr

INDENT = " " * 4
MAX_COMPLETIONS = 300


def make_format(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(700)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class PythonHighlighter(QSyntaxHighlighter):
    STRING_STATES = {
        1: ("'''", False),
        2: ('"""', False),
        3: ("'''", True),
        4: ('"""', True),
    }

    def __init__(self, document: QTextDocument | None) -> None:
        super().__init__(document)
        self.default_format = QTextCharFormat()
        self.string_format = make_format("#98c379")
        self.comment_format = make_format("#7f848e", italic=True)
        self.variable_format = make_format("#e06c75")
        self.function_format = make_format("#61afef")
        self.keywords = set(keyword.kwlist)
        self.builtins = set(dir(builtins))
        self.namespaces = {"api", "debugcore", "libpince", "scancore", "typedefs", "utils", "VALUE_INDEX", "VALUE_REPR"}
        self.reserved = self.keywords | self.builtins | self.namespaces
        self.identifier_regex = re.compile(r"\b[A-Za-z_]\w*\b")
        self.function_regex = re.compile(r"\b([A-Za-z_]\w*)\s*(?=\()")
        self.rules = [
            (re.compile(r"\b(" + "|".join(keyword.kwlist) + r")\b"), make_format("#c678dd", bold=True), 0),
            (re.compile(r"\b(" + "|".join(dir(builtins)) + r")\b"), make_format("#e5c07b"), 0),
            (re.compile(r"\b(" + "|".join(self.namespaces) + r")\b"), make_format("#56b6c2", bold=True), 0),
            (re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)"), make_format("#61afef", bold=True), 1),
            (re.compile(r"\b(0x[0-9a-fA-F]+|\d+(\.\d+)?)\b"), make_format("#d19a66"), 0),
        ]

    def highlightBlock(self, text: str) -> None:
        self.setCurrentBlockState(0)
        state = self.previousBlockState()
        i = 0
        quote, is_fstring = self.STRING_STATES.get(state, (None, False))
        if quote:
            end = text.find(quote)
            span_end = len(text) if end == -1 else end + 3
            self.setFormat(0, span_end, self.string_format)
            if is_fstring:
                self.format_fstring_expressions(text, 0, span_end)
            if end == -1:
                self.setCurrentBlockState(state)
                return
            i = span_end
        code_start = i
        while i < len(text):
            string_info = self.string_at(text, i)
            if string_info:
                prefix_start, quote_start, quote, quote_len, is_fstring = string_info
                self.apply_code_rules(text, code_start, prefix_start)
                if quote_len == 3:
                    end = text.find(quote * 3, quote_start + 3)
                    span_end = len(text) if end == -1 else end + 3
                    self.setFormat(prefix_start, span_end - prefix_start, self.string_format)
                    if is_fstring:
                        self.format_fstring_expressions(text, prefix_start, span_end)
                    if end == -1:
                        if is_fstring:
                            self.setCurrentBlockState(3 if quote == "'" else 4)
                        else:
                            self.setCurrentBlockState(1 if quote == "'" else 2)
                        return
                else:
                    span_end = self.find_string_end(text, quote_start + 1, quote)
                    self.setFormat(prefix_start, span_end - prefix_start, self.string_format)
                    if is_fstring:
                        self.format_fstring_expressions(text, prefix_start, span_end)
                i = span_end
                code_start = i
                continue
            if text[i] == "#":
                self.apply_code_rules(text, code_start, i)
                self.setFormat(i, len(text) - i, self.comment_format)
                return
            i += 1
        self.apply_code_rules(text, code_start, len(text))

    def apply_code_rules(self, text: str, start: int, end: int) -> None:
        if start >= end:
            return
        segment = text[start:end]
        for match in self.identifier_regex.finditer(segment):
            name = match.group()
            absolute_start = start + match.start()
            next_index = start + match.end()
            next_char = text[next_index:].lstrip()[:1]
            if (
                name not in self.reserved
                and next_char != "("
                and (absolute_start == 0 or text[absolute_start - 1] != ".")
            ):
                self.setFormat(absolute_start, len(name), self.variable_format)
        for match in self.function_regex.finditer(segment):
            name = match.group(1)
            if name not in self.keywords:
                self.setFormat(start + match.start(1), len(name), self.function_format)
        for regex, fmt, group in self.rules:
            for match in regex.finditer(segment):
                span_start, span_end = match.span(group)
                self.setFormat(start + span_start, span_end - span_start, fmt)

    def string_at(self, text: str, index: int) -> tuple[int, int, str, int, bool] | None:
        match = re.match(r"(?i)([rubf]*)(['\"])", text[index:])
        if not match:
            return
        prefix = match.group(1)
        if prefix and index > 0 and (text[index - 1].isalnum() or text[index - 1] == "_"):
            return
        quote_start = index + len(prefix)
        quote = match.group(2)
        quote_len = 3 if text.startswith(quote * 3, quote_start) else 1
        return index, quote_start, quote, quote_len, "f" in prefix.lower()

    def find_string_end(self, text: str, index: int, quote: str) -> int:
        escape = False
        while index < len(text):
            if escape:
                escape = False
            elif text[index] == "\\":
                escape = True
            elif text[index] == quote:
                return index + 1
            index += 1
        return len(text)

    def format_fstring_expressions(self, text: str, start: int, end: int) -> None:
        i = start
        while i < end:
            if text.startswith("{{", i) or text.startswith("}}", i):
                i += 2
                continue
            if text[i] == "{":
                expression_end = self.find_fstring_expression_end(text, i + 1, end)
                if expression_end == -1:
                    return
                self.setFormat(i + 1, expression_end - i - 1, self.default_format)
                self.apply_code_rules(text, i + 1, i + 1 + self.fstring_code_length(text[i + 1 : expression_end]))
                i = expression_end + 1
                continue
            i += 1

    def find_fstring_expression_end(self, text: str, index: int, end: int) -> int:
        depth = 0
        while index < end:
            if text.startswith("{{", index) or text.startswith("}}", index):
                index += 2
                continue
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                if depth == 0:
                    return index
                depth -= 1
            index += 1
        return -1

    def fstring_code_length(self, expression: str) -> int:
        depth = 0
        quote = None
        escape = False
        for index, char in enumerate(expression):
            if quote:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote:
                    quote = None
                continue
            if char in "'\"":
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth = max(0, depth - 1)
            elif depth == 0 and (char == ":" or (char == "!" and expression[index + 1 : index + 2] != "=")):
                return index
        return len(expression)


class LineNumberArea(QWidget):
    def __init__(self, editor: "ScriptEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.editor.line_number_area_paint_event(event)


class ScriptEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.file_path: str | None = None
        self.saved_content = ""
        self.is_modified = False
        self.tab_widget: QTabWidget | None = None
        self.namespace: dict[str, Any] = {}

        self.line_number_area = LineNumberArea(self)
        self.completion_model = QStringListModel(self)
        self.completer = QCompleter(self.completion_model, self)
        self.completer.setWidget(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setMaxVisibleItems(12)
        self.completer.activated.connect(self.insert_completion)
        self.completer.highlighted.connect(self.show_help)

        self.highlighter = PythonHighlighter(self.document())
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.textChanged.connect(self.handle_text_changed)
        self.update_line_number_area_width()
        self.highlight_current_line()

    def bind_tab_widget(self, tab_widget: QTabWidget) -> None:
        self.tab_widget = tab_widget

    def set_namespace(self, namespace: dict[str, Any]) -> None:
        self.namespace = namespace

    def handle_text_changed(self) -> None:
        modified = self.toPlainText() != self.saved_content
        if modified != self.is_modified:
            self.is_modified = modified
            self.update_tab_title()

    def update_tab_title(self) -> None:
        if not self.tab_widget:
            return
        index = self.tab_widget.indexOf(self.parent())
        base_title = os.path.basename(self.file_path) if self.file_path else tr.UNTITLED
        self.tab_widget.setTabText(index, f"{base_title}*" if self.is_modified else base_title)

    def line_number_area_width(self) -> int:
        return 12 + self.fontMetrics().horizontalAdvance("9") * len(str(max(1, self.blockCount())))

    def update_line_number_area_width(self) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        rect = self.contentsRect()
        self.line_number_area.setGeometry(QRect(rect.left(), rect.top(), self.line_number_area_width(), rect.height()))

    def line_number_area_paint_event(self, event: QPaintEvent) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#252830"))
        painter.setPen(QColor("#7f848e"))
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(number + 1),
                )
            block = block.next()
            if not block.isValid():
                break
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    def highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#2c313a"))
        selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def keyPressEvent(self, event: QKeyEvent) -> None:
        popup = self.completer.popup()
        if popup.isVisible():
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Tab):
                self.insert_completion(popup.currentIndex().data())
                popup.hide()
                return
            if event.key() == Qt.Key.Key_Escape:
                popup.hide()
                return
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                QApplication.sendEvent(popup, event)
                return

        key = event.key()
        modifiers = event.modifiers()
        if key == Qt.Key.Key_Space and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.complete(force=True)
            return
        if key == Qt.Key.Key_Tab and not modifiers:
            self.indent_selection()
            return
        if key == Qt.Key.Key_Backtab or (key == Qt.Key.Key_Tab and modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.unindent_selection()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.insert_auto_indent()
            return
        if key == Qt.Key.Key_Backspace and self.backspace_unindent():
            return

        super().keyPressEvent(event)
        text = event.text()
        if text == ".":
            self.complete(force=True)
        elif text == "(":
            self.show_help(self.callable_before_cursor())
        elif text and (text.isalnum() or text == "_"):
            self.complete()
        elif not text.strip():
            popup.hide()

    def word_before_cursor(self) -> str:
        text = self.textCursor().block().text()[: self.textCursor().positionInBlock()]
        match = re.search(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\.?)$", text)
        return match.group(1) if match else ""

    def callable_before_cursor(self) -> str:
        text = self.textCursor().block().text()[: self.textCursor().positionInBlock()].rstrip("(").rstrip()
        match = re.search(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)$", text)
        return match.group(1) if match else ""

    def resolve(self, name: str) -> Any:
        parts = name.split(".")
        obj = self.namespace.get(parts[0], getattr(builtins, parts[0], None))
        for item in parts[1:]:
            try:
                obj = getattr(obj, item)
            except Exception:
                return
        return obj

    def complete(self, force: bool = False) -> None:
        prefix = self.word_before_cursor()
        if not force and not prefix.endswith(".") and len(prefix) < 2:
            self.completer.popup().hide()
            return
        if "." in prefix:
            base, partial = prefix.rsplit(".", 1)
            obj = self.resolve(base)
            names = (
                []
                if obj is None
                else [
                    f"{base}.{name}"
                    for name in dir(obj)
                    if name.startswith(partial) and (partial.startswith("_") or not name.startswith("_"))
                ]
            )
        else:
            all_names = sorted(set(keyword.kwlist) | set(dir(builtins)) | set(self.namespace))
            names = (
                all_names
                if force and not prefix
                else [name for name in all_names if name.startswith(prefix) or prefix in name]
            )
        if not names:
            self.completer.popup().hide()
            return
        self.completion_model.setStringList(names[:MAX_COMPLETIONS])
        self.completer.setCompletionPrefix(prefix)
        popup = self.completer.popup()
        popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
        rect = self.cursorRect()
        width = popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width() + 20
        rect.setWidth(min(max(width, 240), 620))
        self.completer.complete(rect)

    def insert_completion(self, completion: str) -> None:
        if not completion:
            return
        prefix = self.word_before_cursor()
        self.textCursor().insertText(completion[len(prefix) :] if completion.startswith(prefix) else completion)

    def show_help(self, name: str | QModelIndex | None) -> None:
        if not isinstance(name, str):
            name = name.data() if name is not None else ""
        obj = self.resolve(name)
        if obj is None:
            return
        try:
            signature = str(inspect.signature(obj)) if callable(obj) else ""
        except (TypeError, ValueError):
            signature = ""
        text = f"{name}{signature}\n{inspect.getdoc(obj) or ''}".strip()
        if text:
            QToolTip.showText(self.mapToGlobal(self.cursorRect().bottomRight()), text[:1200], self)

    def selected_blocks(self) -> Iterator[QTextBlock]:
        cursor = self.textCursor()
        document = self.document()
        start = document.findBlock(cursor.selectionStart())
        end = document.findBlock(cursor.selectionEnd())
        last = end.blockNumber() - int(cursor.hasSelection() and end.positionInBlock() == 0)
        return map(document.findBlockByNumber, range(start.blockNumber(), max(start.blockNumber(), last) + 1))

    def indent_selection(self) -> None:
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.insertText(INDENT)
            return
        cursor.beginEditBlock()
        for block in self.selected_blocks():
            cursor.setPosition(block.position())
            cursor.insertText(INDENT)
        cursor.endEditBlock()

    def unindent_selection(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        for block in self.selected_blocks():
            count = min(len(block.text()) - len(block.text().lstrip(" ")), len(INDENT))
            count = count or int(block.text().startswith("\t"))
            if count:
                cursor.setPosition(block.position())
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, count)
                cursor.removeSelectedText()
        cursor.endEditBlock()

    def insert_auto_indent(self) -> None:
        text = self.textCursor().block().text()[: self.textCursor().positionInBlock()]
        indent = re.match(r"\s*", text).group(0).replace("\t", INDENT)
        self.textCursor().insertText("\n" + indent + (INDENT if text.rstrip().endswith(":") else ""))

    def backspace_unindent(self) -> bool:
        cursor = self.textCursor()
        text = cursor.block().text()[: cursor.positionInBlock()]
        if cursor.hasSelection() or not text.isspace():
            return False
        count = min(cursor.positionInBlock() % len(INDENT) or len(INDENT), cursor.positionInBlock())
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, count)
        cursor.removeSelectedText()
        return True
