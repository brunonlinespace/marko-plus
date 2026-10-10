#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.3 external-change convergence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
editor = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors: list[str] = []


def require(fragment: str, text: str, message: str) -> None:
    if fragment not in text:
        errors.append(message)


require('APP_VERSION = "0.0.3"', init, "0.0.3 package identity missing")
require('QPushButton("Save Version As…")', editor, "external-change banner lacks Save Version As")
require('dialog.setWindowTitle("File Changed on Disk")', editor, "save conflict dialog missing")
require('dialog.addButton("Reload", QMessageBox.ButtonRole.ActionRole)', editor, "Reload conflict action missing")
require('"Save Version As…", QMessageBox.ButtonRole.ActionRole', editor, "Save Version As conflict action missing")
require('"Overwrite", QMessageBox.ButtonRole.DestructiveRole', editor, "explicit Overwrite conflict action missing")
require('def _has_external_change(self) -> bool:', editor, "exact-content external-change helper missing")
require('current.digest != loaded.digest', editor, "external-change decision is not digest-based")
require('current.digest == loaded.digest', editor, "watcher notification does not dismiss timestamp-only changes")
require('def _save_external_change_version_as(self, page: EditorPage) -> bool:', main, "Marko Save Version As bridge missing")
require('"Choose a different filename. The original file changed "', main, "changed source is not forbidden as Save Version As destination")
require('page.save_copy_to(target)', main, "Save Version As does not use Marko existing Save As writer")
require('page.mark_clean_for_save_as()', main, "Save Version As does not retain Marko existing Save As lifecycle")
require('self.editor_manager.close_module(module)', main, "Save Version As does not retain Marko existing page retirement lifecycle")
require('self._queue_created_module_open(target)', main, "Save Version As does not retain Marko existing reopen lifecycle")

for forbidden in (
    'QPushButton("Keep My Version")',
    'def _keep_editor_version(self)',
    '"Keeping the editor version; save to overwrite disk"',
):
    if forbidden in editor:
        errors.append(f"obsolete Keep My Version path remains: {forbidden}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.3 external-change convergence check passed.")
