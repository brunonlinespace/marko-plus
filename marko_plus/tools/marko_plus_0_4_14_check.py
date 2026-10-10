#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.14 New File editable-layout gate."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
MAIN = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
PAGE = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
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

req('APP_VERSION = "0.4.14"' in INIT, "0.4.14 package identity missing")
req('APP_REVISION = "0.4.14"' in CONSTANTS, "0.4.14 revision identity missing")

# Explicit user choices of Source or Split update a separate editable-layout
# preference; Preview remains a valid ordinary persisted document view but does
# not overwrite the editable preference.
req('''        if persist:
            if mode in {"source", "split"}:
                self.config.set("markopad_last_editable_view_mode", mode, save=False)
            self.config.set("markopad_view_mode", mode, save=True)''' in PAGE,
    "EditorPage does not persist a Preview-safe last editable layout")

# New File captures the last editable layout at creation time, including a safe
# migration fallback from the pre-0.4.14 three-state preference.
for frag in (
    'self._pending_new_file_view_mode: str | None = None',
    'preferred = str(self.config.get("markopad_last_editable_view_mode", ""))',
    'if preferred not in {"source", "split"}:',
    'current = str(self.config.get("markopad_view_mode", "split"))',
    'preferred = current if current in {"source", "split"} else "split"',
    'self._pending_new_file_view_mode = preferred',
):
    req(frag in MAIN, f"New File editable-layout capture missing: {frag}")

# Only the created-file pending-open path consumes the override. Regular queued
# opens explicitly clear it and continue to use markopad_view_mode normally.
req('''    def queue_open_path(self, path: str | Path) -> None:
        """Open a path without importing external OS-open documents."""
        self._pending_new_file_view_mode = None''' in MAIN,
    "ordinary queued Open does not clear the New File-only layout override")
req('''        preferred = self._pending_new_file_view_mode
        self._pending_new_file_view_mode = None
        page = self.editor_manager.open_module(module)
        if page is not None and preferred in {"source", "split"}:
            page.set_view_mode(preferred, persist=False)''' in MAIN,
    "created file is not reopened in the remembered editable layout")

# Existing documents still use the ordinary three-state preference, including
# Preview Only. The EditorManager implementation is protected byte-for-byte.
for rel, digest in {
    "widgets/markopad_source_editor.py":"0264f2515d499c3a877742e08877535323b825021fe7c1c15d0f95a9c2f2e327",
    "widgets/markopad_preview.py":"e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "controllers/file_actions.py":"0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "controllers/editor_manager.py":"e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "widgets/shell_ribbon.py":"44b1232c59a768632c448e13aa2c6fcb5fcc8a060eddd64d99eb1e07f6b66079",
}.items():
    req(hashlib.sha256((PACKAGE / rel).read_bytes()).hexdigest() == digest,
        f"protected implementation changed: {rel}")

# Project switches cannot leak a pending created-file override into another
# workspace.
req('''        self._pending_open_path = None
        self._pending_new_file_view_mode = None
        self._repair_navigation_after_scan = False''' in MAIN,
    "workspace switch does not clear pending New File layout state")

# Preserve the preceding UI/icon contract and icon family unchanged.
req('"editor_layout_menu_action":"toolbar-tabbed"' in MAIN,
    "0.4.13 Editor Layout icon mapping regressed")
ICON_ROOT = PACKAGE / "assets" / "toolbar-icons"
expected_icons = {
    "light": "2241488dcb703c08f82d6389358c77d306dbf1299efa0d5220e3bc189c56311e",
    "dark": "217bfe74d20ea492e21a1964de5bd8b399081246be6a3fa47bc5bdbfd1a3b825",
}
for scheme, digest in expected_icons.items():
    files = sorted((ICON_ROOT / scheme).glob("*.png"))
    req(len(files) == 122, f"{scheme} icon family count changed")
    req(tree_hash(ICON_ROOT / scheme) == digest, f"{scheme} icon family changed")

if errors:
    print("Marko Plus 0.4.14 check failed:")
    for error in errors:
        print("-", error)
    sys.exit(1)
print("PASS: Marko Plus 0.4.14 New File editable-layout contract")
