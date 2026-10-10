#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.11 approved UI-backlog gate."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
MAIN = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
RIBBON = (PACKAGE / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
INIT = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
CONSTANTS = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
errors: list[str] = []

def req(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)

def tree_hash(root: Path, *, exclude: set[str] | None = None) -> str:
    exclude = exclude or set()
    h = hashlib.sha256()
    for p in sorted(root.glob("*.png")):
        if p.name in exclude:
            continue
        h.update(p.name.encode("utf-8") + b"\0" + p.read_bytes())
    return h.hexdigest()

req('APP_VERSION = "0.4.11"' in INIT, "0.4.11 package identity missing")
req('APP_REVISION = "0.4.11"' in CONSTANTS, "0.4.11 revision identity missing")

# Approved shortcut contract.
for frag in (
    'self.theme_light_action = self._command("Light", lambda: self._set_theme("light"), "Ctrl+Alt+Shift+1", checkable=True)',
    'self.theme_dark_action = self._command("Dark", lambda: self._set_theme("dark"), "Ctrl+Alt+Shift+2", checkable=True)',
    'self.theme_system_action = self._command("System", lambda: self._set_theme("system"), "Ctrl+Alt+Shift+3", checkable=True)',
    '"Toggle List/Grid View", self._toggle_dashboard_view,\n            "Ctrl+Alt+Shift+V",',
):
    req(frag in MAIN, f"missing 0.4.11 shortcut contract: {frag}")
req('"Ctrl+Alt+Shift+D",' not in MAIN, "old List/Grid shortcut remains")

# Comment toolbar action is visible but does not take ownership of Ctrl+/.
for frag in (
    'self.comment_action = self._command("Toggle Comment", self._toggle_comment)',
    'self.comment_action.setToolTip("Toggle Comment — Ctrl+/")',
    '"comment_action":"comment-toggle"',
    '"delete_line_action", "comment_action",',
    '[("undo_action"), ("redo_action"), ("duplicate_line_action"), ("delete_line_action"), ("comment_action"), ("find_action")',
):
    req(frag in MAIN or frag in RIBBON, f"missing Toggle Comment UI wiring: {frag}")
req('self.comment_action = self._command("Toggle Comment", self._toggle_comment, "Ctrl+/"' not in MAIN,
    "0.4.11 moved Ctrl+/ ownership into MainWindow")
req('("Toggle Comment", "Ctrl+/"),' in MAIN,
    "existing editor-owned Toggle Comment shortcut inventory entry changed")

# Heading AppMenu submenu uses the same heading-group asset as the Ribbon flyout.
req('self.heading_menu_action = headings.menuAction()' in MAIN, "Heading AppMenu action handle missing")
req('"heading_tabbed_action":"heading-group", "heading_menu_action":"heading-group"' in MAIN,
    "Heading AppMenu is not mapped to heading-group")

# Existing icon family is untouched; only approved Comment pair is added.
ICON_ROOT = PACKAGE / "assets" / "toolbar-icons"
old_tree = {
    "light": "460c0c1d6b625a43fa76efb84178b4baf2c5faef2727c6f12e226101fd863dd9",
    "dark": "32700ede0da30ebe1f2f67e090c29d50751c9bf42978f22235abc8ed637dc700",
}
comment_hash = {
    "light": "8672a84b6898bff8c4184f04e8059d1578f542d7cd7f11a039d43c7debeac963",
    "dark": "1c769b67fd7a4dca3c09b69b7f63aa88b97de1ba620b85b810ff3b00ae16a169",
}
for scheme in ("light", "dark"):
    files = sorted((ICON_ROOT / scheme).glob("*.png"))
    req(len(files) == 122, f"{scheme} icon family must contain 122 assets")
    req(tree_hash(ICON_ROOT / scheme, exclude={"comment-toggle.png"}) == old_tree[scheme],
        f"existing {scheme} icon family changed")
    comment = ICON_ROOT / scheme / "comment-toggle.png"
    req(comment.is_file(), f"missing {scheme}/comment-toggle.png")
    if comment.is_file():
        req(hashlib.sha256(comment.read_bytes()).hexdigest() == comment_hash[scheme],
            f"wrong {scheme} Comment Toggle asset")

# Preserve Item 1 authority and major protected engines/lifecycle files.
for rel, digest in {
    "widgets/markopad_source_editor.py":"0264f2515d499c3a877742e08877535323b825021fe7c1c15d0f95a9c2f2e327",
    "widgets/markopad_preview.py":"e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "controllers/file_actions.py":"0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py":"e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "widgets/editor_page.py":"8e5c510c8a3c1d8affc330165064a130996fb2928386a067a9fb0a8884993b7a",
}.items():
    req(hashlib.sha256((PACKAGE / rel).read_bytes()).hexdigest() == digest,
        f"protected implementation changed: {rel}")

# Item 32 active-surface routing stays in force.
for frag in (
    'def _active_text_surface(self, page: EditorPage | None = None) -> str:',
    'def _source_interaction_active(self, page: EditorPage | None = None) -> bool:',
    'page.preview.copy()', 'page.preview.selectAll()',
    'source_active = self._source_interaction_active(page)',
):
    req(frag in MAIN, f"Item 32 routing regressed: {frag}")

if errors:
    print("Marko Plus 0.4.11 check failed:")
    for e in errors:
        print("-", e)
    sys.exit(1)
print("PASS: Marko Plus 0.4.11 approved UI-backlog contract")
