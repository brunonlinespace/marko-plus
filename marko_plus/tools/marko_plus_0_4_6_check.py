#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.4.6 Keyboard Shortcuts inventory regression gate."""
from __future__ import annotations

import ast
import hashlib
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


init = src("__init__.py")
constants = src("app_constants.py")
main = src("widgets/main_window.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.4.6"' in init, "0.4.6 package identity missing")
req('APP_REVISION = "0.4.6"' in constants, "0.4.6 revision identity missing")
req('Current release: **0.4.6**' in readme, "README current release stale")

# The actual AppMenu must be the catalogue authority.
for attr, label in (
    ("file_menu", "File"),
    ("edit_menu", "Edit"),
    ("markdown_menu", "Markdown"),
    ("insert_menu", "Insert"),
    ("view_menu", "View"),
    ("settings_menu", "Settings"),
    ("help_menu", "Help"),
):
    req(f"self.{attr} = bar.addMenu" in main, f"{label} AppMenu is not stored as live shortcut-catalogue authority")

module = ast.parse(main, filename="widgets/main_window.py")
window_class = next(
    (node for node in module.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"),
    None,
)
req(window_class is not None, "MainWindow class missing")
shortcut_fn = None
if window_class is not None:
    shortcut_fn = next(
        (node for node in window_class.body if isinstance(node, ast.FunctionDef) and node.name == "_shortcut_catalog"),
        None,
    )
req(shortcut_fn is not None, "_shortcut_catalog() missing")

if shortcut_fn is not None:
    segment = ast.get_source_segment(main, shortcut_fn) or ""
    for fragment in (
        "for action in menu.actions()",
        "submenu = action.menu()",
        "entries.extend(collect(submenu))",
        "action.shortcut().toString(",
        '"File": collect(self.file_menu)',
        '"Edit": collect(self.edit_menu)',
        '"Markdown": collect(self.markdown_menu)',
        '"Insert": collect(self.insert_menu)',
        '"View": collect(self.view_menu)',
        '"Settings": collect(self.settings_menu)',
        '"Help": collect(self.help_menu)',
    ):
        req(fragment in segment, f"live-menu shortcut inventory contract missing: {fragment}")

    # Menu-backed QAction entries must not be manually mirrored again. Only the
    # semantic label override and intentionally non-menu QAction shortcuts may
    # be referenced explicitly by the catalogue implementation.
    referenced_actions = {
        node.attr
        for node in ast.walk(shortcut_fn)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
        and node.attr.endswith("_action")
    }
    allowed_actions = {
        "rename_file_action",  # label override: Rename File or Folder
        "close_context_action",
        "open_context_tab_action",
        "next_document_tab_action",
        "previous_document_tab_action",
        "toggle_dashboard_view_action",
        "toggle_sidebar_position_action",
    }
    unexpected = sorted(referenced_actions - allowed_actions)
    req(not unexpected, f"manual menu-backed shortcut inventory returned: {unexpected}")

# Demonstrated regression: this real File-menu QAction must now be discovered
# automatically, not hand-copied into _shortcut_catalog().
req(
    'self.refresh_workspace_action = self._command("Refresh Workspace", self._refresh_workspace, "Ctrl+Shift+F5")' in main,
    "Refresh Workspace shortcut assignment changed or missing",
)
req(
    "file_menu.addAction(self.refresh_workspace_action)" in main,
    "Refresh Workspace is not present in the real File AppMenu",
)
if shortcut_fn is not None:
    segment = ast.get_source_segment(main, shortcut_fn) or ""
    req(
        "refresh_workspace_action" not in segment,
        "Refresh Workspace was manually duplicated in the shortcut catalogue instead of being live-discovered",
    )

# 0.4.6 is intentionally limited to MainWindow shortcut inventory plus
# release/QA metadata. Preserve the already-fixed 0.4.5 drag path and all
# unrelated production architecture byte-for-byte.
protected = {
    "widgets/navigation.py": "a075815775c4220ab1c707cc8a06c1ec5d6497d0a32ade39f177f1a151c7b35a",
    "controllers/file_actions.py": "0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8",
    "widgets/editor_page.py": "2753b368d6cd3d85234bf5481a6e88299c906d81de6f89bed90143934dd9e8e3",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "services/module_scanner.py": "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "models/module_repository.py": "bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5",
    "services/file_io.py": "27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38",
    "widgets/shortcuts_dialog.py": "c8b91135b3387e4d4bd38cb2b1bf65175b4f936d311b70683b7b7bf4a7f5aa37",
    "widgets/shell_ribbon.py": "dd4f555f893923a26cd5429a082bd15acba8017946302fa950cd5394f2ce95b0",
}
for relative, digest in protected.items():
    req(sha(relative) == digest, f"protected out-of-scope 0.4.5 production file changed: {relative}")

if errors:
    print("Marko Plus 0.4.6 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("PASS: Marko Plus 0.4.6 live AppMenu Keyboard Shortcuts inventory contract")
