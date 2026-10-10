# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Main application window for Marko Plus."""

from __future__ import annotations

import json
import os
import sys
import time
import subprocess
import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QEvent, QTimer, Qt, QUrl
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QIcon,
    QKeySequence,
    QTextCursor,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QSpinBox,
    QTabBar,
    QWizard,
    QWizardPage,
    QVBoxLayout,
    QWidget,
)

from marko_plus import APP_NAME
from marko_plus.app_constants import (
    GITHUB_URL,
    ISSUES_URL,
    MARKDOWN_EXTENSIONS,
)
from marko_plus.controllers.editor_manager import EditorManager
from marko_plus.controllers.file_actions import FileActionsController
from marko_plus.models.module import Module
from marko_plus.models.module_repository import ModuleRepository
from marko_plus.models.module_state_store import ModuleStateStore
from marko_plus.services.config_service import ConfigService
from marko_plus.services.filesystem_watcher import FilesystemWatcher
from marko_plus.services.desktop_launcher import DesktopLauncher
from marko_plus.services.project_registry import ProjectRegistry
from marko_plus.services.runtime_paths import RuntimePaths
from marko_plus.widgets.about_dialog import AboutDialog
from marko_plus.widgets.closing_dialog import ClosingDialog
from marko_plus.widgets.editor_page import EditorPage
from marko_plus.widgets.navigation import (
    NavigationWidget,
    SIDEBAR_MINIMUM_WIDTH,
)
from marko_plus.widgets.projects_dialog import ProjectsDialog
from marko_plus.widgets.shortcuts_dialog import ShortcutsDialog
from marko_plus.widgets.shell_ribbon import ShellRibbon
from marko_plus.widgets.markopad_theme import apply_theme, effective_scheme


SHUTDOWN_PROFILE_ENV = "MARKO_PLUS_PROFILE_SHUTDOWN"


class MainWindow(QMainWindow):
    """Assembles the repository, services, controllers, and persistent views."""

    def __init__(
        self,
        library_root: str | Path,
        config: ConfigService,
        project_registry: ProjectRegistry,
        runtime_paths: RuntimePaths,
        parent=None,
        *,
        icon_path: str | Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.library_root = Path(library_root).expanduser().resolve(strict=False)
        self.config = config
        self.project_registry = project_registry
        self.runtime_paths = runtime_paths

        self.package_root = Path(__file__).resolve().parent.parent
        self.project_root = self.package_root.parent
        self.icon_path = (
            Path(icon_path)
            if icon_path is not None
            else self.package_root / "assets" / "icons" / "markopad.png"
        )
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))

        self.repository = ModuleRepository(self)
        self.states = ModuleStateStore(self.repository, self)
        self.watcher = FilesystemWatcher(self.library_root, self.repository, parent=self)
        self.desktop_launcher = DesktopLauncher(self.runtime_paths, self)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.navigation = NavigationWidget(self.library_root, self.repository, self.states, self.splitter)

        # Tabs are a thin presentation layer over the existing EditorManager/stack.
        # Open Markdown documents receive persistent tabs. Dashboard/folder navigation
        # surfaces use one temporary tab while consulted, then disappear as soon
        # as a document becomes active.
        self.content_host = QWidget(self.splitter)
        self.content_host.setMinimumWidth(0)
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.document_tabs = QTabBar(self.content_host)
        self.document_tabs.setDocumentMode(True)
        self.document_tabs.setMinimumWidth(0)
        self.document_tabs.setTabsClosable(True)
        self.document_tabs.setMovable(False)
        self.document_tabs.setExpanding(False)
        self.document_tabs.setUsesScrollButtons(True)
        self.document_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.document_tabs.setVisible(False)
        self.stack = QStackedWidget(self.content_host)
        self.stack.setMinimumWidth(0)
        self.content_layout.addWidget(self.document_tabs)
        self.content_layout.addWidget(self.stack, 1)

        self.splitter.addWidget(self.navigation)
        self.splitter.addWidget(self.content_host)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        # Easier grab target without changing either pane's contents.
        self.splitter.setHandleWidth(8)
        # Keep the validated rubber-band resize path for large Grid views:
        # one layout pass on release rather than continuous reflow.
        self.splitter.setOpaqueResize(False)

        # Markopad command surface above the Marko Plus workspace splitter.
        self.central_host = QWidget(self)
        self.central_layout = QVBoxLayout(self.central_host)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)
        self.tabbed_container = QWidget(self.central_host)
        self.tabbed_layout = QVBoxLayout(self.tabbed_container)
        self.tabbed_layout.setContentsMargins(0, 0, 0, 0)
        self.tabbed_layout.setSpacing(0)
        self.central_layout.addWidget(self.tabbed_container)
        self.central_layout.addWidget(self.splitter, 1)
        self.setCentralWidget(self.central_host)

        self.editor_manager = EditorManager(
            self.library_root, self.repository, self.states, self.stack, self.config, self
        )
        self.file_actions = FileActionsController(
            self.library_root,
            self.repository,
            self.states,
            self.editor_manager,
            self.desktop_launcher,
            watcher=self.watcher,
            parent_widget=self,
            parent=self,
        )

        self.desktop_launcher.status_message.connect(self.show_status)
        self.desktop_launcher.launch_error.connect(self._show_launch_error)

        self._closing = False
        self.about_dialog: AboutDialog | None = None
        self.shortcuts_dialog: ShortcutsDialog | None = None
        self.quick_tour_dialog: QWizard | None = None
        # Temporary F10 viewing mode. The user's independent visibility choices
        # are captured and restored; Focused Mode does not rewrite them.
        self._collapsed_mode_restore: dict[str, object] | None = None
        # Browser-style context history for the dedicated mouse Back button.
        # Navigation signals are coalesced so Tabs Disabled document switches do
        # not expose the EditorManager's internal Dashboard close surface.
        self._navigation_history: list[str] = []
        self._navigation_current = "dashboard"
        self._navigation_pending: str | None = None
        self._navigation_record_scheduled = False
        self._navigation_back_in_progress = False
        self._status_label = QLabel("Ready.")
        self._repair_navigation_after_scan = False
        self._pending_open_path: Path | None = None
        self._pending_new_file_view_mode: str | None = None
        self._startup_scan_pending = True
        self._startup_open_requested = False
        status = QStatusBar(self)
        status.addWidget(self._status_label, 1)
        self.setStatusBar(status)

        self._build_menu_bar()
        self._create_tabbed_toolbar()
        self._connect_signals()
        self._sync_tabs_mode_ui()
        self._restore_window_state()
        self.watcher.start(initial_scan=True)
        self._update_action_states()
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def _add_action(self, menu, text, slot, shortcut=None, *, checkable=False):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.setCheckable(checkable)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _command(self, text, slot=None, shortcut=None, *, checkable=False) -> QAction:
        action = QAction(text, self)
        if slot is not None:
            action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut) if isinstance(shortcut, str) else shortcut)
        action.setCheckable(checkable)
        label = text.replace("&", "").replace("…", "...").strip()
        shortcut_text = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        action.setToolTip(f"{label} — {shortcut_text}" if shortcut_text else label)
        return action

    def _build_menu_bar(self) -> None:
        # Markopad's command language, adapted only where the workspace
        # genuinely has a different file/workspace operation.
        self.new_action = self._command("New File…", self._new_markdown_file, QKeySequence.StandardKey.New)
        self.new_window_action = self._command("New Window…", self._new_window, "Ctrl+Alt+Shift+N")
        self.new_folder_action = self._command("New Folder…", self._new_folder, "Ctrl+Shift+N")
        self.manage_workspaces_action = self._command("Open / Manage Workspaces...", self._show_projects, "Ctrl+O")
        self.import_file_action = self._command("Import File into Workspace...", self._import_file_into_workspace, "Ctrl+Alt+Shift+I")
        self.open_external_file_action = self._command("Open External File...", self._open_external_file, "Ctrl+Alt+Shift+O")
        self.refresh_workspace_action = self._command("Refresh Workspace", self._refresh_workspace, "Ctrl+Shift+F5")
        self.save_action = self._command("Save", self._save_current, QKeySequence.StandardKey.Save)
        self.save_as_action = self._command("Save As…", self._save_current_as)
        self.save_new_action = self._command("Save and New", self._save_and_new, "Ctrl+Shift+S")
        self.save_dashboard_action = self._command("Save and Dashboard", self._save_and_dashboard, "Ctrl+Shift+W")
        self.save_exit_action = self._command("Save and Exit", self._save_and_exit, "Ctrl+Shift+Q")
        self.duplicate_action = self._command("Duplicate File…", self._duplicate_current, "Ctrl+Shift+D")
        self.rename_file_action = self._command("Rename File…", self._rename_current, "F2")
        self.delete_file_action = self._command("Delete File", self._delete_current_file)
        self.open_document_folder_action = self._command("Open Containing Folder", self._open_current_document_folder, "Ctrl+Shift+O")
        self.external_editor_action = self._command("Open in External Editor", self._open_current_external, "Ctrl+Shift+E")
        self.properties_action = self._command("Properties", self._show_properties, "F4")
        self.print_action = self._command("Print…", self._print_current, QKeySequence.StandardKey.Print)
        self.export_pdf_action = self._command("Export PDF…", self._export_pdf_current, "Ctrl+Shift+P")
        self.exit_action = self._command("Exit", self.close, QKeySequence.StandardKey.Quit)

        self.undo_action = self._command("Undo", self._undo, QKeySequence.StandardKey.Undo)
        self.redo_action = self._command("Redo", self._redo, "Ctrl+Y")
        self.cut_action = self._command("Cut", self._cut, QKeySequence.StandardKey.Cut)
        self.copy_action = self._command("Copy", self._copy, QKeySequence.StandardKey.Copy)
        self.paste_action = self._command("Paste", self._paste, QKeySequence.StandardKey.Paste)
        self.paste_plain_action = self._command("Paste as Plain Text", self._paste_plain_text, "Ctrl+Shift+V")
        self.delete_text_action = self._command("Delete", self._delete_text, "Delete")
        self.duplicate_line_action = self._command("Duplicate Line / Selection", self._duplicate_line, "Ctrl+D")
        self.delete_line_action = self._command("Delete Line", self._delete_line, "Ctrl+Shift+K")
        self.select_all_action = self._command("Select All", self._select_all, QKeySequence.StandardKey.SelectAll)
        self.comment_action = self._command("Toggle Comment", self._toggle_comment, "Ctrl+/")
        self.find_action = self._command("Find", self._focus_find, QKeySequence.StandardKey.Find)
        self.replace_action = self._command("Find and Replace", self._focus_replace, "Ctrl+H")
        self.goto_action = self._command("Go To Line...", self._go_to_line, "Ctrl+G")

        self.bold_action = self._command("Bold", lambda: self._editor_call("toggle_bold"), "Ctrl+B")
        self.italic_action = self._command("Italic", lambda: self._editor_call("toggle_italic"), "Ctrl+I")
        self.strike_action = self._command("Strikethrough", lambda: self._editor_call("toggle_strikethrough"), "Ctrl+Shift+X")
        self.quote_action = self._command("Quote Block\t>", lambda: self._editor_call("toggle_blockquote"))
        self.bullet_action = self._command("Bullet List", lambda: self._editor_call("toggle_bullet_list"), "Ctrl+L")
        self.number_action = self._command("Numbered List", lambda: self._editor_call("toggle_numbered_list"), "Ctrl+Shift+L")
        self.task_action = self._command("Task List", lambda: self._editor_call("toggle_task_list"))
        self.indent_action = self._command("Indent", lambda: self._editor_call("indent_selection_or_insert_spaces"), "Ctrl+]")
        self.outdent_action = self._command("Outdent", lambda: self._editor_call("unindent_selection_or_line"), "Ctrl+[")
        self.inline_code_action = self._command("Inline Code", lambda: self._editor_call("toggle_inline_code"), "Ctrl+`")
        self.code_fence_action = self._command("Code Block\t```", self._insert_code_block)
        self.heading_actions = []
        for level in range(0, 7):
            label = "Normal Paragraph" if level == 0 else f"Heading {level}"
            self.heading_actions.append(self._command(label, lambda _checked=False, n=level: self._editor_call("apply_heading", n), f"Ctrl+Shift+{level}"))
        self.heading_tabbed_action = QAction("Heading", self)
        heading_menu = QMenu(self)
        for action in self.heading_actions: heading_menu.addAction(action)
        self.heading_tabbed_action.setMenu(heading_menu)

        self.code_tabbed_action = QAction("Code", self)
        code_menu = QMenu(self)
        code_menu.addAction(self.inline_code_action)
        code_menu.addAction(self.code_fence_action)
        self.code_tabbed_action.setMenu(code_menu)

        self.link_action = self._command("Insert Link…", self._insert_link, "Ctrl+K")
        self.edit_link_action = self._command("Edit Link…", self._edit_link)
        self.remove_link_action = self._command("Remove Link", self._remove_link)
        self.rule_action = self._command("Horizontal Rule", lambda: self._editor_call("insert_horizontal_rule"), "Ctrl+Shift+H")
        self.image_action = self._command("Image Reference…", self._insert_image, "Ctrl+Shift+I")
        self.table_action = self._command("Table…", self._insert_table, "Ctrl+Shift+T")
        self.date_time_action = self._command("Date and Time", lambda: self._insert_text(datetime.now().strftime("%Y-%m-%d %H:%M")), "F5")
        self.date_action = self._command("Date Only", lambda: self._insert_text(datetime.now().strftime("%Y-%m-%d")), "Ctrl+;")
        self.time_action = self._command("Time Only", lambda: self._insert_text(datetime.now().strftime("%H:%M")), "Ctrl+:")
        self.symbol_action = self._command("Symbol…", self._insert_symbol, "Shift+F5")
        self.link_tabbed_action = QAction("Link", self)
        link_tabbed_menu = QMenu(self)
        link_tabbed_menu.addAction(self.link_action)
        link_tabbed_menu.addAction(self.edit_link_action)
        link_tabbed_menu.addSeparator()
        link_tabbed_menu.addAction(self.remove_link_action)
        self.link_tabbed_action.setMenu(link_tabbed_menu)

        self.source_only_action = self._command("Source Only", lambda: self._set_document_view("source"), "Ctrl+1", checkable=True)
        self.split_action = self._command("Source + Preview", lambda: self._set_document_view("split"), "Ctrl+2", checkable=True)
        self.preview_only_action = self._command("Preview Only", lambda: self._set_document_view("preview"), "Ctrl+3", checkable=True)
        view_group = QActionGroup(self); view_group.setExclusive(True)
        for action in (self.source_only_action, self.split_action, self.preview_only_action): view_group.addAction(action)
        self.view_only_action = self._command("Locked Mode", self._toggle_lock_editor_current, "F12", checkable=True)
        self.word_wrap_action = self._command("Word Wrap", self._toggle_word_wrap, "Ctrl+Alt+Shift+W", checkable=True)
        self.line_numbers_action = self._command("Line Numbers", self._toggle_line_numbers, "Ctrl+Alt+Shift+L", checkable=True)
        canvas_light = self.config.get("editor_canvas_light", True)
        if not isinstance(canvas_light, bool):
            canvas_light = True
        self.editor_canvas_theme_action = self._command(
            "Dark Editor", self._toggle_editor_canvas_light,
            "Ctrl+Alt+Shift+E", checkable=True,
        )
        self.editor_canvas_theme_action.setChecked(not canvas_light)
        self.status_bar_action = self._command(
            "Show Status", self._toggle_status_bar,
            "Ctrl+Alt+Shift+S", checkable=True,
        )
        self.status_bar_action.setChecked(bool(self.config.get("show_status_bar", True)))
        self.statusBar().setVisible(self.status_bar_action.isChecked())
        self.file_header_action = self._command("File Header", self._toggle_file_header, "Ctrl+Alt+Shift+F", checkable=True)
        self.file_header_action.setChecked(bool(self.config.get("show_file_header", True)))
        self.collapsed_mode_action = self._command("Focused Mode", self._toggle_collapsed_mode, "F10", checkable=True)
        self.zoom_in_action = self._command("Zoom In", lambda: self._zoom_current(1), QKeySequence.StandardKey.ZoomIn)
        self.zoom_out_action = self._command("Zoom Out", lambda: self._zoom_current(-1), QKeySequence.StandardKey.ZoomOut)
        self.zoom_reset_action = self._command("Reset Zoom", self._zoom_reset, "Ctrl+0")
        self.display_font_action = self._command("Source Font…", self._choose_display_font, "Ctrl+Shift+[")
        self.preview_font_action = self._command("Preview Font…", self._choose_preview_font, "Ctrl+Shift+]")
        self.tab_width_action = self._command("Tab Width…", self._choose_tab_width)

        self.dashboard_action = self._command("Dashboard", self.editor_manager.show_dashboard)
        # Context-sensitive tab/navigation shortcuts are window-owned rather
        # than attached to the Dashboard or Markdown actions.
        self.close_context_action = self._command(
            "Close Tab / Dashboard", self._close_context, "Ctrl+W"
        )
        self.open_context_tab_action = self._command(
            "Open Context Tab", self._open_context_tab, "Ctrl+T"
        )
        self.addAction(self.close_context_action)
        self.addAction(self.open_context_tab_action)
        self.list_action = self._command("List View", lambda: self.editor_manager.set_view_mode("list"), checkable=True)
        self.grid_action = self._command("Grid View", lambda: self.editor_manager.set_view_mode("grid"), checkable=True)
        self.list_action.setToolTip("Dashboard — List View")
        self.grid_action.setToolTip("Dashboard — Grid View")
        self.toggle_dashboard_view_action = self._command(
            "Toggle List/Grid View", self._toggle_dashboard_view,
            "Ctrl+Alt+Shift+V",
        )
        dashboard_view_group = QActionGroup(self); dashboard_view_group.setExclusive(True)
        dashboard_view_group.addAction(self.list_action); dashboard_view_group.addAction(self.grid_action)
        self.sidebar_action = self._command("Show Sidebar", self._toggle_sidebar, "F9", checkable=True); self.sidebar_action.setChecked(True)
        sidebar_position = str(self.config.get("sidebar_position", "left"))
        if sidebar_position not in {"left", "right"}:
            sidebar_position = "left"
        self.sidebar_position_actions: dict[str, QAction] = {}
        sidebar_position_group = QActionGroup(self)
        sidebar_position_group.setExclusive(True)
        for value, label in (("left", "Dock to Left"), ("right", "Dock to Right")):
            action = self._command(
                label,
                lambda _checked=False, selected=value: self._set_sidebar_position(selected),
                checkable=True,
            )
            action.setChecked(value == sidebar_position)
            sidebar_position_group.addAction(action)
            self.sidebar_position_actions[value] = action
        self.left_sidebar_action = self.sidebar_position_actions["left"]
        self.right_sidebar_action = self.sidebar_position_actions["right"]
        self.left_sidebar_action.setToolTip("Sidebar — Dock to Left")
        self.right_sidebar_action.setToolTip("Sidebar — Dock to Right")
        self.toggle_sidebar_position_action = self._command(
            "Toggle Sidebar Position", self._toggle_sidebar_position, "Shift+F9"
        )
        self.addAction(self.toggle_sidebar_position_action)
        self.fullscreen_action = self._command("Full Screen", self._toggle_fullscreen, "F11", checkable=True)
        self.theme_system_action = self._command("System", lambda: self._set_theme("system"), checkable=True)
        self.theme_dark_action = self._command("Dark", lambda: self._set_theme("dark"), checkable=True)
        self.theme_light_action = self._command("Light", lambda: self._set_theme("light"), checkable=True)
        self.theme_light_action.setToolTip("Theme — Light")
        self.theme_dark_action.setToolTip("Theme — Dark")
        self.theme_system_action.setToolTip("Theme — System")
        theme_group = QActionGroup(self); theme_group.setExclusive(True)
        for action in (self.theme_light_action, self.theme_dark_action, self.theme_system_action): theme_group.addAction(action)
        current_theme = str(self.config.get("app_theme", "light"))
        {"system": self.theme_system_action, "dark": self.theme_dark_action, "light": self.theme_light_action}.get(current_theme, self.theme_system_action).setChecked(True)

        self.app_launch_screen = str(
            self.config.get("app_launch_screen", "dashboard")
        )
        if self.app_launch_screen not in {"dashboard", "last_file"}:
            self.app_launch_screen = "dashboard"
        self.launch_dashboard_action = self._command(
            "Dashboard",
            lambda: self._set_app_launch_screen("dashboard"),
            checkable=True,
        )
        self.launch_last_file_action = self._command(
            "Last File",
            lambda: self._set_app_launch_screen("last_file"),
            checkable=True,
        )
        launch_screen_group = QActionGroup(self)
        launch_screen_group.setExclusive(True)
        launch_screen_group.addAction(self.launch_dashboard_action)
        launch_screen_group.addAction(self.launch_last_file_action)
        self.launch_dashboard_action.setChecked(
            self.app_launch_screen == "dashboard"
        )
        self.launch_last_file_action.setChecked(
            self.app_launch_screen == "last_file"
        )
        self.launch_dashboard_action.setToolTip("Launch Screen — Dashboard")
        self.launch_last_file_action.setToolTip("Launch Screen — Last File")

        tabs_enabled = bool(self.config.get("tabs_enabled", True))
        self.tabs_actions: dict[str, QAction] = {}
        tabs_group = QActionGroup(self)
        tabs_group.setExclusive(True)
        for value, label in (
            (True, "Tabs Enabled"),
            (False, "Tabs Disabled"),
        ):
            action = self._command(
                label,
                lambda _checked=False, enabled=value: self._set_tabs_enabled(enabled),
                (None if value else "Ctrl+Alt+Shift+T"),
                checkable=True,
            )
            action.setChecked(value == tabs_enabled)
            tabs_group.addAction(action)
            self.tabs_actions["enabled" if value else "disabled"] = action
        self.tabs_enabled_action = self.tabs_actions["enabled"]
        self.tabs_disabled_action = self.tabs_actions["disabled"]
        self.tabs_enabled_action.setToolTip("File Launch — Tabs Enabled")
        self.tabs_disabled_action.setToolTip("File Launch — Tabs Disabled")
        self.app_tabs_toggle_action = self._command(
            "Tabs Enabled / Disabled", self._toggle_tabs_mode
        )

        duplicate_policy = str(self.config.get("dirty_duplicate_action", "ask")).lower()
        if duplicate_policy not in {"ask", "current", "saved"}:
            duplicate_policy = "ask"
        self.dirty_duplicate_actions: dict[str, QAction] = {}
        dirty_duplicate_group = QActionGroup(self)
        dirty_duplicate_group.setExclusive(True)
        for value, label in (
            ("ask", "Ask Every Time"),
            ("current", "Duplicate Current Document"),
            ("saved", "Duplicate Last Saved Version"),
        ):
            action = self._command(
                label,
                lambda _checked=False, selected=value:
                    self._set_dirty_duplicate_action(selected),
                checkable=True,
            )
            action.setChecked(value == duplicate_policy)
            dirty_duplicate_group.addAction(action)
            self.dirty_duplicate_actions[value] = action

        external_policy = str(self.config.get("dirty_external_action", "ask")).lower()
        if external_policy not in {"ask", "save", "saved"}:
            external_policy = "ask"
        self.dirty_external_actions: dict[str, QAction] = {}
        dirty_external_group = QActionGroup(self)
        dirty_external_group.setExclusive(True)
        for value, label in (
            ("ask", "Ask Every Time"),
            ("save", "Save Changes and Open"),
            ("saved", "Open Last Saved Version"),
        ):
            action = self._command(
                label,
                lambda _checked=False, selected=value:
                    self._set_dirty_external_action(selected),
                checkable=True,
            )
            action.setChecked(value == external_policy)
            dirty_external_group.addAction(action)
            self.dirty_external_actions[value] = action

        self.next_document_tab_action = self._command("Next Tab", lambda: self._cycle_context_tab(1), "Ctrl+Tab")
        self.previous_document_tab_action = self._command("Previous Tab", lambda: self._cycle_context_tab(-1), "Ctrl+Shift+Tab")
        self.previous_file_action = self._command("Previous File", lambda: self.navigation.navigate_adjacent_module(-1), "Ctrl+Up")
        self.next_file_action = self._command("Next File", lambda: self.navigation.navigate_adjacent_module(1), "Ctrl+Down")
        for action in (self.next_document_tab_action, self.previous_document_tab_action, self.previous_file_action, self.next_file_action, self.toggle_dashboard_view_action):
            self.addAction(action)

        self.docs_action = self._command("Documentation", self._open_documentation, QKeySequence.StandardKey.HelpContents)
        self.shortcuts_action = self._command("Keyboard Shortcuts", self._show_shortcuts, "Ctrl+Shift+/")
        self.quick_start_action = self._command("Quick Tour…", self._show_quick_tour, "Shift+F1")
        self.quick_start_action.setToolTip("Quick Tour… — Shift+F1")
        self.github_action = self._command("GitHub Repository", self._open_github)
        self.issue_action = self._command("Raise an Issue", self._open_issues)
        self.about_action = self._command("About Marko Plus", self._show_about_dialog); self.about_action.setMenuRole(QAction.MenuRole.AboutRole)

        bar = self.menuBar()
        bar.setNativeMenuBar(True)
        self.file_menu = bar.addMenu("&File")
        file_menu = self.file_menu
        for action in (self.new_action, self.new_folder_action): file_menu.addAction(action)
        file_menu.addSeparator()
        file_menu.addAction(self.dashboard_action)
        file_menu.addAction(self.next_file_action)
        file_menu.addAction(self.previous_file_action)
        file_menu.addSeparator()
        file_menu.addAction(self.refresh_workspace_action)
        self.workspace_menu = file_menu.addMenu("Workspace(s)")
        self.workspace_tabbed_action = self.workspace_menu.menuAction()
        self.workspace_action_group = QActionGroup(self.workspace_menu)
        self.workspace_action_group.setExclusive(True)
        self.workspace_menu.aboutToShow.connect(self._rebuild_workspace_menu)
        self._rebuild_workspace_menu()
        file_menu.addAction(self.import_file_action)
        file_menu.addSeparator()
        file_menu.addAction(self.open_external_file_action)
        file_menu.addAction(self.new_window_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action); file_menu.addAction(self.save_as_action); file_menu.addAction(self.save_new_action); file_menu.addAction(self.save_dashboard_action)
        more = file_menu.addMenu("More Actions")
        for action in (self.duplicate_action, self.rename_file_action, self.delete_file_action): more.addAction(action)
        more.addSeparator()
        more.addAction(self.external_editor_action)
        more.addAction(self.open_document_folder_action)
        more.addSeparator()
        more.addAction(self.properties_action)
        file_menu.addSeparator(); file_menu.addAction(self.print_action); file_menu.addAction(self.export_pdf_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action); file_menu.addAction(self.save_exit_action)

        self.edit_menu = bar.addMenu("&Edit")
        edit = self.edit_menu
        edit.addAction(self.undo_action); edit.addAction(self.redo_action); edit.addSeparator()
        for action in (self.cut_action, self.copy_action, self.paste_action, self.paste_plain_action): edit.addAction(action)
        edit.addSeparator(); edit.addAction(self.delete_text_action); edit.addSeparator()
        edit.addAction(self.comment_action)
        edit.addAction(self.duplicate_line_action); edit.addAction(self.delete_line_action); edit.addSeparator(); edit.addAction(self.select_all_action)
        edit.addSeparator(); edit.addAction(self.find_action); edit.addAction(self.goto_action); edit.addAction(self.replace_action)

        self.markdown_menu = bar.addMenu("&Markdown")
        markdown = self.markdown_menu
        for action in (self.bold_action, self.italic_action, self.strike_action, self.quote_action): markdown.addAction(action)
        markdown.addSeparator()
        for action in (self.bullet_action, self.number_action, self.task_action): markdown.addAction(action)
        markdown.addSeparator(); markdown.addAction(self.indent_action); markdown.addAction(self.outdent_action)
        markdown.addSeparator(); markdown.addAction(self.inline_code_action); markdown.addAction(self.code_fence_action)
        markdown.addSeparator()
        headings = markdown.addMenu("Heading")
        for action in self.heading_actions: headings.addAction(action)
        self.heading_menu_action = headings.menuAction()

        self.insert_menu = bar.addMenu("&Insert")
        insert = self.insert_menu
        insert.addAction(self.image_action)
        links = insert.addMenu("Link"); links.addAction(self.link_action); links.addAction(self.edit_link_action); links.addSeparator(); links.addAction(self.remove_link_action)
        insert.addSeparator()
        insert.addAction(self.table_action)
        insert.addSeparator()
        for action in (self.date_time_action, self.date_action, self.time_action): insert.addAction(action)
        insert.addSeparator()
        insert.addAction(self.rule_action); insert.addAction(self.symbol_action)

        self.view_menu = bar.addMenu("&View")
        view = self.view_menu
        view.addAction(self.fullscreen_action)
        view.addAction(self.status_bar_action)
        view.addSeparator()
        view.addAction(self.word_wrap_action)
        view.addAction(self.line_numbers_action)
        view.addAction(self.editor_canvas_theme_action)
        view.addSeparator()
        view.addAction(self.view_only_action)
        layout_menu = view.addMenu("Editor Layout")
        layout_menu.addAction(self.file_header_action)
        layout_menu.addSeparator()
        layout_menu.addAction(self.source_only_action)
        layout_menu.addAction(self.split_action)
        layout_menu.addAction(self.preview_only_action)
        self.editor_layout_menu_action = layout_menu.menuAction()
        view.addSeparator()
        zoom = view.addMenu("Editor Zoom")
        zoom.addAction(self.zoom_in_action)
        zoom.addAction(self.zoom_out_action)
        zoom.addSeparator()
        zoom.addAction(self.zoom_reset_action)
        more_settings = view.addMenu("Editor Miscellaneous")
        more_settings.addAction(self.tab_width_action)
        more_settings.addSeparator()
        more_settings.addAction(self.display_font_action)
        more_settings.addAction(self.preview_font_action)

        self.settings_menu = bar.addMenu("&Settings")
        settings = self.settings_menu
        settings.addAction(self.collapsed_mode_action)
        settings.addSeparator()
        theme_menu = settings.addMenu("App Theme")
        theme_menu.addAction(self.theme_light_action)
        theme_menu.addAction(self.theme_dark_action)
        theme_menu.addAction(self.theme_system_action)
        self.theme_tabbed_action = theme_menu.menuAction()
        dashboard_menu = settings.addMenu("App Dashboard")
        dashboard_menu.addAction(self.list_action)
        dashboard_menu.addAction(self.grid_action)
        self.dashboard_tabbed_action = dashboard_menu.menuAction()
        sidebar_menu = settings.addMenu("App Sidebar")
        sidebar_menu.addAction(self.sidebar_action)
        sidebar_menu.addSeparator()
        sidebar_menu.addAction(self.left_sidebar_action)
        sidebar_menu.addAction(self.right_sidebar_action)
        self.app_sidebar_menu_action = sidebar_menu.menuAction()
        settings.addSeparator()
        launch_screen_menu = settings.addMenu("App Launch Screen")
        launch_screen_menu.addAction(self.launch_dashboard_action)
        launch_screen_menu.addAction(self.launch_last_file_action)
        self.launch_screen_tabbed_action = launch_screen_menu.menuAction()
        file_launch_menu = settings.addMenu("App File Launch")
        file_launch_menu.addAction(self.tabs_enabled_action)
        file_launch_menu.addAction(self.tabs_disabled_action)
        self.app_file_launch_menu_action = file_launch_menu.menuAction()
        settings.addSeparator()
        dirty_duplicate_menu = settings.addMenu("Duplicate File with Unsaved Changes")
        for key in ("ask", "current", "saved"):
            dirty_duplicate_menu.addAction(self.dirty_duplicate_actions[key])
        self.dirty_duplicate_tabbed_action = dirty_duplicate_menu.menuAction()
        dirty_external_menu = settings.addMenu("Open Externally with Unsaved Changes")
        for key in ("ask", "save", "saved"):
            dirty_external_menu.addAction(self.dirty_external_actions[key])
        self.dirty_external_tabbed_action = dirty_external_menu.menuAction()

        self.help_menu = bar.addMenu("&Help")
        help_menu = self.help_menu
        help_menu.addAction(self.docs_action)
        help_menu.addSeparator()
        help_menu.addAction(self.quick_start_action); help_menu.addAction(self.shortcuts_action)
        help_menu.addSeparator()
        help_menu.addAction(self.github_action); help_menu.addAction(self.issue_action)
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)
        self._refresh_action_icons()

    def _toolbar_icon_path(self, name: str) -> Path:
        return self.package_root / "assets" / "toolbar-icons" / effective_scheme(str(self.config.get("app_theme", "light"))) / f"{name}.png"

    def _refresh_action_icons(self) -> None:
        mapping = {
            "new_action":"new", "new_window_action":"new-window", "new_folder_action":"new-folder", "dashboard_action":"show-dashboard", "workspace_tabbed_action":"manage-workspaces", "import_file_action":"import-file", "open_external_file_action":"open-external-file", "previous_file_action":"previous", "next_file_action":"next", "save_action":"save", "save_as_action":"save-as", "save_new_action":"save-new", "save_dashboard_action":"save-dashboard", "save_exit_action":"save-exit",
            "duplicate_action":"duplicate-file", "rename_file_action":"rename", "delete_file_action":"delete-file", "open_document_folder_action":"open-folder", "external_editor_action":"external-editor", "properties_action":"properties",
            "print_action":"print", "export_pdf_action":"export-pdf", "exit_action":"exit", "undo_action":"undo", "redo_action":"redo", "cut_action":"cut", "copy_action":"copy", "paste_action":"paste", "paste_plain_action":"paste-plain", "delete_text_action":"delete-text", "comment_action":"comment-toggle", "select_all_action":"select-all", "duplicate_line_action":"duplicate-line", "delete_line_action":"delete-line", "find_action":"find", "replace_action":"replace", "goto_action":"goto-line",
            "bold_action":"bold", "italic_action":"italic", "strike_action":"strikethrough", "quote_action":"quote-block", "bullet_action":"bullet-list", "number_action":"numbered-list", "task_action":"task-list", "indent_action":"indent", "outdent_action":"outdent", "inline_code_action":"inline-code", "code_fence_action":"code-block", "link_action":"insert-link", "edit_link_action":"edit-link", "remove_link_action":"remove-link", "rule_action":"horizontal-rule", "image_action":"insert-image", "table_action":"insert-table", "date_time_action":"date-time", "date_action":"insert-date", "time_action":"insert-time", "symbol_action":"symbols",
            "fullscreen_action":"full-screen", "file_header_action":"file-header", "collapsed_mode_action":"focused-mode", "sidebar_action":"show-sidebar", "left_sidebar_action":"dock-left", "right_sidebar_action":"dock-right", "source_only_action":"source-only", "split_action":"source-preview", "preview_only_action":"preview-only", "view_only_action":"view-only", "word_wrap_action":"word-wrap", "line_numbers_action":"line-numbers", "editor_canvas_theme_action":"editor-canvas", "status_bar_action":"status-bar", "zoom_in_action":"zoom-in", "zoom_out_action":"zoom-out", "zoom_reset_action":"zoom-reset", "display_font_action":"default-font", "preview_font_action":"font-dialog", "tab_width_action":"tab-width",
            "theme_tabbed_action":"app-theme", "dashboard_tabbed_action":"app-dashboard", "app_sidebar_menu_action":"sidebar-settings", "launch_screen_tabbed_action":"app-launch-screen", "app_file_launch_menu_action":"file-launch", "tabs_enabled_action":"tabs-enabled", "tabs_disabled_action":"tabs-disabled", "editor_layout_menu_action":"toolbar-tabbed", "dirty_duplicate_tabbed_action":"dirty-duplicate-policy", "dirty_external_tabbed_action":"dirty-external-policy",
            "theme_system_action":"system-theme", "theme_dark_action":"dark-mode", "theme_light_action":"light-theme", "list_action":"list-view", "grid_action":"grid-view", "launch_dashboard_action":"launch-dashboard", "launch_last_file_action":"launch-last-file", "heading_tabbed_action":"heading-group", "heading_menu_action":"heading-group", "code_tabbed_action":"code-group", "link_tabbed_action":"link-group", "docs_action":"documentation", "quick_start_action":"tutorial", "shortcuts_action":"shortcuts", "github_action":"github", "issue_action":"issue", "about_action":"about",
        }
        for attr, name in mapping.items():
            action = getattr(self, attr, None); path = self._toolbar_icon_path(name)
            if action is not None and path.is_file(): action.setIcon(QIcon(str(path)))
        for level, action in enumerate(self.heading_actions):
            path = self._toolbar_icon_path(f"heading-{level}")
            if path.is_file(): action.setIcon(QIcon(str(path)))
        if hasattr(self, "app_tabs_toggle_action"):
            path = self._toolbar_icon_path("tabs-enabled" if self._tabs_enabled() else "tabs-disabled")
            if path.is_file(): self.app_tabs_toggle_action.setIcon(QIcon(str(path)))
        if hasattr(self, "shell_ribbon"):
            self.shell_ribbon.refresh_theme()

    def _create_tabbed_toolbar(self) -> None:
        names = (
            "new_action", "new_folder_action", "new_window_action", "dashboard_action", "workspace_tabbed_action",
            "import_file_action", "open_external_file_action", "previous_file_action", "next_file_action",
            "save_action", "save_as_action", "save_new_action", "save_dashboard_action", "save_exit_action",
            "properties_action", "external_editor_action", "rename_file_action", "delete_file_action",
            "duplicate_action", "open_document_folder_action", "print_action", "export_pdf_action",
            "cut_action", "copy_action", "paste_action", "paste_plain_action", "delete_text_action",
            "select_all_action", "undo_action", "redo_action", "duplicate_line_action", "delete_line_action", "comment_action",
            "find_action", "goto_action", "replace_action", "bold_action", "italic_action", "strike_action",
            "code_tabbed_action", "heading_tabbed_action", "bullet_action", "number_action", "task_action",
            "quote_action", "indent_action", "outdent_action", "rule_action", "image_action", "table_action",
            "link_tabbed_action", "link_action", "edit_link_action", "remove_link_action", "date_time_action", "date_action", "time_action", "symbol_action",
            "fullscreen_action", "status_bar_action", "sidebar_action", "word_wrap_action",
            "line_numbers_action", "editor_canvas_theme_action", "file_header_action", "view_only_action", "zoom_in_action",
            "zoom_out_action", "zoom_reset_action", "source_only_action", "split_action",
            "preview_only_action", "tab_width_action", "display_font_action", "preview_font_action",
            "collapsed_mode_action", "theme_light_action", "theme_dark_action", "theme_system_action", "list_action", "grid_action",
            "left_sidebar_action", "right_sidebar_action", "launch_dashboard_action", "launch_last_file_action",
            "tabs_enabled_action", "tabs_disabled_action", "dirty_duplicate_tabbed_action", "dirty_external_tabbed_action",
            "docs_action", "quick_start_action", "shortcuts_action", "github_action", "issue_action",
            "about_action",
        )
        self.shell_ribbon = ShellRibbon({name: getattr(self, name) for name in names}, self.tabbed_container)
        self.tabbed_layout.addWidget(self.shell_ribbon)
        self.shell_ribbon.collapsed_changed.connect(
            lambda value: self.config.set("markopad_tabbed_collapsed", bool(value), save=True)
        )
        if bool(self.config.get("markopad_tabbed_collapsed", False)):
            self.shell_ribbon.set_collapsed(True, emit=False)

    def _tabs_enabled(self) -> bool:
        return bool(self.config.get("tabs_enabled", True))

    def _sync_tabs_mode_ui(self) -> None:
        enabled = self._tabs_enabled()
        if not enabled:
            self._remove_navigation_tab()
            self.document_tabs.setVisible(False)
        elif self.editor_manager.current_module is not None:
            self._select_document_tab(self.editor_manager.current_module)
        elif self.editor_manager.current_folder is not None:
            self._show_folder_navigation_tab(self.editor_manager.current_folder)
        else:
            self._show_dashboard_navigation_tab()
        for key, action in self.tabs_actions.items():
            action.blockSignals(True)
            action.setChecked((key == "enabled") == enabled)
            action.blockSignals(False)
        text = f"Tabs {'Enabled' if enabled else 'Disabled'}"
        self.app_tabs_toggle_action.setText(text)
        self.app_tabs_toggle_action.setToolTip(
            f"File Launch — Tabs {'Enabled' if enabled else 'Disabled'}"
        )
        self._refresh_action_icons()

    def _set_tabs_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        current = self._tabs_enabled()
        if enabled == current:
            self._sync_tabs_mode_ui()
            return
        if not enabled and current:
            if not self.editor_manager.prepare_tabs_disabled():
                self._sync_tabs_mode_ui()
                return
        self.config.set("tabs_enabled", enabled, save=True)
        self._sync_tabs_mode_ui()

    def _toggle_tabs_mode(self, _checked=False) -> None:
        self._set_tabs_enabled(not self._tabs_enabled())

    def _open_context_navigation_for_path(self, path: str | Path) -> None:
        """Open the temporary navigation surface for a document's location."""
        module_path = Path(path).expanduser().resolve(strict=False)
        parent = module_path.parent
        try:
            parent.relative_to(self.library_root)
        except ValueError:
            self.editor_manager.show_dashboard()
            return
        if parent == self.library_root or not parent.is_dir():
            self.editor_manager.show_dashboard()
            return
        self.editor_manager.open_folder(parent)

    def _open_context_tab(self, _checked=False) -> None:
        """Open/reuse the contextual temporary tab, enabling tabs if needed."""
        module = self.editor_manager.current_module
        module_path = module.path if module is not None else None
        if not self._tabs_enabled():
            self._set_tabs_enabled(True)
        if module_path is not None:
            self._open_context_navigation_for_path(module_path)
            return
        folder = self.editor_manager.current_folder
        if folder is not None:
            self.editor_manager.open_folder(folder)
        else:
            self.editor_manager.show_dashboard()

    def _close_context(self, _checked=False) -> None:
        """Ctrl+W: close the active tab contextually, or show Dashboard."""
        if not self._tabs_enabled():
            self.editor_manager.show_dashboard()
            return
        module = self.editor_manager.current_module
        if module is None:
            self.editor_manager.show_dashboard()
            return
        path = module.path
        if not self.editor_manager.close_module(module):
            return
        self._open_context_navigation_for_path(path)

    def _cycle_context_tab(self, direction: int) -> None:
        if self._tabs_enabled():
            self._cycle_document_tab(direction)
            return
        if hasattr(self, "shell_ribbon"):
            self.shell_ribbon.cycle_tab(direction)

    def _tab_index_for_path(self, path: str | Path) -> int:
        target = str(Path(path).expanduser().resolve(strict=False))
        for index in range(self.document_tabs.count()):
            if self.document_tabs.tabData(index) == target:
                return index
        return -1

    @staticmethod
    def _document_tab_text(module: Module) -> str:
        return f"{module.filename}{'*' if module.dirty else ''}"

    _NAV_TAB_PREFIX = "marko-plus://navigation/"
    _NAV_DASHBOARD_TOKEN = _NAV_TAB_PREFIX + "dashboard"
    _NAV_FOLDER_PREFIX = _NAV_TAB_PREFIX + "folder/"

    def _navigation_tab_index(self) -> int:
        for index in range(self.document_tabs.count()):
            data = self.document_tabs.tabData(index)
            if isinstance(data, str) and data.startswith(self._NAV_TAB_PREFIX):
                return index
        return -1

    def _remove_navigation_tab(self) -> None:
        index = self._navigation_tab_index()
        if index < 0:
            return
        self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self.document_tabs.blockSignals(False)
        self.document_tabs.setVisible(self._tabs_enabled() and self.document_tabs.count() > 0)

    def _show_navigation_tab(self, text: str, token: str, tooltip: str) -> None:
        if not self._tabs_enabled():
            return
        index = self._navigation_tab_index()
        self.document_tabs.blockSignals(True)
        if index < 0:
            index = self.document_tabs.addTab(text)
        else:
            self.document_tabs.setTabText(index, text)
        self.document_tabs.setTabData(index, token)
        self.document_tabs.setTabToolTip(index, tooltip)
        self.document_tabs.setTabButton(index, QTabBar.ButtonPosition.LeftSide, None)
        self.document_tabs.setTabButton(index, QTabBar.ButtonPosition.RightSide, None)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)
        self.document_tabs.setVisible(True)

    def _show_dashboard_navigation_tab(self, *_args) -> None:
        self._show_navigation_tab("Dashboard", self._NAV_DASHBOARD_TOKEN, "Dashboard")

    def _show_folder_navigation_tab(self, folder_path: str | Path) -> None:
        path = Path(folder_path).expanduser().resolve(strict=False)
        label = path.name or "Folder"
        self._show_navigation_tab(label, self._NAV_FOLDER_PREFIX + str(path), str(path))

    def _ensure_document_tab(self, module: Module) -> int:
        path_text = str(module.path.expanduser().resolve(strict=False))
        index = self._tab_index_for_path(module.path)
        if index < 0:
            self.document_tabs.blockSignals(True)
            index = self.document_tabs.addTab(self._document_tab_text(module))
            self.document_tabs.setTabData(index, path_text)
            self.document_tabs.blockSignals(False)
        else:
            self.document_tabs.setTabText(index, self._document_tab_text(module))
        self.document_tabs.setTabToolTip(index, path_text)
        self.document_tabs.setVisible(self._tabs_enabled() and self.document_tabs.count() > 0)
        return index

    def _select_document_tab(self, module: Module) -> None:
        self._remove_navigation_tab()
        index = self._ensure_document_tab(module)
        self.document_tabs.blockSignals(True)
        self.document_tabs.setCurrentIndex(index)
        self.document_tabs.blockSignals(False)

    def _activate_document_tab(self, index: int) -> None:
        if index < 0 or index >= self.document_tabs.count():
            return
        data = self.document_tabs.tabData(index)
        if not data:
            return
        token = str(data)
        if token == self._NAV_DASHBOARD_TOKEN:
            self.editor_manager.show_dashboard()
            return
        if token.startswith(self._NAV_FOLDER_PREFIX):
            self.editor_manager.open_folder(Path(token[len(self._NAV_FOLDER_PREFIX):]))
            return
        path = Path(token)
        module = self.repository.get(path)
        if module is None:
            self._remove_document_tab(path)
            return
        self.editor_manager.open_module(module)

    def _remove_document_tab(self, path: str | Path) -> None:
        index = self._tab_index_for_path(path)
        if index < 0:
            return
        self.document_tabs.blockSignals(True)
        self.document_tabs.removeTab(index)
        self.document_tabs.blockSignals(False)
        self.document_tabs.setVisible(self._tabs_enabled() and self.document_tabs.count() > 0)

    def _close_document_tab(self, index: int) -> None:
        if index < 0 or index >= self.document_tabs.count():
            return
        data = self.document_tabs.tabData(index)
        if not data:
            return
        token = str(data)
        if token.startswith(self._NAV_TAB_PREFIX):
            return
        path = Path(token)
        neighbor_path: Path | None = None
        if self.document_tabs.count() > 1:
            neighbor_index = index + 1 if index + 1 < self.document_tabs.count() else index - 1
            neighbor_data = self.document_tabs.tabData(neighbor_index)
            if neighbor_data:
                neighbor_path = Path(str(neighbor_data))
        if not self.editor_manager.close_module(path):
            return
        if self.editor_manager.current_module is None and neighbor_path is not None:
            neighbor = self.repository.get(neighbor_path)
            if neighbor is not None:
                self.editor_manager.open_module(neighbor)

    def _cycle_document_tab(self, direction: int) -> None:
        count = self.document_tabs.count()
        if count <= 0:
            return
        current = self.document_tabs.currentIndex()
        if current < 0:
            target = 0 if direction >= 0 else count - 1
        else:
            target = (current + (1 if direction >= 0 else -1)) % count
        self._activate_document_tab(target)

    def _update_document_tab(self, module: Module) -> None:
        current = self.editor_manager.current_module
        if current is not None and current.path == module.path:
            self._update_window_title()
        index = self._tab_index_for_path(module.path)
        if index < 0:
            return
        self.document_tabs.setTabText(index, self._document_tab_text(module))
        self.document_tabs.setTabToolTip(index, str(module.path))

    def _rebind_document_tab(self, old_path: str | Path, new_path: str | Path) -> None:
        index = self._tab_index_for_path(old_path)
        if index < 0:
            return
        new_path = Path(new_path).expanduser().resolve(strict=False)
        self.document_tabs.setTabData(index, str(new_path))
        module = self.repository.get(new_path)
        if module is not None:
            self.document_tabs.setTabText(index, self._document_tab_text(module))
            self.document_tabs.setTabToolTip(index, str(new_path))

    def _on_repository_module_path_changed(self, module: Module, old_path: Path) -> None:
        self._rebind_document_tab(old_path, module.path)

    def _reset_document_tabs(self) -> None:
        self.document_tabs.blockSignals(True)
        while self.document_tabs.count():
            self.document_tabs.removeTab(0)
        self.document_tabs.blockSignals(False)
        self.document_tabs.setVisible(False)

    @staticmethod
    def _widget_is_within(container: QWidget, candidate) -> bool:
        return isinstance(candidate, QWidget) and (
            candidate is container or container.isAncestorOf(candidate)
        )

    def _active_text_surface(self, page: EditorPage | None = None) -> str:
        page = self._current_page() if page is None else page
        if page is None:
            return "source"
        if page.view_mode == "preview":
            return "preview"
        if page.view_mode == "source":
            return "source"
        surface = getattr(page, "_active_text_surface", "source")
        return surface if surface in {"source", "preview"} else "source"

    def _source_interaction_active(self, page: EditorPage | None = None) -> bool:
        page = self._current_page() if page is None else page
        return bool(
            page is not None
            and page.view_mode != "preview"
            and self._active_text_surface(page) == "source"
        )

    def _editor_call(self, method: str, *args) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            getattr(page.editor, method)(*args)

    def _set_document_view(self, mode: str) -> None:
        page = self._current_page()
        if page is not None: page.set_view_mode(mode)

    def _insert_text(self, text: str) -> None:
        page = self._current_page()
        if self._source_interaction_active(page) and not page.editor.isReadOnly():
            page.editor.insert_guarded_text(text)

    def _insert_code_block(self) -> None:
        language, ok = QInputDialog.getText(self, "Code Block — Marko Plus", "Language (optional):")
        if ok: self._editor_call("insert_code_fence", language)

    def _insert_link(self) -> None:
        page = self._current_page()
        if page is None: return
        selected = page.editor.textCursor().selectedText().replace("\u2029", " ")
        label, ok = QInputDialog.getText(self, "Insert Link — Marko Plus", "Link text:", text=selected or "Link")
        if not ok: return
        url, ok = QInputDialog.getText(self, "Insert Link — Marko Plus", "URL:")
        if ok and url.strip(): page.editor.insert_link(label, url.strip())

    def _link_at_cursor(self):
        page = self._current_page()
        if page is None: return None
        cursor = page.editor.textCursor(); block = cursor.block(); text = block.text(); pos = cursor.position() - block.position()
        for match in re.finditer(r"(?<!!)\[([^\]]*)\]\(([^\n)]*)\)", text):
            if match.start() <= pos <= match.end(): return page, block.position()+match.start(), block.position()+match.end(), match.group(1), match.group(2)
        return None

    def _edit_link(self) -> None:
        found = self._link_at_cursor()
        if not found: self.show_status("Place the cursor inside a Markdown link first."); return
        page, start, end, label, url = found
        new_label, ok = QInputDialog.getText(self, "Edit Link — Marko Plus", "Link text:", text=label)
        if not ok: return
        new_url, ok = QInputDialog.getText(self, "Edit Link — Marko Plus", "URL:", text=url)
        if not ok: return
        cursor = QTextCursor(page.editor.document()); cursor.setPosition(start); cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(f"[{new_label.replace(']', r'\]')}]({new_url.replace(' ', '%20').replace(')', r'\)')})")

    def _remove_link(self) -> None:
        found = self._link_at_cursor()
        if not found: self.show_status("Place the cursor inside a Markdown link first."); return
        page, start, end, label, _url = found
        cursor = QTextCursor(page.editor.document()); cursor.setPosition(start); cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor); cursor.insertText(label)

    def _insert_image(self) -> None:
        page = self._current_page()
        if page is None: return
        kind, ok = QInputDialog.getItem(self, "Image Reference — Marko Plus", "Image source:", ["Local file (relative path)", "Web URL"], 0, False)
        if not ok: return
        if kind.startswith("Web"):
            url, ok = QInputDialog.getText(self, "Image URL — Marko Plus", "URL:")
            if not ok or not url.strip(): return
            reference = url.strip().replace(" ", "%20").replace(")", r"\)"); alt_default = "Image"
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Choose Image — Marko Plus", str(page.module.path.parent), "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg);;All Files (*)")
            if not path: return
            target = Path(path).resolve()
            try: reference = os.path.relpath(target, page.module.path.parent).replace(os.sep, "/")
            except ValueError: QMessageBox.warning(self, "Portable Image Reference", "This image cannot be expressed as a relative path from the Markdown document."); return
            reference = reference.replace(" ", "%20").replace(")", r"\)"); alt_default = target.stem
        alt, ok = QInputDialog.getText(self, "Image Description — Marko Plus", "Alternative text:", text=alt_default)
        if ok: self._insert_text(f"![{alt.replace(']', r'\]')}]({reference})")

    def _insert_table(self) -> None:
        page = self._current_page()
        if page is None: return
        dialog = QDialog(self); dialog.setWindowTitle("Table — Marko Plus"); form = QFormLayout(dialog)
        rows = QSpinBox(dialog); cols = QSpinBox(dialog); rows.setRange(1,100); cols.setRange(1,20); rows.setValue(3); cols.setValue(3)
        form.addRow("Rows:", rows); form.addRow("Columns:", cols)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog); buttons.accepted.connect(dialog.accept); buttons.rejected.connect(dialog.reject); form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted: page.editor.insert_table(rows.value(), cols.value())

    def _insert_symbol(self) -> None:
        page = self._current_page()
        if page is not None:
            page.show_symbols_dialog()

    def _paste(self) -> None:
        page = self._current_page()
        if not self._source_interaction_active(page) or page.editor.isReadOnly(): return
        mime = QApplication.clipboard().mimeData()
        if mime.hasHtml():
            html = mime.html()
            if len(html) > page.editor.MAX_PASTE_CHARACTERS: self.show_status("Clipboard HTML is too large to convert safely."); return
            doc = QTextDocument(); doc.setHtml(html)
            try: text = doc.toMarkdown()
            except AttributeError: text = doc.toPlainText()
            text = re.sub(r"!\[([^\]]*)\]\(data:[^\n)]*\)", lambda m: m.group(1) or "[embedded image omitted]", text, flags=re.IGNORECASE)
        else: text = mime.text() if mime.hasText() else ""
        if text:
            page.editor.insert_guarded_text(text)
        else:
            page.show_editor_status(
                "Clipboard does not contain text that can be pasted.",
                3500,
            )

    def _delete_line(self) -> None:
        page = self._current_page()
        if not self._source_interaction_active(page) or page.editor.isReadOnly(): return
        cursor = page.editor.textCursor(); cursor.beginEditBlock(); cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock); cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        if not cursor.atEnd(): cursor.deleteChar()
        elif cursor.position() > 0: cursor.deletePreviousChar()
        cursor.endEditBlock()

    def _set_editor_zoom(self, percent: int) -> None:
        if self._current_page() is None:
            return
        clamped = max(50, min(300, int(percent)))
        self.config.set("markopad_zoom", clamped, save=True)
        self.editor_manager.apply_editor_preferences()

    def _zoom_current(self, steps: int) -> None:
        current = self.config.get_int("markopad_zoom", 100, minimum=50, maximum=300)
        self._set_editor_zoom(current + (10 * int(steps)))

    def _zoom_reset(self) -> None:
        self._set_editor_zoom(100)

    def adjust_zoom_from_wheel(self, delta: int) -> None:
        """Honor Markopad's Ctrl+mouse-wheel zoom contract through the Plus shell."""
        if delta > 0:
            self._zoom_current(1)
        elif delta < 0:
            self._zoom_current(-1)

    def _set_theme(self, theme: str) -> None:
        if theme not in {"system", "dark", "light"}:
            return
        # Application chrome is independent from the persisted Dark Editor choice.
        self.config.set("app_theme", theme, save=True)
        apply_theme(QApplication.instance(), theme)
        {"system": self.theme_system_action, "dark": self.theme_dark_action, "light": self.theme_light_action}[theme].setChecked(True)
        self._refresh_action_icons(); self.editor_manager.dashboard.refresh_theme()
        for folder_page in self.editor_manager._folder_pages.values(): folder_page.refresh_theme()
        for _path, state in tuple(self.states):
            if isinstance(state.editor_page, EditorPage):
                # Re-apply only the independent editor presentation through
                # the dirty-state-preserving path.
                state.editor_page.apply_canvas_theme()
        label = "System" if theme == "system" else theme.title()
        self.show_status(f"Theme: {label}.")

    def _save_and_exit(self) -> None:
        page = self._current_page()
        if page is None or page.save_to_disk(): self.close()

    def _save_and_new(self) -> None:
        page = self._current_page()
        if page is None or page.save_to_disk():
            self._new_markdown_file()

    def _save_and_dashboard(self) -> None:
        page = self._current_page()
        if page is None or page.save_to_disk():
            self.editor_manager.show_dashboard()

    def _rename_current(self) -> None:
        module = self._current_module()
        if module is not None:
            self.file_actions.rename_module(module)
            return
        folder = self._selected_folder()
        if folder is not None and folder != self.library_root:
            self.file_actions.rename_folder(folder)

    def _choose_tab_width(self) -> None:
        current = self.config.get_int(
            "editor_tab_width_spaces", 4, minimum=1, maximum=16
        )
        width, accepted = QInputDialog.getInt(
            self,
            "Tab Width — Marko Plus",
            "Spaces per tab:",
            current,
            1,
            16,
            1,
        )
        if accepted:
            self.config.set("editor_tab_width_spaces", width, save=True)
            self.editor_manager.apply_editor_preferences()

    def _toggle_dashboard_view(self) -> None:
        self.editor_manager.dashboard.toggle_view_mode()

    def _set_dirty_duplicate_action(self, choice: str) -> None:
        if choice not in {"ask", "current", "saved"}:
            return
        self.config.set("dirty_duplicate_action", choice, save=True)
        self._on_file_policy_changed("dirty_duplicate_action", choice)

    def _set_dirty_external_action(self, choice: str) -> None:
        if choice not in {"ask", "save", "saved"}:
            return
        self.config.set("dirty_external_action", choice, save=True)
        self._on_file_policy_changed("dirty_external_action", choice)

    def _on_file_policy_changed(self, key: str, value: str) -> None:
        actions = (
            self.dirty_duplicate_actions
            if key == "dirty_duplicate_action"
            else self.dirty_external_actions
            if key == "dirty_external_action"
            else {}
        )
        for selected, action in actions.items():
            action.blockSignals(True)
            action.setChecked(selected == value)
            action.blockSignals(False)

    def _set_app_launch_screen(self, screen: str) -> None:
        if screen not in {"dashboard", "last_file"}:
            return
        self.app_launch_screen = screen
        self.launch_dashboard_action.setChecked(screen == "dashboard")
        self.launch_last_file_action.setChecked(screen == "last_file")
        self.config.set("app_launch_screen", screen, save=True)

    def _handle_editor_file_drop(
        self,
        supplied_paths: list[str | Path],
        _context_folder: str | Path | None = None,
    ) -> None:
        """Open supported editor drops in their own Marko Plus windows."""
        seen: set[Path] = set()
        for supplied in supplied_paths:
            path = Path(supplied).expanduser().resolve(strict=False)
            if (
                path in seen
                or not path.is_file()
                or path.suffix.casefold() not in MARKDOWN_EXTENSIONS
            ):
                continue
            seen.add(path)
            self._launch_new_window(path)

    def _handle_app_drop(
        self,
        supplied_paths: list[str | Path],
        destination_folder: str | Path | None = None,
    ) -> None:
        """Import external Markdown drops without opening them."""
        external: list[Path] = []
        seen: set[Path] = set()
        for supplied in supplied_paths:
            path = Path(supplied).expanduser().resolve(strict=False)
            if (
                path in seen
                or not path.is_file()
                or path.suffix.casefold() not in MARKDOWN_EXTENSIONS
            ):
                continue
            seen.add(path)
            try:
                path.relative_to(self.library_root)
            except ValueError:
                external.append(path)

        if not external:
            return

        self.file_actions.import_files(
            external,
            destination_folder or self._creation_folder(),
        )

    def _delete_current_file(self) -> None:
        module = self._current_module()
        if module is not None: self.file_actions.remove_module(module)

    def _open_current_external(self) -> None:
        module = self._current_module()
        if module is not None: self.file_actions.open_external_editor(module)

    def _printable_document(self):
        page = self._current_page()
        if page is None: return None
        doc = QTextDocument(self); doc.setDefaultFont(QApplication.font())
        doc.setBaseUrl(QUrl.fromLocalFile(str(page.module.path.parent) + "/"))
        try: doc.setMarkdown(page.editor.toPlainText())
        except AttributeError: doc.setPlainText(page.editor.toPlainText())
        return doc

    def _print_current(self) -> None:
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
        doc = self._printable_document()
        if doc is None: return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution); dialog = QPrintDialog(printer, self); dialog.setWindowTitle("Print — Marko Plus")
        if dialog.exec() == QDialog.DialogCode.Accepted: doc.print(printer)

    def _export_pdf_current(self) -> None:
        from PyQt6.QtPrintSupport import QPrinter
        page = self._current_page(); doc = self._printable_document()
        if page is None or doc is None: return
        initial = str(page.module.path.with_suffix(".pdf")); path, _ = QFileDialog.getSaveFileName(self, "Export PDF — Marko Plus", initial, "PDF (*.pdf)")
        if not path: return
        if not path.lower().endswith(".pdf"): path += ".pdf"
        printer = QPrinter(QPrinter.PrinterMode.HighResolution); printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat); printer.setOutputFileName(path); doc.print(printer)

    def _show_quick_tour(self) -> None:
        """Show the richer first-run tour in Ricopad's wizard style."""
        if self.quick_tour_dialog is not None:
            self.quick_tour_dialog.show()
            self.quick_tour_dialog.raise_()
            self.quick_tour_dialog.activateWindow()
            return

        wizard = QWizard(self)
        wizard.setWindowTitle("Quick Tour — Marko Plus")
        wizard.setWindowIcon(self.windowIcon())
        wizard.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        wizard.setModal(False)
        wizard.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        wizard.setMinimumSize(700, 470)
        wizard.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)
        startup_checkbox = QCheckBox("Don't show Quick Tour on startup again", wizard)
        startup_checkbox.setChecked(bool(self.config.get("quick_tour_seen", False)))
        startup_checkbox.toggled.connect(
            lambda checked: self.config.set("quick_tour_seen", bool(checked), save=True)
        )
        wizard.setButton(QWizard.WizardButton.CustomButton1, startup_checkbox)
        wizard.setOption(QWizard.WizardOption.HaveCustomButton1, True)
        wizard.setButtonLayout([
            QWizard.WizardButton.CustomButton1,
            QWizard.WizardButton.Stretch,
            QWizard.WizardButton.BackButton,
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton,
        ])

        def add_page(title: str, subtitle: str, body: str, button=None) -> None:
            page = QWizardPage(wizard)
            page.setTitle(title)
            page.setSubTitle(subtitle)
            layout = QVBoxLayout(page)
            label = QLabel(body, page)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            layout.addWidget(label)
            if button is not None:
                layout.addWidget(button, 0, Qt.AlignmentFlag.AlignLeft)
            layout.addStretch(1)
            wizard.addPage(page)

        add_page(
            "Welcome to Marko Plus",
            "A workspace-scale Markopad for ordinary Markdown files.",
            "<p>The command bar has six tabs: <b>File, Home, Insert, View, Settings "
            "and Help</b>, with Home open by default.</p>"
            "<p>When document tabs are <b>enabled</b>, <b>Ctrl+Tab</b> and "
            "<b>Ctrl+Shift+Tab</b> move forward and backward through open document "
            "and navigation tabs. When document tabs are <b>disabled</b>, the same "
            "shortcuts move through command-bar pages instead.</p>"
            "<p><b>Ctrl+T</b> opens the current navigation context as a tab, enabling "
            "tabs first if necessary. <b>Ctrl+W</b> closes the active document tab "
            "when tabs are enabled and returns to its folder context; with tabs "
            "disabled, or no active document, it returns to Dashboard.</p>"
            "<p>Double-click a command-bar tab title to collapse its controls; click "
            "a tab title to reveal them again.</p>",
        )
        add_page(
            "Workspaces and Dashboard",
            "Keep separate Markdown collections without moving the application.",
            "<p><b>File → Workspace(s)</b> lists registered Workspaces and marks "
            "the active one. <b>Open / Manage Workspaces...</b> adds an existing folder, "
            "renames its display label, relinks it, or removes only its "
            "registration.</p>"
            "<p>Only the active Workspace is scanned and watched. On the "
            "Dashboard, one click selects a card and double-click opens Edit. "
            "Each card also provides <b>Edit, Split View and Preview</b>.</p>",
        )
        add_page(
            "Folders and files",
            "Create documents where you are already working.",
            "<p>New File uses the open folder dashboard, the active "
            "document's containing folder, or the Workspace root when the main "
            "Dashboard is open. The new file opens as soon as its name is "
            "saved.</p>"
            "<p>Use <b>Ctrl+Up</b> and <b>Ctrl+Down</b> for adjacent Markdown "
            "files shown in the folder tree. External files dropped on a folder "
            "are imported there; internal cards can be dragged onto sidebar "
            "folders to move them.</p>",
        )
        add_page(
            "Edit and preview",
            "Use Markopad's three document layouts and Markdown commands.",
            "<p><b>Source Only, Source + Preview and Preview Only</b> are "
            "available from View. Home and Insert provide Markdown formatting, "
            "headings, lists, links, images, tables, rules, dates, times and "
            "symbols.</p>"
            "<p>Locked Mode protects source text from accidental edits and stays "
            "active when you move between documents. App Theme and Dark Editor "
            "are independent: Light, Dark or System changes application chrome, "
            "while Dark Editor controls the source and preview canvas.</p>"
            "<p><b>Ctrl+Shift+[</b> opens Source Font and <b>Ctrl+Shift+]</b> opens "
            "Preview Font. <b>Ctrl+F</b> opens document Find while editing (press it again while Find has focus to close), and "
            "focuses the active Dashboard or folder search box in navigation "
            "contexts.</p>",
        )
        add_page(
            "Save safely",
            "Marko Plus edits your Markdown files directly.",
            "<p><b>Save</b> writes the active document. Save and New, Save and "
            "Dashboard, and Save and Exit save first, then perform the named "
            "action.</p>"
            "<p>If another program changes an open file, Marko Plus checks the "
            "on-disk content before overwriting it and asks what to do when the "
            "contents genuinely differ.</p>",
        )
        shortcuts_button = QPushButton("Open Keyboard Shortcuts…", wizard)
        shortcuts_button.setAutoDefault(False)
        shortcuts_button.clicked.connect(self._show_shortcuts)
        add_page(
            "Drag, drop and help",
            "External file drops are import-only.",
            "<p><b>Settings</b> contains application theme, Dashboard, launch-"
            "screen, tab, and file-handling choices. App Launch Screen defaults "
            "to Dashboard; Last File reopens the active Workspace's most recently "
            "opened valid file.</p>"
            "<p>Drag external Markdown files onto the Dashboard, workspace tree, "
            "or Folder Dashboard to import them into that target. Imported files "
            "stay closed until you choose to open or manage them.</p>"
            "<p>Help contains the bundled documentation, this Quick Tour, the "
            "live keyboard-shortcut inventory, the Marko Plus GitHub repository, "
            "issue reporting and About.</p>",
            shortcuts_button,
        )

        def tour_finished(_result: int) -> None:
            self.quick_tour_dialog = None
            page = self._current_page()
            if page is not None:
                QTimer.singleShot(
                    0,
                    (page.preview if page.view_mode == "preview" else page.editor).setFocus,
                )

        wizard.finished.connect(tour_finished)
        self.quick_tour_dialog = wizard
        wizard.show()
        wizard.raise_()
        wizard.activateWindow()

    def _current_page(self) -> EditorPage | None:
        page = self.stack.currentWidget()
        return page if isinstance(page, EditorPage) else None

    def _current_module(self) -> Module | None:
        return self.editor_manager.current_module

    def _creation_folder(self) -> Path:
        """Return the folder implied by the current document or dashboard."""
        folder = self._selected_folder()
        if folder is not None:
            return folder
        module = self._current_module()
        if module is not None and not module.external:
            return module.path.parent
        return self.library_root

    def _new_markdown_file(self) -> None:
        self.file_actions.create_file(self._creation_folder())

    def _window_launch_command(self, open_path: Path | None = None) -> list[str]:
        if self.runtime_paths.running_as_appimage:
            executable = os.environ.get("APPIMAGE", "").strip()
            command = [executable] if executable else []
        elif self.runtime_paths.running_frozen:
            command = [sys.executable]
        else:
            command = [
                sys.executable,
                str(self.runtime_paths.launcher_root / "main.py"),
            ]
        if command and open_path is not None:
            command.append(str(Path(open_path).resolve(strict=False)))
        return command

    def _launch_new_window(self, open_path: Path | None = None) -> bool:
        command = self._window_launch_command(open_path)
        if not command:
            QMessageBox.warning(
                self,
                "New Window Failed",
                "Marko Plus could not locate its launcher.",
            )
            return False
        try:
            subprocess.Popen(
                command,
                cwd=str(self.runtime_paths.launcher_root),
                start_new_session=True,
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "New Window Failed",
                f"Marko Plus could not open a new window:\n\n{error}",
            )
            return False
        return True

    def _new_window(self) -> None:
        self._launch_new_window()

    def _import_file_into_workspace(self) -> None:
        patterns = "*.md *.markdown *.mdown *.mkd"
        selected, _filter = QFileDialog.getOpenFileName(
            self,
            "Import File into Workspace — Marko Plus",
            "",
            f"Markdown Files ({patterns})",
        )
        if not selected:
            return
        # Reuse the exact external-drop import path: validate as external
        # Markdown, copy into the Workspace root, rescan, and stop without opening.
        self._handle_app_drop([Path(selected)], self.library_root)

    def _open_external_file(self) -> None:
        patterns = "*.md *.markdown *.mdown *.mkd"
        selected, _filter = QFileDialog.getOpenFileName(
            self,
            "Open External File — Marko Plus",
            "",
            f"Markdown Files ({patterns})",
        )
        if not selected:
            return
        path = Path(selected).expanduser().resolve(strict=False)
        if not path.is_file() or path.suffix.casefold() not in MARKDOWN_EXTENSIONS:
            QMessageBox.warning(
                self,
                "Open External File Failed",
                "Choose a supported Markdown file (.md, .markdown, .mdown, or .mkd).",
            )
            return
        try:
            path.relative_to(self.library_root)
        except ValueError:
            self._launch_new_window(path)
            return
        QMessageBox.information(
            self,
            "Managed Workspace File",
            "That file belongs to the active Workspace. Open it from the Workspace instead.",
        )

    def _new_folder(self) -> None:
        created = self.file_actions.create_folder(self._creation_folder())
        if created is not None:
            # Empty folders contain no modules, so a repository rescan alone
            # cannot add them to the document-derived tree. Rebuild the tree
            # after the directory is created so the folder appears at once.
            QTimer.singleShot(100, self.navigation.rebuild_from_repository)

    def _show_projects(self) -> None:
        dialog = ProjectsDialog(self.project_registry, self)
        result = dialog.exec()
        if (
            result == QDialog.DialogCode.Accepted
            and dialog.selected_project_id
        ):
            self._switch_project(dialog.selected_project_id)
        self._update_window_title()
        self._rebuild_workspace_menu()

    def _rebuild_workspace_menu(self) -> None:
        """Build the radio inventory only from the lightweight registry."""
        for action in tuple(self.workspace_action_group.actions()):
            self.workspace_action_group.removeAction(action)
            self.workspace_menu.removeAction(action)
            action.deleteLater()
        self.workspace_menu.clear()
        self.workspace_menu.addAction(self.manage_workspaces_action)
        self.workspace_menu.addSeparator()

        active_id = self.project_registry.active_project_id
        for workspace in self.project_registry.projects:
            action = QAction(workspace.name, self.workspace_menu)
            action.setCheckable(True)
            action.setChecked(workspace.project_id == active_id)
            action.setData(workspace.project_id)
            action.setToolTip(str(workspace.folder))
            action.setStatusTip(str(workspace.folder))
            action.triggered.connect(
                lambda _checked=False, workspace_id=workspace.project_id:
                self._switch_project(workspace_id)
            )
            self.workspace_action_group.addAction(action)
            self.workspace_menu.addAction(action)


    def _switch_project(self, project_id: str) -> bool:
        project = self.project_registry.get(project_id)
        if project is None:
            return False
        if project.project_id == self.project_registry.active_project_id:
            self._update_window_title()
            self.editor_manager.show_dashboard()
            return True
        if not project.folder.is_dir():
            QMessageBox.warning(
                self,
                "Workspace Folder Unavailable",
                "Relink this Workspace to an available folder before opening it.",
            )
            return False
        try:
            project_root = self.runtime_paths.ensure_writable_workspace(project.folder)
        except OSError as error:
            QMessageBox.warning(
                self,
                "Workspace Cannot Be Opened",
                f"Marko Plus could not use this Workspace folder:\n\n{error}",
            )
            return False
        if not self.editor_manager.can_close_application():
            return False

        self._save_active_project_state(save=True)
        stopped = self.watcher.stop(
            timeout_ms=2500,
            pump_events=QApplication.processEvents,
        )
        if not stopped:
            self._install_watcher(self.library_root, start=True, retire_current=False)
            QMessageBox.warning(
                self,
                "Workspace Switch Cancelled",
                "The current Workspace scanner did not stop safely. "
                "The existing Workspace remains active.",
            )
            return False

        self._pending_open_path = None
        self._pending_new_file_view_mode = None
        self._repair_navigation_after_scan = False
        self.library_root = project_root
        self.editor_manager.switch_workspace_root(project_root)
        self.navigation.switch_workspace_root(project_root)
        self.repository.clear()
        self.project_registry.set_active(project.project_id)
        self._apply_active_project_state()
        self._install_watcher(project_root, start=True, retire_current=True)
        self.editor_manager.show_dashboard()
        self._update_action_states()
        self.show_status(f"Opening Workspace: {project.name}")
        return True


    def _selected_folder(self) -> Path | None:
        return self.editor_manager.current_folder

    def _open_current_document_folder(self) -> None:
        module = self._current_module()
        if module is not None:
            self.file_actions.open_module_folder(module)

    def _open_current_folder_external(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.open_folder_external(folder)

    def _rename_current_folder(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.rename_folder(folder)

    def _remove_current_folder(self) -> None:
        folder = self._selected_folder()
        if folder is not None:
            self.file_actions.remove_folder(folder)

    def _save_current(self) -> None:
        page = self._current_page()
        if page:
            page.save_to_disk()

    def _save_external_change_version_as(self, page: EditorPage) -> bool:
        """Preserve the live Marko version while leaving the changed source untouched."""
        source_path = page.module.path.resolve(strict=False)
        suffix = source_path.suffix or ".md"
        suggested = source_path.with_name(
            f"{source_path.stem} - Marko Version{suffix}"
        )
        counter = 2
        while suggested.exists():
            suggested = source_path.with_name(
                f"{source_path.stem} - Marko Version {counter}{suffix}"
            )
            counter += 1

        extensions = " ".join(f"*{ext}" for ext in sorted(MARKDOWN_EXTENSIONS))
        while True:
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "Save Version As — Marko Plus",
                str(suggested),
                f"Markdown ({extensions});;All Files (*)",
            )
            if not selected:
                return False

            target = Path(selected).expanduser().resolve(strict=False)
            if not target.suffix:
                target = target.with_suffix(".md")
            if target.suffix.casefold() not in MARKDOWN_EXTENSIONS:
                QMessageBox.warning(
                    self,
                    "Unsupported Extension — Marko Plus",
                    "Marko Plus saves Markdown documents only.",
                )
                suggested = target
                continue
            if target == source_path:
                QMessageBox.warning(
                    self,
                    "Save Version As — Marko Plus",
                    "Choose a different filename. The original file changed "
                    "externally and will be left untouched.",
                )
                suggested = target
                continue
            existing = self.repository.get(target)
            if existing is not None:
                state = self.states.get(target)
                if state is not None and isinstance(state.editor_page, EditorPage):
                    QMessageBox.warning(
                        self,
                        "Save Version As — Marko Plus",
                        "That Markdown file is already open in another editor page. "
                        "Close it before replacing it with Save Version As.",
                    )
                    suggested = target
                    continue

            if not page.save_as_file(target):
                return False

            self.show_status(
                f"Saved Marko Plus version as {target.name}; external disk copy preserved."
            )
            return True

    def _save_current_as(self) -> None:
        page = self._current_page()
        module = self._current_module()
        if page is None or module is None:
            return

        extensions = " ".join(f"*{ext}" for ext in sorted(MARKDOWN_EXTENSIONS))
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Save As — Marko Plus",
            str(module.path),
            f"Markdown ({extensions});;All Files (*)",
        )
        if not selected:
            return

        target = Path(selected).expanduser().resolve(strict=False)
        if not target.suffix:
            target = target.with_suffix(".md")
        if target.suffix.casefold() not in MARKDOWN_EXTENSIONS:
            QMessageBox.warning(
                self,
                "Unsupported Extension — Marko Plus",
                "Marko Plus saves Markdown documents only.",
            )
            return
        if target == module.path.resolve(strict=False):
            page.save_to_disk()
            return

        existing = self.repository.get(target)
        if existing is not None:
            state = self.states.get(target)
            if state is not None and isinstance(state.editor_page, EditorPage):
                QMessageBox.warning(
                    self,
                    "Save As — Marko Plus",
                    "That Markdown file is already open in another editor page. "
                    "Close it before replacing it with Save As.",
                )
                return

        if not page.save_as_file(target):
            return

        self.show_status(f"Saved as {target.name}")

    def _undo(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.undo()

    def _redo(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.redo()

    def _cut(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.cut()

    def _copy(self) -> None:
        page = self._current_page()
        if page is None:
            return
        if self._active_text_surface(page) == "preview":
            page.preview.copy()
        else:
            page.editor.copy()

    def _delete_text(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.delete_selection_or_character()

    def _toggle_comment(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.toggle_comment()

    def _duplicate_line(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.duplicate_current_line_or_selection()

    def _paste_plain_text(self) -> None:
        page = self._current_page()
        if self._source_interaction_active(page):
            page.editor.paste_safely()

    def _select_all(self) -> None:
        page = self._current_page()
        if page is None:
            return
        if self._active_text_surface(page) == "preview":
            page.preview.selectAll()
        else:
            page.editor.select_all_text()

    def _duplicate_current(self) -> None:
        module = self._current_module()
        if module is not None:
            self.file_actions.duplicate_module(module)

    def _focus_find(self) -> None:
        """Ctrl+F toggles document Find when focused there, or targets navigation search."""
        page = self._current_page()
        if page is not None:
            page.toggle_find_panel(False)
            return

        search = getattr(self.stack.currentWidget(), "search_input", None)
        if search is not None:
            search.setFocus(Qt.FocusReason.ShortcutFocusReason)
            search.selectAll()

    def _focus_replace(self) -> None:
        page = self._current_page()
        if page:
            page.toggle_find_panel(True)

    def _go_to_line(self) -> None:
        page = self._current_page()
        if page:
            page.show_go_to_line()

    def _show_properties(self) -> None:
        page = self._current_page()
        if page:
            page.show_properties_dialog()

    def _toggle_lock_editor_current(self, checked: bool) -> None:
        # Preserve Marko's protective unlock warning, then make the resulting
        # lock state application-wide so it follows the user across files and
        # survives the next session.
        page = self._current_page()
        if page is None:
            self.view_only_action.blockSignals(True)
            self.view_only_action.setChecked(
                bool(self.config.get("lock_editor", False))
            )
            self.view_only_action.blockSignals(False)
            return
        desired = bool(checked)
        source = page.view_only_action
        if bool(page.view_only) != desired:
            source.trigger()
        resulting = bool(page.view_only)
        self.editor_manager.set_lock_editor(resulting)
        self._sync_editor_view_actions()
        self._update_action_states()
        self._update_window_title()

    def _toggle_word_wrap(self, checked: bool) -> None:
        page = self._current_page()
        if page:
            page.word_wrap_action.setChecked(bool(checked))
            page.toggle_word_wrap(bool(checked))

    def _toggle_line_numbers(self, checked: bool) -> None:
        page = self._current_page()
        if page:
            page.line_numbers_action.setChecked(bool(checked))
            page.toggle_line_numbers(bool(checked))

    def _toggle_editor_canvas_light(self, checked: bool) -> None:
        # 0.1.7 contract: application chrome and Markdown canvases are independent.
        # The action is named "Dark Editor": checked means both canvases are dark.
        self.config.set("editor_canvas_light", not bool(checked), save=True)
        self.editor_manager.apply_editor_theme()
        self.editor_manager.show_current_editor_status(
            "Editor canvas switched to a dark background."
            if bool(checked)
            else "Editor canvas switched to a light background.",
            3000,
        )

    def _choose_display_font(self) -> None:
        page = self._current_page()
        if page:
            page.choose_display_font()

    def _choose_preview_font(self) -> None:
        page = self._current_page()
        if page:
            page.choose_preview_font()

    def _sync_editor_view_actions(self) -> None:
        page = self._current_page()
        actions = (self.view_only_action, self.word_wrap_action, self.line_numbers_action, self.editor_canvas_theme_action, self.source_only_action, self.split_action, self.preview_only_action)
        for action in actions: action.blockSignals(True)
        self.view_only_action.setChecked(bool(page.view_only) if page else bool(self.config.get("lock_editor", False)))
        self.word_wrap_action.setChecked(bool(self.config.get("editor_word_wrap", True)))
        self.line_numbers_action.setChecked(bool(self.config.get("editor_line_numbers", True)))
        canvas_light = self.config.get("editor_canvas_light", True)
        if not isinstance(canvas_light, bool):
            canvas_light = True
        self.editor_canvas_theme_action.setChecked(not canvas_light)
        mode = page.view_mode if page else str(self.config.get("markopad_view_mode", "split"))
        self.source_only_action.setChecked(mode == "source")
        self.split_action.setChecked(mode == "split")
        self.preview_only_action.setChecked(mode == "preview")
        for action in actions: action.blockSignals(False)

    def _sidebar_position(self) -> str:
        return "right" if self.splitter.indexOf(self.navigation) > self.splitter.indexOf(self.content_host) else "left"

    def _logical_splitter_sizes(self) -> list[int]:
        sizes = list(self.splitter.sizes())
        if len(sizes) != 2:
            return [int(getattr(self, "_restored_sidebar_width", 260)), 1090]
        if self._sidebar_position() == "right":
            return [sizes[1], sizes[0]]
        return sizes

    def _set_splitter_sidebar_width(self, sidebar_width: int) -> None:
        total = max(1, self.splitter.width() - max(1, self.splitter.handleWidth()))
        content_floor = min(420, max(1, total - SIDEBAR_MINIMUM_WIDTH))
        maximum = max(SIDEBAR_MINIMUM_WIDTH, total - content_floor)
        sidebar = max(SIDEBAR_MINIMUM_WIDTH, min(int(sidebar_width), maximum))
        content = max(1, total - sidebar)
        if self._sidebar_position() == "right":
            self.splitter.setSizes([content, sidebar])
        else:
            self.splitter.setSizes([sidebar, content])
        self._restored_sidebar_width = sidebar

    def _toggle_sidebar_position(self) -> None:
        """Move the existing sidebar to the opposite side and persist the choice."""
        self._set_sidebar_position("left" if self._sidebar_position() == "right" else "right")

    def _set_sidebar_position(self, position: str, *, persist: bool = True) -> None:
        position = "right" if str(position).lower() == "right" else "left"
        current_sizes = self._logical_splitter_sizes()
        sidebar_width = current_sizes[0] if current_sizes and current_sizes[0] > 0 else int(getattr(self, "_restored_sidebar_width", 260))
        target_index = 0 if position == "left" else 1
        if self.splitter.indexOf(self.navigation) != target_index:
            self.splitter.insertWidget(target_index, self.navigation)
        sidebar_index = self.splitter.indexOf(self.navigation)
        content_index = self.splitter.indexOf(self.content_host)
        self.splitter.setStretchFactor(sidebar_index, 0)
        self.splitter.setStretchFactor(content_index, 1)
        self.splitter.setCollapsible(sidebar_index, False)
        self.splitter.setCollapsible(content_index, False)
        for value, action in self.sidebar_position_actions.items():
            action.blockSignals(True)
            action.setChecked(value == position)
            action.blockSignals(False)
        if persist:
            self.config.set("sidebar_position", position, save=True)
        self._set_splitter_sidebar_width(sidebar_width)

    def _set_sidebar_visible(self, visible: bool, *, sync_action: bool = True) -> None:
        visible = bool(visible)
        self.navigation.setVisible(visible)
        if sync_action:
            self.sidebar_action.blockSignals(True)
            self.sidebar_action.setChecked(visible)
            self.sidebar_action.blockSignals(False)

    def _toggle_sidebar(self, checked: bool) -> None:
        self._set_sidebar_visible(bool(checked), sync_action=False)

    def _set_status_visible(self, visible: bool, *, persist: bool, sync_action: bool = True) -> None:
        visible = bool(visible)
        self.statusBar().setVisible(visible)
        for _path, state in tuple(self.states):
            page = state.editor_page
            if isinstance(page, EditorPage):
                page.editor_status.setVisible(visible)
        if sync_action:
            self.status_bar_action.blockSignals(True)
            self.status_bar_action.setChecked(visible)
            self.status_bar_action.blockSignals(False)
        if persist:
            self.config.set("show_status_bar", visible, save=True)

    def _toggle_status_bar(self, checked: bool) -> None:
        self._set_status_visible(bool(checked), persist=True, sync_action=False)

    def _set_file_header_visible(self, visible: bool, *, persist: bool, sync_action: bool = True) -> None:
        visible = bool(visible)
        for _path, state in tuple(self.states):
            page = state.editor_page
            if isinstance(page, EditorPage):
                page.set_header_visible(visible)
        if sync_action:
            self.file_header_action.blockSignals(True)
            self.file_header_action.setChecked(visible)
            self.file_header_action.blockSignals(False)
        if persist:
            self.config.set("show_file_header", visible, save=True)

    def _toggle_file_header(self, checked: bool) -> None:
        self._set_file_header_visible(bool(checked), persist=True, sync_action=False)

    def _toggle_collapsed_mode(self, checked: bool) -> None:
        """Temporarily focus the workspace without overwriting view preferences."""
        checked = bool(checked)
        if checked:
            if self._collapsed_mode_restore is None:
                self._collapsed_mode_restore = {
                    "sidebar": self.navigation.isVisible(),
                    "status": self.statusBar().isVisible(),
                    "header": self.file_header_action.isChecked(),
                    "ribbon_collapsed": bool(getattr(self.shell_ribbon, "_collapsed", False)),
                    "splitter_sizes": self._logical_splitter_sizes(),
                }
            self._set_sidebar_visible(False)
            self._set_status_visible(False, persist=False)
            self._set_file_header_visible(False, persist=False)
            self.shell_ribbon.set_collapsed(True, emit=False)
            return

        restore = self._collapsed_mode_restore or {
            "sidebar": self.sidebar_action.isChecked(),
            "status": bool(self.config.get("show_status_bar", True)),
            "header": bool(self.config.get("show_file_header", True)),
            "ribbon_collapsed": bool(self.config.get("markopad_tabbed_collapsed", False)),
        }
        self._set_sidebar_visible(bool(restore.get("sidebar", True)))
        self._set_status_visible(bool(restore.get("status", True)), persist=False)
        self._set_file_header_visible(bool(restore.get("header", True)), persist=False)
        self.shell_ribbon.set_collapsed(bool(restore.get("ribbon_collapsed", False)), emit=False)
        self._collapsed_mode_restore = None

    def _toggle_fullscreen(self, checked: bool) -> None:
        self.showFullScreen() if checked else self.showNormal()

    def _open_documentation(self) -> None:
        readme = self.runtime_paths.package_root / "docs" / "README.md"
        if not readme.is_file():
            QMessageBox.information(
                self,
                "Documentation — Marko Plus",
                "The bundled Marko Plus Markdown documentation could not be found.",
            )
            return
        self._launch_new_window(readme)

    def _shortcut_catalog(self) -> dict[str, list[tuple[str, QAction | str]]]:
        """Return every assigned shortcut, grouped by the live AppMenu taxonomy.

        AppMenu actions are collected recursively so nested menu commands stay
        synchronized with the Keyboard Shortcuts dialog automatically. Only
        shortcuts that intentionally have no AppMenu QAction are appended
        explicitly below.
        """
        label_overrides = {
            self.rename_file_action: "Rename File or Folder",
        }

        def collect(menu: QMenu) -> list[tuple[str, QAction | str]]:
            entries: list[tuple[str, QAction | str]] = []
            for action in menu.actions():
                submenu = action.menu()
                if submenu is not None:
                    entries.extend(collect(submenu))
                    continue
                if action.shortcut().toString(
                    QKeySequence.SequenceFormat.NativeText
                ).strip():
                    entries.append((label_overrides.get(action, action.text()), action))
            return entries

        catalog: dict[str, list[tuple[str, QAction | str]]] = {
            "File": collect(self.file_menu),
            "Edit": collect(self.edit_menu),
            "Markdown": collect(self.markdown_menu),
            "Insert": collect(self.insert_menu),
            "View": collect(self.view_menu),
            "Settings": collect(self.settings_menu),
            "Help": collect(self.help_menu),
        }

        # These shortcuts are intentionally not represented by AppMenu QActions.
        catalog["File"].extend((
            ("Close Tab / Dashboard", self.close_context_action),
            ("Open Context Tab", self.open_context_tab_action),
        ))
        catalog["Edit"].extend((
            ("Find Next", "F3"),
            ("Find Previous", "Shift+F3"),
            ("Clear Search", "Esc"),
            ("Toggle Overwrite Mode", "Insert"),
        ))
        catalog["View"].extend((
            (("Next Document Tab" if self._tabs_enabled() else "Next Ribbon Tab"), self.next_document_tab_action),
            (("Previous Document Tab" if self._tabs_enabled() else "Previous Ribbon Tab"), self.previous_document_tab_action),
        ))
        catalog["Settings"].extend((
            ("Toggle List/Grid View", self.toggle_dashboard_view_action),
            ("Toggle Sidebar Position", self.toggle_sidebar_position_action),
        ))
        return catalog

    def _show_shortcuts(self) -> None:
        if self.shortcuts_dialog is not None:
            self.shortcuts_dialog.show()
            self.shortcuts_dialog.raise_()
            self.shortcuts_dialog.activateWindow()
            return
        dialog = ShortcutsDialog(self._shortcut_catalog(), self)
        dialog.finished.connect(
            lambda _result: setattr(self, "shortcuts_dialog", None)
        )
        self.shortcuts_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.search.setFocus(Qt.FocusReason.ShortcutFocusReason)


    def _open_github(self) -> None:
        self.desktop_launcher.open_url(GITHUB_URL)

    def _open_issues(self) -> None:
        self.desktop_launcher.open_url(ISSUES_URL)

    def _show_about_dialog(self) -> None:
        if self.about_dialog is not None:
            self.about_dialog.show()
            self.about_dialog.raise_()
            self.about_dialog.activateWindow()
            return

        about_icon = self.package_root / "assets" / "icons" / "markopad-about.png"
        dialog = AboutDialog(
            about_icon if about_icon.is_file() else self.icon_path,
            self.runtime_paths.config_path,
            self,
            desktop_launcher=self.desktop_launcher,
        )
        dialog.finished.connect(
            lambda _result: setattr(self, "about_dialog", None)
        )
        self.about_dialog = dialog
        dialog.show()

    def _queue_navigation_record(self, target: str) -> None:
        if self._navigation_back_in_progress:
            self._navigation_current = target
            self._navigation_pending = None
            return
        self._navigation_pending = target
        if self._navigation_record_scheduled:
            return
        self._navigation_record_scheduled = True
        QTimer.singleShot(0, self._commit_navigation_record)

    def _commit_navigation_record(self) -> None:
        self._navigation_record_scheduled = False
        target = self._navigation_pending
        self._navigation_pending = None
        if not target or target == self._navigation_current:
            return
        if self._navigation_current:
            self._navigation_history.append(self._navigation_current)
            if len(self._navigation_history) > 64:
                del self._navigation_history[:-64]
        self._navigation_current = target

    def _record_dashboard_navigation(self, *_args) -> None:
        self._queue_navigation_record("dashboard")

    def _record_folder_navigation(self, path: str | Path) -> None:
        folder = Path(path).expanduser().resolve(strict=False)
        self._queue_navigation_record(f"folder:{folder}")

    def _record_module_navigation(self, module) -> None:
        path = Path(module.path).expanduser().resolve(strict=False)
        self._queue_navigation_record(f"document:{path}")

    def _navigate_back(self) -> None:
        self._commit_navigation_record()
        while self._navigation_history:
            target = self._navigation_history.pop()
            if target == self._navigation_current:
                continue
            self._navigation_back_in_progress = True
            try:
                if target == "dashboard":
                    if not self.editor_manager.show_dashboard():
                        self._navigation_history.append(target)
                    return
                if target.startswith("folder:"):
                    path = Path(target.split(":", 1)[1]).expanduser().resolve(strict=False)
                    try:
                        path.relative_to(self.library_root)
                    except ValueError:
                        continue
                    if not path.is_dir():
                        continue
                    if self.editor_manager.open_folder(path) is None:
                        self._navigation_history.append(target)
                    return
                if target.startswith("document:"):
                    path = Path(target.split(":", 1)[1]).expanduser().resolve(strict=False)
                    if self.repository.get(path) is None:
                        continue
                    if self.editor_manager.open_module(path) is None:
                        self._navigation_history.append(target)
                    return
            finally:
                self._navigation_back_in_progress = False

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.FocusIn:
            page = self._current_page()
            if page is not None:
                surface = None
                if self._widget_is_within(page.editor, watched):
                    surface = "source"
                elif self._widget_is_within(page.preview, watched):
                    surface = "preview"
                if surface is not None and surface != getattr(page, "_active_text_surface", None):
                    page._active_text_surface = surface
                    self._update_action_states()
        if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
            page = self._current_page()
            if (
                page is not None
                and page.view_mode == "split"
                and watched is page.content_splitter.handle(1)
            ):
                page.reset_content_splitter()
                event.accept()
                return True
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and self.isActiveWindow()
            and event.button() == Qt.MouseButton.BackButton
        ):
            self._navigate_back()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _open_sidebar_module(self, path):
        """Open a sidebar document transactionally and roll back rejected selection."""
        page = self.editor_manager.open_module(path)
        if page is None:
            current = self.editor_manager.current_module
            if current is not None and not current.external:
                self.navigation.select_module(current.path)
        return page

    def _connect_signals(self) -> None:
        self.document_tabs.currentChanged.connect(self._activate_document_tab)
        self.document_tabs.tabCloseRequested.connect(self._close_document_tab)

        self.navigation.dashboard_requested.connect(self.editor_manager.show_dashboard)
        self.navigation.refresh_requested.connect(self._refresh_workspace)
        self.navigation.folder_requested.connect(self.editor_manager.open_folder)
        self.navigation.module_requested.connect(self._open_sidebar_module)
        self.navigation.module_move_requested.connect(self.file_actions.move_module)
        self.navigation.external_files_import_requested.connect(
            self.file_actions.import_files
        )
        self.editor_manager.dashboard_shown.connect(self.navigation.select_dashboard)
        self.editor_manager.dashboard_shown.connect(self._record_dashboard_navigation)
        self.editor_manager.dashboard_shown.connect(self._show_dashboard_navigation_tab)
        self.editor_manager.dashboard_shown.connect(self._update_action_states)
        self.editor_manager.dashboard_shown.connect(self._sync_editor_view_actions)
        self.editor_manager.current_folder_changed.connect(self.navigation.select_folder)
        self.editor_manager.current_folder_changed.connect(self._record_folder_navigation)
        self.editor_manager.current_folder_changed.connect(self._show_folder_navigation_tab)
        self.editor_manager.current_folder_changed.connect(self._update_action_states)
        self.editor_manager.current_module_changed.connect(self._select_document_tab)
        self.editor_manager.current_module_changed.connect(self._record_module_navigation)
        self.editor_manager.current_module_changed.connect(
            lambda module: (
                self.navigation.select_module(module.path)
                if not module.external else False
            )
        )
        self.editor_manager.current_module_changed.connect(self._remember_last_opened_module)
        self.editor_manager.current_module_changed.connect(self._update_action_states)
        self.editor_manager.current_module_changed.connect(lambda _module: self._sync_editor_view_actions())
        self.editor_manager.external_editor_requested.connect(
            self.file_actions.open_external_editor
        )
        self.editor_manager.containing_folder_requested.connect(
            self.file_actions.open_module_folder
        )
        self.editor_manager.rename_requested.connect(self.file_actions.rename_module)
        self.editor_manager.remove_requested.connect(self.file_actions.remove_module)
        self.editor_manager.duplicate_requested.connect(
            self.file_actions.duplicate_module
        )
        self.editor_manager.editor_history_changed.connect(
            self._on_editor_history_changed
        )
        self.editor_manager.editor_preferences_changed.connect(
            self._sync_editor_view_actions
        )
        self.editor_manager.editor_preferences_changed.connect(
            self._update_action_states
        )
        self.editor_manager.folder_open_external_requested.connect(self.file_actions.open_folder_external)
        self.editor_manager.folder_rename_requested.connect(self.file_actions.rename_folder)
        self.editor_manager.folder_remove_requested.connect(self.file_actions.remove_folder)
        self.editor_manager.create_file_requested.connect(self.file_actions.create_file)
        self.editor_manager.create_folder_requested.connect(self._create_folder_from_dashboard)
        self.editor_manager.external_files_import_requested.connect(
            self.file_actions.import_files
        )
        self.editor_manager.editor_files_dropped.connect(self._handle_editor_file_drop)
        self.editor_manager.refresh_requested.connect(self._refresh_workspace)
        self.editor_manager.sort_mode_changed.connect(self._remember_sort_mode)
        self.editor_manager.view_mode_changed.connect(self._remember_view_mode)
        self.editor_manager.view_mode_changed.connect(self._sync_view_actions)
        self.editor_manager.module_path_rebound.connect(self._rebind_document_tab)
        self.editor_manager.module_path_rebound.connect(lambda _old, _new: self.watcher.request_rescan())
        self.editor_manager.module_closed.connect(self._remove_document_tab)
        self.editor_manager.modules_reset.connect(self._reset_document_tabs)
        self.file_actions.folder_renamed.connect(self._on_folder_renamed)
        self.file_actions.folder_removed.connect(lambda _path: self.editor_manager.show_dashboard())
        self.file_actions.module_created.connect(self._queue_created_open)
        self.file_actions.file_policy_changed.connect(self._on_file_policy_changed)
        self.repository.module_added.connect(self._open_pending_if_ready)
        for source in (self.editor_manager, self.file_actions):
            source.status_message.connect(self.show_status)
        self._connect_watcher_signals(self.watcher)
        self.repository.dirty_count_changed.connect(self._update_dirty_status)
        self.repository.module_changed.connect(self._update_document_tab)
        self.repository.module_changed.connect(lambda _module: self._update_action_states())
        self.repository.module_path_changed.connect(self._remember_renamed_module_path)
        self.repository.module_path_changed.connect(self._on_repository_module_path_changed)
        self.repository.module_path_changed.connect(lambda _module, _old: self._update_action_states())

    def _connect_watcher_signals(self, watcher: FilesystemWatcher) -> None:
        watcher.scan_started.connect(self._on_scan_started)
        watcher.folders_discovered.connect(self.navigation.set_disk_folders)
        watcher.scan_details.connect(self._on_scan_details)
        watcher.scan_finished.connect(self._on_scan_finished)
        watcher.scan_failed.connect(self._on_scan_failed)

    def _install_watcher(
        self,
        library_root: Path,
        *,
        start: bool,
        retire_current: bool,
    ) -> None:
        previous = self.watcher
        watcher = FilesystemWatcher(library_root, self.repository, parent=self)
        self.watcher = watcher
        self.file_actions.switch_workspace_root(library_root, watcher)
        self._connect_watcher_signals(watcher)
        if start:
            watcher.start(initial_scan=True)
        if retire_current and previous is not watcher:
            previous.deleteLater()

    def _create_folder_from_dashboard(self, parent: Path) -> None:
        created = self.file_actions.create_folder(parent)
        if created is not None:
            QTimer.singleShot(100, self.navigation.rebuild_from_repository)

    def _queue_created_open(self, path: Path) -> None:
        self._startup_open_requested = True
        preferred = str(self.config.get("markopad_last_editable_view_mode", ""))
        if preferred not in {"source", "split"}:
            current = str(self.config.get("markopad_view_mode", "split"))
            preferred = current if current in {"source", "split"} else "split"
        self._pending_new_file_view_mode = preferred
        self._pending_open_path = Path(path).resolve(strict=False)
        module = self.repository.get(self._pending_open_path)
        if module is not None:
            self._open_pending_if_ready(module)

    def queue_open_path(self, path: str | Path) -> None:
        """Open a path without importing external OS-open documents."""
        self._pending_new_file_view_mode = None
        target = Path(path).expanduser().resolve(strict=False)
        if not target.is_file() or target.suffix.casefold() not in MARKDOWN_EXTENSIONS:
            return
        self._startup_open_requested = True
        try:
            target.relative_to(self.library_root)
        except ValueError:
            self._open_external_path(target)
            return
        self._pending_open_path = target
        module = self.repository.get(target)
        if module is not None:
            self._open_pending_if_ready(module)
        elif not self._startup_scan_pending:
            self.watcher.request_rescan()

    def _open_external_path(self, path: Path) -> None:
        try:
            info = path.stat()
        except OSError:
            return
        module = self.repository.get(path)
        if module is None:
            module = self.repository.add(
                Module(
                    path=path,
                    filename=path.name,
                    display_name=path.stem.replace("-", " ").replace("_", " ").title(),
                    folder=str(path.parent),
                    created=info.st_ctime,
                    modified=info.st_mtime,
                    size=info.st_size,
                    external=True,
                )
            )
        page = self.editor_manager.open_module(module)
        if page is None:
            self.repository.remove(path)
            return
        self._apply_external_verification_mode(page)

    def _apply_external_verification_mode(self, page: EditorPage) -> None:
        """Start an externally launched document in transient Preview + Locked + Focused Mode."""
        page.set_view_mode("preview", persist=False)
        page.set_view_only(True)
        page.scroll_to_top()
        self._sync_editor_view_actions()
        self.collapsed_mode_action.blockSignals(True)
        self.collapsed_mode_action.setChecked(True)
        self.collapsed_mode_action.blockSignals(False)
        self._toggle_collapsed_mode(True)
        self._update_action_states()
        self._update_window_title()

    def _open_pending_if_ready(self, module: Module) -> None:
        if (
            self._pending_open_path is None
            or module.path.resolve(strict=False) != self._pending_open_path
        ):
            return
        self._pending_open_path = None
        preferred = self._pending_new_file_view_mode
        self._pending_new_file_view_mode = None
        page = self.editor_manager.open_module(module)
        if page is not None and preferred in {"source", "split"}:
            page.set_view_mode(preferred, persist=False)

    def _sync_view_actions(self, mode: str) -> None:
        self.list_action.setChecked(mode == "list")
        self.grid_action.setChecked(mode == "grid")

    def _remember_last_opened_module(self, module: Module) -> None:
        if module.external:
            return
        self.project_registry.update_state(
            self.project_registry.active_project_id,
            {"last_opened_file": str(module.path)},
        )

    def _remember_renamed_module_path(
        self,
        module: Module,
        old_path: Path,
    ) -> None:
        if module.external:
            return
        last_path = self.project_registry.active_project.state.get(
            "last_opened_file"
        )
        if not last_path:
            return
        if Path(str(last_path)).resolve(strict=False) != Path(old_path).resolve(
            strict=False
        ):
            return
        self.project_registry.update_state(
            self.project_registry.active_project_id,
            {"last_opened_file": str(module.path)},
        )

    def _on_editor_history_changed(
        self,
        undo_available: bool,
        redo_available: bool,
    ) -> None:
        page = self._current_page()
        if page is None:
            return
        source_active = self._source_interaction_active(page)
        self.undo_action.setEnabled(undo_available and source_active)
        self.redo_action.setEnabled(redo_available and source_active)

    def _update_action_states(self, *_args) -> None:
        page = self._current_page()
        module = self._current_module()
        if page is not None and hasattr(self, "collapsed_mode_action") and self.collapsed_mode_action.isChecked():
            page.editor_status.setVisible(False)
            page.set_header_visible(False)
        editing = page is not None and module is not None
        document_actions = (
            self.save_action, self.save_as_action, self.save_new_action, self.save_dashboard_action, self.save_exit_action, self.undo_action, self.redo_action,
            self.cut_action, self.copy_action, self.paste_action, self.paste_plain_action,
            self.delete_text_action, self.duplicate_line_action, self.delete_line_action, self.comment_action, self.select_all_action,
            self.duplicate_action, self.delete_file_action, self.properties_action,
            self.external_editor_action, self.open_document_folder_action, self.print_action, self.export_pdf_action,
            self.replace_action, self.goto_action, self.view_only_action, self.word_wrap_action,
            self.line_numbers_action, self.display_font_action, self.preview_font_action, self.source_only_action, self.split_action,
            self.preview_only_action, self.zoom_in_action, self.zoom_out_action, self.zoom_reset_action,
            self.bold_action, self.italic_action, self.strike_action, self.quote_action, self.bullet_action,
            self.number_action, self.task_action, self.indent_action, self.outdent_action, self.inline_code_action,
            self.code_fence_action, self.heading_tabbed_action, self.link_action, self.edit_link_action,
            self.remove_link_action, self.rule_action, self.image_action, self.table_action, self.date_time_action,
            self.date_action, self.time_action, self.symbol_action,
        )
        for action in document_actions: action.setEnabled(editing)
        for action in self.heading_actions: action.setEnabled(editing)
        folder = self._selected_folder()
        self.rename_file_action.setEnabled(
            editing or (folder is not None and folder != self.library_root)
        )
        self._sync_editor_view_actions()
        if page:
            view_only = page.view_only
            source_active = self._source_interaction_active(page)
            self.undo_action.setEnabled(page.editor.document().isUndoAvailable() and not view_only and source_active)
            self.redo_action.setEnabled(page.editor.document().isRedoAvailable() and not view_only and source_active)
            mutable = not view_only and source_active
            for action in (self.cut_action, self.paste_action, self.paste_plain_action, self.delete_text_action, self.duplicate_line_action, self.delete_line_action, self.comment_action, self.bold_action, self.italic_action, self.strike_action, self.quote_action, self.bullet_action, self.number_action, self.task_action, self.indent_action, self.outdent_action, self.inline_code_action, self.code_fence_action, self.link_action, self.edit_link_action, self.remove_link_action, self.rule_action, self.image_action, self.table_action, self.date_time_action, self.date_action, self.time_action, self.symbol_action):
                action.setEnabled(mutable)
            for action in self.heading_actions: action.setEnabled(mutable)
            self.heading_tabbed_action.setEnabled(mutable)
        self._update_window_title()

    def _on_folder_renamed(self, old_path: Path, new_path: Path) -> None:
        self.show_status(f"Folder renamed to {new_path.name}")
        QTimer.singleShot(600, lambda: self.editor_manager.open_folder(new_path))

    def _restore_window_state(self) -> None:
        width = self.config.get_int("window_width", 1350, minimum=900)
        height = self.config.get_int("window_height", 850, minimum=600)
        self.resize(width, height)
        sizes = self.config.get_int_list(
            "splitter_sizes",
            [260, 1090],
            length=2,
        )
        self._restored_sidebar_width = (
            int(sizes[0]) if sizes and int(sizes[0]) > 0 else 260
        )
        self._set_sidebar_position(
            str(self.config.get("sidebar_position", "left")), persist=False
        )
        # Restore after Qt has a real central-widget geometry. This avoids
        # stale total widths producing a jumpy or apparently stuck handle.
        QTimer.singleShot(0, self._restore_splitter_geometry)

        self._apply_active_project_state()
        if bool(self.config.get("window_maximized", False)):
            self.showMaximized()

    def _apply_active_project_state(self) -> None:
        self._update_window_title()
        state = self.project_registry.active_project.state
        folders = state.get("collapsed_folders", [])
        if isinstance(folders, list):
            self.navigation.restore_collapsed_folders(folders)
        sort_mode = str(state.get("dashboard_sort", "modified"))
        search_text = str(state.get("dashboard_search", ""))
        view_mode = str(state.get("dashboard_view", "list"))
        self.editor_manager.set_sort_mode(sort_mode)
        self.editor_manager.set_search_text(search_text)
        self.editor_manager.set_view_mode(view_mode)
        self._sync_view_actions(view_mode)

    def _update_window_title(self) -> None:
        workspace = self.project_registry.active_project.name.strip()
        module = self.editor_manager.current_module
        if module is not None:
            scope = "External" if module.external else workspace
            page = self._current_page()
            lock_suffix = " — Locked Mode" if page is not None and page.view_only else ""
            dirty_prefix = "*" if module.dirty else ""
            self.setWindowTitle(
                f"{dirty_prefix}{module.filename} — {scope} — {APP_NAME}{lock_suffix}"
            )
        else:
            self.setWindowTitle(f"{workspace} — {APP_NAME}")

    def _save_active_project_state(self, *, save: bool) -> None:
        values: dict[str, object] = {
            "collapsed_folders": sorted(self.navigation.collapsed_folders()),
            "dashboard_sort": self.editor_manager.dashboard._sort_mode,
            "dashboard_search": self.editor_manager.dashboard.search_input.text(),
            "dashboard_view": self.editor_manager.dashboard.view_mode(),
            "last_opened_folder": (
                str(self.editor_manager.current_folder)
                if self.editor_manager.current_folder is not None
                else None
            ),
        }
        # Last File means the most recently opened document, even if the user
        # returns to Dashboard before quitting. Do not erase that history merely
        # because no editor page is current at shutdown or Workspace switch.
        module = self.editor_manager.current_module
        if module is not None and not module.external:
            values["last_opened_file"] = str(module.path)
        self.project_registry.update_state(
            self.project_registry.active_project_id,
            values,
            save=save,
        )

    def _restore_splitter_geometry(self) -> None:
        """Restore sidebar width against the live splitter geometry."""
        self._set_splitter_sidebar_width(
            int(getattr(self, "_restored_sidebar_width", 260))
        )

    def _refresh_workspace(self) -> None:
        """Run one background scan, then repair navigation from its result."""
        self._repair_navigation_after_scan = True
        self.show_status("Refreshing workspace in background…")
        self.watcher.request_rescan()

    def _on_scan_started(self) -> None:
        message = (
            "Refreshing your workspace…"
            if self._repair_navigation_after_scan
            else "Preparing your workspace…"
        )
        self.editor_manager.dashboard.set_loading(True, message)
        self.navigation.set_loading(True, "Building folder tree…")
        self.show_status("Scanning workspace in background…")

    def _on_scan_details(self, entries: int, seconds: float) -> None:
        detail = f"Scanned {entries:,} filesystem entries in {seconds:.1f}s."
        self.editor_manager.dashboard.set_loading_detail(detail)
        self.navigation.set_loading_detail(
            f"{sum(1 for module in self.repository if not module.external):,} Markdown files found"
        )
        self.show_status(detail)

    def _on_scan_finished(self, count: int) -> None:
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        project_name = self.project_registry.active_project.name
        if self._repair_navigation_after_scan:
            self._repair_navigation_after_scan = False
            self.navigation.rebuild_from_repository()
            self.show_status(
                f"Refreshed {count} Markdown file(s) in {project_name}."
            )
        else:
            self.show_status(
                f"Loaded {count} Markdown file(s) in {project_name}."
            )
        if self._pending_open_path is not None:
            module = self.repository.get(self._pending_open_path)
            if module is not None:
                self._open_pending_if_ready(module)
        if not self._startup_scan_pending:
            return
        self._startup_scan_pending = False
        if self._startup_open_requested:
            return
        if self.app_launch_screen != "last_file":
            self.editor_manager.show_dashboard()
            return
        project_state = self.project_registry.active_project.state
        last_path = project_state.get("last_opened_file")
        if last_path:
            module = self.repository.get(last_path)
            if module is not None:
                self.editor_manager.open_module(module)
                return
        self.editor_manager.show_dashboard()

    def _on_scan_failed(self, message: str) -> None:
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        self.show_status(f"Workspace scan failed: {message}")
        QMessageBox.warning(self, "Workspace Scan Failed", message)

    def _remember_sort_mode(self, mode: str) -> None:
        self.config.set("dashboard_sort", mode)
        self.project_registry.update_state(
            self.project_registry.active_project_id,
            {"dashboard_sort": mode},
        )

    def _remember_view_mode(self, mode: str) -> None:
        self.config.set("dashboard_view", mode)
        self.project_registry.update_state(
            self.project_registry.active_project_id,
            {"dashboard_view": mode},
        )

    def _update_dirty_status(self, count: int) -> None:
        if count:
            self.show_status(f"{count} Markdown file has unsaved changes." if count == 1 else f"{count} Markdown files have unsaved changes.")

    def _show_launch_error(self, message: str) -> None:
        QMessageBox.warning(self, "Could Not Open", message)

    def show_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _write_shutdown_timing(self, timings: dict[str, float]) -> None:
        """Write shutdown diagnostics only when explicitly requested."""
        enabled = os.environ.get(SHUTDOWN_PROFILE_ENV, "").casefold()
        if enabled not in {"1", "true", "yes", "on"}:
            return

        report_path = self.runtime_paths.config_root / "shutdown-timing.jsonl"
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "documents": len(self.repository),
            "timings_ms": {
                key: round(value * 1000.0, 2)
                for key, value in timings.items()
            },
        }
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with report_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        except OSError:
            pass

        printable = " · ".join(
            f"{key}={value * 1000.0:.1f} ms"
            for key, value in timings.items()
        )
        print(f"Marko Plus shutdown: {printable}", flush=True)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._closing:
            event.accept()
            return

        started = time.perf_counter()
        timings: dict[str, float] = {}

        unsaved_started = time.perf_counter()
        if not self.editor_manager.can_close_application():
            timings["unsaved_prompt"] = time.perf_counter() - unsaved_started
            event.ignore()
            return
        timings["unsaved_prompt"] = time.perf_counter() - unsaved_started

        self._closing = True

        closing_dialog = ClosingDialog(self)
        closing_dialog.start()
        QApplication.processEvents()

        def stage(detail: str) -> None:
            closing_dialog.set_stage(detail)
            QApplication.processEvents()

        stage("Saving your preferences…")
        config_started = time.perf_counter()
        self._save_active_project_state(save=True)
        self.config.update(
            {
                "window_width": self.width(),
                "window_height": self.height(),
                "window_maximized": self.isMaximized(),
                "splitter_sizes": (
                    list(
                        self._collapsed_mode_restore.get(
                            "splitter_sizes", self._logical_splitter_sizes()
                        )
                    )
                    if self._collapsed_mode_restore is not None
                    else self._logical_splitter_sizes()
                ),
                "collapsed_folders": sorted(
                    self.navigation.collapsed_folders()
                ),
                "dashboard_sort": self.editor_manager.dashboard._sort_mode,
                "dashboard_search": (
                    self.editor_manager.dashboard.search_input.text()
                ),
                "dashboard_view": (
                    self.editor_manager.dashboard.view_mode()
                ),
                # Compatibility mirror for the application-level fallback.
                # The per-Workspace value preserved above is authoritative.
                "last_opened_file": self.project_registry.active_project.state.get(
                    "last_opened_file"
                ),
                "last_opened_folder": (
                    str(self.editor_manager.current_folder)
                    if self.editor_manager.current_folder is not None
                    else None
                ),
            },
            save=True,
        )
        timings["save_config"] = time.perf_counter() - config_started

        # Hide the large main hierarchy while retaining the small dialog.
        self.editor_manager.dashboard.set_loading(False)
        self.navigation.set_loading(False)
        self.centralWidget().hide()
        self.menuBar().hide()
        self.statusBar().hide()
        closing_dialog.adjustSize()
        closing_dialog.move(
            self.frameGeometry().center()
            - closing_dialog.rect().center()
        )
        QApplication.processEvents()

        stage("Stopping the workspace scanner…")
        scanner_started = time.perf_counter()
        scan_stopped = self.watcher.stop(
            timeout_ms=2000,
            pump_events=QApplication.processEvents,
        )
        timings["stop_scanner"] = time.perf_counter() - scanner_started

        if not scan_stopped:
            self._closing = False
            closing_dialog.close()
            self.centralWidget().show()
            self.menuBar().show()
            self.statusBar().show()
            self.show_status("Could not cancel the workspace scan yet.")
            event.ignore()
            return

        timings["total_before_exit"] = time.perf_counter() - started
        self._write_shutdown_timing(timings)

        stage("Closing Marko Plus…")
        event.accept()
        QApplication.processEvents()

        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(0)
