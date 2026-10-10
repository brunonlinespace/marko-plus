#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.10 Item 1 source-authority gate."""
from __future__ import annotations

import ast
import hashlib
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def class_methods(path: Path, class_name: str) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    return {
        n.name for n in cls.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


init = (PKG / "__init__.py").read_text(encoding="utf-8")
constants = (PKG / "app_constants.py").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.4.10"' in init, "0.4.10 package identity missing")
req('APP_REVISION = "0.4.10"' in constants, "0.4.10 revision identity missing")
req('Current release: **0.4.10**' in readme, "README current release stale")

source_path = PKG / "widgets/markopad_source_editor.py"
code_path = PKG / "widgets/code_editor.py"
source = source_path.read_text(encoding="utf-8")
code = code_path.read_text(encoding="utf-8")

# Exact Markopad 0.2.4 authority hash.
req(
    sha(source_path) == "0264f2515d499c3a877742e08877535323b825021fe7c1c15d0f95a9c2f2e327",
    "vendored Markopad source editor is not the exact Markopad 0.2.4 authority",
)
for fragment in (
    "overwrite_mode_changed = pyqtSignal(bool)",
    "def _resize_gutter_above_horizontal_scrollbar(self) -> None:",
    "if key == Qt.Key.Key_Insert",
    "if modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Slash:",
    "def toggle_comment(self) -> None:",
):
    req(fragment in source, f"current Markopad authority behavior missing: {fragment}")

expected_adapter_methods = {
    "__init__",
    "keyPressEvent",
    "paste_safely",
    "delete_selection_or_character",
    "select_all_text",
    "go_to_line",
    "mark_clean",
    "is_modified",
}
req(
    class_methods(code_path, "CodeEditor") == expected_adapter_methods,
    "CodeEditor no longer contains exactly the approved Plus-only adapter surface",
)
for fragment in (
    "def toggle_comment(",
    "def _resize_gutter_above_horizontal_scrollbar(",
    "overwrite_mode_changed = pyqtSignal",
    "Key_Insert",
    "Key_Slash",
):
    req(fragment not in code, f"redundant Markopad catch-up behavior remains in CodeEditor: {fragment}")
for fragment in (
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
    req(fragment in code, f"genuine Plus adapter behavior missing: {fragment}")

# Item 32 and unrelated application surfaces are protected exactly at 0.4.9.
protected = {
    "widgets/main_window.py": "d71153fd5cbbbcd79e74492258fbbe6b89f12e80660aae69f5433697953e3e86",
    "widgets/editor_page.py": "8e5c510c8a3c1d8affc330165064a130996fb2928386a067a9fb0a8884993b7a",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "widgets/shell_ribbon.py": "87e93e981703fee9bd67b61c0fa316f9fc0fa696d99867cc50d8541eeec8eccb",
    "controllers/file_actions.py": "0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "widgets/navigation.py": "a075815775c4220ab1c707cc8a06c1ec5d6497d0a32ade39f177f1a151c7b35a",
}
for relative, digest in protected.items():
    req(sha(PKG / relative) == digest, f"out-of-scope 0.4.9 implementation changed: {relative}")

integration = (PKG / "tools/markopad_integration_check.py").read_text(encoding="utf-8")
req("Markopad 0.2.4" in integration, "integration gate does not name Markopad 0.2.4 authority")
req("r8.2 source editor" not in integration, "historical r8.2 source-editor authority remains active")

if errors:
    print("Marko Plus 0.4.10 check failed:")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)
print("PASS: Marko Plus 0.4.10 Item 1 source-editor authority contract")
