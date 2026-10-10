#!/usr/bin/env python3
"""Static checks for the surgical Marko Plus exp3-r2 corrections."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def visible_project_strings(source: str) -> list[str]:
    """Return literal user-facing strings that still use Project terminology."""
    strings: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = node.value
        if "project" not in value.casefold():
            continue
        # The persisted registry key and QAction attribute are compatibility
        # internals, not labels presented to the user.
        if value in {"projects", "change_project_action"}:
            continue
        strings.append(value)
    return strings


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    app = (PACKAGE / "app.py").read_text(encoding="utf-8")
    registry = (PACKAGE / "services/project_registry.py").read_text(encoding="utf-8")
    first_run = (PACKAGE / "widgets/first_run_dialog.py").read_text(encoding="utf-8")
    workspaces = (PACKAGE / "widgets/projects_dialog.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")

    require(not (PACKAGE / "widgets/preferences_dialog.py").exists(),
            "Preferences dialog module still exists", errors)
    for forbidden in (
        "PreferencesDialog", "preferences_action", "_show_preferences",
        'self._command("Preferences…"', "view.addAction(self.preferences_action)",
    ):
        require(forbidden not in window,
                f"Preferences dialog entry point remains: {forbidden}", errors)

    for source_name, source in (
        ("app.py", app),
        ("main_window.py", window),
        ("projects_dialog.py", workspaces),
        ("first_run_dialog.py", first_run),
    ):
        stale = visible_project_strings(source)
        require(not stale,
                f"Visible Project terminology remains in {source_name}: {stale}", errors)
    for fragment in (
        'self.manage_workspaces_action = self._command("Manage Workspaces…"',
        'file_menu.addMenu("Workspace(s)")',
        'self.setWindowTitle("Change Workspace — Marko Plus")',
        'open_button.setText("Open Workspace")',
        '"Workspace Name"',
        '"Workspace label:"',
        '"Remove Workspace Registration"',
        '"File > Workspace(s) > Manage Workspaces to relink it."',
    ):
        require(fragment in app or fragment in window or fragment in workspaces,
                f"Workspace relabel missing: {fragment}", errors)
    require('"projects"' in registry and '"active_project_id"' in registry,
            "Compatible persisted registry keys changed", errors)

    for fragment in (
        'self.new_folder_action = self._command("New Folder…", self._new_folder, "Ctrl+Shift+N")',
        'self.save_new_action = self._command("Save and New", self._save_and_new, "Ctrl+Shift+S")',
        'self.line_numbers_action = self._command("Line Numbers", self._toggle_line_numbers, "Ctrl+Alt+Shift+N", checkable=True)',
    ):
        require(fragment in window, f"Shortcut correction missing: {fragment}", errors)
    require(window.count('"Ctrl+Shift+N"') == 1,
            "Ctrl+Shift+N is not exclusive to New Folder", errors)
    require(window.count('"Ctrl+Shift+S"') == 1,
            "Ctrl+Shift+S is not exclusive to Save and New", errors)
    require(window.count('"Ctrl+Alt+Shift+N"') == 1,
            "Ctrl+Alt+Shift+N is not exclusive to Line Numbers", errors)

    require("def _update_window_title" in window and
            "self.setWindowTitle(workspace_name)" in window,
            "Title bar does not use the active Workspace name", errors)
    require(window.count("self._update_window_title()") >= 3,
            "Workspace title is not refreshed at startup and after registry changes", errors)
    require('APP_DISPLAY_NAME = APP_BRAND_NAME' in constants and
            "Markdown Workspace" not in constants,
            "Generic Markdown Workspace display name remains", errors)

    quick_start = window[
        window.index("    def _show_quick_tour"):
        window.index("    def _current_page")
    ]
    for fragment in (
        "File → Workspace(s)",
        "Only the active Workspace is scanned and watched",
        "one click selects a card",
        "Ctrl+Up",
        "Ctrl+Down",
        "External files dropped on a folder",
        "opens as soon as its name is",
        "Source Only, Source + Preview and Preview Only",
        "View Only protects source text",
        "Save and New, Save and",
    ):
        require(fragment in quick_start,
                f"Established Quick Tour behavior missing: {fragment}", errors)

    if errors:
        print("Marko Plus exp3-r2 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r2 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
