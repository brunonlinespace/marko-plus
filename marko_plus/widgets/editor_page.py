# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""One lazily-created editor page for a Markdown document.

Responsibilities:
- load and save a single file
- synchronize Qt's native modified flag with ModuleRepository
- provide Find, Replace, and Go to Line controls
- detect external file changes without silently discarding edits
- expose external-editor, rename, duplicate, and remove signals

The page does not rename or delete files itself. Those actions belong to the
file controller, keeping this widget focused and testable.
"""

from __future__ import annotations

from html import escape
import codecs
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDropEvent,
    QColor,
    QFont,
    QFontDatabase,
    QKeySequence,
    QPalette,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFontDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from marko_plus.app_constants import MARKDOWN_EXTENSIONS
from marko_plus.legacy_ricopad import strip_legacy_envelope
from marko_plus.models.module import Module
from marko_plus.models.module_repository import ModuleRepository
from marko_plus.widgets.code_editor import CodeEditor
from marko_plus.widgets.markopad_preview import MarkdownPreview
from marko_plus.services.config_service import ConfigService
from marko_plus.services.file_io import (
    FileSnapshot,
    FileStateChangedError,
    FileTooLargeError,
    UnsupportedFileError,
    current_file_state,
    fsync_directory,
    install_new_file_from_temp,
    read_regular_file,
    snapshot_from_payload,
    validated_symlink_target,
)


def _host_process_environment() -> dict[str, str]:
    """Return a clean host environment for More Symbols utilities."""
    environment = os.environ.copy()
    if sys.platform == "win32":
        return environment
    if not (environment.get("APPDIR") or getattr(sys, "frozen", False)):
        return environment
    appdir = environment.get("APPDIR")
    original_library_path = environment.pop("LD_LIBRARY_PATH_ORIG", None)
    if original_library_path is None:
        environment.pop("LD_LIBRARY_PATH", None)
    else:
        environment["LD_LIBRARY_PATH"] = original_library_path
    for variable in (
        "APPDIR", "APPIMAGE", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM",
        "QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_PLATFORMTHEME",
        "QT_STYLE_OVERRIDE", "QML_IMPORT_PATH", "QML2_IMPORT_PATH",
    ):
        environment.pop(variable, None)
    if appdir and environment.get("PATH"):
        appdir_real = os.path.realpath(appdir)
        clean_path: list[str] = []
        for entry in environment["PATH"].split(os.pathsep):
            if not entry:
                continue
            try:
                entry_real = os.path.realpath(entry)
                inside = os.path.commonpath((appdir_real, entry_real)) == appdir_real
            except (OSError, ValueError):
                inside = False
            if not inside:
                clean_path.append(entry)
        environment["PATH"] = os.pathsep.join(clean_path)
    return environment


class EditorPage(QWidget):
    """Editor and file controls for one repository Module."""

    MAX_FILE_BYTES = 25 * 1024 * 1024
    MAX_SEARCH_QUERY_CHARACTERS = 4096
    MAX_SEARCH_MATCHES = 10_000

    external_editor_requested = pyqtSignal(object)
    containing_folder_requested = pyqtSignal(object)
    rename_requested = pyqtSignal(object)
    remove_requested = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)
    undo_redo_changed = pyqtSignal(bool, bool)
    status_message = pyqtSignal(str)
    saved = pyqtSignal(object)
    preferences_changed = pyqtSignal()
    external_files_dropped = pyqtSignal(object, object)
    view_mode_changed = pyqtSignal(str)
    path_changed = pyqtSignal(object, object, object)

    def __init__(
        self,
        module: Module,
        repository: ModuleRepository,
        config: ConfigService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.module = module
        self.repository = repository
        self.config = config
        self.editor = CodeEditor(self)
        self.preview = MarkdownPreview(self)
        self.preview.setAcceptDrops(False)
        self.view_mode = str(self.config.get("markopad_view_mode", "split"))
        if self.view_mode not in {"source", "split", "preview"}:
            self.view_mode = "split"
        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.setInterval(180)
        self.preview_timer.timeout.connect(self.refresh_preview_now)
        self.view_only = bool(self.config.get("lock_editor", False))
        self._view_only_notice_shown = False
        self.file_encoding = "utf-8"
        self.file_bom = b""
        self.file_newline = "\n"
        self.file_disk_snapshot: FileSnapshot | None = None
        self.legacy_ricopad_loaded = False
        stored_split = self.config.get_int_list(
            "markopad_editor_splitter_sizes", [3, 2], length=2
        )
        self._last_splitter_sizes = (
            stored_split if len(stored_split) == 2 and all(value > 0 for value in stored_split)
            else [3, 2]
        )
        self._header_visible = bool(config.get("show_file_header", True))

        self._loaded_mtime_ns: int | None = None
        self._external_change_pending = False
        self._backing_state = "normal"
        self._ignore_document_signal = False
        self._last_find_text = ""
        self._search_matches: list[tuple[int, int]] = []
        self._current_search_index = -1
        self._search_results_truncated = False
        self._search_refresh_suspended = False

        self._build_ui()
        self._connect_signals()
        self.loaded_successfully = self.load_from_disk(show_errors=False)
        self._refresh_header()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setVisible(self._header_visible)
        root.addWidget(self.title_label)

        self.external_banner = QFrame()
        self.external_banner.setFrameShape(QFrame.Shape.StyledPanel)
        banner_layout = QHBoxLayout(self.external_banner)
        self.external_label = QLabel("This file changed on disk after it was opened.")
        self.external_label.setWordWrap(True)
        banner_layout.addWidget(self.external_label, 1)
        self.reload_external_button = QPushButton("Reload from Disk")
        self.reload_external_button.clicked.connect(self._reload_external_change)
        save_version = QPushButton("Save Version As…")
        save_version.clicked.connect(self._save_editor_version_as)
        banner_layout.addWidget(self.reload_external_button)
        banner_layout.addWidget(save_version)
        self.external_banner.hide()
        root.addWidget(self.external_banner)

        # Keep the Sheepy-derived editor actions internally available for
        # state synchronization; the application-global menu bar is the only
        # visible editor command menu surface.
        self._build_editor_menus()

        # Marko Plus keeps the established document page shell and uses Markopad's
        # canonical Source / Source + Preview / Preview document surface.
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.content_splitter.addWidget(self.editor)
        self.content_splitter.addWidget(self.preview)
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setSizes(self._last_splitter_sizes)
        root.addWidget(self.content_splitter, 1)

        # Markopad's authoritative two-row Find/Replace panel lives at the
        # bottom of the editor surface. Plus keeps the newer bounded/safe
        # search engine underneath without changing this interaction model.
        self.search_frame = QFrame(self)
        self.search_frame.setFrameShape(QFrame.Shape.StyledPanel)
        search_grid = QGridLayout(self.search_frame)
        search_grid.setContentsMargins(8, 6, 8, 6)
        self.find_input = QLineEdit(self.search_frame)
        self.find_input.setMaxLength(self.MAX_SEARCH_QUERY_CHARACTERS)
        self.find_input.setPlaceholderText("Find")
        self.replace_input = QLineEdit(self.search_frame)
        self.replace_input.setPlaceholderText("Replace")
        self.search_case_checkbox = QCheckBox("Match case", self.search_frame)
        self.search_counter = QLabel("", self.search_frame)
        self.search_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search_previous_button = QPushButton("Previous", self.search_frame)
        self.search_next_button = QPushButton("Next", self.search_frame)
        replace_button = QPushButton("Replace", self.search_frame)
        replace_all_button = QPushButton("Replace All", self.search_frame)
        close_search = QPushButton("Close", self.search_frame)
        search_grid.addWidget(self.find_input, 0, 0, 1, 3)
        search_grid.addWidget(self.search_previous_button, 0, 3)
        search_grid.addWidget(self.search_next_button, 0, 4)
        search_grid.addWidget(self.search_case_checkbox, 0, 5)
        search_grid.addWidget(self.search_counter, 0, 6)
        search_grid.addWidget(self.replace_input, 1, 0, 1, 3)
        search_grid.addWidget(replace_button, 1, 3)
        search_grid.addWidget(replace_all_button, 1, 4)
        search_grid.addWidget(close_search, 1, 6)
        self.find_input.textChanged.connect(self.refresh_search)
        self.search_case_checkbox.toggled.connect(self.refresh_search)
        self.find_input.returnPressed.connect(self.find_next)
        self.search_previous_button.clicked.connect(self.find_previous)
        self.search_next_button.clicked.connect(self.find_next)
        replace_button.clicked.connect(self.replace_current)
        replace_all_button.clicked.connect(self.replace_all)
        close_search.clicked.connect(self.hide_find_panel)
        # Compatibility aliases keep the hardened Plus replace implementation
        # attached to the Markopad panel fields rather than a separate dialog.
        self.replace_find_entry = self.find_input
        self.replace_with_entry = self.replace_input
        self.replace_case_checkbox = self.search_case_checkbox
        self.search_frame.hide()
        root.addWidget(self.search_frame)

        self.editor_status = QStatusBar(self)
        self.position_label = QLabel("Ln 1/1, Col 1, Char 0")
        self.operation_mode_label = QLabel("Insert")
        self.encoding_status_label = QLabel("UTF-8")
        # Markopad-style document status: edit mode, position, encoding.
        self.editor_status.addWidget(self.operation_mode_label)
        self.editor_status.addWidget(self.position_label, 1)
        self.editor_status.addPermanentWidget(self.encoding_status_label)
        root.addWidget(self.editor_status)

        self.apply_preferences()

    def _menu_action(
        self, menu, text: str, callback, *, checkable: bool = False,
        shortcut: str | None = None,
    ) -> QAction:
        action = QAction(text, self)
        action.setCheckable(checkable)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def _build_editor_menus(self) -> None:
        self.editor_file_menu = QMenu("File", self)
        file_menu = self.editor_file_menu
        self.save_action = self._menu_action(file_menu, "Save Changes", self.save_to_disk)
        self.discard_action = self._menu_action(file_menu, "Discard Changes", self.confirm_reload)
        file_menu.addSeparator()
        self.properties_action = self._menu_action(file_menu, "Properties…", self.show_properties_dialog)
        file_menu.addSeparator()
        self.external_action = self._menu_action(file_menu, "Open in External Editor", lambda: self.external_editor_requested.emit(self.module))
        self.folder_action = self._menu_action(file_menu, "Open Containing Folder", lambda: self.containing_folder_requested.emit(self.module))
        self.rename_action = self._menu_action(file_menu, "Rename…", lambda: self.rename_requested.emit(self.module))
        self.duplicate_file_action = self._menu_action(file_menu, "Duplicate Markdown File…", lambda: self.duplicate_requested.emit(self.module))
        file_menu.addSeparator()
        self.remove_action = self._menu_action(file_menu, "Remove Markdown File…", lambda: self.remove_requested.emit(self.module))

        self.editor_edit_menu = QMenu("Edit", self)
        edit_menu = self.editor_edit_menu
        self.undo_action = self._menu_action(edit_menu, "Undo", self.editor.undo)
        self.redo_action = self._menu_action(edit_menu, "Redo", self.editor.redo)
        edit_menu.addSeparator()
        self.cut_action = self._menu_action(edit_menu, "Cut", self.editor.cut)
        self.copy_action = self._menu_action(edit_menu, "Copy", self.editor.copy)
        self.paste_plain_action = self._menu_action(edit_menu, "Paste as Plain Text", self.editor.paste_safely)
        self.delete_action = self._menu_action(edit_menu, "Delete", self.editor.delete_selection_or_character)
        edit_menu.addSeparator()
        self.comment_action = self._menu_action(edit_menu, "Toggle Comment", self.editor.toggle_comment)
        self.duplicate_line_action = self._menu_action(edit_menu, "Duplicate Line or Selection", self.editor.duplicate_current_line_or_selection)
        self.select_all_action = self._menu_action(edit_menu, "Select All", self.editor.select_all_text)
        edit_menu.addSeparator()
        self.find_next_action = self._menu_action(edit_menu, "Find Next", self.find_next, shortcut="F3")
        self.find_previous_action = self._menu_action(edit_menu, "Find Previous", self.find_previous, shortcut="Shift+F3")
        # These menu actions belong to EditorPage's private editor menu, which is
        # not itself installed in the Plus MainWindow. Install the actions on the
        # live page as well so their WidgetWithChildren shortcuts actually work.
        self.addAction(self.find_next_action)
        self.addAction(self.find_previous_action)
        self.clear_search_action = self._menu_action(edit_menu, "Clear Search", self.clear_search)
        self.dismiss_find_action = QAction("Close Find/Replace", self)
        self.dismiss_find_action.setShortcut(QKeySequence("Esc"))
        self.dismiss_find_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.dismiss_find_action.triggered.connect(self.hide_find_panel)
        self.addAction(self.dismiss_find_action)
        self.replace_action = self._menu_action(edit_menu, "Replace", self.replace_current)
        self.replace_all_action = self._menu_action(edit_menu, "Replace All", self.replace_all)
        self.goto_action = self._menu_action(edit_menu, "Go to Line…", self.show_go_to_line)

        self.editor_view_menu = QMenu("View", self)
        view_menu = self.editor_view_menu
        self.view_only_action = self._menu_action(view_menu, "Locked Mode", self.toggle_view_only, checkable=True)
        view_menu.addSeparator()
        self.word_wrap_action = self._menu_action(view_menu, "Word Wrap", self.toggle_word_wrap, checkable=True)
        self.line_numbers_action = self._menu_action(view_menu, "Line Numbers", self.toggle_line_numbers, checkable=True)
        self.font_action = self._menu_action(view_menu, "Display Font…", self.choose_display_font)


    @staticmethod
    def _dropped_markdown_paths(mime_data) -> list[Path]:
        if not mime_data.hasUrls():
            return []
        paths: list[Path] = []
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile()).expanduser().resolve(strict=False)
            if path.is_file() and path.suffix.casefold() in MARKDOWN_EXTENSIONS:
                paths.append(path)
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._dropped_markdown_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._dropped_markdown_paths(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = self._dropped_markdown_paths(event.mimeData())
        if paths:
            self.external_files_dropped.emit(paths, self.module.path.parent)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    def _connect_signals(self) -> None:
        self.editor.document().modificationChanged.connect(self._on_modification_changed)
        self.editor.document().undoAvailable.connect(self._emit_undo_redo_state)
        self.editor.document().redoAvailable.connect(self._emit_undo_redo_state)
        self.editor.paste_rejected.connect(self.status_message)
        self.editor.go_to_line_requested.connect(self.show_go_to_line)
        self.editor.view_only_edit_attempt.connect(self.show_view_only_edit_prompt)
        self.editor.overwrite_mode_changed.connect(self._update_operation_mode)
        self.editor.files_dropped.connect(
            lambda paths: self.external_files_dropped.emit(paths, self.module.path.parent)
        )
        self.editor.cursorPositionChanged.connect(self._update_cursor_position)
        self.editor.textChanged.connect(self.schedule_preview)
        self.editor.textChanged.connect(
            lambda: (
                None if self._search_refresh_suspended
                else self.refresh_search() if self.search_frame.isVisible()
                else self.clear_search_results()
            )
        )
        self.repository.module_changed.connect(self._on_repository_module_changed)
        self.repository.module_path_changed.connect(self._on_module_path_changed)
        self.content_splitter.splitterMoved.connect(self._remember_splitter_sizes)

    def _emit_undo_redo_state(self, *_args) -> None:
        document = self.editor.document()
        undo_available = document.isUndoAvailable() and not self.view_only
        redo_available = document.isRedoAvailable() and not self.view_only
        self.undo_action.setEnabled(undo_available)
        self.redo_action.setEnabled(redo_available)
        self.undo_redo_changed.emit(undo_available, redo_available)

    def _apply_presentation_safely(self, callback) -> None:
        """Run presentation-only work without changing document dirty state."""
        document = self.editor.document()
        was_modified = bool(document.isModified())
        previous_ignore = self._ignore_document_signal
        self._ignore_document_signal = True
        try:
            callback()
            if bool(document.isModified()) != was_modified:
                document.setModified(was_modified)
        finally:
            self._ignore_document_signal = previous_ignore
        # The repository is authoritative for the Plus dirty indicator; keep it
        # synchronized with the exact state that existed before presentation work.
        self.repository.set_dirty(self.module.path, was_modified)
        self._refresh_header()

    def apply_preferences(self) -> None:
        """Apply shared Markopad display preferences without mutating document state."""
        def apply() -> None:
            self.word_wrap_action.setChecked(bool(self.config.get("editor_word_wrap", True)))
            self.line_numbers_action.setChecked(bool(self.config.get("editor_line_numbers", True)))
            self.editor.set_word_wrap_enabled(self.word_wrap_action.isChecked())
            self.editor.set_line_numbers_visible(self.line_numbers_action.isChecked())
            self.editor.set_tab_width_spaces(
                self.config.get_int("editor_tab_width_spaces", 4, minimum=1, maximum=16)
            )
            fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
            family = str(self.config.get("editor_font_family", "") or "").strip() or fixed.family()
            size = self.config.get_int("editor_font_size", 11, minimum=6, maximum=72)
            weight = self.config.get_int("editor_font_weight", 400, minimum=100, maximum=900)
            zoom_percent = self.config.get_int("markopad_zoom", 100, minimum=50, maximum=300)
            font = QFont(family)
            font.setPointSizeF(max(6.0, size * zoom_percent / 100.0))
            font.setStyleHint(QFont.StyleHint.Monospace)
            try:
                font.setWeight(QFont.Weight(weight))
            except (TypeError, ValueError):
                font.setWeight(QFont.Weight.Normal)
            font.setItalic(bool(self.config.get("editor_font_italic", False)))
            self.editor.set_editor_font(font)
            self.apply_preview_font()
            self.editor_status.setVisible(bool(self.config.get("show_status_bar", True)))
            self.apply_theme()
            self.set_view_mode(self.view_mode, persist=False)
        self._apply_presentation_safely(apply)

    def apply_canvas_theme(self) -> None:
        """Apply only Dark Editor canvas presentation while preserving dirty state."""
        self._apply_presentation_safely(self.apply_theme)

    def _canvas_is_light(self) -> bool:
        stored = self.config.get("editor_canvas_light", True)
        return stored if isinstance(stored, bool) else True

    def apply_theme(self) -> None:
        canvas_light = self._canvas_is_light()

        self.editor.set_color_scheme("light" if canvas_light else "dark")
        editor_palette = QPalette(self.editor.palette())
        preview_palette = QPalette(self.preview.palette())
        if canvas_light:
            base_color = QColor("#FFFFFF")
            text_color = QColor("#202124")
            highlight_color = QColor("#0B8781")
            link_color = QColor("#174EA6")
        else:
            base_color = QColor("#151719")
            text_color = QColor("#F1F3F4")
            highlight_color = QColor("#158B86")
            link_color = QColor("#82AAFF")

        for palette in (editor_palette, preview_palette):
            palette.setColor(QPalette.ColorRole.Base, base_color)
            palette.setColor(QPalette.ColorRole.Text, text_color)
            palette.setColor(QPalette.ColorRole.Highlight, highlight_color)
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        preview_palette.setColor(QPalette.ColorRole.Link, link_color)
        preview_palette.setColor(QPalette.ColorRole.LinkVisited, link_color)

        self.editor.setPalette(editor_palette)
        self.editor.viewport().setPalette(editor_palette)
        self.editor.line_number_area.update()
        self.preview.setPalette(preview_palette)
        self.preview.viewport().setPalette(preview_palette)
        self.preview.document().setDefaultStyleSheet(
            f"a {{ color: {link_color.name()}; }}"
        )
        self._apply_preview_link_color(link_color)

    def show_editor_status(self, message: str, timeout: int = 0) -> None:
        """Show a transient message in this document's editor status bar."""
        self.editor_status.showMessage(str(message), max(0, int(timeout)))

    def _apply_preview_link_color(self, link_color: QColor | None = None) -> None:
        """Keep every rendered anchor on the active canvas's Markopad blue."""
        if link_color is None:
            canvas_light = self._canvas_is_light()
            link_color = QColor("#174EA6" if canvas_light else "#82AAFF")

        document = self.preview.document()
        cursor = QTextCursor(document)
        cursor.beginEditBlock()
        block = document.firstBlock()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isAnchor():
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(
                        fragment.position() + fragment.length(),
                        QTextCursor.MoveMode.KeepAnchor,
                    )
                    anchor_format = fragment.charFormat()
                    anchor_format.setForeground(link_color)
                    cursor.setCharFormat(anchor_format)
                iterator += 1
            block = block.next()
        cursor.endEditBlock()

    def reset_content_splitter(self) -> None:
        """Restore and persist the canonical 3:2 Source/Preview split."""
        if self.view_mode != "split":
            return
        self._last_splitter_sizes = [3, 2]
        self.content_splitter.setSizes([3, 2])
        sizes = [int(value) for value in self.content_splitter.sizes()]
        if len(sizes) == 2 and all(value > 0 for value in sizes):
            self._last_splitter_sizes = sizes
        self.config.set(
            "markopad_editor_splitter_sizes",
            list(self._last_splitter_sizes),
            save=True,
        )

    def _remember_splitter_sizes(self, *_args) -> None:
        """Remember the Source/Preview split without confusing it with the app sidebar splitter."""
        if self.view_mode != "split":
            return
        sizes = [int(value) for value in self.content_splitter.sizes()]
        if len(sizes) != 2 or not all(value > 0 for value in sizes):
            return
        self._last_splitter_sizes = sizes
        self.config.set("markopad_editor_splitter_sizes", list(sizes), save=False)

    def set_view_mode(self, mode: str, *, persist: bool = True) -> None:
        if mode not in {"source", "split", "preview"}:
            return
        if self.view_mode == "split" and mode != "split":
            self._remember_splitter_sizes()
        self.view_mode = mode
        self.editor.setVisible(mode in {"source", "split"})
        self.preview.setVisible(mode in {"split", "preview"})
        if mode == "source":
            self.content_splitter.setSizes([1, 0])
        elif mode == "preview":
            self.content_splitter.setSizes([0, 1])
            self.refresh_preview_now(force=True)
        else:
            stored = self.config.get_int_list(
                "markopad_editor_splitter_sizes", self._last_splitter_sizes, length=2
            )
            if len(stored) != 2 or not all(value > 0 for value in stored):
                stored = list(self._last_splitter_sizes)
            self._last_splitter_sizes = [int(value) for value in stored]
            self.content_splitter.setSizes(self._last_splitter_sizes)
            self.refresh_preview_now(force=True)
        if persist:
            if mode in {"source", "split"}:
                self.config.set("markopad_last_editable_view_mode", mode, save=False)
            self.config.set("markopad_view_mode", mode, save=True)
        self.view_mode_changed.emit(mode)
        (self.editor if mode != "preview" else self.preview).setFocus()

    def schedule_preview(self) -> None:
        if self.preview.isVisible():
            self.preview_timer.start()

    def refresh_preview_now(self, *, force: bool = False) -> None:
        if force or self.preview.isVisible():
            self.preview.render_markdown(self.editor.toPlainText())
            self._apply_preview_link_color()
            self._apply_preview_quote_effect()

    def toggle_find_panel(self, replace: bool = False) -> bool:
        """Toggle the requested search field when its own shortcut is pressed again."""
        target = self.replace_input if replace else self.find_input
        if self.search_frame.isVisible() and target.hasFocus():
            self.hide_find_panel()
            return False
        self.show_find_panel(replace)
        return True

    def show_find_panel(self, replace: bool = False) -> None:
        """Show Markopad's bottom Find/Replace panel and focus the requested row."""
        self.search_frame.show()
        selected = self.editor.textCursor().selectedText().replace("\u2029", "\n")
        if selected and "\n" not in selected and len(selected) <= self.MAX_SEARCH_QUERY_CHARACTERS:
            self.find_input.setText(selected)
        self.find_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.find_input.selectAll()
        if replace:
            self.replace_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self.replace_input.selectAll()
        self.refresh_search()

    def hide_find_panel(self) -> None:
        if not self.search_frame.isVisible():
            return
        self.search_frame.hide()
        self.clear_search_results()
        if self.view_mode == "preview":
            self.preview.setFocus()
        else:
            self.editor.setFocus()

    def show_replace_dialog(self) -> None:
        """Compatibility entry point: Markopad uses the shared bottom panel, not a dialog."""
        self.show_find_panel(True)

    def _replace_flags(self):
        flags = QTextDocument.FindFlag(0)
        if self.search_case_checkbox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _selection_matches_replace_query(self, cursor: QTextCursor, query: str) -> bool:
        if not cursor.hasSelection():
            return False
        selected = cursor.selectedText().replace("\u2029", "\n")
        if self.search_case_checkbox.isChecked():
            return selected == query
        return selected.casefold() == query.casefold()

    def _find_replace_match(self, query: str, start_cursor=None) -> QTextCursor:
        document = self.editor.document()
        start = QTextCursor(start_cursor or self.editor.textCursor())
        if start.hasSelection():
            start.setPosition(start.selectionEnd())
        match = document.find(query, start, self._replace_flags())
        if match.isNull():
            match = document.find(query, QTextCursor(document), self._replace_flags())
        return match

    def _insert_curated_symbol(self, symbol: str, dialog: QDialog | None = None) -> None:
        if self.view_only or self.editor.isReadOnly() or self.view_mode == "preview":
            self.show_view_only_edit_prompt() if self.view_only else None
            if dialog is not None:
                dialog.reject()
            return
        if self.editor.insert_guarded_text(symbol):
            if dialog is not None:
                dialog.accept()
            self.editor.setFocus()
            self.editor.ensureCursorVisible()

    def _open_more_symbols(self, dialog: QDialog | None = None) -> None:
        if dialog is not None:
            dialog.accept()
        if sys.platform == "win32":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            candidates = (
                os.path.join(system_root, "System32", "charmap.exe"),
                "charmap.exe",
            )
            missing = "Windows Character Map could not be found on this system."
        else:
            candidates = ("kcharselect", "gucharmap", "gnome-characters", "charmap")
            missing = (
                "No supported character-map application was found.\n\n"
                "Install KCharSelect, GNOME Characters, or Gucharmap to use this option."
            )
        host_environment = _host_process_environment()
        host_path = host_environment.get("PATH")
        for command in candidates:
            executable = command if os.path.isfile(command) else shutil.which(command, path=host_path)
            if not executable:
                continue
            try:
                subprocess.Popen(
                    [executable],
                    env=host_environment,
                    start_new_session=(sys.platform != "win32"),
                )
                self.editor.setFocus()
                return
            except OSError:
                continue
        QMessageBox.information(self, "More Symbols", missing)
        self.editor.setFocus()

    def show_symbols_dialog(self) -> None:
        """Show the common Plus curated symbol grid using Marko insertion safety."""
        if self.view_only or self.editor.isReadOnly() or self.view_mode == "preview":
            if self.view_only:
                self.show_view_only_edit_prompt()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Symbols")
        dialog.setModal(True)
        layout = QGridLayout(dialog)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(5)
        layout.setVerticalSpacing(5)
        symbols = (
            "©", "®", "™", "°", "•", "·", "—", "–",
            "…", "→", "←", "↑", "↓", "✓", "✗", "§",
            "£", "€", "$", "¥", "¢", "±", "×", "÷",
            "≠", "≤", "≥", "≈", "∞", "µ", "¶", "№",
            "★", "☆", "♥", "♦", "♣", "♠", "☐", "☑",
        )
        columns = 8
        for index, symbol in enumerate(symbols):
            button = QToolButton(dialog)
            button.setText(symbol)
            button.setToolTip(f"Insert {symbol}")
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(34, 30)
            button.clicked.connect(
                lambda _checked=False, value=symbol: self._insert_curated_symbol(value, dialog)
            )
            layout.addWidget(button, index // columns, index % columns)
        row = (len(symbols) + columns - 1) // columns
        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator, row, 0, 1, columns)
        more_button = QPushButton("More Symbols…", dialog)
        more_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        more_button.clicked.connect(lambda _checked=False: self._open_more_symbols(dialog))
        layout.addWidget(more_button, row + 1, 0, 1, columns)
        dialog.adjustSize()
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            dialog.move(
                geometry.center().x() - dialog.width() // 2,
                geometry.center().y() - dialog.height() // 2,
            )
        dialog.exec()
        self.editor.setFocus()

    def toggle_word_wrap(self, checked: bool) -> None:
        self.config.set("editor_word_wrap", bool(checked), save=True)
        self.preferences_changed.emit()

    def toggle_line_numbers(self, checked: bool) -> None:
        self.config.set("editor_line_numbers", bool(checked), save=True)
        self.preferences_changed.emit()

    def choose_display_font(self) -> None:
        selected, accepted = QFontDialog.getFont(self.editor.font(), self, "Display Font")
        if not accepted:
            return
        self.config.update({
            "editor_font_family": selected.family(),
            "editor_font_size": selected.pointSize(),
            "editor_font_weight": int(selected.weight()),
            "editor_font_italic": selected.italic(),
        }, save=True)
        self.preferences_changed.emit()

    def preview_base_font(self) -> QFont:
        """Return Markopad's application-based persisted Preview font."""
        font = QFont(QApplication.font())
        stored = self.config.get("preview_font", "")
        if isinstance(stored, str) and stored:
            candidate = QFont()
            if candidate.fromString(stored):
                font = candidate
        if font.pointSizeF() <= 0:
            font.setPointSizeF(10.0)
        return font

    def apply_preview_font(self) -> None:
        font = self.preview_base_font()
        zoom_percent = self.config.get_int("markopad_zoom", 100, minimum=50, maximum=300)
        font.setPointSizeF(max(6.0, font.pointSizeF() * zoom_percent / 100.0))
        self.preview.document().setDefaultFont(font)

    def choose_preview_font(self) -> None:
        dialog = QFontDialog(self.preview_base_font(), self)
        dialog.setWindowTitle("Preview Font — Marko Plus")
        dialog.setOption(
            QFontDialog.FontDialogOption.DontUseNativeDialog,
            True,
        )

        effects = next(
            (
                group
                for group in dialog.findChildren(QGroupBox)
                if group.title().replace("&", "").strip().casefold() == "effects"
            ),
            None,
        )
        if effects is None or effects.layout() is None:
            return

        effects_layout = effects.layout()
        italic_quotes = QCheckBox("Italicize block quotations", effects)
        italic_quotes.setChecked(
            bool(self.config.get("preview_italic_quotes", False))
        )
        if isinstance(effects_layout, QGridLayout):
            effects_layout.addWidget(
                italic_quotes,
                effects_layout.rowCount(),
                0,
                1,
                max(1, effects_layout.columnCount()),
            )
        else:
            effects_layout.addWidget(italic_quotes)

        def update_effect_availability(font: QFont) -> None:
            already_italic = font.italic()
            italic_quotes.setEnabled(not already_italic)
            italic_quotes.setToolTip(
                "The selected Preview font is already italic."
                if already_italic
                else ""
            )

        dialog.currentFontChanged.connect(update_effect_availability)
        update_effect_availability(dialog.currentFont())

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.currentFont()
        self.config.update({
            "preview_font": selected.toString(),
            "preview_italic_quotes": italic_quotes.isChecked(),
        }, save=True)
        self.apply_preview_font()
        self.refresh_preview_now(force=True)
        self.preferences_changed.emit()

    def _apply_preview_quote_effect(self) -> None:
        """Italicize only Qt-rendered Markdown quotation blocks when requested."""
        if (
            not bool(self.config.get("preview_italic_quotes", False))
            or self.preview_base_font().italic()
        ):
            return

        document = self.preview.document()
        cursor = QTextCursor(document)
        italic = QTextCharFormat()
        italic.setFontItalic(True)
        cursor.beginEditBlock()
        block = document.firstBlock()
        while block.isValid():
            block_format = block.blockFormat()
            if block_format.hasProperty(QTextFormat.Property.BlockQuoteLevel):
                cursor.setPosition(block.position())
                cursor.setPosition(
                    block.position() + max(0, block.length() - 1),
                    QTextCursor.MoveMode.KeepAnchor,
                )
                if cursor.hasSelection():
                    cursor.mergeCharFormat(italic)
            block = block.next()
        cursor.endEditBlock()

    def toggle_view_only(self, checked: bool) -> None:
        requested = bool(checked)
        should_confirm = bool(self.config.get("confirm_locked_mode_disable", True))
        if self.view_only and not requested and should_confirm:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Disable Locked Mode? — Marko Plus")
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setText("Locked Mode protects files from accidental changes.")
            dialog.setInformativeText(
                "Continue only when you intend to edit the document."
            )
            dont_ask = QCheckBox(
                "Don't ask again when disabling Locked Mode", dialog
            )
            dialog.setCheckBox(dont_ask)
            keep = dialog.addButton(
                "Keep Locked", QMessageBox.ButtonRole.RejectRole
            )
            cont = dialog.addButton(
                "Continue", QMessageBox.ButtonRole.AcceptRole
            )
            dialog.setDefaultButton(keep)
            dialog.setEscapeButton(keep)
            dialog.exec()
            if dialog.clickedButton() is not cont:
                self.view_only_action.blockSignals(True)
                self.view_only_action.setChecked(True)
                self.view_only_action.blockSignals(False)
                return
            if dont_ask.isChecked():
                self.config.set(
                    "confirm_locked_mode_disable", False, save=True
                )
        self.set_view_only(requested)
        message = "Locked Mode enabled." if requested else "Locked Mode disabled."
        self.editor_status.showMessage(message, 3000)
        self.status_message.emit(message)

    def scroll_to_top(self) -> None:
        """Reset the editor viewport to the document start.

        Locked Mode uses this when a document is opened, matching the Plus-family
        read-only opening behavior without changing normal editable reopening.
        """
        cursor = self.editor.textCursor()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        bar = self.editor.verticalScrollBar()
        bar.setValue(bar.minimum())

    def set_view_only(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.view_only = enabled
        self._view_only_notice_shown = False
        self.view_only_action.blockSignals(True)
        self.view_only_action.setChecked(enabled)
        self.view_only_action.blockSignals(False)
        self.editor.set_view_only(enabled)
        for action in (self.undo_action, self.redo_action, self.cut_action, self.paste_plain_action, self.delete_action, self.comment_action, self.duplicate_line_action, self.replace_action, self.replace_all_action):
            action.setEnabled(not enabled)
        self._emit_undo_redo_state()
        self.status_message.emit(
            "Locked Mode enabled." if enabled else "Editing mode enabled."
        )

    def show_view_only_edit_prompt(self) -> None:
        message = "Editing is disabled while Locked Mode is enabled."
        self.editor_status.showMessage(message, 4000)
        self.status_message.emit(message)
        if self._view_only_notice_shown:
            return
        self._view_only_notice_shown = True
        QMessageBox.information(
            self,
            "Locked Mode — Marko Plus",
            "Editing is disabled because Locked Mode is enabled.\n\n"
            "Clear View → Locked Mode and confirm Continue to edit the document.",
        )

    def _update_operation_mode(self, overwrite: bool) -> None:
        self.operation_mode_label.setText("Overwrite" if overwrite else "Insert")

    def _update_cursor_position(self) -> None:
        cursor = self.editor.textCursor()
        self.position_label.setText(
            f"Ln {cursor.blockNumber() + 1}/{self.editor.blockCount()}, "
            f"Col {cursor.positionInBlock() + 1}, Char {cursor.position()}"
        )

    def clear_search_results(self) -> None:
        self._search_matches = []
        self._current_search_index = -1
        self._search_results_truncated = False
        self.editor.clear_search_selections()
        self._update_search_counter()

    def _update_search_counter(self) -> None:
        total = len(self._search_matches)
        current = self._current_search_index + 1 if 0 <= self._current_search_index < total else 0
        total_text = f"{total:,}+" if self._search_results_truncated else f"{total:,}"
        self.search_counter.setText(f"{current:,}/{total_text}")
        self.search_counter.setToolTip(
            f"Showing the first {self.MAX_SEARCH_MATCHES:,} matches."
            if self._search_results_truncated else ""
        )
        enabled = total > 0
        self.search_previous_button.setEnabled(enabled)
        self.search_next_button.setEnabled(enabled)

    def refresh_search(self, _value=None) -> bool:
        """Markopad search model: all matches gold; active hit is a real selection."""
        if not self.search_frame.isVisible():
            return False
        query = self.find_input.text()[: self.MAX_SEARCH_QUERY_CHARACTERS]
        self._search_matches = []
        self._current_search_index = -1
        self._search_results_truncated = False
        if not query:
            self.editor.clear_search_selections()
            self._update_search_counter()
            return False
        document = self.editor.document()
        cursor = QTextCursor(document)
        flags = self._replace_flags()
        while len(self._search_matches) < self.MAX_SEARCH_MATCHES:
            found = document.find(query, cursor, flags)
            if found.isNull():
                break
            self._search_matches.append((found.selectionStart(), found.selectionEnd()))
            cursor = QTextCursor(found)
            cursor.setPosition(found.selectionEnd())
        if len(self._search_matches) == self.MAX_SEARCH_MATCHES:
            self._search_results_truncated = not document.find(query, cursor, flags).isNull()
        selections: list[QTextEdit.ExtraSelection] = []
        for start, end in self._search_matches:
            cursor = QTextCursor(document)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = QTextCharFormat()
            selection.format.setBackground(QColor("#C9A227"))
            selection.format.setForeground(QColor("#101010"))
            selections.append(selection)
        self.editor.set_search_selections(selections)
        if self._search_matches:
            self._current_search_index = 0
            start, end = self._search_matches[0]
            active_cursor = self.editor.textCursor()
            active_cursor.setPosition(start)
            active_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            self.editor.setTextCursor(active_cursor)
            self.editor.ensureCursorVisible()
        self._update_search_counter()
        return bool(self._search_matches)

    def find_text(self, show_message: bool = True) -> bool:
        # Compatibility entry point retained for shell/runtime callers. Markopad
        # performs live search as the Find field changes and does not show a modal
        # "no matches" message.
        return self.refresh_search()

    def find_text_and_refocus(self, _checked=False) -> None:
        self.refresh_search()
        self.find_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def _ensure_search_matches(self) -> bool:
        if not self.search_frame.isVisible():
            self.show_find_panel(False)
        if not self.find_input.text():
            self.find_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self.find_input.selectAll()
            return False
        if not self._search_matches:
            return self.refresh_search()
        return True

    def _jump_search(self, step: int) -> bool:
        if not self._ensure_search_matches():
            return False
        if self._current_search_index < 0:
            self._current_search_index = 0 if step > 0 else len(self._search_matches) - 1
        else:
            self._current_search_index = (self._current_search_index + step) % len(self._search_matches)
        start, end = self._search_matches[self._current_search_index]
        cursor = self.editor.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self._update_search_counter()
        return True

    def clear_search(self) -> None:
        self.find_input.clear()
        self.clear_search_results()
        self.editor.setFocus()

    def find_next(self) -> bool:
        return self._jump_search(1)

    def find_previous(self) -> bool:
        return self._jump_search(-1)

    def show_properties_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Properties — Marko Plus")
        dialog.setWindowIcon(self.windowIcon())
        dialog.setMinimumWidth(640)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(12)

        def add_group(title: str, rows) -> None:
            box = QGroupBox(title, dialog)
            form = QFormLayout(box)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            for label, value in rows:
                field = QLineEdit(str(value), box)
                field.setReadOnly(True)
                field.setCursorPosition(0)
                form.addRow(label, field)
            layout.addWidget(box)

        try:
            stat_result = self.module.path.stat()
            permissions = oct(stat_result.st_mode & 0o777)
            modified = str(self.module.modified)
            size = f"{stat_result.st_size:,} bytes"
        except OSError:
            permissions = modified = size = "Unavailable"

        add_group("File", (
            ("Name", self.module.filename),
            ("Location", str(self.module.path.parent)),
            ("Full path", str(self.module.path)),
            ("Size", size),
            ("Modified", modified),
            ("Permissions", permissions),
        ))
        add_group("Document", (
            ("Lines", f"{self.editor.blockCount():,}"),
            ("Characters", f"{max(0, self.editor.document().characterCount() - 1):,}"),
            ("Encoding", self.file_encoding),
            ("Newline", {"\n": "LF", "\r\n": "CRLF", "\r": "CR"}.get(self.file_newline, "LF")),
            ("Locked Mode", "On" if self.view_only else "Off"),
            ("Edit mode", "Overwrite" if self.editor.overwriteMode() else "Insert"),
        ))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, dialog)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def _decode_source(self, data: bytes) -> tuple[str, str, bytes]:
        """Decode a Markdown document with BOM and safe fallback handling."""
        bom_map = (
            (codecs.BOM_UTF32_LE, "utf-32-le"),
            (codecs.BOM_UTF32_BE, "utf-32-be"),
            (codecs.BOM_UTF8, "utf-8"),
            (codecs.BOM_UTF16_LE, "utf-16-le"),
            (codecs.BOM_UTF16_BE, "utf-16-be"),
        )
        for bom, encoding in bom_map:
            if data.startswith(bom):
                return data[len(bom):].decode(encoding, errors="strict"), encoding, bom

        try:
            return data.decode("utf-8", errors="strict"), "utf-8", b""
        except UnicodeDecodeError:
            system_encoding = locale.getpreferredencoding(False) or "utf-8"
            choices = [
                "Windows-1252",
                "ISO-8859-1",
                "UTF-16 LE",
                "UTF-16 BE",
                f"System encoding ({system_encoding})",
            ]
            selected, accepted = QInputDialog.getItem(
                self,
                "Choose Source Encoding",
                f"{self.module.filename} is not valid UTF-8 or a recognised text encoding.\n\nOpen using:",
                choices,
                0,
                False,
            )
            if not accepted:
                raise UnicodeDecodeError("utf-8", data, 0, min(1, len(data)), "opening cancelled")
            encoding = {
                "Windows-1252": "cp1252",
                "ISO-8859-1": "iso-8859-1",
                "UTF-16 LE": "utf-16-le",
                "UTF-16 BE": "utf-16-be",
                f"System encoding ({system_encoding})": system_encoding,
            }[selected]
            return data.decode(encoding, errors="strict"), encoding, b""

    @staticmethod
    def _looks_binary_text(text: str) -> bool:
        if "\x00" in text:
            return True
        if not text:
            return False
        controls = sum(
            1 for char in text
            if ord(char) < 32 and char not in "\t\n\r\f\b"
        )
        return controls / len(text) > 0.02

    @staticmethod
    def _detect_newline_style(content: str) -> str:
        crlf = content.count("\r\n")
        lf = content.count("\n") - crlf
        cr = content.count("\r") - crlf
        count, newline = max(((crlf, "\r\n"), (lf, "\n"), (cr, "\r")))
        return newline if count else "\n"

    def load_from_disk(self, *, show_errors: bool = True) -> bool:
        """Load one stable regular Markdown file with bounded decoding."""
        try:
            data, snapshot = read_regular_file(self.module.path, self.MAX_FILE_BYTES)
            text, encoding, bom = self._decode_source(data)
            if self._looks_binary_text(text):
                raise UnsupportedFileError("The file appears to contain binary control data.")
        except FileTooLargeError as error:
            if show_errors:
                QMessageBox.warning(self, "File Too Large", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except UnsupportedFileError as error:
            if show_errors:
                QMessageBox.warning(self, "Unsupported File", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except FileStateChangedError as error:
            if show_errors:
                QMessageBox.warning(self, "File Changed", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except UnicodeDecodeError as error:
            if show_errors:
                QMessageBox.warning(self, "Encoding Error", str(error))
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False
        except (OSError, MemoryError) as error:
            if show_errors:
                QMessageBox.critical(
                    self,
                    "Could Not Open File",
                    f"Could not read {self.module.filename}:\n\n{error}",
                )
            self.status_message.emit(f"Could not load {self.module.filename}: {error}")
            return False

        portable_text, legacy = strip_legacy_envelope(text)
        if legacy:
            QMessageBox.information(
                self,
                "Legacy Ricopad Markdown",
                "This file contains legacy Ricopad rich-format metadata. "
                "Marko Plus will edit only the portable Markdown content. "
                "Saving removes the Ricopad metadata.",
            )
        if len(portable_text) > self.editor.MAX_DOCUMENT_CHARACTERS:
            message = "The decoded document exceeds Marko Plus's editor safety limit."
            if show_errors:
                QMessageBox.warning(self, "File Too Large", message)
            self.status_message.emit(f"Could not load {self.module.filename}: {message}")
            return False
        newline = self._detect_newline_style(text)
        normalised = portable_text.replace("\r\n", "\n").replace("\r", "\n")
        self._ignore_document_signal = True
        try:
            self.editor.load_text(normalised)
            cursor = self.editor.textCursor()
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
            self.editor.verticalScrollBar().setValue(
                self.editor.verticalScrollBar().minimum()
            )
            self.editor.document().clearUndoRedoStacks()
            self.editor.mark_clean()
        finally:
            self._ignore_document_signal = False

        self.file_encoding = encoding
        self.file_bom = bom
        self.legacy_ricopad_loaded = legacy
        self.file_newline = newline
        self.file_disk_snapshot = snapshot
        self._loaded_mtime_ns = snapshot.state.mtime_ns
        self._set_backing_state("normal")
        self.module.loaded = True
        self.module.modified = snapshot.state.mtime_ns / 1_000_000_000
        self.module.size = snapshot.state.size
        self.repository.set_dirty(self.module.path, False)
        self._refresh_header()
        self._update_cursor_position()
        self.refresh_search()
        self.encoding_status_label.setText(self.file_encoding.upper())
        self.preview.set_document_path(str(self.module.path))
        self.schedule_preview()
        self.status_message.emit(f"Loaded {self.module.filename}")
        return True

    def _encoded_editor_payload(self) -> bytes | None:
        content = self.editor.toPlainText()
        if self.file_newline != "\n":
            content = content.replace("\n", self.file_newline)
        try:
            payload = self.file_bom + content.encode(
                self.file_encoding, errors="strict"
            )
        except UnicodeEncodeError as error:
            QMessageBox.critical(
                self,
                "Encoding Error",
                f"The edited text cannot be represented as {self.file_encoding}:\n\n{error}",
            )
            return None
        if len(payload) > self.MAX_FILE_BYTES:
            message = (
                f"The file exceeds Marko Plus's "
                f"{self.MAX_FILE_BYTES // (1024 * 1024)} MiB editor safety limit."
            )
            QMessageBox.warning(self, "Save Cancelled", message)
            self.status_message.emit(message)
            return None
        return payload

    def current_markdown_payload(self) -> bytes | None:
        """Return the live Markdown buffer using this document's encoding/newline contract."""
        return self._encoded_editor_payload()

    def save_copy_to(self, target: str | Path) -> bool:
        """Atomically write the live Markdown buffer to a distinct path."""
        destination = Path(target).expanduser().resolve(strict=False)
        payload = self._encoded_editor_payload()
        if payload is None:
            return False

        if destination.exists() or destination.is_symlink():
            response = QMessageBox.question(
                self,
                "Replace Markdown File? — Marko Plus",
                f"'{destination.name}' already exists. Replace it with the "
                "current document?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return False
            try:
                expected = current_file_state(destination)
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "Save As Cancelled",
                    f"Marko Plus could not verify the destination:\n\n{error}",
                )
                return False
        else:
            expected = None

        temporary: Path | None = None
        descriptor: int | None = None
        try:
            parent = destination.parent
            parent.mkdir(parents=False, exist_ok=True)
            if expected is not None and current_file_state(destination) != expected:
                raise FileStateChangedError(
                    "The destination changed before Marko Plus could save it."
                )
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{destination.name}.marko-plus-",
                suffix=".tmp",
                dir=parent,
            )
            temporary = Path(raw_path)
            if expected is not None and hasattr(os, "fchmod"):
                os.fchmod(descriptor, expected.target_mode & 0o7777)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if expected is None:
                install_new_file_from_temp(temporary, destination)
                temporary = None
            else:
                if current_file_state(destination) != expected:
                    raise FileStateChangedError(
                        "The destination changed again before replacement."
                    )
                os.replace(temporary, destination)
                temporary = None
            fsync_directory(parent)
        except FileStateChangedError as error:
            QMessageBox.warning(self, "Save As Cancelled", str(error))
            return False
        except OSError as error:
            QMessageBox.critical(self, "Save As Failed", str(error))
            return False
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except OSError:
                    pass

        self.status_message.emit(f"Saved as {destination.name}")
        return True

    def save_as_file(self, target: str | Path) -> bool:
        """Save to a new managed path and keep this live EditorPage."""
        destination = Path(target).expanduser().resolve(strict=False)
        old_path = self.module.path.resolve(strict=False)
        if destination == old_path:
            return self.save_to_disk()
        if not self.save_copy_to(destination):
            return False

        try:
            _payload, snapshot = read_regular_file(destination, self.MAX_FILE_BYTES)
        except OSError:
            self.file_disk_snapshot = None
            self._loaded_mtime_ns = None
        else:
            self.file_disk_snapshot = snapshot
            self._loaded_mtime_ns = snapshot.state.mtime_ns

        self._ignore_document_signal = True
        try:
            self.editor.mark_clean()
        finally:
            self._ignore_document_signal = False

        self.legacy_ricopad_loaded = False
        self._set_backing_state("normal")
        self.path_changed.emit(self, old_path, destination)
        self.preview.set_document_path(str(destination))
        self.schedule_preview()
        self._refresh_header()
        self.saved.emit(self.module)
        return True

    def save_to_disk(self) -> bool:
        """Safely save while preserving encoding, newline style and file mode."""
        expected = self.file_disk_snapshot
        if expected is not None:
            action = self._external_change_action()
            if action == "reload":
                self.load_from_disk(show_errors=True)
                return False
            if action == "save_version_as":
                return self._save_editor_version_as()
            if action == "handled_success":
                return True
            if action != "overwrite":
                return False

            # Explicit Overwrite is the only conflict decision allowed to replace
            # the changed disk copy. Refresh the expected snapshot at that point
            # so the existing Marko Plus atomic-save race guards still protect
            # against another change before replacement.
            try:
                _disk_data, expected = read_regular_file(
                    self.module.path, self.MAX_FILE_BYTES
                )
            except FileNotFoundError:
                expected = None
            except OSError as error:
                QMessageBox.warning(
                    self,
                    "File Check Failed",
                    f"Marko Plus could not verify the file before saving:\n\n{error}",
                )
                return False

        payload = self._encoded_editor_payload()
        if payload is None:
            return False

        temporary: Path | None = None
        descriptor: int | None = None
        try:
            if expected is None:
                if self.module.path.exists() or self.module.path.is_symlink():
                    raise FileStateChangedError(
                        "A file appeared at the save location. Saving was cancelled."
                    )
                write_path = self.module.path
                existing_mode = 0o666
            else:
                if current_file_state(self.module.path) != expected.state:
                    raise FileStateChangedError(
                        "The file changed again before Marko Plus could save it."
                    )
                write_path = (
                    validated_symlink_target(self.module.path, expected.state)
                    if expected.state.is_symlink
                    else self.module.path
                )
                existing_mode = expected.state.target_mode & 0o7777

            parent = write_path.parent
            descriptor, raw_path = tempfile.mkstemp(
                prefix=f".{write_path.name}.marko-plus-",
                suffix=".tmp",
                dir=parent,
            )
            temporary = Path(raw_path)
            if hasattr(os, "fchmod"):
                os.fchmod(descriptor, existing_mode)
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())

            if expected is None:
                install_new_file_from_temp(temporary, write_path)
                temporary = None
            else:
                if current_file_state(self.module.path) != expected.state:
                    raise FileStateChangedError(
                        "The file changed again before Marko Plus could replace it."
                    )
                if expected.state.is_symlink and validated_symlink_target(
                    self.module.path, expected.state
                ) != write_path:
                    raise FileStateChangedError(
                        "The symbolic-link target changed before replacement."
                    )
                os.replace(temporary, write_path)
                temporary = None
            fsync_directory(parent)
        except FileStateChangedError as error:
            QMessageBox.warning(self, "Save Cancelled", str(error))
            return False
        except OSError as error:
            QMessageBox.critical(self, "Save Failed", str(error))
            self.status_message.emit(f"Could not save {self.module.filename}: {error}")
            return False
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    temporary.unlink()
                except OSError:
                    pass

        try:
            snapshot = snapshot_from_payload(self.module.path, payload)
            stat_result = self.module.path.stat()
            self.file_disk_snapshot = snapshot
            self._loaded_mtime_ns = snapshot.state.mtime_ns
            self.module.modified = stat_result.st_mtime
            self.module.size = stat_result.st_size
        except OSError:
            self.file_disk_snapshot = None
            self._loaded_mtime_ns = None

        self._ignore_document_signal = True
        try:
            self.editor.mark_clean()
        finally:
            self._ignore_document_signal = False

        self.legacy_ricopad_loaded = False
        self._set_backing_state("normal")
        self.repository.set_dirty(self.module.path, False)
        self.repository.module_changed.emit(self.module)
        self._refresh_header()
        self.saved.emit(self.module)
        self.status_message.emit(f"Saved {self.module.filename}")
        return True

    def confirm_reload(self) -> None:
        if self.editor.is_modified:
            response = QMessageBox.question(
                self,
                "Discard Changes",
                "Discard all unsaved changes and reload this file from disk?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
        self.load_from_disk()

    def replace_current(self) -> bool:
        if self.view_only:
            self.show_view_only_edit_prompt()
            return False
        query = self.find_input.text()[: self.MAX_SEARCH_QUERY_CHARACTERS]
        if not query:
            self.find_input.setFocus()
            return False
        cursor = self.editor.textCursor()
        if not self._selection_matches_replace_query(cursor, query):
            if not self.find_next():
                return False
            cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            return False
        replacement = self.replace_input.text()
        document_length = max(0, self.editor.document().characterCount() - 1)
        selected_length = abs(cursor.selectionEnd() - cursor.selectionStart())
        if document_length - selected_length + len(replacement) > self.editor.MAX_DOCUMENT_CHARACTERS:
            self.status_message.emit("The replacement would exceed Marko Plus's document safety limit.")
            return False
        cursor.insertText(replacement)
        self.editor.setTextCursor(cursor)
        self.refresh_search()
        return True

    def replace_all(self) -> int:
        if self.view_only:
            self.show_view_only_edit_prompt()
            return 0
        query = self.find_input.text()[: self.MAX_SEARCH_QUERY_CHARACTERS]
        if not query:
            self.find_input.setFocus()
            return 0
        replacement = self.replace_input.text()
        document = self.editor.document()
        flags = self._replace_flags()

        scan = QTextCursor(document)
        count = 0
        while count <= self.MAX_SEARCH_MATCHES:
            match = document.find(query, scan, flags)
            if match.isNull():
                break
            count += 1
            scan = QTextCursor(match)
            scan.setPosition(match.selectionEnd())
        if count > self.MAX_SEARCH_MATCHES:
            self.status_message.emit(f"Replace All is limited to {self.MAX_SEARCH_MATCHES:,} matches.")
            return 0
        if not count:
            self.refresh_search()
            return 0
        current_length = max(0, document.characterCount() - 1)
        resulting_length = current_length + count * (len(replacement) - len(query))
        if resulting_length > self.editor.MAX_DOCUMENT_CHARACTERS:
            self.status_message.emit("Replace All would exceed Marko Plus's document safety limit.")
            return 0

        scan = QTextCursor(document)
        edit_cursor = QTextCursor(document)
        replaced = 0
        self._search_refresh_suspended = True
        edit_cursor.beginEditBlock()
        try:
            while replaced < count:
                match = document.find(query, scan, flags)
                if match.isNull():
                    break
                match.insertText(replacement)
                scan = QTextCursor(match)
                replaced += 1
        finally:
            edit_cursor.endEditBlock()
            self._search_refresh_suspended = False
        self.status_message.emit(f"Replaced {replaced} occurrence(s).")
        self.refresh_search()
        return replaced

    def show_go_to_line(self) -> None:
        line, accepted = QInputDialog.getInt(
            self,
            "Go to Line",
            f"Line number (1–{self.editor.blockCount()}):",
            self.editor.textCursor().blockNumber() + 1,
            1,
            max(1, self.editor.blockCount()),
        )
        if accepted:
            self.editor.go_to_line(line)

    @property
    def is_modified(self) -> bool:
        return bool(self.editor.is_modified)

    @property
    def backing_state(self) -> str:
        return self._backing_state

    def can_close(self) -> bool:
        """Ask whether an unsaved or backing-at-risk page may be closed."""
        if self._backing_state == "missing":
            return self._confirm_close_missing_backing()
        if not self.editor.is_modified:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Unsaved Changes")
        box.setText(f"Save changes to {self.module.filename}?")
        save = box.addButton("Save", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked is save:
            return self.save_to_disk()
        if clicked is discard:
            return True
        # Cancel, closing the dialog via its title-bar button, or any unknown
        # result must preserve the unsaved editor.
        return False

    def _confirm_close_missing_backing(self) -> bool:
        """Protect a clean or dirty live copy whose original pathname vanished."""
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("Backing File Missing")
        dialog.setText(
            f"{self.module.filename} is no longer available at its original path."
        )
        dialog.setInformativeText(
            "This open editor may be the only remaining copy. Save Version As "
            "preserves it at a new path. Recreate Original enters the protected "
            "Save flow, where Overwrite is still an explicit confirmation."
        )
        save_version = dialog.addButton(
            "Save Version As…", QMessageBox.ButtonRole.AcceptRole
        )
        recreate = dialog.addButton(
            "Recreate Original…", QMessageBox.ButtonRole.ActionRole
        )
        close_without = dialog.addButton(
            "Close Without Saving", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel = dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(save_version)
        dialog.setEscapeButton(cancel)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is save_version:
            return self._save_editor_version_as()
        if clicked is recreate:
            return self.save_to_disk()
        if clicked is close_without:
            return True
        return False

    def _on_modification_changed(self, modified: bool) -> None:
        if self._ignore_document_signal:
            return
        self.repository.set_dirty(self.module.path, modified)
        self._refresh_header()

    def _on_module_path_changed(self, changed: Module, _old_path: Path) -> None:
        if changed is not self.module:
            return
        self._refresh_header()
        self.preview.set_document_path(str(self.module.path))
        self.schedule_preview()
        try:
            current_state = current_file_state(self.module.path)
            self._loaded_mtime_ns = current_state.mtime_ns
            if self.file_disk_snapshot is not None:
                self.file_disk_snapshot = FileSnapshot(
                    state=current_state,
                    digest=self.file_disk_snapshot.digest,
                )
        except OSError:
            self._loaded_mtime_ns = None

    def _set_backing_state(self, state: str) -> None:
        """Update the persistent live-document backing-path state."""
        if state not in {"normal", "changed", "missing"}:
            raise ValueError(f"Unknown backing state: {state}")
        self._backing_state = state
        self._external_change_pending = state != "normal"
        if state == "normal":
            self.reload_external_button.setEnabled(True)
            self.external_label.setText("This file changed on disk after it was opened.")
            self.external_banner.hide()
            return
        if state == "missing":
            self.external_label.setText(
                "This file is no longer available at its original disk path. "
                "Save Version As preserves the live document; Reload is unavailable."
            )
            self.reload_external_button.setEnabled(False)
        else:
            self.external_label.setText("This file changed on disk after it was opened.")
            self.reload_external_button.setEnabled(True)
        self.external_banner.show()
        self._refresh_header()

    def handle_backing_path_event(self) -> None:
        """Resolve a targeted monitor event using the exact Markdown byte snapshot."""
        loaded = self.file_disk_snapshot
        if loaded is None:
            return
        current = self._current_disk_snapshot()
        if current is None:
            self._set_backing_state("missing")
        elif current.digest == loaded.digest:
            self._loaded_mtime_ns = current.state.mtime_ns
            self.file_disk_snapshot = current
            self._set_backing_state("normal")
        else:
            self._set_backing_state("changed")

    def _current_disk_snapshot(self) -> FileSnapshot | None:
        """Return the exact-byte snapshot for the managed disk copy."""
        try:
            _payload, snapshot = read_regular_file(
                self.module.path, self.MAX_FILE_BYTES
            )
        except OSError:
            return None
        return snapshot

    def _has_external_change(self) -> bool:
        loaded = self.file_disk_snapshot
        if loaded is None:
            return False
        current = self._current_disk_snapshot()
        return current is None or current.digest != loaded.digest

    def _external_change_action(self) -> str:
        """Own the managed Plus conflict decision for every Save route."""
        if not self._has_external_change():
            self._set_backing_state("normal")
            return "overwrite"

        current_snapshot = self._current_disk_snapshot()
        self._set_backing_state(
            "missing" if current_snapshot is None else "changed"
        )

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle("File Changed on Disk")
        if current_snapshot is None:
            dialog.setText(
                "This file is no longer available at its original disk path."
            )
            dialog.setInformativeText(
                "Save Version As preserves the current Marko Plus document at a "
                "new path. Overwrite explicitly recreates the original path. "
                "Reload is unavailable until a disk copy exists again."
            )
        else:
            dialog.setText(
                "This file has changed on disk since Marko Plus opened or saved it."
            )
            dialog.setInformativeText(
                "Choose Reload to discard the current Marko Plus edits and use the "
                "disk copy, Save Version As to preserve both versions, or Overwrite "
                "to explicitly replace the changed disk copy with the current document."
            )
        reload_button = dialog.addButton("Reload", QMessageBox.ButtonRole.ActionRole)
        reload_button.setEnabled(current_snapshot is not None)
        save_version_button = dialog.addButton(
            "Save Version As…", QMessageBox.ButtonRole.ActionRole
        )
        overwrite_button = dialog.addButton(
            "Overwrite", QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked is reload_button:
            self._reload_external_change()
            return "cancel"
        if clicked is save_version_button:
            return "handled_success" if self._save_editor_version_as() else "cancel"
        if clicked is overwrite_button:
            return "overwrite"
        return "cancel"

    def _on_repository_module_changed(self, changed: Module) -> None:
        """Surface watcher-detected external changes for this open document.

        Scanner metadata is only the notification trigger. The decision is made
        from the exact file digest, so timestamp-only touches do not produce a
        false warning.
        """
        if changed is not self.module and changed.path != self.module.path:
            return

        self.handle_backing_path_event()

    def _reload_external_change(self) -> None:
        if self.editor.is_modified:
            response = QMessageBox.question(
                self,
                "Discard Editor Changes",
                "Reloading will discard your unsaved editor changes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if response != QMessageBox.StandardButton.Yes:
                return
        self.load_from_disk()

    def _save_editor_version_as(self) -> bool:
        """Preserve the Marko editor version without touching the changed disk copy."""
        handler = getattr(self.window(), "_save_external_change_version_as", None)
        if not callable(handler):
            return False
        return bool(handler(self))

    def set_header_visible(self, visible: bool) -> None:
        self._header_visible = bool(visible)
        self.title_label.setVisible(self._header_visible)

    def _refresh_header(self) -> None:
        dirty = " [Unsaved]" if self.module.dirty else ""
        display_name = escape(self.module.display_name)
        path_text = escape(str(self.module.path))
        self.title_label.setText(
            f"<h2>{display_name}{dirty}</h2>"
            f"{path_text}"
        )
