#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r4 canvas revision."""

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


def main() -> int:
    errors: list[str] = []
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    require('"editor_canvas_light": None' in config,
            "Canvas preference does not preserve Markopad's first-run theme match", errors)
    for fragment in (
        '"Dark Editor", self._toggle_editor_canvas_light,',
        '"Ctrl+Alt+Shift+E", checkable=True,',
        'self.editor_canvas_theme_action.setChecked(not canvas_light)',
        'view.addAction(self.editor_canvas_theme_action)',
        '"editor_canvas_theme_action":"editor-canvas"',
        'self.editor_canvas_theme_action',
        '("Dark Editor", self.editor_canvas_theme_action)',
        'self.editor_manager.apply_editor_preferences()',
    ):
        require(fragment in window, f"Recovered Dark Editor wiring missing: {fragment}", errors)
    require(
        'self.config.set("editor_canvas_light", not bool(checked), save=True)' in window
        or '"editor_canvas_light": not bool(checked)' in window,
        "Recovered Dark Editor preference write is missing",
        errors,
    )
    require(window.count('"Ctrl+Alt+Shift+E"') == 1,
            "Dark Editor shortcut is absent or duplicated", errors)

    for fragment in (
        'self.editor.set_color_scheme("light" if canvas_light else "dark")',
        'base_color = QColor("#FFFFFF")',
        'text_color = QColor("#202124")',
        'highlight_color = QColor("#0B8781")',
        'base_color = QColor("#151719")',
        'text_color = QColor("#F1F3F4")',
        'highlight_color = QColor("#158B86")',
        'link_color = QColor("#174EA6")',
        'link_color = QColor("#82AAFF")',
        'preview_palette.setColor(QPalette.ColorRole.Link, link_color)',
        'preview_palette.setColor(QPalette.ColorRole.LinkVisited, link_color)',
        'self.preview.document().setDefaultStyleSheet(',
        'f"a {{ color: {link_color.name()}; }}"',
    ):
        require(fragment in page, f"Canvas or Preview-link styling missing: {fragment}", errors)

    for source in (PACKAGE / "services/config_service.py", PACKAGE / "widgets/editor_page.py", PACKAGE / "widgets/main_window.py"):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r4 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r4 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
