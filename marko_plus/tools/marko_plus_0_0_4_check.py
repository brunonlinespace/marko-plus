#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.4 dirty-Duplicate convergence."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
controller = (ROOT / "controllers/file_actions.py").read_text(encoding="utf-8")
editor = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
config = (ROOT / "services/config_service.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors: list[str] = []


def require(fragment: str, text: str, message: str) -> None:
    if fragment not in text:
        errors.append(message)


require('APP_VERSION = "0.0.4"', init, "0.0.4 package identity missing")
require('"dirty_duplicate_action": "ask"', config, "dirty Duplicate policy does not default to Ask")
require('"Duplicate Current Document"', controller, "current-document duplicate choice missing")
require('"Duplicate Last Saved Version"', controller, "last-saved duplicate choice missing")
require('QCheckBox("Remember this choice"', controller, "remember-choice control missing")
require('self._set_file_policy("dirty_duplicate_action", choice)', controller, "remembered duplicate policy is not persisted")
require('payload = page.current_markdown_payload()', controller, "dirty current-document path does not use live Markdown payload")
require('shutil.copy2(stored.path, destination)', controller, "last-saved duplicate path no longer uses existing Marko disk-copy behavior")
require('def current_markdown_payload(self) -> bytes | None:', editor, "live Markdown payload bridge missing")
require('return self._encoded_editor_payload()', editor, "live Markdown payload does not preserve encoding/newline contract")
require('settings.addSeparator()\n        dirty_duplicate_menu = settings.addMenu("Duplicate File with Unsaved Changes")', main, "Settings duplicate policy is not the final separated menu entry")
require('self.dirty_duplicate_tabbed_action = dirty_duplicate_menu.menuAction()', main, "Settings toolbar does not reuse the AppMenu policy submenu")
require('"dirty_duplicate_tabbed_action":"duplicate-file"', main, "Settings flyout does not use duplicate-file icon")
require('[self.dirty_duplicate_tabbed_action]],', main, "duplicate policy flyout is not the final Settings toolbar group")
require('self.file_actions.file_policy_changed.connect(self._on_file_policy_changed)', main, "remembered controller choice does not synchronize Settings radios")

# Later Phase 1 items must remain parked in 0.0.4.
if '"Save Changes and Open"' in controller or '"Open Last Saved Version"' in controller:
    errors.append("external-editor convergence was pulled into 0.0.4")
if 'install_new_file_from_temp' in controller:
    errors.append("later no-clobber Duplicate/New implementation was pulled into 0.0.4")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.4 dirty-Duplicate convergence check passed.")
