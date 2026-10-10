# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility shell exposing Markopad's source editor to Marko Plus."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPalette, QTextCursor
from PyQt6.QtWidgets import QApplication

from marko_plus.widgets.markopad_source_editor import MarkopadSourceEditor


class CodeEditor(MarkopadSourceEditor):
    """Markopad editor adapted to the Marko Plus editor-page API."""

    go_to_line_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        base = QApplication.palette().color(QPalette.ColorRole.Base)
        self.set_color_scheme("dark" if base.lightness() < 128 else "light")

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt API name
        modifiers = event.modifiers()
        key = event.key()

        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_G:
            self.go_to_line_requested.emit()
            event.accept()
            return

        if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_D:
            self.duplicate_current_line_or_selection()
            event.accept()
            return

        super().keyPressEvent(event)

    def paste_safely(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            self.insertFromMimeData(clipboard.mimeData())

    def delete_selection_or_character(self) -> None:
        if self.isReadOnly():
            self.view_only_edit_attempt.emit()
            return
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
        else:
            cursor.deleteChar()
        self.setTextCursor(cursor)
        self.setFocus()

    def select_all_text(self) -> None:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)
        self.setFocus()
        self._decoration_timer.stop()
        self.setExtraSelections([])

    def go_to_line(self, line_number: int) -> bool:
        if line_number < 1 or line_number > self.blockCount():
            return False
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return False
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()
        self.setFocus()
        return True

    def mark_clean(self) -> None:
        self.document().setModified(False)

    @property
    def is_modified(self) -> bool:
        return self.document().isModified()
