#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.9 File Header parity."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
page = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
config = (ROOT / "services/config_service.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.0.9"', init, "0.0.9 package identity missing")
require('"show_file_header": True', config, "show_file_header default missing")
require('self._header_visible = bool(config.get("show_file_header", True))', page, "EditorPage persisted header state missing")
require('self.title_label.setVisible(self._header_visible)', page, "new EditorPages do not apply header state")
require('def set_header_visible(self, visible: bool) -> None:', page, "EditorPage header visibility API missing")
require('self.file_header_action = self._command("File Header", self._toggle_file_header, "Ctrl+Alt+Shift+F", checkable=True)', main, "File Header action/shortcut mismatch")
require('self.file_header_action.setChecked(bool(self.config.get("show_file_header", True)))', main, "File Header action does not reflect persisted state")
require('more_settings.addAction(self.file_header_action)\n        more_settings.addSeparator()\n        more_settings.addAction(self.tab_width_action)', main, "View -> Editor Miscellaneous File Header placement mismatch")
require('def _set_file_header_visible(self, visible: bool, *, persist: bool, sync_action: bool = True) -> None:', main, "MainWindow File Header propagation missing")
require('page.set_header_visible(visible)', main, "loaded EditorPages are not updated")
require('self.config.set("show_file_header", visible, save=True)', main, "File Header persistence missing")
require('("File Header", self.file_header_action)', main, "File Header missing from shortcut reference")

# Strict exclusions: later Phase 3 work must not enter 0.0.9.
for fragment, label in (
    ('document_tabs', 'Document Tabs'),
    ('_toggle_collapsed_mode', 'Focused Mode'),
):
    if fragment in main:
        errors.append(f"0.0.9 unexpectedly introduced {label}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.9 File Header parity check passed.")
