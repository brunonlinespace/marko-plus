#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r8 revision."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"
PROTECTED_ENGINES = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_in_order(source: str, fragments: tuple[str, ...], message: str, errors: list[str]) -> None:
    cursor = -1
    for fragment in fragments:
        cursor = source.find(fragment, cursor + 1)
        if cursor < 0:
            errors.append(f"{message}: {fragment}")
            return


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    memory = (PACKAGE / "docs/PROJECT_MEMORY.md").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    require('APP_REVISION = "exp3-r8"' in constants or
            'APP_REVISION = "exp3-r9"' in constants or
            'APP_REVISION = "exp3-r10"' in constants or
            'APP_REVISION = "exp3-r11"' in constants or
            'APP_REVISION = "0.0.1"' in constants or
            'APP_REVISION = "0.0.1-r3"' in constants,
            "Current source revision predates exp3-r8", errors)
    require('"app_launch_screen": "dashboard"' in config,
            "Dashboard is not the default launch screen", errors)
    require("editor_palette.setColor(QPalette.ColorRole.Window, base_color)" not in page,
            "The deferred r7 scrollbar palette workaround remains", errors)

    view_menu = window[
        window.index('view = bar.addMenu("&View")'):
        window.index('settings = bar.addMenu("&Settings")')
    ]
    require_in_order(
        view_menu,
        (
            "view.addAction(self.fullscreen_action)",
            "view.addAction(self.view_only_action)",
            "view.addAction(self.sidebar_action)",
            "view.addAction(self.status_bar_action)",
            "view.addAction(self.word_wrap_action)",
            "view.addAction(self.line_numbers_action)",
            "view.addAction(self.editor_canvas_theme_action)",
            'zoom = view.addMenu("Editor Zoom")',
            'layout_menu = view.addMenu("Editor Layout")',
            'more_settings = view.addMenu("Editor Miscellaneous")',
        ),
        "View menu order is incomplete",
        errors,
    )
    for moved in ("App Theme", "App Dashboard", "App Launch Screen", "App Drag-and-Drop"):
        require(moved not in view_menu, f"{moved} remains in View", errors)

    settings_menu = window[
        window.index('settings = bar.addMenu("&Settings")'):
        window.index('help_menu = bar.addMenu("&Help")')
    ]
    require_in_order(
        settings_menu,
        (
            'theme_menu = settings.addMenu("App Theme")',
            'dashboard_menu = settings.addMenu("App Dashboard")',
            "settings.addSeparator()",
            'launch_screen_menu = settings.addMenu("App Launch Screen")',
            'drop_menu = settings.addMenu("App Drag-and-Drop")',
        ),
        "Settings menu order is incomplete",
        errors,
    )
    require('"Settings": [[' in window,
            "Settings tab is missing or out of order", errors)
    for fragment in (
        '"Show Status", self._toggle_status_bar,',
        'self.launch_dashboard_action.setChecked(',
        'self.launch_last_file_action.setChecked(',
        'def _set_app_launch_screen',
        'self.config.set("app_launch_screen", screen, save=True)',
        'self._startup_open_requested = True',
        'self.editor_manager.current_module_changed.connect(self._remember_last_opened_module)',
        'def _remember_last_opened_module',
        'if self.app_launch_screen != "last_file":',
        'self.editor_manager.open_module(module)',
    ):
        require(fragment in window, f"Launch-screen or label behavior missing: {fragment}", errors)

    scan_body = window[
        window.index("    def _on_scan_finished"):
        window.index("    def _on_scan_failed")
    ]
    require("last_opened_folder" not in scan_body,
            "Last File mode still restores folder dashboards", errors)
    require('{"last_opened_file": None' not in scan_body,
            "Opening Last File still erases its history", errors)

    for shortcut, label in (
        ('"Ctrl+Alt+Shift+S"', "Show Status"),
        ('"Ctrl+Alt+Shift+E"', "Dark Editor"),
        ('"Ctrl+Alt+Shift+D"', "Toggle List/Grid View"),
    ):
        require(window.count(shortcut) == 1,
                f"{label} shortcut is missing or duplicated", errors)

    gutter_at = memory.find("correct the\n  source gutter geometry")
    tree_at = memory.find("Only after that gutter correction")
    gutter_completed = "completed the gutter geometry correction" in memory
    tree_still_deferred = (
        "experimental folder-tree keyboard/navigation line may now begin" in memory
        and "remains deferred from the normal revision line" in memory
    )
    require(
        (gutter_at >= 0 and tree_at > gutter_at)
        or (gutter_completed and tree_still_deferred),
        "Gutter/tree experiment ordering is missing",
        errors,
    )
    require(all(label in memory for label in (
                "Editor Zoom", "Editor Layout", "Editor Miscellaneous")),
            "Markopad submenu-label backport reminder is missing", errors)

    for source in (
        PACKAGE / "app_constants.py",
        PACKAGE / "services/config_service.py",
        PACKAGE / "widgets/editor_page.py",
        PACKAGE / "widgets/main_window.py",
    ):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r8 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r8 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
