#!/usr/bin/env python3
# Marko Plus
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static contract check for Marko Plus 0.2.3 reconciliation."""

from __future__ import annotations

import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def source(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")


init = source("__init__.py")
constants = source("app_constants.py")
main = source("widgets/main_window.py")
file_actions = source("controllers/file_actions.py")
desktop = source("packaging/appimage/marko-plus.desktop")
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

# Identity and protected Suite contract.
require('APP_VERSION = "0.2.3"' in init, "0.2.3 package identity missing")
require('APP_REVISION = "0.2.3"' in constants, "0.2.3 revision identity missing")
require(component.get("version") == "0.2.3", "Suite component version mismatch")
require(manifest.get("version") == "0.2.3", "project manifest version mismatch")
require(component.get("component_kind") == "extension", "Suite component kind changed")
require(component.get("extensions") == [], "Suite routing extensions changed")
require(component.get("capabilities") == {"routing": False, "open": False, "create": False},
        "Suite routing/open/create capabilities changed")
require("Exec=marko-plus %f" in desktop and "%F" not in desktop,
        "single-file desktop routing changed")
require("MimeType=text/markdown;" in desktop, "desktop Markdown MIME changed")

# Duplicate Last Saved Version now follows Rico Plus 0.1.5 new-document semantics.
require("MAX_DOCUMENT_BYTES = 25 * 1024 * 1024" in file_actions,
        "25 MiB duplicate/reopen limit missing")
require("read_regular_file," in file_actions, "guarded file reader not imported")

duplicate = file_actions.split("    def duplicate_module", 1)[1].split("    def create_file", 1)[0]
for fragment in (
    'payload = page.current_markdown_payload()',
    'payload, _snapshot = read_regular_file(',
    'stored.path, MAX_DOCUMENT_BYTES',
    'if len(payload) > MAX_DOCUMENT_BYTES:',
    '"The duplicate would exceed Marko Plus\'s 25 MiB reopen limit."',
    'descriptor, raw_path = tempfile.mkstemp(',
    'with os.fdopen(descriptor, "wb") as handle:',
    'handle.write(payload)',
    'handle.flush()',
    'os.fsync(handle.fileno())',
    'os.chmod(temporary, stored.path.stat().st_mode & 0o777)',
    'install_new_file_from_temp(temporary, destination)',
    'fsync_directory(destination.parent)',
):
    require(fragment in duplicate, f"duplicate reconciliation missing: {fragment}")
require("shutil.copy2" not in duplicate,
        "Duplicate Last Saved Version still uses filesystem-copy semantics")
require("shutil.copymode" not in duplicate,
        "duplicate branches are not using the common Rico permission-restoration path")
require("except (OSError, ValueError, RuntimeError, MemoryError) as error:" in duplicate,
        "Rico-aligned duplicate error boundary missing")

# Import deliberately retains its separate copy/import semantics.
import_method = file_actions.split("    def import_files", 1)[1].split("    def open_in_external_editor", 1)[0]
require("shutil.copy2(source, temporary)" in import_method,
        "0.2.3 accidentally changed established import copy semantics")

# Scanner terminology aligns exactly with Rico Plus wording.
require('self.show_status(f"Workspace scan failed: {message}")' in main,
        "Workspace scan-failure status wording missing")
require('QMessageBox.warning(self, "Workspace Scan Failed", message)' in main,
        "Workspace Scan Failed warning title missing")
require("Library scan failed" not in main and "Library Scan Failed" not in main,
        "stale Library scan-failure terminology remains")

# Preserve selected 0.2.2 UX contracts.
for fragment in (
    'self.import_file_action = self._command("Import File into Workspace...", self._import_file_into_workspace)',
    'self.open_external_file_action = self._command("Open External File...", self._open_external_file)',
    'page.set_view_mode("preview", persist=False)',
    'if page.search_frame.isVisible():',
    'page.hide_find_panel()',
):
    require(fragment in main, f"0.2.2 behavior regressed: {fragment}")

if errors:
    print("Marko Plus 0.2.3 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("Marko Plus 0.2.3 reconciliation check passed.")
