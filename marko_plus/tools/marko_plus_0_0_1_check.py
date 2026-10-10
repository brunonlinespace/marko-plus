#!/usr/bin/env python3
"""Checks for the focused Marko Plus 0.0.1-r3 correction release."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"
PROTECTED_ENGINES = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    package_init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    page_path = PACKAGE / "widgets/editor_page.py"
    page = page_path.read_text(encoding="utf-8")
    release_notes = (PACKAGE / "docs/RELEASE_NOTES.md").read_text(encoding="utf-8")
    about = (PACKAGE / "widgets/about_dialog.py").read_text(encoding="utf-8")
    manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

    require('APP_VERSION = "0.0.1-r3"' in package_init,
            "Package version is not 0.0.1-r3", errors)
    require('APP_REVISION = "0.0.1-r3"' in constants,
            "About-dialog revision is not 0.0.1-r3", errors)
    require(manifest.get("version") == "0.0.1-r3",
            "Project manifest version is not 0.0.1-r3", errors)
    require(manifest.get("repository") == "https://github.com/brunonlinespace/marko-plus",
            "Project repository is not the Marko Plus repository", errors)

    for relative, expected in PROTECTED_ENGINES.items():
        require(digest(PACKAGE / relative) == expected,
                f"Protected Markopad engine changed: {relative}", errors)

    require('"preview_italic_quotes": False' in config,
            "Quote-effect default is missing", errors)
    for fragment in (
        'QCheckBox("Italicize block quotations", effects)',
        'dialog.findChildren(QGroupBox)',
        'effects.layout()',
        "QFontDialog.FontDialogOption.DontUseNativeDialog",
        'self.config.get("preview_italic_quotes", False)',
        '"preview_italic_quotes": italic_quotes.isChecked()',
        "italic_quotes.setEnabled(not already_italic)",
        "def _apply_preview_quote_effect(self) -> None:",
        "QTextFormat.Property.BlockQuoteLevel",
        "italic.setFontItalic(True)",
        "cursor.mergeCharFormat(italic)",
        "self._apply_preview_quote_effect()",
    ):
        require(fragment in page, f"Preview Font effect missing: {fragment}", errors)

    require('QGroupBox("Effects", dialog)' not in page,
            "Preview Font still creates a duplicate Effects box", errors)
    require("Preview Font correction release" in release_notes,
            "0.0.1-r3 release notes are missing", errors)
    require("No preview colour controls or text themes are added" in release_notes,
            "The intentionally narrow scope is not recorded", errors)
    require("Preview Colours" not in page,
            "Deferred Preview Colours UI was added", errors)
    for fragment in (
        "self.setMinimumSize(560, 560)",
        "self.resize(620, 620)",
        "details.setWordWrap(True)",
        '.replace("/", "/&#8203;")',
        "GITHUB_URL",
    ):
        require(fragment in about, f"About correction missing: {fragment}", errors)

    try:
        ast.parse(page, filename=str(page_path))
    except SyntaxError as exc:
        errors.append(f"Could not parse EditorPage: {exc}")

    if errors:
        print("Marko Plus 0.0.1-r3 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Marko Plus 0.0.1-r3 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
