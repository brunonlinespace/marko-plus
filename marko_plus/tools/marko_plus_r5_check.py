#!/usr/bin/env python3
"""Static shell contract check for Marko Plus 0.0.1-r5."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
page = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
navigation = (ROOT / "widgets/navigation.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

def ordered(text, fragments, message):
    pos = -1
    for fragment in fragments:
        nxt = text.find(fragment, pos + 1)
        if nxt < 0:
            errors.append(f"{message}: missing {fragment!r}")
            return
        pos = nxt

require('<h3>My Workspace</h3>', navigation, "My Workspace sidebar label missing")
require('self.new_window_action = self._command("New Window…", self._new_window)', main, "New Window should have no shortcut")
require('self.new_folder_action = self._command("New Folder…", self._new_folder, "Ctrl+Shift+N")', main, "New Folder Ctrl+Shift+N contract missing")
if 'self.new_window_action = self._command("New Window…", self._new_window, "Ctrl+Shift+N")' in main:
    errors.append("New Window still owns Ctrl+Shift+N")
require('self.save_as_action = self._command("Save As…", self._save_current_as)', main, "Save As action missing")
require('self.previous_file_action = self._command("Previous File",', main, "Previous File label missing")
require('self.next_file_action = self._command("Next File",', main, "Next File label missing")
require('self.workspace_menu.addAction(self.refresh_workspace_action)', main, "Refresh Workspace missing from submenu")
require('self.view_only_action = self._command("Lock Editor",', main, "shell Lock Editor label missing")
require('"Disable Lock Editor? — Marko Plus"', page, "disable-lock dialog missing")
require('"Keep Locked"', page, "Keep Locked button missing")
require('"Continue"', page, "Continue button missing")
require('"Lock Editor — Marko Plus"', page, "blocked-edit dialog missing")
require('"Editing is disabled while Lock Editor is enabled."', page, "blocked-edit status missing")
require('def save_copy_to(self, target: str | Path) -> bool:', page, "Save As write path missing")

file_start = main.index('file_menu = bar.addMenu("&File")')
file_end = main.index('edit = bar.addMenu("&Edit")')
file_block = main[file_start:file_end]
ordered(file_block, [
    'self.new_action', 'self.new_window_action', 'self.new_folder_action',
    'self.dashboard_action', 'self.previous_file_action', 'self.next_file_action',
    'self.workspace_menu', 'self.save_action', 'self.save_as_action',
], "File menu order")
ordered(file_block, [
    'more.addAction(self.external_editor_action)', 'more.addSeparator()',
    'self.rename_file_action', 'self.delete_file_action', 'self.duplicate_action',
    'more.addSeparator()', 'more.addAction(self.open_document_folder_action)',
], "More Actions order")

view_start = main.index('view = bar.addMenu("&View")')
view_end = main.index('settings = bar.addMenu("&Settings")')
view_block = main[view_start:view_end]
ordered(view_block, [
    'view.addAction(self.fullscreen_action)',
    'view.addAction(self.sidebar_action)',
    'view.addAction(self.status_bar_action)',
    'view.addSeparator()',
    'view.addAction(self.word_wrap_action)',
    'view.addAction(self.line_numbers_action)',
    'view.addAction(self.editor_canvas_theme_action)',
    'view.addSeparator()',
    'view.addAction(self.view_only_action)',
    'zoom = view.addMenu("Editor Zoom")',
    'layout_menu = view.addMenu("Editor Layout")',
    'more_settings = view.addMenu("Editor Miscellaneous")',
], "View menu order")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.1-r5 shell contract check passed.")
