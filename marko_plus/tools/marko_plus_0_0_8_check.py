#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.8 shell-parity convergence."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
nav = (ROOT / "widgets/navigation.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors: list[str] = []


def require(fragment: str, text: str, message: str) -> None:
    if fragment not in text:
        errors.append(message)


require('APP_VERSION = "0.0.8"', init, "0.0.8 package identity missing")

# Item 6: exact shared View ordering, both AppMenu and Marko command toolbar.
menu_order = '''        view.addAction(self.fullscreen_action)\n        view.addAction(self.status_bar_action)\n        view.addAction(self.sidebar_action)'''
require(menu_order, main, "AppMenu View order is not Full Screen -> Show Status -> Show Sidebar")
require('"View": [[self.fullscreen_action, self.status_bar_action, self.sidebar_action],', main,
        "command-toolbar View order is not Full Screen -> Show Status -> Show Sidebar")

# Item 5: Rico exposure, Marko refresh implementation/status semantics retained.
require('self.refresh_workspace_action = self._command("Refresh Workspace", self._refresh_workspace, "Ctrl+Shift+F5")', main,
        "Refresh Workspace shortcut is not Ctrl+Shift+F5")
require('refresh_requested = pyqtSignal()', nav, "sidebar refresh signal missing")
require('QPushButton("Refresh Workspace")', nav, "sidebar Refresh Workspace button missing")
require('self.refresh_button.setToolTip("Refresh Workspace (Ctrl+Shift+F5)")', nav,
        "sidebar Refresh Workspace tooltip mismatch")
require('self.refresh_button.clicked.connect(self.refresh_requested.emit)', nav, "sidebar refresh routing missing")
require('self.navigation.refresh_requested.connect(self._refresh_workspace)', main, "sidebar refresh does not use canonical refresh path")
require('self.refresh_button.setEnabled(not loading)', nav, "sidebar refresh is not disabled during loading")
require('self.show_status("Refreshing workspace in background…")', main, "Marko refresh-start feedback changed")
require('f"Refreshed {count} Markdown file(s) in {project_name}."', main, "Marko refresh-complete feedback changed")

# Item 15: explicit native/global AppMenu contract.
require('bar.setNativeMenuBar(True)', main, "native/global AppMenu contract is not explicit")
if 'setNativeMenuBar(False)' in main:
    errors.append("native/global AppMenu was explicitly disabled")

# Item 16: Rico New Window placement/shortcut; Line Numbers collision resolved exactly as approved.
require('self.new_window_action = self._command("New Window…", self._new_window, "Ctrl+Alt+Shift+N")', main,
        "New Window shortcut mismatch")
require('self.line_numbers_action = self._command("Line Numbers", self._toggle_line_numbers, "Ctrl+Alt+Shift+L", checkable=True)', main,
        "Line Numbers shortcut mismatch")
require('for action in (self.new_action, self.new_folder_action): file_menu.addAction(action)', main,
        "New Window still appears in the top-level File create row")
workspace_tail = '''        self.workspace_menu.addSeparator()\n        self.workspace_menu.addAction(self.manage_workspaces_action)\n        self.workspace_menu.addAction(self.new_window_action)'''
require(workspace_tail, main, "New Window is not directly after Manage Workspaces in Workspace(s)")
if main.count('"Ctrl+Alt+Shift+N"') != 1:
    errors.append("Ctrl+Alt+Shift+N is not exclusive to New Window")
if main.count('"Ctrl+Alt+Shift+L"') != 1:
    errors.append("Ctrl+Alt+Shift+L is not exclusive to Line Numbers")

# Explicit scope exclusions for this convergence release.
for forbidden, label in (
    ('document_tabs', 'Document Tabs'),
    ('_toggle_collapsed_mode', 'Focused Mode'),
    ('file_header_action', 'File Header'),
):
    if forbidden in main:
        errors.append(f"0.0.8 unexpectedly introduced {label}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.8 shell-parity convergence check passed.")
