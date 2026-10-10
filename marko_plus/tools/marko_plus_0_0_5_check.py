#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.5 dirty external-editor convergence."""
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


require('APP_VERSION = "0.0.5"', init, "0.0.5 package identity missing")
require('"dirty_external_action": "ask"', config, "dirty External Editor policy does not default to Ask")
require('"Save Changes and Open"', controller, "save-and-open choice missing")
require('"Open Last Saved Version"', controller, "last-saved external-editor choice missing")
require('QCheckBox("Remember this choice"', controller, "remember-choice control missing")
require('self._set_file_policy("dirty_external_action", choice)', controller, "remembered external-editor policy is not persisted")
require('if page is None or not page.save_to_disk():', controller, "save-and-open does not use protected Marko save path")
require('target = page._external_version_saved_path or page.module.path', controller, "Save Version As target bridge is missing")
require('self._external_version_saved_path: Path | None = None', editor, "saved-version target bridge state missing")
require('self._external_version_saved_path = None', editor, "saved-version target bridge is not reset per save")
require('page._external_version_saved_path = target', main, "Save Version As does not expose the preserved target")
require('dirty_external_menu = settings.addMenu("Open Externally with Unsaved Changes")', main, "Settings external-editor policy entry missing")
require('self.dirty_external_tabbed_action = dirty_external_menu.menuAction()', main, "Settings toolbar does not reuse the external-editor policy submenu")
require('"dirty_external_tabbed_action":"external-editor"', main, "Settings flyout does not use external-editor icon")
require('[self.dirty_duplicate_tabbed_action], [self.dirty_external_tabbed_action]],', main, "external-editor policy flyout is not immediately after Duplicate and final in Settings")
require('self.file_actions.file_policy_changed.connect(self._on_file_policy_changed)', main, "remembered controller choice does not synchronize Settings radios")

# Later Phase 1 items remain parked in 0.0.5.
if 'install_new_file_from_temp' in controller:
    errors.append("later no-clobber Duplicate/New implementation was pulled into 0.0.5")
if 'show_file_header' in config:
    errors.append("File Header convergence was pulled into 0.0.5")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.5 dirty External Editor convergence check passed.")
