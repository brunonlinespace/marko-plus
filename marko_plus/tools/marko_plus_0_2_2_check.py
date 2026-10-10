#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.2.2 UI/UX alignment."""
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
main = source("widgets/main_window.py")
dashboard = source("widgets/dashboard.py")
folder = source("widgets/folder_dashboard.py")
navigation = source("widgets/navigation.py")
shell = source("widgets/shell_ribbon.py")
repository = source("models/module_repository.py")
manager = source("controllers/editor_manager.py")
file_actions = source("controllers/file_actions.py")
scanner = source("services/module_scanner.py")
watcher = source("services/filesystem_watcher.py")
desktop = source("packaging/appimage/marko-plus.desktop")
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

# Identity and protected Suite contract.
require('APP_VERSION = "0.2.2"' in init, "0.2.2 package identity missing")
require('APP_REVISION = "0.2.2"' in constants, "0.2.2 revision identity missing")
require(component.get("version") == "0.2.2", "Suite component version mismatch")
require(manifest.get("version") == "0.2.2", "project manifest version mismatch")
require(component.get("component_kind") == "extension", "Suite component kind changed")
require(component.get("extensions") == [], "Suite routing extensions changed")
require(component.get("capabilities") == {"routing": False, "open": False, "create": False},
        "Suite routing/open/create capabilities changed")
require("Exec=marko-plus %f" in desktop and "%F" not in desktop,
        "single-file desktop routing changed")
require(desktop.count("MimeType=") == 1 and "MimeType=text/markdown;" in desktop,
        "desktop MIME changed")

# Exact Markdown extension contract remains unchanged.
tree = ast.parse(constants)
extensions = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "MARKDOWN_EXTENSIONS" for t in node.targets):
        call = node.value
        if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == "frozenset" and call.args:
            extensions = ast.literal_eval(call.args[0])
require(extensions == {".md", ".markdown", ".mdown", ".mkd"},
        f"Markdown extension set changed: {extensions!r}")

# File-menu common Plus order follows Rico Plus 0.1.4.
for fragment in (
    'self.dashboard_action = self._command("Dashboard", self.editor_manager.show_dashboard)',
    'self.import_file_action = self._command("Import File into Workspace...", self._import_file_into_workspace)',
    'self.open_external_file_action = self._command("Open External File...", self._open_external_file)',
    'self.rename_file_action = self._command("Rename File…", self._rename_current, "F2")',
    'self.delete_file_action = self._command("Delete File", self._delete_current_file)',
):
    require(fragment in main, f"missing approved action contract: {fragment}")
menu_order = '''        file_menu.addAction(self.dashboard_action)\n        file_menu.addAction(self.next_file_action)\n        file_menu.addAction(self.previous_file_action)\n        file_menu.addSeparator()\n        file_menu.addAction(self.refresh_workspace_action)\n        self.workspace_menu = file_menu.addMenu("Workspace(s)")'''
require(menu_order in main, "File menu Dashboard/Next/Previous/Refresh/Workspace order is wrong")
post_workspace = '''        self._rebuild_workspace_menu()\n        file_menu.addAction(self.import_file_action)\n        file_menu.addSeparator()\n        file_menu.addAction(self.open_external_file_action)\n        file_menu.addAction(self.new_window_action)\n        file_menu.addSeparator()\n        file_menu.addAction(self.save_action)'''
require(post_workspace in main, "File menu Workspace/Import/Open External/New Window/Save order is wrong")

workspace = main.split("    def _rebuild_workspace_menu", 1)[1].split("    def _switch_project", 1)[0]
require('self.workspace_menu.addAction(self.manage_workspaces_action)\n        self.workspace_menu.addSeparator()' in workspace,
        "Workspace(s) does not begin with Open / Manage Workspaces and a separator")
require("self.workspace_menu.addAction(self.refresh_workspace_action)" not in workspace,
        "Refresh Workspace still lives inside Workspace(s)")
require(workspace.count("self.workspace_menu.addAction(self.manage_workspaces_action)") == 1,
        "Open / Manage Workspaces duplicated in Workspace(s)")

# Import menu reuses exact existing drag/drop import route and does not auto-open.
import_method = main.split("    def _import_file_into_workspace", 1)[1].split("    def _open_external_file", 1)[0]
for fragment in (
    'patterns = "*.md *.markdown *.mdown *.mkd"',
    'QFileDialog.getOpenFileName(',
    'self._handle_app_drop([Path(selected)], self.library_root)',
):
    require(fragment in import_method, f"Import File workflow missing: {fragment}")
for forbidden in ("import_files(", "_open_external_path", "queue_open_path", "_launch_new_window"):
    require(forbidden not in import_method, f"Import File command bypasses drag/drop import path: {forbidden}")

# More Actions and ellipsis convention.
more = '''        more = file_menu.addMenu("More Actions")\n        for action in (self.duplicate_action, self.rename_file_action, self.delete_file_action): more.addAction(action)\n        more.addSeparator()\n        more.addAction(self.external_editor_action)\n        more.addAction(self.open_document_folder_action)\n        more.addSeparator()\n        more.addAction(self.properties_action)'''
require(more in main, "More Actions order is not the approved common structure")
require('self.duplicate_action = self._command("Duplicate File…"' in main, "Duplicate File lost its ellipsis")
require('self.rename_file_action = self._command("Rename File…"' in main, "Rename File label/ellipsis is wrong")
require('self.delete_file_action = self._command("Delete File",' in main and '"Delete File…"' not in main,
        "Delete File ellipsis convention is wrong")

# Discoverability mirrors Rico Plus 0.1.4 main Dashboard text.
require("File → Import File into Workspace..." in dashboard,
        "Dashboard does not advertise File → Import File into Workspace")

# Requested icon rewires only.
for fragment in (
    '"import_file_action":"drop-active"',
    '"open_external_file_action":"open"',
    '"tabs_disabled_action":"drop-new-window"',
    '"editor_layout_menu_action":"toolbar-tabbed"',
):
    require(fragment in main, f"icon rewire missing: {fragment}")
require('self._toolbar_icon_path("app-drag-and-drop" if self._tabs_enabled() else "drop-new-window")' in main,
        "dynamic Tabs Disabled icon does not use drop-new-window")
for asset in ("drop-active.png", "drop-new-window.png", "open.png", "toolbar-tabbed.png"):
    for scheme in ("light", "dark"):
        require((PACKAGE / "assets/toolbar-icons" / scheme / asset).is_file(), f"missing existing icon asset: {scheme}/{asset}")

# Ctrl+F editor behavior is a toggle/retract; dashboard search stays focus/select.
focus = main.split("    def _focus_find", 1)[1].split("    def _focus_replace", 1)[0]
for fragment in (
    "if page.search_frame.isVisible():",
    "page.hide_find_panel()",
    "page.show_find_panel(False)",
    'search = getattr(self.stack.currentWidget(), "search_input", None)',
    "search.setFocus(Qt.FocusReason.ShortcutFocusReason)",
    "search.selectAll()",
):
    require(fragment in focus, f"Ctrl+F toggle/context behavior missing: {fragment}")

# External verification reuses existing Preview mode transiently, then Locked + Focused.
verification = main.split("    def _apply_external_verification_mode", 1)[1].split("    def _open_pending_if_ready", 1)[0]
for fragment in (
    'page.set_view_mode("preview", persist=False)',
    "page.set_view_only(True)",
    "page.scroll_to_top()",
    "self.collapsed_mode_action.setChecked(True)",
    "self._toggle_collapsed_mode(True)",
):
    require(fragment in verification, f"external Preview/Locked/Focused contract missing: {fragment}")
require('persist=True' not in verification and 'config.set("markopad_view_mode"' not in verification,
        "external Preview selection is being persisted")

# Preserve core converged implementation boundaries.
require("existing_paths = set(self._modules) - set(external)" in repository,
        "external repository preservation regressed")
require("external = False" in manager and "external = True" in manager and "external=external" in manager,
        "managed/external Save As classification regressed")
require("self.file_actions.import_files(" in main.split("    def _handle_app_drop", 1)[1].split("    def _delete_current_file", 1)[0],
        "external mouse-drop import path regressed")
require("QScroller" not in folder and "QScroller" not in navigation and "QScroller" not in shell,
        "kinetic scrolling leaked into protected non-root surfaces")
require("def import_files" in file_actions, "existing import engine missing")
require("class ModuleScanner" in scanner and "class FilesystemWatcher" in watcher,
        "protected scanner/watcher scaffold missing")
require("import_file_action" not in shell,
        "AppMenu-only Import File action leaked into the Ribbon")

try:
    meta = ET.parse(PACKAGE / "packaging/appimage/io.github.brunonlinespace.marko_plus.metainfo.xml").getroot()
    media = {(node.text or "").strip() for node in meta.findall("./provides/mediatype")}
    releases = meta.findall("./releases/release")
except (OSError, ET.ParseError) as exc:
    errors.append(f"Invalid AppStream metadata: {exc}")
    media, releases = set(), []
require(media == {"text/markdown"}, f"AppStream MIME changed: {media!r}")
require(len(releases) == 1 and releases[0].attrib.get("version") == "0.2.2",
        "AppStream current-release metadata is stale")

if errors:
    print("Marko Plus 0.2.2 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("Marko Plus 0.2.2 UI/UX alignment check passed.")
