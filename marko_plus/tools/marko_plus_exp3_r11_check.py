#!/usr/bin/env python3
"""Checks for the surgical Marko Plus exp3-r11 shortcut-search revision."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import re


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


def load_search_helpers(source: str):
    tree = ast.parse(source, filename="shortcuts_dialog.py")
    wanted = {
        "_SHORTCUT_TOKEN_RE",
        "_SHORTCUT_TOKEN_ALIASES",
        "_shortcut_tokens",
        "_shortcut_query_matches",
    }
    selected: list[ast.stmt] = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            names = {
                target.id
                for target in (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                if isinstance(target, ast.Name)
            }
            if names & wanted:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted:
            selected.append(node)
    namespace = {"re": re}
    exec(compile(ast.Module(selected, type_ignores=[]), "shortcuts_dialog.py", "exec"), namespace)
    return namespace["_shortcut_tokens"], namespace["_shortcut_query_matches"]


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    dialog_path = PACKAGE / "widgets/shortcuts_dialog.py"
    dialog = dialog_path.read_text(encoding="utf-8")
    memory = (PACKAGE / "docs/PROJECT_MEMORY.md").read_text(encoding="utf-8")

    require('APP_REVISION = "exp3-r11"' in constants or
            'APP_REVISION = "0.0.1"' in constants or
            'APP_REVISION = "0.0.1-r3"' in constants,
            "Current source revision predates exp3-r11", errors)
    for relative, expected in PROTECTED_ENGINES.items():
        require(digest(PACKAGE / relative) == expected,
                f"Protected Markopad engine changed: {relative}", errors)

    for fragment in (
        '"control": "ctrl"',
        '"ctrl": "ctrl"',
        '"ctl": "ctrl"',
        "def _shortcut_tokens",
        "def _shortcut_query_matches",
        "_shortcut_tokens(shortcut)",
        "_shortcut_query_matches(query, shortcut_tokens)",
        "or query in label_search",
        '(selected == "All" or selected == tab_name)',
    ):
        require(fragment in dialog, f"Shortcut-search behavior missing: {fragment}", errors)

    try:
        tokenize, matches = load_search_helpers(dialog)
        target = tokenize("Ctrl+Alt+Shift+N")
        for query in (
            "control alt shift",
            "CONTROL+ALT+SHIFT",
            "ctl shift alt",
            "shift+control+alt",
            "alt ctrl shift n",
        ):
            require(matches(query, target),
                    f"Expected shortcut query did not match: {query}", errors)
        for query in ("ctrl q", "meta shift", "ctrl al"):
            require(not matches(query, target),
                    f"Unrelated shortcut query matched: {query}", errors)
    except Exception as exc:
        errors.append(f"Could not exercise shortcut normalization: {exc}")

    require("Marko Plus exp3-r11 completed the controlled fuzzy search" in memory,
            "Completed r11 behavior is not recorded", errors)
    require("still to be backported to Markopad" in memory,
            "Markopad backport reminder is missing", errors)

    try:
        ast.parse(dialog, filename=str(dialog_path))
    except SyntaxError as exc:
        errors.append(f"Could not parse shortcuts dialog: {exc}")

    if errors:
        print("Marko Plus exp3-r11 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Marko Plus exp3-r11 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
