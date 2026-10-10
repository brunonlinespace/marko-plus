#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.8 Toggle Comment convergence gate."""
from __future__ import annotations

import ast
import hashlib
import textwrap
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
CODE_PATH = PACKAGE / "widgets" / "code_editor.py"
CODE = CODE_PATH.read_text(encoding="utf-8")
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


def method_source(source: str, class_name: str, method_name: str) -> str:
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)
    lines = source.splitlines()
    return textwrap.dedent("\n".join(lines[node.lineno - 1: node.end_lineno]))


init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.4.8"' in init, "0.4.8 package identity missing")
req('APP_REVISION = "0.4.8"' in constants, "0.4.8 revision identity missing")
req('Current release: **0.4.8**' in readme, "README current release stale")

# Exact Markopad 0.2.3 authority contract for Toggle Comment.
expected = '''def toggle_comment(self) -> None:
    """Toggle a Markdown-compatible HTML comment around the selection or current line."""
    if self.isReadOnly():
        self.view_only_edit_attempt.emit()
        return

    cursor = self.textCursor()
    if cursor.hasSelection():
        selected = cursor.selectedText().replace("\\u2029", "\\n")
        stripped = selected.strip()
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            leading = len(selected) - len(selected.lstrip())
            trailing = len(selected) - len(selected.rstrip())
            core = selected[leading: len(selected) - trailing if trailing else None]
            core = core[4:-3]
            if core.startswith(" "):
                core = core[1:]
            if core.endswith(" "):
                core = core[:-1]
            replacement = selected[:leading] + core + (selected[len(selected)-trailing:] if trailing else "")
        else:
            replacement = f"<!-- {selected} -->"
        if not self._replacement_fits(
            cursor.selectionStart(), cursor.selectionEnd(), len(replacement)
        ):
            self._reject_document_growth()
            return
        cursor.insertText(replacement)
        self.setTextCursor(cursor)
        return

    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
    text = cursor.selectedText()
    stripped = text.strip()
    if stripped.startswith("<!--") and stripped.endswith("-->"):
        leading = len(text) - len(text.lstrip())
        trailing = len(text) - len(text.rstrip())
        core = text[leading: len(text) - trailing if trailing else None][4:-3]
        if core.startswith(" "):
            core = core[1:]
        if core.endswith(" "):
            core = core[:-1]
        replacement = text[:leading] + core + (text[len(text)-trailing:] if trailing else "")
    else:
        replacement = f"<!-- {text} -->"
    if not self._replacement_fits(
        cursor.selectionStart(), cursor.selectionEnd(), len(replacement)
    ):
        self._reject_document_growth()
        return
    cursor.insertText(replacement)
    self.setTextCursor(cursor)
'''
actual = method_source(CODE, "CodeEditor", "toggle_comment")
req(actual.strip() == expected.strip(), "CodeEditor.toggle_comment no longer matches Markopad 0.2.3 authority")
req(actual.count("self._replacement_fits(") == 2, "Toggle Comment must guard both selection and current-line growth")
req(actual.count("self._reject_document_growth()") == 2, "Toggle Comment must reject both oversize mutation paths")
req(actual.count("self.setTextCursor(cursor)") == 2, "Toggle Comment cursor restoration drifted from Markopad")

# Inherited editor core and unrelated Plus surfaces stay exactly at the 0.4.7 state.
protected = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/main_window.py": "e5def185792b85e8a8e4704b368b91582c6b71503874debad54b16994f33a17e",
    "widgets/editor_page.py": "25ea31126089dcc79f10fd5fe7ef665f4ff2fa542769eeabbb98b9162e8796c1",
    "widgets/shell_ribbon.py": "87e93e981703fee9bd67b61c0fa316f9fc0fa696d99867cc50d8541eeec8eccb",
    "controllers/file_actions.py": "0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "widgets/navigation.py": "a075815775c4220ab1c707cc8a06c1ec5d6497d0a32ade39f177f1a151c7b35a",
}
for relative, digest in protected.items():
    req(sha(relative) == digest, f"out-of-scope protected file changed: {relative}")

req(
    sha("widgets/code_editor.py") == "bcecbc3c3bb5e744dce5683ab508578bec85901e323b313500745b27a48efb87",
    "CodeEditor contains changes outside the approved 0.4.8 convergence state",
)

if errors:
    print("Marko Plus 0.4.8 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.4.8 Toggle Comment convergence contract")
