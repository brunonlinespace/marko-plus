#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r5 preview revision."""

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
    about = (PACKAGE / "widgets/about_dialog.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    require(
        'APP_REVISION = "exp3-r5"' in constants
        or 'APP_REVISION = "exp3-r6"' in constants
        or 'APP_REVISION = "exp3-r7"' in constants
        or 'APP_REVISION = "exp3-r8"' in constants
        or 'APP_REVISION = "exp3-r9"' in constants
        or 'APP_REVISION = "exp3-r10"' in constants
        or 'APP_REVISION = "exp3-r11"' in constants
        or 'APP_REVISION = "0.0.1"' in constants
        or 'APP_REVISION = "0.0.1-r3"' in constants,
        "Current source revision no longer carries the r5 fixes",
        errors,
    )
    require('APP_BRAND_NAME, APP_REVISION' in about,
            "About dialog does not use the current source revision", errors)
    require('QLabel(f"Version {APP_REVISION}", self)' in about,
            "About dialog does not display exp3-r5", errors)

    for fragment in (
        "def _apply_preview_link_color",
        'QColor("#174EA6" if canvas_light else "#82AAFF")',
        "fragment.charFormat().isAnchor()",
        "anchor_format.setForeground(link_color)",
        "cursor.setCharFormat(anchor_format)",
        "self._apply_preview_link_color(link_color)",
        "self._apply_preview_link_color()",
        "preview_palette.setColor(QPalette.ColorRole.Link, link_color)",
        "preview_palette.setColor(QPalette.ColorRole.LinkVisited, link_color)",
    ):
        require(fragment in page, f"Permanent blue-link handling missing: {fragment}", errors)

    render_at = page.index("self.preview.render_markdown(self.editor.toPlainText())")
    recolor_at = page.index("self._apply_preview_link_color()", render_at)
    require(render_at < recolor_at,
            "Preview anchors are not recolored after Markdown rendering", errors)

    for source in (
        PACKAGE / "app_constants.py",
        PACKAGE / "widgets/about_dialog.py",
        PACKAGE / "widgets/editor_page.py",
    ):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r5 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r5 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
