#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r7 revision."""

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
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    memory = (PACKAGE / "docs/PROJECT_MEMORY.md").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    require(
        'APP_REVISION = "exp3-r7"' in constants
        or 'APP_REVISION = "exp3-r8"' in constants
        or 'APP_REVISION = "exp3-r9"' in constants
        or 'APP_REVISION = "exp3-r10"' in constants
        or 'APP_REVISION = "exp3-r11"' in constants
        or 'APP_REVISION = "0.0.1"' in constants
        or 'APP_REVISION = "0.0.1-r3"' in constants,
        "Current source revision no longer carries the r7 command work",
        errors,
    )

    file_menu = window[
        window.index('file_menu = bar.addMenu("&File")'):
        window.index('edit = bar.addMenu("&Edit")')
    ]
    require_in_order(
        file_menu,
        (
            "for action in (self.new_action, self.new_folder_action): file_menu.addAction(action)",
            "file_menu.addSeparator()",
            "file_menu.addAction(self.dashboard_action)",
            'file_menu.addMenu("Workspace(s)")',
        ),
        "File menu placement is incomplete",
        errors,
    )

    view_menu = window[
        window.index('view = bar.addMenu("&View")'):
        window.index('help_menu = bar.addMenu("&Help")')
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
        "View menu placement is incomplete",
        errors,
    )
    require("dashboard_menu.addAction(self.dashboard_action)" not in view_menu,
            "Show Dashboard remains in View", errors)

    for shortcut, label in (
        ('"Ctrl+Alt+Shift+S"', "Status Bar"),
        ('"Ctrl+Alt+Shift+E"', "Dark Editor"),
        ('"Ctrl+Alt+Shift+D"', "Toggle List/Grid View"),
    ):
        require(window.count(shortcut) == 1,
                f"{label} shortcut is missing or duplicated", errors)
    require("remap markopad's dark editor shortcut to" in memory.casefold()
            and "Ctrl+Alt+Shift+E" in memory,
            "Future Markopad shortcut reminder is missing", errors)

    for source in (
        PACKAGE / "app_constants.py",
        PACKAGE / "widgets/editor_page.py",
        PACKAGE / "widgets/main_window.py",
    ):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r7 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r7 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
