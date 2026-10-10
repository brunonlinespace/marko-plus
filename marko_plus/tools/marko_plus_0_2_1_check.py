#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.2.1 Phase 2 lifecycle completion."""
from __future__ import annotations

import ast
import json
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def source(name: str) -> str:
    return (PACKAGE / name).read_text(encoding="utf-8")


init = source("__init__.py")
constants = source("app_constants.py")
app = source("app.py")
model = source("models/module.py")
repository = source("models/module_repository.py")
manager = source("controllers/editor_manager.py")
file_actions = source("controllers/file_actions.py")
main = source("widgets/main_window.py")
navigation = source("widgets/navigation.py")
dashboard = source("widgets/dashboard.py")
card = source("widgets/dashboard_card.py")
folder = source("widgets/folder_dashboard.py")
shell = source("widgets/shell_ribbon.py")
desktop = source("packaging/appimage/marko-plus.desktop")
metainfo_path = PACKAGE / "packaging/appimage/io.github.brunonlinespace.marko_plus.metainfo.xml"
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

# Identity only; Suite routing/type must remain unchanged.
require('APP_VERSION = "0.2.1"' in init, "0.2.1 package identity missing")
require('APP_REVISION = "0.2.1"' in constants, "0.2.1 revision identity missing")
require(component.get("version") == "0.2.1", "Suite component version mismatch")
require(manifest.get("version") == "0.2.1", "project manifest version mismatch")
require(component.get("component_kind") == "extension", "Suite component kind changed")
require(component.get("extensions") == [], "Suite routing extensions changed")
require(component.get("capabilities") == {"routing": False, "open": False, "create": False},
        "Suite routing/open/create capabilities changed")

# Markopad-authoritative Markdown contract remains exact.
tree = ast.parse(constants)
extensions = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MARKDOWN_EXTENSIONS" for t in node.targets):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "frozenset" and call.args:
            extensions = ast.literal_eval(call.args[0])
require(extensions == {".md", ".markdown", ".mdown", ".mkd"},
        f"Markdown extension set changed: {extensions!r}")
require("Exec=marko-plus %f" in desktop and "%F" not in desktop,
        "desktop routing must remain single-file %f")
require(desktop.count("MimeType=") == 1 and "MimeType=text/markdown;" in desktop,
        "desktop MIME must remain exactly text/markdown")
require("text/plain" not in desktop and "text/x-markdown" not in desktop,
        "unsupported Markdown MIME alias was introduced")
try:
    meta = ET.parse(metainfo_path).getroot()
    media = {(node.text or "").strip() for node in meta.findall("./provides/mediatype")}
    releases = meta.findall("./releases/release")
except (OSError, ET.ParseError) as exc:
    errors.append(f"Invalid AppStream metadata: {exc}")
    media, releases = set(), []
require(media == {"text/markdown"}, f"AppStream media types changed: {media!r}")
require(len(releases) == 1 and releases[0].attrib.get("version") == "0.2.1",
        "AppStream current-release metadata is stale")

# Dedicated open lifecycle: do not reuse new-file pending state.
require("self._pending_open_path: Path | None = None" in main,
        "dedicated pending-open state missing")
require("_pending_created_path" not in main,
        "old creation-specific pending state remains")
require("def _queue_created_open(self, path: Path)" in main,
        "Rico-style created/open queue helper missing")
require("def _open_pending_if_ready(self, module: Module)" in main,
        "pending-open resolver missing")
require("self.file_actions.module_created.connect(self._queue_created_open)" in main,
        "new-file creation is not routed through common pending-open helper")
require("self.repository.module_added.connect(self._open_pending_if_ready)" in main,
        "repository additions do not resolve pending opens")
queue = main.split("    def queue_open_path", 1)[1].split("    def _open_external_path", 1)[0]
require("self._startup_open_requested = True" in queue,
        "explicit startup file request is not recorded")
require(queue.find("self._startup_open_requested = True") < queue.find("target.relative_to(self.library_root)"),
        "startup-open flag must be set before managed/external classification")
require("self._pending_open_path = target" in queue,
        "managed OS-open does not use dedicated pending-open state")
require("self._open_pending_if_ready(module)" in queue,
        "ready managed OS-open does not use common pending-open resolver")
scan = main.split("    def _on_scan_finished", 1)[1].split("    def _on_scan_failed", 1)[0]
require("if self._pending_open_path is not None:" in scan and "self._open_pending_if_ready(module)" in scan,
        "scan completion does not explicitly retry pending managed open")
require("if self._startup_open_requested:\n            return" in scan,
        "explicit startup open can still fall through to normal Dashboard startup")

# External launch remains the 0.2.0 session architecture, now with verification mode.
external_open = main.split("    def _open_external_path", 1)[1].split("    def _apply_external_verification_mode", 1)[0]
require("external=True" in external_open, "external session classification regressed")
require("self.editor_manager.open_module(module)" in external_open,
        "external session bypasses normal EditorManager open")
require("self._apply_external_verification_mode(page)" in external_open,
        "external launch does not apply verification mode")
verification = main.split("    def _apply_external_verification_mode", 1)[1].split("    def _open_pending_if_ready", 1)[0]
for fragment in (
    "page.set_view_only(True)",
    "page.scroll_to_top()",
    "self.collapsed_mode_action.setChecked(True)",
    "self._toggle_collapsed_mode(True)",
    "self._update_window_title()",
):
    require(fragment in verification, f"external verification mode missing: {fragment}")
require('config.set("lock_editor"' not in verification,
        "external verification mode must not rewrite the persisted Locked Mode preference")
require('config.set("show_' not in verification,
        "external verification mode must not rewrite persisted view preferences")

# File menu placement and single implementation path.
require('self.open_external_file_action = self._command("Open External File...", self._open_external_file)' in main,
        "Open External File action missing")
menu_order = '''        self._rebuild_workspace_menu()\n        file_menu.addSeparator()\n        file_menu.addAction(self.open_external_file_action)\n        file_menu.addAction(self.new_window_action)\n        file_menu.addSeparator()\n        file_menu.addAction(self.save_action)'''
require(menu_order in main,
        "File menu order is not Workspace(s) / separator / Open External File / New Window / separator / Save")
workspace_rebuild = main.split("    def _rebuild_workspace_menu", 1)[1].split("    def _switch_project", 1)[0]
require("self.workspace_menu.addAction(self.new_window_action)" not in workspace_rebuild,
        "New Window was not migrated out of the Workspace(s) submenu")
require("def _window_launch_command(self, open_path: Path | None = None)" in main,
        "common new-window launch command helper missing")
require("def _launch_new_window(self, open_path: Path | None = None)" in main,
        "common new-window launcher missing")
new_window = main.split("    def _new_window", 1)[1].split("    def _open_external_file", 1)[0]
require("self._launch_new_window()" in new_window,
        "existing New Window action was not preserved through the common launcher")
open_file = main.split("    def _open_external_file", 1)[1].split("    def _new_folder", 1)[0]
for fragment in (
    'patterns = "*.md *.markdown *.mdown *.mkd"',
    "QFileDialog.getOpenFileName(",
    "path.suffix.casefold() not in MARKDOWN_EXTENSIONS",
    "path.relative_to(self.library_root)",
    "self._launch_new_window(path)",
):
    require(fragment in open_file, f"Open External File workflow missing: {fragment}")
require("import_files" not in open_file and "_open_external_path" not in open_file,
        "menu command bypasses the standalone new-window startup contract")

# External containing-folder parity with Rico: no workspace-membership rejection.
folder_method = file_actions.split("    def open_module_folder", 1)[1].split("    def ", 1)[0]
require("folder = stored.path.parent" in folder_method and "self.desktop_launcher.open_path(folder)" in folder_method,
        "Open Containing Folder no longer opens the document parent")
require("relative_to(self.library_root)" not in folder_method and "outside the active workspace" not in folder_method,
        "external Open Containing Folder is still incorrectly workspace-restricted")

# Small confirmed wording corrections.
require("File > Workspace(s) > Open / Manage Workspaces... to relink it." in app,
        "unavailable-Workspace guidance is stale")
require('f"{count} Markdown file has unsaved changes." if count == 1' in main,
        "singular dirty-document status wording missing")
require('f"{count} Markdown files have unsaved changes."' in main,
        "plural dirty-document status wording missing")

# Preserve Phase 1 and Phase 2 architecture; no opportunistic changes.
require("external: bool = False" in model, "external model flag missing")
require("existing_paths = set(self._modules) - set(external)" in repository,
        "repository external preservation regressed")
require("external = False" in manager and "external = True" in manager and "external=external" in manager,
        "Save As managed/external rebind classification regressed")
require("if module.external" in navigation and "if module.external:" in dashboard and "if not module.external" in folder,
        "external workspace-UI filtering regressed")
require("QScroller.grabGesture(" in dashboard and dashboard.count("touch_moves_scroll_only=True") == 2,
        "root Dashboard touch contract regressed")
require("event.deviceType() != QInputDevice.DeviceType.Mouse" in card and "drag = QDrag(self)" in card,
        "touch/mouse Dashboard drag contract regressed")
require("QScroller" not in folder and "QScroller" not in navigation and "QScroller" not in shell,
        "kinetic scrolling leaked outside the root Dashboard")
drop = main.split("    def _handle_app_drop", 1)[1].split("    def _delete_current_file", 1)[0]
require("self.file_actions.import_files(" in drop,
        "external desktop drop no longer imports")
for forbidden in ("_open_external_path", "queue_open_path", "_launch_new_window"):
    require(forbidden not in drop, f"desktop drop incorrectly enters external-open path: {forbidden}")

if errors:
    print("Marko Plus 0.2.1 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("Marko Plus 0.2.1 Phase 2 lifecycle-completion check passed.")
