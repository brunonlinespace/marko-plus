#!/usr/bin/env python3
# ==============================================================================
# Markopad - Markdown source editor
# Copyright (C) 2026 Bruno Machado
# GPLv3-or-later
#
# Generic editor architecture adapted from the Sheepy Pad source-editor core,
# with Markdown-specific highlighter and structural matching inspired by the
# language-aware evolution in Timblee Pad. Markopad remains fully standalone.
# ==============================================================================

from __future__ import annotations

import re
from dataclasses import dataclass

from PyQt6.QtCore import QMimeData, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QInputMethodEvent,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QSyntaxHighlighter,
)
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget


@dataclass(frozen=True, slots=True)
class HighlightRule:
    pattern: re.Pattern[str]
    text_format: QTextCharFormat


MARKDOWN_COLOR_SCHEMES = {
    "dark": {
        "gutter_background": "#181B1D",
        "gutter_current": "#EFF0F1",
        "gutter_foreground": "#8B949E",
        "current_line": "#252A2E",
        "match_background": "#415A54",
        "match_foreground": "#FFFFFF",
        "heading": "#7DCFFF",
        "emphasis": "#E6B566",
        "strong": "#FFCC66",
        "strike": "#C792EA",
        "code": "#A7D46F",
        "quote": "#89DDFF",
        "list": "#F78C6C",
        "link": "#82AAFF",
        "image": "#C3E88D",
        "rule": "#B0BEC5",
        "comment": "#6A9955",
        "escape": "#FF5370",
        "table": "#89DDFF",
    },
    "light": {
        "gutter_background": "#F2F4F6",
        "gutter_current": "#202124",
        "gutter_foreground": "#687078",
        "current_line": "#EEF5FB",
        "match_background": "#C8E6C9",
        "match_foreground": "#16351B",
        "heading": "#005A9C",
        "emphasis": "#8A4B08",
        "strong": "#7A3E00",
        "strike": "#6A1B9A",
        "code": "#2E7D32",
        "quote": "#006064",
        "list": "#A13A16",
        "link": "#174EA6",
        "image": "#33691E",
        "rule": "#59636D",
        "comment": "#2E7D32",
        "escape": "#B00020",
        "table": "#006064",
    },
}


def _scheme(name: str) -> str:
    return "light" if name == "light" else "dark"


class MarkdownHighlighter(QSyntaxHighlighter):
    """Small, dependency-free Markdown highlighter with fenced-block state."""

    FENCE_STATE_BACKTICK = 1
    FENCE_STATE_TILDE = 2

    def __init__(self, document: QTextDocument, color_scheme: str = "dark") -> None:
        super().__init__(document)
        self._color_scheme = _scheme(color_scheme)
        self._build_formats()

    @staticmethod
    def _format(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
        fmt.setFontItalic(italic)
        return fmt

    def _build_formats(self) -> None:
        colors = MARKDOWN_COLOR_SCHEMES[self._color_scheme]
        self.heading_format = self._format(colors["heading"], bold=True)
        self.strong_format = self._format(colors["strong"], bold=True)
        self.emphasis_format = self._format(colors["emphasis"], italic=True)
        self.strike_format = self._format(colors["strike"])
        self.code_format = self._format(colors["code"])
        self.quote_format = self._format(colors["quote"])
        self.list_format = self._format(colors["list"], bold=True)
        self.link_format = self._format(colors["link"])
        self.image_format = self._format(colors["image"])
        self.rule_format = self._format(colors["rule"], bold=True)
        self.comment_format = self._format(colors["comment"], italic=True)
        self.escape_format = self._format(colors["escape"])
        self.table_format = self._format(colors["table"])

    def set_color_scheme(self, color_scheme: str) -> None:
        selected = _scheme(color_scheme)
        if selected == self._color_scheme:
            return
        self._color_scheme = selected
        self._build_formats()
        self.rehighlight()

    @staticmethod
    def _apply_pattern(highlighter, text: str, pattern: str, fmt: QTextCharFormat, flags=0) -> None:
        for match in re.finditer(pattern, text, flags):
            highlighter.setFormat(match.start(), match.end() - match.start(), fmt)

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt API name
        previous = self.previousBlockState()
        stripped = text.lstrip()

        if previous in (self.FENCE_STATE_BACKTICK, self.FENCE_STATE_TILDE):
            delimiter = "```" if previous == self.FENCE_STATE_BACKTICK else "~~~"
            self.setFormat(0, len(text), self.code_format)
            if stripped.startswith(delimiter):
                self.setCurrentBlockState(0)
            else:
                self.setCurrentBlockState(previous)
            return

        fence = re.match(r"^\s*(`{3,}|~{3,})([^`]*)$", text)
        if fence:
            self.setFormat(0, len(text), self.code_format)
            self.setCurrentBlockState(
                self.FENCE_STATE_BACKTICK if fence.group(1).startswith("`")
                else self.FENCE_STATE_TILDE
            )
            return

        self.setCurrentBlockState(0)

        # Block-level tokens first.
        heading = re.match(r"^\s{0,3}(#{1,6})(?:\s+|$)", text)
        if heading:
            self.setFormat(heading.start(1), len(heading.group(1)), self.heading_format)
            self.setFormat(heading.end(1), len(text) - heading.end(1), self.heading_format)
        quote = re.match(r"^\s{0,3}>\s?", text)
        if quote:
            self.setFormat(quote.start(), quote.end() - quote.start(), self.quote_format)
        list_marker = re.match(r"^(\s*)(?:[-+*]|\d+[.)])\s+", text)
        if list_marker:
            marker_start = len(list_marker.group(1))
            self.setFormat(marker_start, list_marker.end() - marker_start, self.list_format)
        task = re.match(r"^\s*[-+*]\s+\[[ xX]\]\s+", text)
        if task:
            self.setFormat(task.start(), task.end() - task.start(), self.list_format)
        if re.match(r"^\s{0,3}(?:_{3,}|-{3,}|\*{3,})\s*$", text):
            self.setFormat(0, len(text), self.rule_format)
        if text.count("|") >= 2 and re.match(r"^\s*\|?.*\|.*\|?\s*$", text):
            for match in re.finditer(r"\|", text):
                self.setFormat(match.start(), 1, self.table_format)

        # Inline code must be coloured before emphasis so asterisks inside code
        # do not look like formatting delimiters.
        code_ranges = []
        for match in re.finditer(r"(`+)(.+?)\1", text):
            self.setFormat(match.start(), match.end() - match.start(), self.code_format)
            code_ranges.append((match.start(), match.end()))

        def outside_code(start: int, end: int) -> bool:
            return not any(start < code_end and end > code_start for code_start, code_end in code_ranges)

        inline_rules = (
            (r"!\[[^\]\n]*\]\([^\n)]*\)", self.image_format),
            (r"(?<!!)\[[^\]\n]+\]\([^\n)]*\)", self.link_format),
            (r"\*\*[^\n*]+\*\*|__[^\n_]+__", self.strong_format),
            (r"~~[^\n~]+~~", self.strike_format),
            (r"(?<!\*)\*[^\n*]+\*(?!\*)|(?<!_)_[^\n_]+_(?!_)", self.emphasis_format),
            (r"\\[\\`*{}_\[\]()#+\-.!>]", self.escape_format),
            (r"<!--.*?-->", self.comment_format),
        )
        for pattern, fmt in inline_rules:
            for match in re.finditer(pattern, text):
                if outside_code(match.start(), match.end()):
                    self.setFormat(match.start(), match.end() - match.start(), fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor: "MarkopadSourceEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.paint_line_number_area(event)


class MarkopadSourceEditor(QPlainTextEdit):
    """Hardened Markdown source editor used by Markopad."""

    paste_rejected = pyqtSignal(str)
    view_only_edit_attempt = pyqtSignal()
    files_dropped = pyqtSignal(list)
    overwrite_mode_changed = pyqtSignal(bool)

    BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}", ")": "(", "]": "[", "}": "{"}
    OPENING_BRACKETS = "([{" 
    MAX_PASTE_CHARACTERS = 5_000_000
    MAX_DOCUMENT_CHARACTERS = 25_000_000
    MAX_BRACKET_SCAN_CHARACTERS = 250_000
    MAX_FENCE_SCAN_BLOCKS = 20_000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setUndoRedoEnabled(True)
        self.setCenterOnScroll(True)
        self._line_numbers_visible = True
        self.line_number_area = LineNumberArea(self)
        self._tab_width_spaces = 4
        self._color_scheme = "dark"
        self._search_selections: list[QTextEdit.ExtraSelection] = []
        self._refreshing_extra_selections = False
        self._pending_full_paste: str | None = None
        self._full_paste_generation = 0
        self._highlighter = MarkdownHighlighter(self.document(), self._color_scheme)

        self._decoration_timer = QTimer(self)
        self._decoration_timer.setSingleShot(True)
        self._decoration_timer.setInterval(0)
        self._decoration_timer.timeout.connect(self._refresh_extra_selections)

        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._schedule_decoration_refresh)
        self.textChanged.connect(self._schedule_decoration_refresh)
        self.horizontalScrollBar().rangeChanged.connect(
            lambda _minimum, _maximum: QTimer.singleShot(
                0, self._resize_gutter_above_horizontal_scrollbar
            )
        )
        self._update_line_number_area_width()
        self._schedule_decoration_refresh()
        QTimer.singleShot(0, self._resize_gutter_above_horizontal_scrollbar)

    # ---------- presentation ----------
    def set_color_scheme(self, color_scheme: str) -> None:
        self._color_scheme = _scheme(color_scheme)
        self._highlighter.set_color_scheme(self._color_scheme)
        self.line_number_area.update()
        self._schedule_decoration_refresh()

    def set_editor_font(self, font: QFont) -> None:
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * self._tab_width_spaces)
        self._update_line_number_area_width()

    def set_tab_width_spaces(self, spaces: int) -> None:
        self._tab_width_spaces = max(1, int(spaces))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * self._tab_width_spaces)

    def set_word_wrap_enabled(self, enabled: bool) -> None:
        self.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if enabled
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def line_number_area_width(self) -> int:
        if not self._line_numbers_visible:
            return 0
        digits = max(1, len(str(max(1, self.blockCount()))))
        return 14 + self.line_number_area.fontMetrics().horizontalAdvance("9") * digits

    def set_line_numbers_visible(self, visible: bool) -> None:
        self._line_numbers_visible = bool(visible)
        self.line_number_area.setVisible(self._line_numbers_visible)
        self._update_line_number_area_width()
        self.line_number_area.update()

    def paint_line_number_area(self, event) -> None:
        if not self._line_numbers_visible:
            return
        colors = MARKDOWN_COLOR_SCHEMES[self._color_scheme]
        painter = QPainter(self.line_number_area)
        painter.setFont(self.line_number_area.font())
        painter.fillRect(event.rect(), QColor(colors["gutter_background"]))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        current_block = self.textCursor().blockNumber()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(
                    colors["gutter_current"] if block_number == current_block
                    else colors["gutter_foreground"]
                ))
                painter.drawText(
                    0, top, self.line_number_area.width() - 7,
                    self.line_number_area.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._resize_gutter_above_horizontal_scrollbar()

    def _resize_gutter_above_horizontal_scrollbar(self) -> None:
        """Keep the line-number gutter out of the native horizontal scrollbar strip."""
        contents = self.contentsRect()
        horizontal = self.horizontalScrollBar()
        gutter_height = contents.height()
        if horizontal.isVisible():
            gutter_height = max(0, gutter_height - horizontal.height())
        self.line_number_area.setGeometry(QRect(
            contents.left(), contents.top(), self.line_number_area_width(), gutter_height
        ))

    def _update_line_number_area_width(self, _new_count: int = 0) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()

    # ---------- safe mutation ----------
    def set_view_only(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled:
            self._pending_full_paste = None
            self._full_paste_generation += 1
        self.setReadOnly(enabled)
        self._schedule_decoration_refresh()

    def _replacement_fits(self, start: int, end: int, replacement_length: int) -> bool:
        current = max(0, self.document().characterCount() - 1)
        removed = max(0, int(end) - int(start))
        return current - removed + max(0, int(replacement_length)) <= self.MAX_DOCUMENT_CHARACTERS

    def _reject_document_growth(self) -> None:
        self.paste_rejected.emit("The edit would exceed Markopad's source document safety limit.")

    @staticmethod
    def _is_mutating_key_event(event: QKeyEvent) -> bool:
        if event.key() in (
            Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Return,
            Qt.Key.Key_Enter, Qt.Key.Key_Tab, Qt.Key.Key_Backtab,
        ):
            return True
        for standard_key in (
            QKeySequence.StandardKey.Cut, QKeySequence.StandardKey.Paste,
            QKeySequence.StandardKey.Undo, QKeySequence.StandardKey.Redo,
        ):
            if event.matches(standard_key):
                return True
        return bool(event.text() and any(ch.isprintable() for ch in event.text()))

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Insert and modifiers in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        ):
            enabled = not self.overwriteMode()
            self.setOverwriteMode(enabled)
            self.overwrite_mode_changed.emit(enabled)
            event.accept()
            return

        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Slash:
            self.toggle_comment()
            event.accept()
            return

        if self.isReadOnly():
            if self._is_mutating_key_event(event):
                self.view_only_edit_attempt.emit()
                event.accept()
                return
            super().keyPressEvent(event)
            return

        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current = cursor.block().text()
            leading = current[: len(current) - len(current.lstrip(" \t"))]
            if not self._replacement_fits(start, end, 1 + len(leading)):
                self._reject_document_growth(); return
            self._insert_newline_with_indent()
            return
        if key == Qt.Key.Key_Tab and not (modifiers & Qt.KeyboardModifier.ControlModifier):
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self.unindent_selection_or_line()
            else:
                if not cursor.hasSelection() and not self._replacement_fits(start, end, self._tab_width_spaces):
                    self._reject_document_growth(); return
                self.indent_selection_or_insert_spaces()
            return
        text = event.text()
        if text and any(ch.isprintable() for ch in text):
            if not self._replacement_fits(start, end, len(text)):
                self._reject_document_growth(); return
        if key == Qt.Key.Key_Backtab:
            self.unindent_selection_or_line()
            return
        super().keyPressEvent(event)

    def toggle_comment(self) -> None:
        """Toggle a Markdown-compatible HTML comment around the selection or current line."""
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return

        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n")
            stripped = selected.strip()
            if stripped.startswith("<!--") and stripped.endswith("-->"):
                leading = len(selected) - len(selected.lstrip())
                trailing = len(selected) - len(selected.rstrip())
                core = selected[leading: len(selected) - trailing if trailing else None]
                core = core[4:-3]
                if core.startswith(" "):
                    core = core[1:]
                if core.endswith(" "):
                    core = core[:-1]
                replacement = selected[:leading] + core + (selected[len(selected)-trailing:] if trailing else "")
            else:
                replacement = f"<!-- {selected} -->"
            if not self._replacement_fits(
                cursor.selectionStart(), cursor.selectionEnd(), len(replacement)
            ):
                self._reject_document_growth()
                return
            cursor.insertText(replacement)
            self.setTextCursor(cursor)
            return

        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        text = cursor.selectedText()
        stripped = text.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            leading = len(text) - len(text.lstrip())
            trailing = len(text) - len(text.rstrip())
            core = text[leading: len(text) - trailing if trailing else None][4:-3]
            if core.startswith(" "):
                core = core[1:]
            if core.endswith(" "):
                core = core[:-1]
            replacement = text[:leading] + core + (text[len(text)-trailing:] if trailing else "")
        else:
            replacement = f"<!-- {text} -->"
        if not self._replacement_fits(
            cursor.selectionStart(), cursor.selectionEnd(), len(replacement)
        ):
            self._reject_document_growth()
            return
        cursor.insertText(replacement)
        self.setTextCursor(cursor)

    def inputMethodEvent(self, event: QInputMethodEvent) -> None:  # noqa: N802
        if self.isReadOnly() and (event.commitString() or event.preeditString()):
            self.view_only_edit_attempt.emit()
            event.accept()
            return
        commit = event.commitString()
        if commit:
            cursor = self.textCursor()
            if not self._replacement_fits(cursor.selectionStart(), cursor.selectionEnd(), len(commit)):
                self._reject_document_growth()
                event.accept()
                return
        super().inputMethodEvent(event)

    def insertFromMimeData(self, source: QMimeData) -> None:  # noqa: N802
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        if source is None or not source.hasText():
            self.paste_rejected.emit("Clipboard content is not plain text and was not pasted.")
            return
        try:
            text = source.text()
        except Exception as error:
            self.paste_rejected.emit(f"Clipboard text could not be read: {error}")
            return
        self.insert_guarded_text(text)

    def insert_guarded_text(self, text: str) -> bool:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return False
        text = str(text).replace("\x00", "")
        if len(text) > self.MAX_PASTE_CHARACTERS:
            self.paste_rejected.emit("Clipboard text is too large to paste safely.")
            return False
        if not text:
            return True
        cursor = self.textCursor()
        document_length = max(0, self.document().characterCount() - 1)
        selected_length = abs(cursor.selectionEnd() - cursor.selectionStart())
        if document_length - selected_length + len(text) > self.MAX_DOCUMENT_CHARACTERS:
            self.paste_rejected.emit("The paste would exceed Markopad's source document safety limit.")
            return False
        selection_start = min(cursor.selectionStart(), cursor.selectionEnd())
        selection_end = max(cursor.selectionStart(), cursor.selectionEnd())
        if cursor.hasSelection() and selection_start == 0 and selection_end >= document_length:
            self._pending_full_paste = text
            self._full_paste_generation += 1
            generation = self._full_paste_generation
            self._decoration_timer.stop()
            self.setExtraSelections([])
            QTimer.singleShot(0, lambda: self._apply_pending_full_paste(generation))
            return True
        cursor.insertText(text)
        self.setTextCursor(cursor)
        self._schedule_decoration_refresh()
        return True

    def _apply_pending_full_paste(self, generation: int) -> None:
        if generation != self._full_paste_generation or self.isReadOnly():
            return
        text = self._pending_full_paste
        self._pending_full_paste = None
        if text is not None:
            self.replace_document_text(text)
            self.setFocus()

    def replace_document_text(self, text: str, *, mark_modified: bool = True) -> bool:
        text = str(text).replace("\x00", "")
        if len(text) > self.MAX_DOCUMENT_CHARACTERS:
            self.paste_rejected.emit("The replacement would exceed Markopad's source document safety limit.")
            return False
        self._decoration_timer.stop()
        self.setExtraSelections([])
        highlighter = self._highlighter
        highlighter.setDocument(None)
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        try:
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.insertText(text)
            self.setTextCursor(cursor)
        finally:
            cursor.endEditBlock()
            highlighter.setDocument(self.document())
            highlighter.rehighlight()
        self.document().setModified(bool(mark_modified))
        self._schedule_decoration_refresh()
        return True

    def load_text(self, text: str) -> bool:
        if len(text) > self.MAX_DOCUMENT_CHARACTERS:
            self.paste_rejected.emit("The Markdown source exceeds Markopad's editor safety limit.")
            return False
        ok = self.replace_document_text(text, mark_modified=False)
        if ok:
            self.document().setModified(False)
        return ok

    # ---------- drops ----------
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasUrls() and any(url.isLocalFile() for url in mime.urls()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime.hasUrls():
            paths = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        window = self.window()
        if (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
            and hasattr(window, "adjust_zoom_from_wheel")
        ):
            window.adjust_zoom_from_wheel(event.angleDelta().y())
            event.accept()
            return
        super().wheelEvent(event)

    # ---------- decoration compositor ----------
    def set_search_selections(self, selections: list[QTextEdit.ExtraSelection]) -> None:
        self._search_selections = list(selections)
        self._schedule_decoration_refresh()

    def clear_search_selections(self) -> None:
        self._search_selections = []
        self._schedule_decoration_refresh()

    def _schedule_decoration_refresh(self, *_args) -> None:
        if not self._decoration_timer.isActive():
            self._decoration_timer.start()

    def _selection_for_range(self, start: int, end: int) -> QTextEdit.ExtraSelection:
        colors = MARKDOWN_COLOR_SCHEMES[self._color_scheme]
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(colors["match_background"]))
        selection.format.setForeground(QColor(colors["match_foreground"]))
        selection.cursor = QTextCursor(self.document())
        selection.cursor.setPosition(start)
        selection.cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        return selection

    def _refresh_extra_selections(self) -> None:
        if self._refreshing_extra_selections:
            return
        self._refreshing_extra_selections = True
        try:
            selections = list(self._search_selections)
            cursor = self.textCursor()
            if not cursor.hasSelection():
                if not self.isReadOnly():
                    current = QTextEdit.ExtraSelection()
                    current.format.setBackground(QColor(MARKDOWN_COLOR_SCHEMES[self._color_scheme]["current_line"]))
                    current.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                    current.cursor = QTextCursor(cursor)
                    current.cursor.clearSelection()
                    selections.append(current)
                selections.extend(self._matching_bracket_selections())
                selections.extend(self._matching_fence_selections())
            self.setExtraSelections(selections)
        except (IndexError, RuntimeError, ValueError):
            self.setExtraSelections(list(self._search_selections))
        finally:
            self.line_number_area.update()
            self._refreshing_extra_selections = False

    def _matching_bracket_selections(self) -> list[QTextEdit.ExtraSelection]:
        document = self.document()
        text_length = max(0, document.characterCount() - 1)
        if not text_length:
            return []
        position = max(0, min(self.textCursor().position(), text_length))
        bracket_position = None
        bracket = ""
        for index in ([position - 1] if position > 0 else []) + ([position] if position < text_length else []):
            character = document.characterAt(index)
            if character in self.BRACKET_PAIRS:
                bracket_position, bracket = index, character
                break
        if bracket_position is None:
            return []
        match = self._find_matching_bracket(bracket_position, bracket, text_length)
        if match is None:
            return []
        return [self._selection_for_range(index, index + 1) for index in (bracket_position, match)]

    def _find_matching_bracket(self, position: int, bracket: str, text_length: int) -> int | None:
        partner = self.BRACKET_PAIRS.get(bracket)
        if not partner:
            return None
        document = self.document()
        if bracket in self.OPENING_BRACKETS:
            depth = 1
            stop = min(text_length, position + 1 + self.MAX_BRACKET_SCAN_CHARACTERS)
            for index in range(position + 1, stop):
                character = document.characterAt(index)
                if character == bracket:
                    depth += 1
                elif character == partner:
                    depth -= 1
                    if depth == 0:
                        return index
        else:
            depth = 1
            stop = max(-1, position - self.MAX_BRACKET_SCAN_CHARACTERS - 1)
            for index in range(position - 1, stop, -1):
                character = document.characterAt(index)
                if character == bracket:
                    depth += 1
                elif character == partner:
                    depth -= 1
                    if depth == 0:
                        return index
        return None

    @staticmethod
    def _fence_info(text: str):
        match = re.match(r"^\s{0,3}(`{3,}|~{3,})", text)
        if not match:
            return None
        delimiter = match.group(1)
        return delimiter[0], len(delimiter), match.start(1), match.end(1)

    def _matching_fence_selections(self) -> list[QTextEdit.ExtraSelection]:
        block = self.textCursor().block()
        info = self._fence_info(block.text())
        if not info:
            return []
        char, width, start_in_block, end_in_block = info
        current_number = block.blockNumber()

        # Determine whether this is an opening or closing fence by counting
        # compatible fences before it within a bounded block window.
        previous_count = 0
        probe = block.previous()
        scanned = 0
        while probe.isValid() and scanned < self.MAX_FENCE_SCAN_BLOCKS:
            other = self._fence_info(probe.text())
            if other and other[0] == char and other[1] >= width:
                previous_count += 1
            probe = probe.previous()
            scanned += 1
        opening = previous_count % 2 == 0

        partner = block.next() if opening else block.previous()
        scanned = 0
        while partner.isValid() and scanned < self.MAX_FENCE_SCAN_BLOCKS:
            other = self._fence_info(partner.text())
            if other and other[0] == char and other[1] >= width:
                current_start = block.position() + start_in_block
                partner_start = partner.position() + other[2]
                return [
                    self._selection_for_range(current_start, current_start + width),
                    self._selection_for_range(partner_start, partner_start + other[1]),
                ]
            partner = partner.next() if opening else partner.previous()
            scanned += 1
        return []

    # ---------- Markdown transformations ----------
    def _selected_block_range(self, cursor: QTextCursor) -> tuple[int, int]:
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        start_cursor = QTextCursor(self.document())
        start_cursor.setPosition(start)
        start_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        end_cursor = QTextCursor(self.document())
        end_cursor.setPosition(end)
        if end > start and end_cursor.positionInBlock() == 0:
            end_cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
        end_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
        return start_cursor.position(), end_cursor.position()

    def _transform_selected_blocks(self, transform) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        start, end = self._selected_block_range(cursor)
        probe = QTextCursor(self.document())
        probe.setPosition(start)
        lines = []
        while probe.position() <= end:
            lines.append(probe.block().text())
            if not probe.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        replacement = "\n".join(transform(lines))
        if not self._replacement_fits(start, end, len(replacement)):
            self._reject_document_growth()
            return
        edit = QTextCursor(self.document())
        edit.setPosition(start)
        edit.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        edit.beginEditBlock()
        edit.insertText(replacement)
        edit.endEditBlock()
        self.setTextCursor(edit)

    def _toggle_inline(self, left: str, right: str | None = None) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        right = left if right is None else right
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        document = self.document()
        selected = cursor.selectedText().replace("\u2029", "\n")
        # Toggle delimiters around an existing selection when the exact pair is
        # immediately outside it; otherwise wrap the selected text.
        if cursor.hasSelection() and start >= len(left):
            before = "".join(document.characterAt(i) for i in range(start - len(left), start))
            after = "".join(document.characterAt(i) for i in range(end, min(end + len(right), document.characterCount() - 1)))
            if before == left and after == right:
                edit = QTextCursor(document)
                edit.beginEditBlock()
                edit.setPosition(end)
                edit.setPosition(end + len(right), QTextCursor.MoveMode.KeepAnchor)
                edit.removeSelectedText()
                edit.setPosition(start - len(left))
                edit.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
                edit.removeSelectedText()
                edit.endEditBlock()
                edit.setPosition(start - len(left))
                edit.setPosition(end - len(left), QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(edit)
                return
        replacement = left + selected + right
        if not self._replacement_fits(start, end, len(replacement)):
            self._reject_document_growth()
            return
        cursor.beginEditBlock()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        # Keep the content selected, not the delimiters.
        new_cursor = self.textCursor()
        insertion_end = new_cursor.position()
        new_cursor.setPosition(insertion_end - len(right) - len(selected))
        new_cursor.setPosition(insertion_end - len(right), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(new_cursor)

    def toggle_bold(self) -> None:
        self._toggle_inline("**")

    def toggle_italic(self) -> None:
        self._toggle_inline("*")

    def toggle_strikethrough(self) -> None:
        self._toggle_inline("~~")

    def toggle_inline_code(self) -> None:
        cursor = self.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n")
        max_run = max((len(match.group(0)) for match in re.finditer(r"`+", selected)), default=0)
        delimiter = "`" * max(1, max_run + 1)
        self._toggle_inline(delimiter)

    def apply_heading(self, level: int) -> None:
        level = max(0, min(6, int(level)))
        def transform(lines):
            output = []
            for line in lines:
                content = re.sub(r"^\s{0,3}#{1,6}(?:\s+|$)", "", line)
                if level:
                    leading = line[: len(line) - len(line.lstrip(" "))][:3]
                    output.append(leading + ("#" * level) + " " + content.lstrip())
                else:
                    output.append(content)
            return output
        self._transform_selected_blocks(transform)

    def toggle_bullet_list(self) -> None:
        def transform(lines):
            if len(lines) == 1 and not lines[0].strip():
                return [lines[0] + "- "]
            meaningful = [line for line in lines if line.strip()]
            remove = bool(meaningful) and all(re.match(r"^\s*[-+*]\s+", line) for line in meaningful)
            output = []
            for line in lines:
                if not line.strip():
                    output.append(line)
                    continue
                indent = line[: len(line) - len(line.lstrip())]
                body = line[len(indent):]
                if remove:
                    body = re.sub(r"^[-+*]\s+", "", body)
                    output.append(indent + body)
                else:
                    body = re.sub(r"^(?:[-+*]|\d+[.)])\s+", "", body)
                    output.append(indent + "- " + body)
            return output
        self._transform_selected_blocks(transform)

    def toggle_numbered_list(self) -> None:
        def transform(lines):
            if len(lines) == 1 and not lines[0].strip():
                return [lines[0] + "1. "]
            meaningful = [line for line in lines if line.strip()]
            remove = bool(meaningful) and all(re.match(r"^\s*\d+[.)]\s+", line) for line in meaningful)
            output = []
            number = 1
            for line in lines:
                if not line.strip():
                    output.append(line)
                    continue
                indent = line[: len(line) - len(line.lstrip())]
                body = line[len(indent):]
                if remove:
                    body = re.sub(r"^\d+[.)]\s+", "", body)
                    output.append(indent + body)
                else:
                    body = re.sub(r"^(?:[-+*]|\d+[.)])\s+", "", body)
                    output.append(f"{indent}{number}. {body}")
                    number += 1
            return output
        self._transform_selected_blocks(transform)

    def toggle_blockquote(self) -> None:
        def transform(lines):
            meaningful = [line for line in lines if line.strip()]
            remove = bool(meaningful) and all(re.match(r"^\s*>\s?", line) for line in meaningful)
            output = []
            for line in lines:
                indent = line[: len(line) - len(line.lstrip())]
                body = line[len(indent):]
                output.append(indent + (re.sub(r"^>\s?", "", body) if remove else "> " + body))
            return output
        self._transform_selected_blocks(transform)

    def toggle_task_list(self) -> None:
        def transform(lines):
            if len(lines) == 1 and not lines[0].strip():
                return [lines[0] + "- [ ] "]
            meaningful = [line for line in lines if line.strip()]
            remove = bool(meaningful) and all(re.match(r"^\s*[-+*]\s+\[[ xX]\]\s+", line) for line in meaningful)
            output = []
            for line in lines:
                if not line.strip():
                    output.append(line)
                    continue
                indent = line[: len(line) - len(line.lstrip())]
                body = line[len(indent):]
                if remove:
                    body = re.sub(r"^[-+*]\s+\[[ xX]\]\s+", "", body)
                    output.append(indent + body)
                else:
                    body = re.sub(r"^(?:[-+*]\s+\[[ xX]\]\s+|[-+*]\s+|\d+[.)]\s+)", "", body)
                    output.append(indent + "- [ ] " + body)
            return output
        self._transform_selected_blocks(transform)

    def insert_code_fence(self, language: str = "") -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n")
        max_run = max((len(match.group(0)) for match in re.finditer(r"`+", selected)), default=0)
        fence = "`" * max(3, max_run + 1)
        lang = re.sub(r"[^A-Za-z0-9_+.#-]", "", language.strip())[:64]
        opening = fence + lang
        content = selected
        if content and not content.endswith("\n"):
            content += "\n"
        insertion = f"{opening}\n{content}{fence}"
        if not self._replacement_fits(cursor.selectionStart(), cursor.selectionEnd(), len(insertion)):
            self._reject_document_growth()
            return
        cursor.beginEditBlock()
        cursor.insertText(insertion)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_link(self, label: str, url: str) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        safe_label = str(label).replace("\n", " ").replace("]", r"\]")
        safe_url = str(url).replace(" ", "%20").replace(")", r"\)")
        insertion = f"[{safe_label}]({safe_url})"
        cursor = self.textCursor()
        if not self._replacement_fits(cursor.selectionStart(), cursor.selectionEnd(), len(insertion)):
            self._reject_document_growth(); return
        cursor.insertText(insertion)

    def insert_horizontal_rule(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        required = 4 + (1 if cursor.block().text() else 0)
        if not self._replacement_fits(cursor.position(), cursor.position(), required):
            self._reject_document_growth(); return
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.beginEditBlock()
        if cursor.block().text():
            cursor.insertText("\n")
        cursor.insertText("___\n")
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def insert_table(self, rows: int, columns: int) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        rows = max(1, min(100, int(rows)))
        columns = max(1, min(20, int(columns)))
        header = "| " + " | ".join(f"Column {i + 1}" for i in range(columns)) + " |"
        divider = "| " + " | ".join("---" for _ in range(columns)) + " |"
        body = ["| " + " | ".join("" for _ in range(columns)) + " |" for _ in range(max(0, rows - 1))]
        text = "\n".join([header, divider, *body])
        cursor = self.textCursor()
        additional = len(text) + (1 if cursor.positionInBlock() != 0 else 0)
        if not self._replacement_fits(cursor.selectionStart(), cursor.selectionEnd(), additional):
            self._reject_document_growth(); return
        cursor.beginEditBlock()
        if cursor.positionInBlock() != 0:
            cursor.insertText("\n")
        cursor.insertText(text)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def duplicate_current_line_or_selection(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n")
            addition = len(selected)
            cursor.setPosition(cursor.selectionEnd())
            insertion = selected
        else:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            line = cursor.selectedText()
            addition = len(line) + 1
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            insertion = "\n" + line
        if max(0, self.document().characterCount() - 1) + addition > self.MAX_DOCUMENT_CHARACTERS:
            cursor.endEditBlock()
            self.paste_rejected.emit("Duplication would exceed Markopad's source document safety limit.")
            return
        cursor.insertText(insertion)
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def indent_selection_or_insert_spaces(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        if not cursor.hasSelection():
            if not self._replacement_fits(cursor.position(), cursor.position(), self._tab_width_spaces):
                self._reject_document_growth()
                return
            cursor.insertText(" " * self._tab_width_spaces)
            return
        start, end = self._selected_block_range(cursor)
        probe = QTextCursor(self.document()); probe.setPosition(start)
        line_count = 0
        while probe.position() <= end:
            line_count += 1
            if not probe.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        if not self._replacement_fits(start, end, (end - start) + line_count * self._tab_width_spaces):
            self._reject_document_growth(); return
        cursor.beginEditBlock()
        cursor.setPosition(start)
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.insertText(" " * self._tab_width_spaces)
            end += self._tab_width_spaces
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    def unindent_selection_or_line(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        start, end = self._selected_block_range(cursor)
        cursor.beginEditBlock()
        cursor.setPosition(start)
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            block_text = cursor.block().text()
            if block_text.startswith("\t"):
                remove_count = 1
            else:
                remove_count = min(self._tab_width_spaces, len(block_text) - len(block_text.lstrip(" ")))
            for _ in range(remove_count):
                cursor.deleteChar()
            end -= remove_count
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
        cursor.endEditBlock()

    def _insert_newline_with_indent(self) -> None:
        """Insert a Markdown-aware newline while keeping source authoritative."""
        cursor = self.textCursor()
        current = cursor.block().text()
        leading = current[: len(current) - len(current.lstrip(" \t"))]
        body = current[len(leading):]

        patterns = (
            (re.compile(r"^([-+*])\s+\[([ xX])\]\s?(.*)$"), "task"),
            (re.compile(r"^([-+*])\s+(.*)$"), "bullet"),
            (re.compile(r"^(\d+)([.)])\s+(.*)$"), "number"),
            (re.compile(r"^(>)\s?(.*)$"), "quote"),
        )
        continuation = leading
        empty_structure = False
        for pattern, kind in patterns:
            match = pattern.match(body)
            if not match:
                continue
            if kind == "task":
                content = match.group(3)
                empty_structure = not content.strip()
                continuation = f"{leading}{match.group(1)} [ ] "
            elif kind == "bullet":
                content = match.group(2)
                empty_structure = not content.strip()
                continuation = f"{leading}{match.group(1)} "
            elif kind == "number":
                content = match.group(3)
                empty_structure = not content.strip()
                continuation = f"{leading}{int(match.group(1)) + 1}{match.group(2)} "
            else:
                content = match.group(2)
                empty_structure = not content.strip()
                continuation = f"{leading}> "
            break

        if empty_structure:
            cursor.beginEditBlock()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(leading)
            cursor.endEditBlock()
        else:
            cursor.insertText("\n" + continuation)
        self.setTextCursor(cursor)
