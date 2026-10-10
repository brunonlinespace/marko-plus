#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.1 Focused Mode convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
shell = (ROOT / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.1"', init, "0.1.1 package identity missing")
require('self._collapsed_mode_restore: dict[str, object] | None = None', main, "Focused Mode restore state missing")
require('self.collapsed_mode_action = self._command("Focused Mode", self._toggle_collapsed_mode, "F10", checkable=True)', main, "Focused Mode F10 action missing")
require('settings.addAction(self.collapsed_mode_action)', main, "Focused Mode is not first-class in Settings")
require('def _toggle_collapsed_mode(self, checked: bool) -> None:', main, "Focused Mode implementation missing")
require('"sidebar": self.navigation.isVisible()', main, "Focused Mode does not capture sidebar state")
require('"status": self.statusBar().isVisible()', main, "Focused Mode does not capture status state")
require('"header": self.file_header_action.isChecked()', main, "Focused Mode does not capture File Header state")
require('"ribbon_collapsed": bool(getattr(self.shell_ribbon, "_collapsed", False))', main, "Focused Mode does not capture ShellRibbon state")
require('"splitter_sizes": list(self.splitter.sizes())', main, "Focused Mode does not capture splitter geometry")
require('self._set_sidebar_visible(False)', main, "Focused Mode does not hide sidebar through canonical helper")
require('self._set_status_visible(False, persist=False)', main, "Focused Mode does not hide status non-persistently")
require('self._set_file_header_visible(False, persist=False)', main, "Focused Mode does not hide File Header non-persistently")
require('self.shell_ribbon.set_collapsed(True, emit=False)', main, "Focused Mode does not collapse shared ShellRibbon non-persistently")
require('self.shell_ribbon.set_collapsed(bool(restore.get("ribbon_collapsed", False)), emit=False)', main, "Focused Mode does not restore ShellRibbon state")
require('if self._collapsed_mode_restore is not None', main, "shutdown does not preserve pre-Focused splitter geometry")
require('page.editor_status.setVisible(False)', main, "new/current pages do not retain focused status visibility")
require('page.set_header_visible(False)', main, "new/current pages do not retain focused header visibility")

# Approved 0.0.10 menu correction carried into the new ShellRibbon line.
layout_block = '''layout_menu = view.addMenu("Editor Layout")\n        layout_menu.addAction(self.file_header_action)\n        layout_menu.addSeparator()\n        layout_menu.addAction(self.source_only_action)\n        layout_menu.addAction(self.split_action)\n        layout_menu.addAction(self.preview_only_action)'''
require(layout_block, main, "File Header is not first in Editor Layout with separator")
if 'more_settings.addAction(self.file_header_action)' in main:
    errors.append("File Header still remains in Editor Miscellaneous")

# 0.1.1 must use the 0.1.0 ShellRibbon architecture, not revive old toolbar mechanics.
for forbidden, label in (
    ('def set_tabbed_collapsed(', 'old MainWindow collapse implementation'),
    ('self.set_tabbed_collapsed(', 'old toolbar Focused Mode adapter'),
    ('self._tabbed_collapsed', 'old MainWindow collapse state'),
    ('document_tabs', 'Document Tabs'),
    ('_ensure_document_tab(', 'Document Tabs lifecycle'),
):
    if forbidden in main:
        errors.append(f"0.1.1 unexpectedly introduced/retained {label}")

EXPECTED_HASHES = {
    'widgets/shell_ribbon.py': '45d56187f52a657d4fc68bdd6308fdc455c62a45bbca84239e16a1f656dd49f0',
    'widgets/editor_page.py': '711fb194d5093149ac50640f4ff267b8bdde2417dea7e2cc0d8aaeb78e2c6c32',
    'controllers/editor_manager.py': '0e1f2177753f2999007a0b9b121f15b1f62512496308730ea43938fa049d0895',
    'controllers/file_actions.py': '3bdedaf92977c792ff43f6f05ce61a568a1f3f295e5ad668f89eab4323c82cc0',
    'services/config_service.py': '28353bf4003d93b8b50904bd70cedc4dc9ca4b742b4ce93f4b2585825c4fcb3b',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
    'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a',
    'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38',
    'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73',
    'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece',
    'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1',
    'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6',
    'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc',
    'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576',
    'widgets/navigation.py': 'af0f5e3febf97ed351869f40772858f00d5c38abce9ebb13d65299dcc37daa30',
    'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d',
    'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397',
    'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf',
}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.0 file missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        errors.append(f"protected 0.1.0 file changed during Focused Mode convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.1 Focused Mode convergence check passed.")
