#!/usr/bin/env python3
# Marko Plus
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static contract check for Marko Plus 0.2.4 drag/drop reconciliation."""

from __future__ import annotations

import hashlib
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


def sha256(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


init = source("__init__.py")
constants = source("app_constants.py")
main = source("widgets/main_window.py")
navigation = source("widgets/navigation.py")
dashboard = source("widgets/dashboard.py")
folder_dashboard = source("widgets/folder_dashboard.py")
editor_page = source("widgets/editor_page.py")
manager = source("controllers/editor_manager.py")
desktop = source("packaging/appimage/marko-plus.desktop")
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

# Identity and protected Suite contract.
require('APP_VERSION = "0.2.4"' in init, "0.2.4 package identity missing")
require('APP_REVISION = "0.2.4"' in constants, "0.2.4 revision identity missing")
require(component.get("version") == "0.2.4", "Suite component version mismatch")
require(manifest.get("version") == "0.2.4", "project manifest version mismatch")
require(component.get("component_kind") == "extension", "Suite component kind changed")
require(component.get("extensions") == [], "Suite routing extensions changed")
require(component.get("capabilities") == {"routing": False, "open": False, "create": False},
        "Suite routing/open/create capabilities changed")
require("Exec=marko-plus %f" in desktop and "%F" not in desktop,
        "single-file desktop routing changed")
require("MimeType=text/markdown;" in desktop, "desktop Markdown MIME changed")

# Broad MainWindow fallback is removed: drops must land on an explicit surface.
require("self.setAcceptDrops(True)" not in main,
        "MainWindow still accepts application-wide drops")
require("def dragEnterEvent(" not in main and "def dropEvent(" not in main,
        "MainWindow-wide drag/drop fallback remains")
require("self.editor_manager.editor_files_dropped.connect(self._handle_editor_file_drop)" in main,
        "editor drops are not routed to the external-open handler")
editor_drop = main.split("    def _handle_editor_file_drop", 1)[1].split("    def _handle_app_drop", 1)[0]
require("self._launch_new_window(path)" in editor_drop,
        "editor drop does not use the existing new-window file-open lifecycle")
require("import_files" not in editor_drop and "_handle_app_drop" not in editor_drop,
        "editor drop still reaches the import path")

# Main Dashboard is an explicit root import surface.
for fragment in (
    "external_files_dropped = pyqtSignal(object)",
    "self.setAcceptDrops(True)",
    "def dragEnterEvent(self, event: QDragEnterEvent)",
    "def dropEvent(self, event: QDropEvent)",
    "self.external_files_dropped.emit(dropped)",
):
    require(fragment in dashboard, f"Main Dashboard root-drop contract missing: {fragment}")
require(
    "self.dashboard.external_files_dropped.connect(" in manager
    and "paths, self.library_root" in manager,
    "Main Dashboard drops are not routed explicitly to Workspace root",
)

# Sidebar tree destination matrix for external imports.
resolver = navigation.split("    def _external_drop_destination", 1)[1].split("    def dragMoveEvent", 1)[0]
for fragment in (
    "if item is None:",
    "return Path(self.parent().library_root).resolve(strict=False)",
    "if kind == self.KIND_FOLDER:",
    "return path",
    'if kind == "module":',
    "return path.parent",
    "return None",
):
    require(fragment in resolver, f"sidebar external destination rule missing: {fragment}")
require(
    "event.mimeData().hasFormat(self.MIME_TYPE) and valid_folder" in navigation,
    "managed tree moves are no longer folder-only",
)
require(
    "self._external_drop_destination(item) is not None" in navigation,
    "external sidebar drag acceptance is not tied to the explicit destination resolver",
)

# Existing explicit import surfaces remain intact.
require("class DashboardNavigationButton" in navigation,
        "Dashboard sidebar root target missing")
require("self.external_files_dropped.emit(paths)" in navigation,
        "Dashboard sidebar root import signal missing")
require("self.setAcceptDrops(True)" in folder_dashboard and "def dropEvent" in folder_dashboard,
        "Folder Dashboard import target changed")
require("self.external_files_dropped.emit(dropped, destination)" in folder_dashboard,
        "Folder Dashboard no longer emits its explicit folder destination")

# Editor page itself is an explicit open surface so Preview/background areas do
# not depend on MainWindow propagation. Source-editor signal routing remains.
require("self.setAcceptDrops(True)" in editor_page,
        "EditorPage is not an explicit file-open drop surface")
require("def _dropped_markdown_paths" in editor_page,
        "EditorPage Markdown drop validation missing")
require("self.external_files_dropped.emit(paths, self.module.path.parent)" in editor_page,
        "EditorPage drop does not reach the editor-drop route")
require("self.editor.files_dropped.connect(" in editor_page,
        "source-editor drop route was removed")

# Protect unrelated 0.2.3 implementation. These hashes intentionally cover
# the import engine and other layers that this release must not change.
expected_hashes = {
    "controllers/file_actions.py": "46f4a4c273461f348a0300b2cdfddf394b2145ffe34439fab23f737dd42fc3a8",
    "models/module_repository.py": "b95a8d5a788ca7add46d5bfa176c5ad4844b81be8ea210f3b1e8af0857403ffc",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "widgets/folder_dashboard.py": "8abdceadae1159b7f9cfdc7e11299dc943793fafb4457d2796770f3c7c93dcbb",
    "widgets/shell_ribbon.py": "e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1",
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
}
for relative, expected in expected_hashes.items():
    require(sha256(relative) == expected, f"protected 0.2.3 implementation changed: {relative}")

if errors:
    print("Marko Plus 0.2.4 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("Marko Plus 0.2.4 drag/drop reconciliation check passed.")
