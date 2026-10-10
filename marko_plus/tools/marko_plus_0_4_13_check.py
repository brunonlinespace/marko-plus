#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.13 Editor Layout icon correction gate."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
MAIN = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
INIT = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
CONSTANTS = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
errors: list[str] = []

def req(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)

def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.glob("*.png")):
        h.update(p.name.encode("utf-8") + b"\0" + p.read_bytes())
    return h.hexdigest()

req('APP_VERSION = "0.4.13"' in INIT, "0.4.13 package identity missing")
req('APP_REVISION = "0.4.13"' in CONSTANTS, "0.4.13 revision identity missing")

# App Theme remains shortcut-free.
for frag in (
    'self.theme_light_action = self._command("Light", lambda: self._set_theme("light"), checkable=True)',
    'self.theme_dark_action = self._command("Dark", lambda: self._set_theme("dark"), checkable=True)',
    'self.theme_system_action = self._command("System", lambda: self._set_theme("system"), checkable=True)',
):
    req(frag in MAIN, f"missing shortcut-free theme action: {frag}")
for shortcut in ("Ctrl+Alt+Shift+1", "Ctrl+Alt+Shift+2", "Ctrl+Alt+Shift+3"):
    req(shortcut not in MAIN, f"removed App Theme shortcut remains: {shortcut}")

# Editor Layout menu heading now uses toolbar-tabbed; child icons remain unchanged.
req('self.editor_layout_menu_action = layout_menu.menuAction()' in MAIN,
    "Editor Layout menu action handle missing")
req('"editor_layout_menu_action":"toolbar-tabbed"' in MAIN,
    "Editor Layout does not use toolbar-tabbed")
req('"editor_layout_menu_action":"toolbar-classic"' not in MAIN,
    "old toolbar-classic Editor Layout mapping remains")
for frag in (
    '"file_header_action":"file-header"',
    '"source_only_action":"source-only"',
    '"split_action":"source-preview"',
    '"preview_only_action":"preview-only"',
):
    req(frag in MAIN, f"Editor Layout child icon mapping regressed: {frag}")

# Preserve 0.4.11/0.4.12 command contracts.
req('"Toggle List/Grid View", self._toggle_dashboard_view,\n            "Ctrl+Alt+Shift+V",' in MAIN,
    "List/Grid shortcut changed")
req('self.comment_action = self._command("Toggle Comment", self._toggle_comment)' in MAIN,
    "Toggle Comment action changed")
req('self.comment_action.setToolTip("Toggle Comment — Ctrl+/")' in MAIN,
    "Toggle Comment tooltip/shortcut ownership changed")

# Existing icon family is rewired only, never modified.
ICON_ROOT = PACKAGE / "assets" / "toolbar-icons"
expected_icons = {
    "light": "2241488dcb703c08f82d6389358c77d306dbf1299efa0d5220e3bc189c56311e",
    "dark": "217bfe74d20ea492e21a1964de5bd8b399081246be6a3fa47bc5bdbfd1a3b825",
}
for scheme, digest in expected_icons.items():
    files = sorted((ICON_ROOT / scheme).glob("*.png"))
    req(len(files) == 122, f"{scheme} icon family count changed")
    req(tree_hash(ICON_ROOT / scheme) == digest, f"{scheme} icon family changed")

# Preserve Item 1 authority and protected lifecycle/editor files.
for rel, digest in {
    "widgets/markopad_source_editor.py":"0264f2515d499c3a877742e08877535323b825021fe7c1c15d0f95a9c2f2e327",
    "widgets/markopad_preview.py":"e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "controllers/file_actions.py":"0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py":"e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "widgets/editor_page.py":"8e5c510c8a3c1d8affc330165064a130996fb2928386a067a9fb0a8884993b7a",
    "widgets/shell_ribbon.py":"44b1232c59a768632c448e13aa2c6fcb5fcc8a060eddd64d99eb1e07f6b66079",
}.items():
    req(hashlib.sha256((PACKAGE / rel).read_bytes()).hexdigest() == digest,
        f"protected implementation changed: {rel}")

# Item 32 routing remains in force.
for frag in (
    'def _active_text_surface(self, page: EditorPage | None = None) -> str:',
    'def _source_interaction_active(self, page: EditorPage | None = None) -> bool:',
    'page.preview.copy()', 'page.preview.selectAll()',
    'source_active = self._source_interaction_active(page)',
):
    req(frag in MAIN, f"Item 32 routing regressed: {frag}")

if errors:
    print("Marko Plus 0.4.13 check failed:")
    for error in errors:
        print("-", error)
    sys.exit(1)
print("PASS: Marko Plus 0.4.13 Editor Layout icon correction contract")
