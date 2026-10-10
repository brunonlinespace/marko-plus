#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.7 Find/Symbols corrective gate."""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def src(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")


def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


page = src("widgets/editor_page.py")
init = src("__init__.py")
constants = src("app_constants.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.3.7"' in init, "0.3.7 package identity missing")
req('APP_REVISION = "0.3.7"' in constants, "0.3.7 revision identity missing")
req('Current release: **0.3.7**' in readme, "root README current release is stale")

# Find: a successful fresh search must immediately have an active result, and
# Marko's established gold active-match painter must remain in use.
req('active_bg = QColor("#FFD54F")' in page, "gold active Find highlight missing")
find_match = re.search(
    r"def find_text\(self, show_message: bool = True\).*?return bool\(self\._search_matches\)",
    page,
    re.S,
)
req(find_match is not None, "find_text implementation missing")
if find_match:
    body = find_match.group(0)
    req('if self._search_matches:' in body, "successful Find does not establish an active result")
    req('self._current_search_index = 0' in body, "fresh Find does not activate the first result")
    req('self._refresh_search_highlights()' in body, "fresh Find does not repaint search highlights")
    req(
        body.index('self._current_search_index = 0') < body.index('self._refresh_search_highlights()'),
        "active result is established only after highlight refresh",
    )
req('active_bg if index == self._current_search_index else passive_bg' in page,
    "active/passive Find distinction missing")

# Symbols: exact 40-entry curated set, preserving prior entries and adding only
# the six approved follow-up symbols.
tree = ast.parse(page)
symbols_value = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "show_symbols_dialog":
        for child in ast.walk(node):
            if isinstance(child, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "symbols" for t in child.targets):
                try:
                    symbols_value = ast.literal_eval(child.value)
                except Exception:
                    symbols_value = None
                break
        break
req(isinstance(symbols_value, tuple), "Symbols tuple not found")
if isinstance(symbols_value, tuple):
    req(len(symbols_value) == 40, f"Symbols must contain exactly 40 entries, found {len(symbols_value)}")
    req(len(set(symbols_value)) == 40, "Symbols contains duplicates")
    for symbol in ("♥", "♦", "♣", "♠", "☐", "☑"):
        req(symbol in symbols_value, f"approved new symbol missing: {symbol}")
    for symbol in ("★", "☆", "£", "€", "≠", "∞", "©", "®", "™"):
        req(symbol in symbols_value, f"existing curated symbol lost: {symbol}")
req('self.editor.insert_guarded_text(symbol)' in page, "Symbols no longer use guarded insertion")

# Protect the 0.3.6 work and unrelated Plus infrastructure from opportunistic changes.
protected = {
    "widgets/main_window.py": "17bae2b919d4ddc85031fd9965e7062c1dba43dde4ff2f9c987ffe6fbc6afb32",
    "widgets/shell_ribbon.py": "dd4f555f893923a26cd5429a082bd15acba8017946302fa950cd5394f2ce95b0",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "services/module_scanner.py": "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "controllers/file_actions.py": "8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241",
    "models/module_repository.py": "bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5",
    "widgets/resolve_open_documents_dialog.py": "38657cbfaf21ab286cb58dc2cd8fac43b2b562d270629d98276274d68c17047e",
    "widgets/dashboard.py": "b75d978aa0c6f1c01a3ca8eae586eda0b646398b20f4b993fc75e8ce70a6c773",
    "widgets/dashboard_card.py": "77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4",
    "widgets/navigation.py": "cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef",
    "services/config_service.py": "5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3",
}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"protected out-of-scope file changed: {relative}")

if errors:
    print("Marko Plus 0.3.7 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.7 Find/Symbols corrective contract")
