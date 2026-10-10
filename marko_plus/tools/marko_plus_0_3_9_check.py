#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.9 Find/Replace keyboard/counter gate."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
page=src("widgets/editor_page.py")
main=src("widgets/main_window.py")
init=src("__init__.py")
constants=src("app_constants.py")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.3.9"' in init, "0.3.9 package identity missing")
req('APP_REVISION = "0.3.9"' in constants, "0.3.9 revision identity missing")
req('Current release: **0.3.9**' in readme, "README current release stale")
# Keep the accepted Markopad bottom panel / gold-all-matches / real-selection model.
for f in (
    'self.search_frame = QFrame(self)', 'self.find_input.setPlaceholderText("Find")',
    'self.replace_input.setPlaceholderText("Replace")', 'self.find_input.returnPressed.connect(self.find_next)',
    'close_search.clicked.connect(self.hide_find_panel)', 'selection.format.setBackground(QColor("#C9A227"))',
    'selection.format.setForeground(QColor("#101010"))',
): req(f in page, f"accepted Find/Replace contract missing: {f}")
for forbidden in ('passive_bg', 'active_bg = QColor("#FFD54F")', 'dialog.setWindowTitle("Find and Replace'):
    req(forbidden not in page, f"retired search model returned: {forbidden}")
# F3/Shift+F3 must be installed on the live page, not merely defined in a private menu.
for f in (
    'self.find_next_action = self._menu_action(edit_menu, "Find Next", self.find_next, shortcut="F3")',
    'self.find_previous_action = self._menu_action(edit_menu, "Find Previous", self.find_previous, shortcut="Shift+F3")',
    'self.addAction(self.find_next_action)', 'self.addAction(self.find_previous_action)',
    'self.dismiss_find_action.setShortcut(QKeySequence("Esc"))',
    'self.dismiss_find_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)',
    'self.addAction(self.dismiss_find_action)',
): req(f in page, f"live page shortcut contract missing: {f}")
# Ctrl+F/Ctrl+H toggle only when their own field already has focus.
toggle=re.search(r'def toggle_find_panel\(self, replace: bool = False\).*?return True', page, re.S)
req(toggle is not None, 'toggle_find_panel missing')
if toggle:
    body=toggle.group(0)
    req('target = self.replace_input if replace else self.find_input' in body, 'toggle does not select requested field')
    req('self.search_frame.isVisible() and target.hasFocus()' in body, 'toggle is not focus-aware')
    req('self.hide_find_panel()' in body and 'self.show_find_panel(replace)' in body, 'toggle open/close routing incomplete')
req('page.toggle_find_panel(False)' in main, 'Ctrl+F does not route through focus-aware toggle')
req('page.toggle_find_panel(True)' in main, 'Ctrl+H does not route through focus-aware toggle')
# Positional counter restored, including bounded Y+ representation.
for f in (
    'current = self._current_search_index + 1 if 0 <= self._current_search_index < total else 0',
    'total_text = f"{total:,}+" if self._search_results_truncated else f"{total:,}"',
    'self.search_counter.setText(f"{current:,}/{total_text}")',
    'self._current_search_index = 0',
    'active_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)',
    'self._update_search_counter()\n        return True',
): req(f in page, f"X/Y active-position contract missing: {f}")
# Out-of-scope major infrastructure must stay byte-identical to 0.3.8.
protected={
"controllers/editor_manager.py":"e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
"controllers/file_actions.py":"8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241",
"services/open_document_monitor.py":"3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
"services/filesystem_watcher.py":"cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
"services/module_scanner.py":"a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
"models/module_repository.py":"bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5",
"services/config_service.py":"5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3",
"widgets/markopad_source_editor.py":"dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
}
for r,h in protected.items(): req(sha(r)==h, f"protected out-of-scope file changed: {r}")
if errors:
    print("Marko Plus 0.3.9 check failed:")
    for e in errors: print(f"- {e}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.9 Find/Replace keyboard + X/Y counter contract")
