#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.5 navigation/drag-target release gate."""
from __future__ import annotations
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
nav = src("widgets/navigation.py")
dashboard = src("widgets/dashboard.py")
folder = src("widgets/folder_dashboard.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.3.5"' in init, "0.3.5 package identity missing")
req('APP_REVISION = "0.3.5"' in constants, "0.3.5 revision identity missing")
req('Current release: **0.3.5**' in readme, "root README current release is stale")

req('QStyle.StandardPixmap.SP_DirIcon' in nav, "native folder icon was removed")
req('QStyle.StandardPixmap.SP_FileIcon' not in nav, "file icons remain in workspace tree")
for fragment in (
    'def _set_drop_highlight(self, item, *, root: bool = False)',
    'QPalette.ColorRole.Highlight',
    'QPalette.ColorRole.HighlightedText',
    'def dragLeaveEvent(self, event: QDragLeaveEvent)',
    'self._set_root_drop_highlight(root)',
):
    req(fragment in nav, f"navigation drop-target feedback missing: {fragment}")
for body, label in ((dashboard, "Dashboard"), (folder, "Folder Dashboard")):
    req('QPalette.ColorRole.Highlight' in body, f"{label} palette-aware drop highlight missing")
    req('self._set_drop_highlight(False)' in body, f"{label} drop highlight is not cleared")
req('"app_sidebar_menu_action":"show-sidebar"' in main, "App Sidebar group icon is not show-sidebar")

protected = {
    'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
    'controllers/editor_manager.py': 'bc51f34fb2937f45ca7b8389f1354cde00a3aaa9d823b8cad80f24fdbe7137d8',
    'widgets/editor_page.py': 'cf2dbbbcbf98168561e3bf6431d7bcb3f07cc372e506320241e64051e1ab940f',
    'widgets/dashboard_card.py': '77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4',
    'widgets/shell_ribbon.py': 'e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1',
    'services/config_service.py': '5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3',
    'controllers/file_actions.py': '8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241',
}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"protected out-of-scope file changed: {relative}")

if errors:
    print("Marko Plus 0.3.5 check failed:")
    for error in errors:
        print("- " + error)
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.5 navigation/drag-target contract")
