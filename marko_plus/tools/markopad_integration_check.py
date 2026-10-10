#!/usr/bin/env python3
"""Verify the current Markopad 0.2.4 editor/preview integration authority."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


SOURCE_HASH = "0264f2515d499c3a877742e08877535323b825021fe7c1c15d0f95a9c2f2e327"
PREVIEW_HASH = "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def class_methods(source: str, class_name: str) -> set[str]:
    tree = ast.parse(source)
    cls = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    return {
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    source = package / "widgets/markopad_source_editor.py"
    preview = package / "widgets/markopad_preview.py"
    wrapper_path = package / "widgets/code_editor.py"

    if digest(source) != SOURCE_HASH:
        raise SystemExit(
            "Vendored source editor no longer matches the exact Markopad 0.2.4 authority."
        )
    if digest(preview) != PREVIEW_HASH:
        raise SystemExit(
            "Vendored preview no longer matches the exact Markopad 0.2.4 preview authority."
        )

    wrapper = wrapper_path.read_text(encoding="utf-8")
    methods = class_methods(wrapper, "CodeEditor")
    expected_methods = {
        "__init__",
        "keyPressEvent",
        "paste_safely",
        "delete_selection_or_character",
        "select_all_text",
        "go_to_line",
        "mark_clean",
        "is_modified",
    }
    if methods != expected_methods:
        raise SystemExit(
            "CodeEditor adapter surface drifted from the approved Plus-only method set: "
            f"{sorted(methods)!r}"
        )

    for forbidden in (
        "def toggle_comment(",
        "def _resize_gutter_above_horizontal_scrollbar(",
        "overwrite_mode_changed = pyqtSignal",
        "Key_Insert",
        "Key_Slash",
    ):
        if forbidden in wrapper:
            raise SystemExit(
                "CodeEditor still duplicates behavior owned by Markopad 0.2.4: "
                f"{forbidden}"
            )

    for required in (
        "class CodeEditor(MarkopadSourceEditor)",
        "go_to_line_requested = pyqtSignal()",
        "Qt.Key.Key_G",
        "Qt.Key.Key_D",
        "super().keyPressEvent(event)",
        "def paste_safely",
        "def delete_selection_or_character",
        "def select_all_text",
        "def go_to_line",
        "def mark_clean",
        "def is_modified",
    ):
        if required not in wrapper:
            raise SystemExit(f"Missing genuine Marko Plus editor adapter contract: {required}")

    print("Markopad 0.2.4 source-editor authority checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
