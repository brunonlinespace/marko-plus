#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r3 menu revision."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    app = (PACKAGE / "app.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")

    require("self.setWindowTitle(workspace_name)" in window,
            "Title bar is not exactly the active Workspace name", errors)
    title_start = window.index("    def _update_window_title")
    title_end = window.index("    def _save_active_project_state", title_start)
    title_body = window[title_start:title_end]
    require("APP_BRAND_NAME" not in title_body and "Marko Plus" not in title_body,
            "Application name is duplicated in the title assignment", errors)

    for forbidden in (
        "self.import_action", "def _import_scripts", "Import Markdown File",
        "MARKDOWN_FILE_GLOB",
    ):
        require(forbidden not in window,
                f"Removed Import Markdown Files option remains: {forbidden}", errors)

    for fragment in (
        'self.workspace_menu = file_menu.addMenu("Workspace(s)")',
        "self.workspace_action_group = QActionGroup(self.workspace_menu)",
        "self.workspace_action_group.setExclusive(True)",
        "self.workspace_menu.aboutToShow.connect(self._rebuild_workspace_menu)",
        "def _rebuild_workspace_menu",
        "for workspace in self.project_registry.projects:",
        "action.setCheckable(True)",
        "action.setChecked(workspace.project_id == active_id)",
        "self.workspace_action_group.addAction(action)",
    ):
        require(fragment in window,
                f"Workspace radio inventory wiring missing: {fragment}", errors)

    rebuild_start = window.index("    def _rebuild_workspace_menu")
    rebuild_end = window.index("    def _switch_project", rebuild_start)
    rebuild = window[rebuild_start:rebuild_end]
    separator_at = rebuild.rfind("self.workspace_menu.addSeparator()")
    manage_at = rebuild.rfind("self.workspace_menu.addAction(self.manage_workspaces_action)")
    require(separator_at >= 0 and separator_at < manage_at,
            "Manage Workspaces is not last after the Workspace separator", errors)
    for forbidden in (
        "ModuleScanner", "FilesystemWatcher", "repository", "rglob(",
        "os.walk(", ".is_dir(",
    ):
        require(forbidden not in rebuild,
                f"Workspace menu performs discovery work: {forbidden}", errors)

    for fragment in (
        'self.manage_workspaces_action = self._command("Manage Workspaces…", self._show_projects, "Ctrl+O")',
        'self.dashboard_action = self._command("Show Dashboard", self.editor_manager.show_dashboard, "Ctrl+W")',
        'self.save_dashboard_action = self._command("Save and Dashboard", self._save_and_dashboard, "Ctrl+Shift+W")',
        'self.save_new_action = self._command("Save and New", self._save_and_new, "Ctrl+Shift+S")',
        'self.new_folder_action = self._command("New Folder…", self._new_folder, "Ctrl+Shift+N")',
        'self.line_numbers_action = self._command("Line Numbers", self._toggle_line_numbers, "Ctrl+Alt+Shift+N", checkable=True)',
    ):
        require(fragment in window, f"Requested shortcut missing: {fragment}", errors)
    for shortcut in (
        "Ctrl+O", "Ctrl+W", "Ctrl+Shift+W", "Ctrl+Shift+S",
        "Ctrl+Shift+N", "Ctrl+Alt+Shift+N",
    ):
        require(window.count(f'"{shortcut}"') == 1,
                f"Shortcut is absent or duplicated: {shortcut}", errors)

    catalog_start = window.index("    def _shortcut_catalog")
    catalog_end = window.index("    def _show_shortcuts", catalog_start)
    catalog = window[catalog_start:catalog_end]
    require('(\"Manage Workspaces\", self.manage_workspaces_action)' in catalog,
            "Manage Workspaces is absent from Keyboard Shortcuts", errors)
    require("Import Markdown" not in catalog,
            "Removed Import command remains in Keyboard Shortcuts", errors)

    require('"File > Workspace(s) > Manage Workspaces to relink it."' in app,
            "Unavailable-Workspace guidance names an obsolete menu route", errors)

    if errors:
        print("Marko Plus exp3-r3 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r3 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
