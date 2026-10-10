#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.7 Item 30 Paste semantic-correction gate."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
MAIN_PATH = PACKAGE / "widgets" / "main_window.py"
MAIN = MAIN_PATH.read_text(encoding="utf-8")
EDITOR_PAGE = (PACKAGE / "widgets" / "editor_page.py").read_text(encoding="utf-8")
RIBBON = (PACKAGE / "widgets" / "shell_ribbon.py").read_text(encoding="utf-8")
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


def method_source(name: str) -> str:
    tree = ast.parse(MAIN)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(MAIN, node) or ""


init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.4.7"' in init, "0.4.7 package identity missing")
req('APP_REVISION = "0.4.7"' in constants, "0.4.7 revision identity missing")
req('Current release: **0.4.7**' in readme, "README current release stale")

# Visible QAction contract: normal Paste is smart, Ctrl+Shift+V is explicitly plain.
req(
    'self.paste_action = self._command("Paste", self._paste, QKeySequence.StandardKey.Paste)' in MAIN,
    "Paste is not the smart StandardKey.Paste command",
)
req(
    'self.paste_plain_action = self._command("Paste as Plain Text", self._paste_plain_text, "Ctrl+Shift+V")' in MAIN,
    "Paste as Plain Text Ctrl+Shift+V command missing",
)
req('Paste as Markdown' not in MAIN, "obsolete visible Paste as Markdown wording remains in MainWindow")
req('paste_markdown_action' not in MAIN, "obsolete paste_markdown_action remains in MainWindow")

smart = method_source("_paste")
for fragment in (
    'mime.hasHtml()',
    'doc = QTextDocument()',
    'doc.setHtml(html)',
    'text = doc.toMarkdown()',
    'text = doc.toPlainText()',
    'data:[^\\n)]*',
    'page.editor.insert_guarded_text(text)',
):
    req(fragment in smart, f"smart Paste conversion contract missing: {fragment}")
req('page.editor.paste_safely()' not in smart, "normal Paste still routes to literal text paste")

plain = method_source("_paste_plain_text")
req('page.editor.paste_safely()' in plain, "Paste as Plain Text does not route to existing guarded literal paste")
req('mime.hasHtml()' not in plain, "Paste as Plain Text unexpectedly performs rich conversion")

# AppMenu/Ribbon/action-state wiring must use the corrected pair.
req(
    'for action in (self.cut_action, self.copy_action, self.paste_action, self.paste_plain_action): edit.addAction(action)' in MAIN,
    "Edit AppMenu Paste pair not corrected",
)
req('paste_plain_action' in RIBBON and 'paste_markdown_action' not in RIBBON, "ShellRibbon Paste pair not corrected")
req('self.paste_plain_action = self._menu_action(edit_menu, "Paste as Plain Text", self.editor.paste_safely)' in EDITOR_PAGE,
    "EditorPage private literal-paste action not semantically corrected")

icons = method_source("_refresh_action_icons")
req('"paste_action":"paste"' in icons, "Paste icon mapping changed/missing")
req('"paste_plain_action":"paste-plain"' in icons, "Paste as Plain Text icon mapping missing")
req('paste-markdown' not in icons, "paste-markdown icon is still wired")

# All three canonical icon assets remain byte-for-byte present. paste-markdown is deliberately unwired, not retired.
asset_hashes = {
    "assets/toolbar-icons/light/paste.png": "a1d4e4a3feb57fe943fcc756e1c5ba2316d9d6c1b8444cdc6622750948bd2504",
    "assets/toolbar-icons/light/paste-plain.png": "483a48c75b4e0bdada4d5f6e274acaf15264f4d4ceb569852f0ea26e51497df4",
    "assets/toolbar-icons/light/paste-markdown.png": "d1359fbd60bc8247bb78af00a0f013d953f93862e8320ffd21b8994bdef64b3e",
    "assets/toolbar-icons/dark/paste.png": "824604b2dd8eeaaa9a6575967cba4f0a3d960ae25409f6a2289ff9f610146cec",
    "assets/toolbar-icons/dark/paste-plain.png": "a0fa3cd350f5f8e509fc76d3f1dad4610d21f96215de5d9d8855e2866933e171",
    "assets/toolbar-icons/dark/paste-markdown.png": "c0af62f91e93091d3b0e3b14fb56bf5ce94733d3d734903dcdb09a97628e2932",
}
for relative, digest in asset_hashes.items():
    req((PACKAGE / relative).is_file(), f"canonical Paste asset missing: {relative}")
    if (PACKAGE / relative).is_file():
        req(sha(relative) == digest, f"canonical Paste asset changed: {relative}")

# Protect unrelated Plus-family behavior and the underlying literal paste engine.
protected = {
    "widgets/code_editor.py": "b0299c063a23d93bea0a9afdf4bfceb16d8843867f5382a02824cd27bbcb4831",
    "controllers/file_actions.py": "0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "widgets/navigation.py": "a075815775c4220ab1c707cc8a06c1ec5d6497d0a32ade39f177f1a151c7b35a",
}
for relative, digest in protected.items():
    req(sha(relative) == digest, f"out-of-scope protected file changed: {relative}")

if errors:
    print("Marko Plus 0.4.7 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.4.7 Item 30 Paste semantic-correction contract")
