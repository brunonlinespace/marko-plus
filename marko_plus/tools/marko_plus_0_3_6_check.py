#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.6 UI-convergence/editor-robustness gate."""
from __future__ import annotations
import hashlib
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]
ROOT=PACKAGE.parent
errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
main=src("widgets/main_window.py")
ribbon=src("widgets/shell_ribbon.py")
page=src("widgets/editor_page.py")
manager=src("controllers/editor_manager.py")
init=src("__init__.py")
constants=src("app_constants.py")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.3.6"' in init, "0.3.6 package identity missing")
req('APP_REVISION = "0.3.6"' in constants, "0.3.6 revision identity missing")
req('Current release: **0.3.6**' in readme, "root README current release is stale")
# Toolbar/Ribbon contract
for frag in (
    '[("tabs_enabled_action"), ("tabs_disabled_action")]',
    '[("left_sidebar_action"), ("right_sidebar_action")]',
    '[("dirty_duplicate_tabbed_action"), ("dirty_external_tabbed_action")]',
    '("workspace_tabbed_action")', '("import_file_action")', '("open_external_file_action")',
): req(frag in ribbon, f"Ribbon contract missing: {frag}")
req('app_tabs_toggle_action' not in ribbon, "old combined tabs toggle remains visible in Ribbon")
req('("refresh_workspace_action")' not in ribbon and '("exit_action")' not in ribbon, "Refresh/Exit were added to Ribbon out of scope")
# Workspace menu and sidebar shortcut
for frag in ('self.workspace_tabbed_action = self.workspace_menu.menuAction()', '"workspace_tabbed_action":"manage-workspaces"', '"Toggle Sidebar Position", self._toggle_sidebar_position, "Shift+F9"', 'def _toggle_sidebar_position(self)'):
    req(frag in main, f"workspace/sidebar command contract missing: {frag}")
req('"manage_workspaces_action":"manage-workspaces"' not in main, "Open / Manage Workspaces still owns the workspace icon")
# Heading contract
req('for action in self.heading_actions: heading_menu.addAction(action)' in main, "Normal Paragraph missing from Heading toolbar menu")
req('"heading_tabbed_action":"heading-0"' in main, "Normal Paragraph is not Heading default icon")
# Dark Editor must use narrow theme path and preserve presentation state.
req('self.editor_manager.apply_editor_theme()' in main, "Dark Editor still uses broad preference path")
req('state.editor_page.apply_canvas_theme()' in main, "App Theme bypasses the dirty-state-preserving canvas path")
req('def apply_editor_theme(self)' in manager and 'page.apply_canvas_theme()' in manager, "narrow editor-theme manager path missing")
for frag in ('def _apply_presentation_safely(self, callback)', 'was_modified = bool(document.isModified())', 'document.setModified(was_modified)', 'def apply_canvas_theme(self)'):
    req(frag in page, f"presentation dirty-state guard missing: {frag}")
# Properties exact style/inventory: grouped Rico presentation, no invented fields.
for frag in ('dialog.setWindowTitle("Properties — Marko Plus")', 'dialog.setMinimumWidth(640)', 'add_group("File"', 'add_group("Document"', 'QDialogButtonBox.StandardButton.Ok'):
    req(frag in page, f"Properties style convergence missing: {frag}")
for label in ('Name','Location','Full path','Size','Modified','Permissions','Lines','Characters','Encoding','Newline','Locked Mode','Edit mode'):
    req(f'("{label}"' in page, f"Marko property missing: {label}")
for forbidden in ('("Words"', '("Compatibility"', '("Document type"'):
    req(forbidden not in page, f"unapproved property added: {forbidden}")
# Symbols merged curation and More Symbols.
for frag in ('def show_symbols_dialog(self)', '"More Symbols…"', '"★", "☆"', '"£", "€", "$", "¥", "¢"', '"≠", "≤", "≥", "≈", "∞"'):
    req(frag in page, f"Symbols convergence missing: {frag}")
req('QInputDialog.getItem(self, "Symbol — Marko Plus"' not in main, "old Symbols dropdown remains")
# Find / Replace convergence
for frag in ('self.find_button = QPushButton("Find"', 'self.search_previous_button = QToolButton', 'self.search_next_button = QToolButton', 'def find_text(self, show_message: bool = True)', 'def _show_search_match(self, index: int)', 'def show_replace_dialog(self)', 'dialog.setModal(False)', 'def _replace_flags(self)', 'def replace_all(self) -> int', 'edit_cursor.beginEditBlock()', 'self.editor.MAX_DOCUMENT_CHARACTERS'):
    req(frag in page, f"Find/Replace convergence missing: {frag}")
req('self.replace_input = QLineEdit()' not in page, "old combined Find/Replace panel remains")
# Protected out-of-scope implementation
protected={'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'controllers/file_actions.py': '8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241', 'models/module_repository.py': 'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5', 'widgets/resolve_open_documents_dialog.py': '38657cbfaf21ab286cb58dc2cd8fac43b2b562d270629d98276274d68c17047e', 'widgets/dashboard.py': 'b75d978aa0c6f1c01a3ca8eae586eda0b646398b20f4b993fc75e8ce70a6c773', 'widgets/dashboard_card.py': '77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4', 'widgets/navigation.py': 'cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef', 'services/config_service.py': '5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3'}
for rel,expected in protected.items(): req(sha(rel)==expected, f"protected out-of-scope file changed: {rel}")
if errors:
    print("Marko Plus 0.3.6 check failed:")
    [print("- "+e) for e in errors]
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.6 UI-convergence/editor-robustness contract")
