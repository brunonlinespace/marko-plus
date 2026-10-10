#!/usr/bin/env python3
"""Static checks for Marko Plus exp3-r10 editor preference corrections."""

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
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    adapter = (PACKAGE / "widgets/code_editor.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    memory = (PACKAGE / "docs/PROJECT_MEMORY.md").read_text(encoding="utf-8")

    require('APP_REVISION = "exp3-r10"' in constants or
            'APP_REVISION = "exp3-r11"' in constants or
            'APP_REVISION = "0.0.1"' in constants or
            'APP_REVISION = "0.0.1-r3"' in constants,
            "Current source revision predates exp3-r10", errors)
    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    for fragment in (
        '"editor_view_only": False',
        '"editor_canvas_follows_app_theme": True',
        '"editor_canvas_light": None',
    ):
        require(fragment in config, f"Config default missing: {fragment}", errors)

    for fragment in (
        'def _canvas_is_light(self) -> bool:',
        'self.config.get("editor_canvas_follows_app_theme", True)',
        'canvas_light = self._canvas_is_light()',
        'self.view_only = bool(self.config.get("editor_view_only", False))',
        'self.config.set("editor_view_only", requested, save=True)',
        'def _apply_view_only_state(self, requested: bool) -> None:',
        'bool(self.config.get("editor_view_only", False))',
    ):
        require(fragment in page, f"Editor preference behavior missing: {fragment}", errors)

    for fragment in (
        '"editor_canvas_follows_app_theme": False',
        '"editor_canvas_light": not bool(checked)',
        'self.editor_manager.apply_editor_preferences()',
        'self.view_only_action.setChecked(bool(self.config.get("editor_view_only", False)))',
    ):
        require(fragment in window, f"Main-window preference wiring missing: {fragment}", errors)
    require('self.config.set("editor_canvas_light", canvas_light)' not in window,
            "Startup still converts the inherited canvas into an override", errors)

    for fragment in (
        'def resizeEvent(self, event) -> None:',
        'def _resize_gutter_above_horizontal_scrollbar(self) -> None:',
        'self.horizontalScrollBar().rangeChanged.connect(',
        'if horizontal.isVisible():',
        'gutter_height = max(0, gutter_height - horizontal.height())',
        'self.line_number_area.setGeometry(QRect(',
    ):
        require(fragment in adapter, f"Adapter gutter correction missing: {fragment}", errors)
    require("completed the gutter geometry correction" in memory,
            "Completed gutter correction is not recorded", errors)
    require("remains deferred from the normal revision line" in memory,
            "Folder-tree experiment is not still deferred", errors)

    for source in (
        PACKAGE / "app_constants.py",
        PACKAGE / "services/config_service.py",
        PACKAGE / "widgets/code_editor.py",
        PACKAGE / "widgets/editor_page.py",
        PACKAGE / "widgets/main_window.py",
    ):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r10 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Marko Plus exp3-r10 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
