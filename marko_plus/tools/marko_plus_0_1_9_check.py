#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.9 polish/icon completion."""
from __future__ import annotations

import ast
import hashlib
import struct
from collections import defaultdict
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
ERRORS: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None
    return struct.unpack(">II", data[16:24])


main = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
shell = (PACKAGE / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
desktop = (PACKAGE / "packaging/appimage/marko-plus.desktop").read_text(encoding="utf-8")
metainfo = (PACKAGE / "packaging/appimage/io.github.brunonlinespace.marko_plus.metainfo.xml").read_text(encoding="utf-8")

# Version + identity continuity.
require('APP_VERSION = "0.1.9"' in init, "0.1.9 package identity missing")
require('APP_REVISION = "0.1.9"' in constants, "0.1.9 revision identity missing")
require('DESKTOP_ID = "marko-plus"' in init, "0.1.8 runtime desktop identity regressed")
require('APP_RUNTIME_DESKTOP_ID = DESKTOP_ID' in constants, "runtime desktop alias regressed")
require('StartupWMClass=marko-plus' in desktop, "desktop StartupWMClass regressed")
require('X-AppImage-Version=0.1.9' in desktop, "desktop release version mismatch")
require('<id>io.github.brunonlinespace.marko_plus</id>' in metainfo, "reverse-DNS AppStream ID regressed")
require('<release version="0.1.9" date="2026-10-04">' in metainfo, "AppStream current release mismatch")

# Exact label + shortcut contract.
require('self.manage_workspaces_action = self._command("Open / Manage Workspaces...", self._show_projects, "Ctrl+O")' in main,
        "Open / Manage Workspaces label/shortcut mismatch")
require('self.display_font_action = self._command("Source Font…", self._choose_display_font, "Ctrl+Shift+[")' in main,
        "Source Font Ctrl+Shift+[ shortcut missing")
require('self.preview_font_action = self._command("Preview Font…", self._choose_preview_font, "Ctrl+Shift+]")' in main,
        "Preview Font Ctrl+Shift+] shortcut missing")

# Context-sensitive Ctrl+F, and Find must not be gated to editor-only state.
for fragment in (
    'def _focus_find(self) -> None:',
    'search = getattr(self.stack.currentWidget(), "search_input", None)',
    'search.setFocus(Qt.FocusReason.ShortcutFocusReason)',
    'search.selectAll()',
):
    require(fragment in main, f"context-sensitive Ctrl+F fragment missing: {fragment}")
document_gate = main[main.index('document_actions = ('):main.index('for action in document_actions: action.setEnabled(editing)')]
require('self.find_action' not in document_gate, "Find remains editor-only and cannot focus Dashboard search")

# Menu ordering. These source blocks are intentionally explicit to protect the approved taxonomy.
markdown_block = '''        markdown = bar.addMenu("&Markdown")
        for action in (self.bold_action, self.italic_action, self.strike_action, self.quote_action): markdown.addAction(action)
        markdown.addSeparator()
        for action in (self.bullet_action, self.number_action, self.task_action): markdown.addAction(action)
        markdown.addSeparator(); markdown.addAction(self.indent_action); markdown.addAction(self.outdent_action)
        markdown.addSeparator(); markdown.addAction(self.inline_code_action); markdown.addAction(self.code_fence_action)
        markdown.addSeparator()
        headings = markdown.addMenu("Heading")'''
require(markdown_block in main, "Markdown order does not place Heading last after a separator")

insert_block = '''        insert = bar.addMenu("&Insert")
        insert.addAction(self.image_action)
        links = insert.addMenu("Link"); links.addAction(self.link_action); links.addAction(self.edit_link_action); links.addSeparator(); links.addAction(self.remove_link_action)
        insert.addSeparator()
        insert.addAction(self.table_action)
        insert.addSeparator()
        for action in (self.date_time_action, self.date_action, self.time_action): insert.addAction(action)
        insert.addSeparator()
        insert.addAction(self.rule_action); insert.addAction(self.symbol_action)'''
require(insert_block in main, "Insert menu order/separators differ from 0.1.9 contract")

view_block = '''        view.addAction(self.fullscreen_action)
        view.addAction(self.status_bar_action)
        view.addAction(self.sidebar_action)
        view.addSeparator()
        view.addAction(self.word_wrap_action)
        view.addAction(self.line_numbers_action)
        view.addAction(self.editor_canvas_theme_action)
        view.addSeparator()
        view.addAction(self.view_only_action)
        layout_menu = view.addMenu("Editor Layout")'''
require(view_block in main, "View primary order differs from 0.1.9 contract")
require('''        layout_menu.addAction(self.preview_only_action)
        view.addSeparator()
        zoom = view.addMenu("Editor Zoom")''' in main,
        "View separator before Editor Zoom missing")
require('theme_menu.addAction(self.theme_light_action)\n        theme_menu.addAction(self.theme_dark_action)\n        theme_menu.addAction(self.theme_system_action)' in main,
        "App Theme order is not Light -> Dark -> System")

# Supplied icon pack + existing icon reclaim.
new_icons = (
    "new-folder", "manage-workspaces", "save-new", "save-dashboard",
    "file-header", "focused-mode", "edit-link", "remove-link",
)
for theme in ("light", "dark"):
    for name in new_icons:
        path = PACKAGE / "assets/toolbar-icons" / theme / f"{name}.png"
        require(path.is_file(), f"missing supplied {theme} icon: {name}.png")
        if path.is_file():
            require(png_size(path) == (64, 64), f"{theme}/{name}.png is not 64x64 PNG")

mapping_fragments = (
    '"new_window_action":"new-window"',
    '"new_folder_action":"new-folder"',
    '"manage_workspaces_action":"manage-workspaces"',
    '"previous_file_action":"previous"',
    '"next_file_action":"next"',
    '"save_as_action":"save-as"',
    '"save_new_action":"save-new"',
    '"save_dashboard_action":"save-dashboard"',
    '"save_exit_action":"save-exit"',
    '"edit_link_action":"edit-link"',
    '"remove_link_action":"remove-link"',
    '"file_header_action":"file-header"',
    '"collapsed_mode_action":"focused-mode"',
)
for fragment in mapping_fragments:
    require(fragment in main, f"icon mapping missing: {fragment}")
for obsolete in (
    '"new_folder_action":"new-window"',
    '"manage_workspaces_action":"open-folder"',
    '"save_new_action":"new"',
    '"save_dashboard_action":"save-exit"',
    '"save_exit_action":"exit"',
    '"edit_link_action":"insert-link"',
    '"remove_link_action":"delete-text"',
):
    require(obsolete not in main, f"obsolete borrowed icon mapping remains: {obsolete}")

# ShellRibbon/control-tab completion and order.
for fragment in (
    '[("new_action"), ("new_folder_action"), ("new_window_action")]',
    '[("dashboard_action"), ("manage_workspaces_action"), ("previous_file_action"), ("next_file_action")]',
    '[("save_action"), ("save_as_action"), ("save_new_action"), ("save_dashboard_action"), ("save_exit_action")]',
    '[("heading_tabbed_action")]',
    '[("image_action"), ("link_action"), ("edit_link_action"), ("remove_link_action")]',
    '[("word_wrap_action"), ("line_numbers_action"), ("editor_canvas_theme_action"), ("view_only_action"), ("file_header_action")]',
    '[("collapsed_mode_action")]',
    '[("theme_light_action"), ("theme_dark_action"), ("theme_system_action")]',
):
    require(fragment in shell, f"ShellRibbon 0.1.9 control missing/order mismatch: {fragment}")
require(shell.index('[("bullet_action"), ("number_action"), ("task_action"), ("quote_action"), ("indent_action"), ("outdent_action")]') < shell.index('[("heading_tabbed_action")]'),
        "Heading control is not last in Home formatting groups")

# Static shortcut collision audit for explicit string shortcuts on MainWindow QActions.
tree = ast.parse(main)
shortcuts: dict[str, list[str]] = defaultdict(list)
for node in ast.walk(tree):
    if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
        continue
    call = node.value
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "_command" or len(call.args) < 3:
        continue
    action_name = "<dynamic>"
    for target in node.targets:
        if isinstance(target, ast.Attribute):
            action_name = target.attr
            break
    for child in ast.walk(call.args[2]):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value:
            shortcuts[child.value].append(action_name)
for sequence, owners in shortcuts.items():
    if len(owners) > 1:
        ERRORS.append(f"explicit shortcut collision: {sequence} -> {owners}")

# Static editor shortcut catalog remains current.
editor_page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
code_editor = (PACKAGE / "widgets/code_editor.py").read_text(encoding="utf-8")
for fragment in ('shortcut="F3"', 'shortcut="Shift+F3"', 'shortcut="Esc"'):
    require(fragment in editor_page, f"editor search shortcut implementation missing: {fragment}")
for label in ('("Find Next", "F3")', '("Find Previous", "Shift+F3")', '("Clear Search", "Esc")', '("Toggle Comment", "Ctrl+/")', '("Toggle Overwrite Mode", "Insert")'):
    require(label in main, f"shortcut catalog stale/missing: {label}")
require('Qt.Key.Key_Slash' in code_editor and 'Qt.Key.Key_Insert' in code_editor,
        "source-editor static shortcut implementation changed unexpectedly")

# Strict exclusions for this polish release.
require('QScroller' not in (PACKAGE / "widgets/dashboard.py").read_text(encoding="utf-8"),
        "Dashboard touch/kinetic QScroller leaked into 0.1.9")
require('QScroller' not in shell, "Ribbon touch/kinetic QScroller leaked into 0.1.9")
require('%F' not in desktop and 'MimeType=' not in desktop,
        "external-session desktop routing leaked into 0.1.9")
require('external=True' not in (PACKAGE / "models/module_repository.py").read_text(encoding="utf-8"),
        "transient external-session repository policy leaked into 0.1.9")

# Critical non-polish implementation files must remain byte-for-byte 0.1.8.
protected = {
    'controllers/editor_manager.py': 'f150a8a8c154392ec00c91faafcdad8b952aa75f8466fc1cee279c8ffb6bd2a5',
    'controllers/file_actions.py': 'd2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334',
    'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
    'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1',
    'widgets/editor_page.py': 'da232f24b51bbe49df97e6157de561feac30f0c663c1dc19fe5c85bec227113e',
    'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d',
    'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397',
    'widgets/navigation.py': '0c628201fdbce6bf37dca693eee6a373849ce5a30dfc8203aabad410827e8368',
}
for relative, expected in protected.items():
    path = PACKAGE / relative
    require(path.is_file(), f"protected 0.1.8 file missing: {relative}")
    if path.is_file():
        require(sha256(path) == expected, f"protected non-polish file changed: {relative}")

if ERRORS:
    for error in ERRORS:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.9 polish/icon/control-tab/shortcut check passed.")
