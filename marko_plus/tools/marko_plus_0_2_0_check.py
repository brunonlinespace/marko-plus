#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.2.0 Phase 2 external-session convergence."""
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

# 0.2.0 identity only; no Suite capability/type change.
require('APP_VERSION = "0.2.0"' in init, "0.2.0 package identity missing")
require('APP_REVISION = "0.2.0"' in constants, "0.2.0 revision identity missing")
require(component.get("version") == "0.2.0", "Suite component version mismatch")
require(manifest.get("version") == "0.2.0", "project manifest version mismatch")
require(component.get("component_kind") == "extension", "Suite component kind changed")
require(component.get("extensions") == [], "Suite document-routing extensions must remain empty")
require(component.get("capabilities") == {"routing": False, "open": False, "create": False},
        "Suite routing/open/create capabilities changed")

# Markopad-authoritative Markdown support: exact extensions and one desktop MIME.
tree = ast.parse(constants)
extensions = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MARKDOWN_EXTENSIONS" for t in node.targets):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "frozenset" and call.args:
            extensions = ast.literal_eval(call.args[0])
require(extensions == {".md", ".markdown", ".mdown", ".mkd"},
        f"Markdown extension set changed: {extensions!r}")
require(desktop.count("MimeType=") == 1, "Desktop entry must contain exactly one MimeType declaration")
require("MimeType=text/markdown;" in desktop, "Desktop MIME is not exactly text/markdown")
require("Exec=marko-plus %f" in desktop, "Desktop entry does not use single-file %f")
require("%F" not in desktop, "Broken multi-file %F routing was reintroduced")
require("text/plain" not in desktop and "text/x-markdown" not in desktop,
        "Unsupported Markdown MIME alias was introduced")
try:
    meta = ET.parse(metainfo_path).getroot()
    media = {(node.text or "").strip() for node in meta.findall("./provides/mediatype")}
except (OSError, ET.ParseError) as exc:
    errors.append(f"Invalid AppStream metadata: {exc}")
    media = set()
require(media == {"text/markdown"}, f"AppStream media types changed: {media!r}")

# Item 23: Rico-style single external OS-open session, not import.
require("def requested_open_path(arguments: list[str]) -> Path | None:" in app,
        "single-file requested_open_path parser missing")
require("def requested_open_paths" not in app, "plural/multi-file startup parser was introduced")
require("window.queue_open_path(open_path)" in app, "startup path is not routed through MainWindow.queue_open_path")
require("external: bool = False" in model, "Module external flag missing")
require("def queue_open_path(self, path: str | Path)" in main, "external-aware queue_open_path missing")
queue = main.split("    def queue_open_path", 1)[1].split("    def _open_external_path", 1)[0]
require("target.relative_to(self.library_root)" in queue, "queue_open_path does not classify workspace membership")
require("self._open_external_path(target)" in queue, "outside-workspace path is not routed to transient session")
require("self.file_actions.import_files" not in queue, "OS-open path incorrectly imports into workspace")
external_open = main.split("    def _open_external_path", 1)[1].split("    def _open_created_module_if_ready", 1)[0]
require("external=True" in external_open, "external session does not mark Module external=True")
require("self.editor_manager.open_module(module)" in external_open, "external session bypasses normal EditorManager open")
require("self.repository.remove(path)" in external_open, "failed external open is not cleaned from repository")

# Item 25: external sessions survive workspace rescans through the common repository.
require("if module.external" in repository, "repository does not identify external modules")
require("existing_paths = set(self._modules) - set(external)" in repository,
        "repository scan replacement does not preserve external modules")
require('"external",' in repository, "repository metadata copy omits external flag")

# Existing Save-As rebind architecture is extended, not replaced.
require("external = False" in manager and "external = True" in manager,
        "EditorManager rebind does not classify managed/external destination")
require("external=external" in manager, "rebound Module does not carry external classification")
require("if old_module.external:" in manager and "self.repository.remove(old_path)" in manager,
        "external source rebind cleanup missing")
require("Choose a location inside the active Workspace" not in main,
        "old workspace-only Save As restriction remains")

# Item 26: external sessions are editor state, not workspace-navigation state.
require("if not module.external" in navigation and "if module.external:" in navigation,
        "Navigation external filtering incomplete")
require("if module.external:" in dashboard, "Dashboard add-path external filter missing")
require(dashboard.count("not module.external") >= 3, "Dashboard count/search external filtering incomplete")
require("if not module.external" in folder, "Folder Dashboard external filter missing")
require('scope = "External" if module.external else workspace' in main,
        "external window-title scope missing")
require("if module.external:\n            return" in main,
        "external document is not excluded from workspace last-opened state")
require("module is not None and not module.external" in main,
        "external document is not excluded from workspace creation/state logic")

# Phase 1 remains a hard boundary: desktop drop imports; touch/card contract unchanged.
require("QScroller.grabGesture(" in dashboard and "QScroller.ScrollerGestureType.TouchGesture" in dashboard,
        "Phase 1 root Dashboard kinetic scrolling regressed")
require(dashboard.count("touch_moves_scroll_only=True") == 2,
        "Phase 1 root List/Grid touch-scroll-only contract regressed")
require("event.deviceType() != QInputDevice.DeviceType.Mouse" in card,
        "Phase 1 touch-origin QDrag guard regressed")
require("drag = QDrag(self)" in card, "managed mouse drag-to-move was removed")
require("QScroller" not in folder and "QScroller" not in navigation and "QScroller" not in shell,
        "forbidden kinetic scrolling leaked beyond the root Dashboard")
require("def _handle_app_drop(" in main and "self.file_actions.import_files(" in main,
        "external desktop drop import path regressed")
drop = main.split("    def _handle_app_drop", 1)[1].split("    def _delete_current_file", 1)[0]
for forbidden in ("_open_external_path", "queue_open_path", "_open_path_in_new_window"):
    require(forbidden not in drop, f"desktop drop incorrectly enters open-session path: {forbidden}")
for retired in ("drop_active_action", "drop_new_window_action", "App Drag-and-Drop", "_effective_drop_open_mode"):
    require(retired not in main, f"retired Active/New Window drop policy returned: {retired}")

# Presentation-only icon rewires requested for 0.2.0.
for fragment in (
    '"app_file_launch_menu_action":"app-drag-and-drop"',
    '"tabs_enabled_action":"app-drag-and-drop"',
    '"tabs_disabled_action":"drop-active"',
    '"editor_layout_menu_action":"drop-new-window"',
):
    require(fragment in main, f"requested icon rewire missing: {fragment}")
require('self.editor_layout_menu_action = layout_menu.menuAction()' in main,
        "Editor Layout menu action is not available for icon wiring")

# No unexpected rewrite of the existing import engine is required by Phase 2.
require("def import_files(" in file_actions, "existing import_files engine missing")

if errors:
    print("Marko Plus 0.2.0 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("Marko Plus 0.2.0 Phase 2 external-session convergence check passed.")
