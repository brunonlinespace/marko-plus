#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.8 Markopad Find/Replace convergence gate."""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def src(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")


def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


page = src("widgets/editor_page.py")
main = src("widgets/main_window.py")
source_editor = src("widgets/markopad_source_editor.py")
init = src("__init__.py")
constants = src("app_constants.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.3.8"' in init, "0.3.8 package identity missing")
req('APP_REVISION = "0.3.8"' in constants, "0.3.8 revision identity missing")
req('Current release: **0.3.8**' in readme, "root README current release is stale")

# Markopad is authoritative for visible Find/Replace interaction: one two-row
# panel at the bottom of the editor, live search, Enter=Next, Esc=Close.
for fragment in (
    'self.search_frame = QFrame(self)',
    'search_grid = QGridLayout(self.search_frame)',
    'self.find_input.setPlaceholderText("Find")',
    'self.replace_input.setPlaceholderText("Replace")',
    'self.search_case_checkbox = QCheckBox("Match case", self.search_frame)',
    'self.search_previous_button = QPushButton("Previous", self.search_frame)',
    'self.search_next_button = QPushButton("Next", self.search_frame)',
    'replace_button = QPushButton("Replace", self.search_frame)',
    'replace_all_button = QPushButton("Replace All", self.search_frame)',
    'close_search = QPushButton("Close", self.search_frame)',
    'search_grid.addWidget(self.find_input, 0, 0, 1, 3)',
    'search_grid.addWidget(self.replace_input, 1, 0, 1, 3)',
    'self.find_input.textChanged.connect(self.refresh_search)',
    'self.search_case_checkbox.toggled.connect(self.refresh_search)',
    'self.find_input.returnPressed.connect(self.find_next)',
    'close_search.clicked.connect(self.hide_find_panel)',
    'self.search_frame.hide()',
    'root.addWidget(self.content_splitter, 1)',
    'root.addWidget(self.search_frame)',
    'root.addWidget(self.editor_status)',
):
    req(fragment in page, f"Markopad Find/Replace panel contract missing: {fragment}")
req(page.index('root.addWidget(self.content_splitter, 1)') < page.index('root.addWidget(self.search_frame)') < page.index('root.addWidget(self.editor_status)'),
    "Find/Replace panel is not at the bottom of the editor above its status bar")
for fragment in (
    'self.dismiss_find_action = QAction("Close Find/Replace", self)',
    'self.dismiss_find_action.setShortcut(QKeySequence("Esc"))',
    'self.dismiss_find_action.triggered.connect(self.hide_find_panel)',
    'page.show_find_panel(False)',
    'page.show_find_panel(True)',
):
    req(fragment in page or fragment in main, f"Find/Replace shortcut/focus contract missing: {fragment}")
req('dialog.setWindowTitle("Find and Replace' not in page, "modeless Find/Replace dialog returned")

# Markopad search presentation: every hit is gold and the current hit is the
# editor's real selected range. No active/passive cyan/gold rendering layer.
req('selection.format.setBackground(QColor("#C9A227"))' in page, "Markopad gold search highlight missing")
req('selection.format.setForeground(QColor("#101010"))' in page, "Markopad search foreground missing")
for forbidden in ('passive_bg', 'active_bg = QColor("#FFD54F")', 'active_bg if index'):
    req(forbidden not in page, f"retired active/passive search rendering remains: {forbidden}")
jump = re.search(r"def _jump_search\(self, step: int\).*?return True", page, re.S)
req(jump is not None, "_jump_search missing")
if jump:
    body = jump.group(0)
    req('cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)' in body, "active Find hit is not a real text selection")
    req('self.editor.setTextCursor(cursor)' in body, "active Find hit is not applied to the editor cursor")
    req('self.editor.setFocus' not in body, "Find navigation improperly steals focus from the Find panel")
    req('0 if step > 0 else len(self._search_matches) - 1' in body, "corrected initial Previous/Next wrap behavior missing")
req('self.MAX_SEARCH_MATCHES = 10_000' in page or 'MAX_SEARCH_MATCHES = 10_000' in page, "10,000-match safety bound missing")
req('self._search_refresh_suspended = True' in page and 'self._search_refresh_suspended = False' in page,
    "Replace All search-refresh suspension missing")
req('beginEditBlock()' in page and 'endEditBlock()' in page, "one-block Replace All contract missing")
req('self.editor.MAX_DOCUMENT_CHARACTERS' in page or 'MAX_DOCUMENT_CHARACTERS' in page, "Marko document-size replacement guard missing")
req('if self.view_only:' in page or 'if not self._editing_available' in page or 'self.editor.isReadOnly()' in page,
    "Locked/View-only replace protection missing")
# Existing compositor behavior that made original Markopad safe must remain:
# current-line highlighting is suppressed whenever the real cursor is selected.
req('if not cursor.hasSelection()' in source_editor, "source-editor selection/current-line separation changed")

# Exact requested settings wording.
for fragment in (
    'setToolTip("Theme — Light")', 'setToolTip("Theme — Dark")', 'setToolTip("Theme — System")',
    'setToolTip("Dashboard — List View")', 'setToolTip("Dashboard — Grid View")',
    'setToolTip("Sidebar — Dock to Left")', 'setToolTip("Sidebar — Dock to Right")',
    'setToolTip("Launch Screen — Dashboard")', 'setToolTip("Launch Screen — Last File")',
    'setToolTip("File Launch — Tabs Enabled")', 'setToolTip("File Launch — Tabs Disabled")',
    '(("left", "Dock to Left"), ("right", "Dock to Right"))',
    'f"File Launch — Tabs {\'Enabled\' if enabled else \'Disabled\'}"',
):
    req(fragment in main, f"settings tooltip/radial convergence missing: {fragment}")

# Marko's established 40-symbol curation must remain exact.
tree = ast.parse(page)
symbols_value = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "show_symbols_dialog":
        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "symbols" for t in child.targets):
                try:
                    symbols_value = ast.literal_eval(child.value)
                except Exception:
                    symbols_value = None
                break
        break
expected_symbols = (
    "©", "®", "™", "°", "•", "·", "—", "–", "…", "→", "←", "↑", "↓", "✓", "✗", "§",
    "£", "€", "$", "¥", "¢", "±", "×", "÷", "≠", "≤", "≥", "≈", "∞", "µ", "¶", "№",
    "★", "☆", "♥", "♦", "♣", "♠", "☐", "☑",
)
req(symbols_value == expected_symbols, "Marko 40-symbol curation changed")

# Status bar is expressly outside this release.
for fragment in (
    'self.editor_status.addWidget(self.operation_mode_label)',
    'self.editor_status.addWidget(self.position_label, 1)',
    'self.editor_status.addPermanentWidget(self.encoding_status_label)',
):
    req(fragment in page, f"out-of-scope Marko editor-status structure changed: {fragment}")

# Protect major file/lifecycle/scanner infrastructure from opportunistic edits.
protected = {
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "controllers/file_actions.py": "8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "services/module_scanner.py": "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "models/module_repository.py": "bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5",
    "widgets/dashboard.py": "b75d978aa0c6f1c01a3ca8eae586eda0b646398b20f4b993fc75e8ce70a6c773",
    "widgets/dashboard_card.py": "77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4",
    "widgets/navigation.py": "cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef",
    "widgets/resolve_open_documents_dialog.py": "38657cbfaf21ab286cb58dc2cd8fac43b2b562d270629d98276274d68c17047e",
    "services/config_service.py": "5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3",
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"protected out-of-scope file changed: {relative}")

if errors:
    print("Marko Plus 0.3.8 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.8 Markopad Find/Replace + settings convergence contract")
