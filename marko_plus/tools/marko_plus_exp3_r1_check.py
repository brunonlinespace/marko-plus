#!/usr/bin/env python3
"""Static checks for the Markopad parity corrections in exp3-r1."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def assigned_shortcut_actions(tree: ast.AST) -> set[str]:
    """Return self attributes created by _command with a shortcut argument."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if (
            not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Attribute)
            or value.func.attr != "_command"
            or len(value.args) < 3
        ):
            continue
        shortcut = value.args[2]
        if isinstance(shortcut, ast.Constant) and shortcut.value is None:
            continue
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                names.add(target.attr)
    return names


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    editor = (PACKAGE / "widgets/code_editor.py").read_text(encoding="utf-8")
    window_path = PACKAGE / "widgets/main_window.py"
    window = window_path.read_text(encoding="utf-8")
    shortcuts = (PACKAGE / "widgets/shortcuts_dialog.py").read_text(encoding="utf-8")

    require('"preview_font": ""' in config, "Preview font setting missing", errors)
    for fragment in (
        "def preview_base_font",
        'self.config.get("preview_font", "")',
        "candidate.fromString(stored)",
        "def apply_preview_font",
        "self.preview.document().setDefaultFont",
        "def choose_preview_font",
        '"preview_font": selected.toString()',
        "self.refresh_preview_now(force=True)",
    ):
        require(fragment in page, f"Markopad Preview font behavior missing: {fragment}", errors)
    require('self.preview_font_action = self._command("Preview Font…"' in window,
            "Preview Font action missing", errors)
    require("page.preview.setFont(QApplication.font())" not in window,
            "Zoom reset still overwrites the selected Preview font", errors)

    for fragment in (
        "QTableWidget",
        'setHorizontalHeaderLabels(["Command", "Shortcut"])',
        'setPlaceholderText("Search commands or shortcuts")',
        'QLabel("Tab:", self)',
        'self.category.addItems(["All", *catalog.keys()])',
        "QAbstractItemView.EditTrigger.NoEditTriggers",
        "QAbstractItemView.SelectionBehavior.SelectRows",
        'QLabel("No matching shortcuts.", self)',
        "Qt.WidgetAttribute.WA_DeleteOnClose",
        "self.setModal(False)",
    ):
        require(fragment in shortcuts, f"Markopad Shortcuts style missing: {fragment}", errors)
    require("QScrollArea" not in shortcuts and "<table" not in shortcuts,
            "Legacy shortcuts presentation remains", errors)

    catalog_start = window.index("    def _shortcut_catalog")
    catalog_end = window.index("    def _show_shortcuts", catalog_start)
    catalog = window[catalog_start:catalog_end]
    assigned = assigned_shortcut_actions(ast.parse(window, filename=str(window_path)))
    missing_actions = sorted(
        name for name in assigned if f"self.{name}" not in catalog
    )
    require(not missing_actions,
            f"Assigned actions missing from Shortcuts dialog: {missing_actions}", errors)
    require("self.heading_actions" in catalog,
            "Heading 0–6 shortcuts are not catalogued", errors)
    for label, binding, evidence in (
        ("Find Next", "F3", 'shortcut="F3"'),
        ("Find Previous", "Shift+F3", 'shortcut="Shift+F3"'),
        ("Clear Search", "Esc", 'shortcut="Esc"'),
        ("Toggle Comment", "Ctrl+/", "Qt.Key.Key_Slash"),
        ("Toggle Overwrite Mode", "Insert", "Qt.Key.Key_Insert"),
    ):
        require(f'("{label}", "{binding}")' in catalog,
                f"Existing editor shortcut is not catalogued: {label}", errors)
        require(evidence in page or evidence in editor,
                f"Catalogued shortcut has no implementation evidence: {label}", errors)

    for fragment in (
        'self.save_new_action = self._command("Save and New", self._save_and_new, "Ctrl+Shift+S")',
        'self.save_dashboard_action = self._command("Save and Dashboard", self._save_and_dashboard, "Ctrl+Shift+W")',
        'self.save_exit_action = self._command("Save and Exit", self._save_and_exit, "Ctrl+Shift+Q")',
        'self.properties_action = self._command("Properties", self._show_properties, "F4")',
        'self.line_numbers_action = self._command("Line Numbers", self._toggle_line_numbers, "Ctrl+Alt+Shift+N", checkable=True)',
        'self.new_folder_action = self._command("New Folder…", self._new_folder, "Ctrl+Shift+N")',
    ):
        require(fragment in window, f"Requested shortcut assignment missing: {fragment}", errors)
    save_new_start = window.index("    def _save_and_new")
    save_new_end = window.index("    def _save_and_dashboard", save_new_start)
    save_new = window[save_new_start:save_new_end]
    require(save_new.find("page.save_to_disk()") < save_new.find("self._new_markdown_file()"),
            "Save and New does not save before creating", errors)
    require(window.count('"Ctrl+Shift+S"') == 1,
            "Save and New shortcut conflicts with another action", errors)
    require(window.count('"Ctrl+Shift+N"') == 1,
            "New Folder shortcut conflicts with another action", errors)
    require(window.count('"Ctrl+Alt+Shift+N"') == 1,
            "Line Numbers shortcut conflicts with another action", errors)

    require('GITHUB_URL = "https://github.com/brunonlinespace/marko-plus"' in constants,
            "Canonical Markopad GitHub URL is not restored", errors)
    require('self.github_action = self._command("GitHub Repository"' in window and
            'self.issue_action = self._command("Raise an Issue"' in window,
            "GitHub/Issue actions are missing", errors)
    help_start = window.index('help_menu = bar.addMenu("&Help")')
    help_end = window.index("self._refresh_action_icons()", help_start)
    help_menu = window[help_start:help_end]
    ordered = (
        "self.docs_action",
        "self.quick_start_action",
        "self.shortcuts_action",
        "self.github_action",
        "self.issue_action",
        "self.about_action",
    )
    positions = [help_menu.find(item) for item in ordered]
    require(all(position >= 0 for position in positions) and positions == sorted(positions),
            "Help actions do not follow canonical Markopad order", errors)
    require(help_menu.count("help_menu.addSeparator()") == 3,
            "Help menu does not have Markopad's three separators", errors)
    require('"Help": [[self.docs_action, self.quick_start_action, self.shortcuts_action], [self.github_action, self.issue_action], [self.about_action]]' in window,
            "Help Tabbed page does not follow Markopad grouping", errors)

    if errors:
        print("Marko Plus exp3-r1 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r1 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
