#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.4.5 sidebar drag-crash regression gate."""
from __future__ import annotations
import ast
import hashlib
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]; ROOT=PACKAGE.parent; errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
init=src("__init__.py"); constants=src("app_constants.py"); nav=src("widgets/navigation.py"); readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.4.5"' in init,"0.4.5 package identity missing")
req('APP_REVISION = "0.4.5"' in constants,"0.4.5 revision identity missing")
req('Current release: **0.4.5**' in readme,"README current release stale")
tree=ast.parse(nav, filename="widgets/navigation.py")
qtgui=set()
for node in tree.body:
    if isinstance(node,ast.ImportFrom) and node.module=="PyQt6.QtGui":
        qtgui.update(alias.name for alias in node.names)
for name in ("QPalette","QDragLeaveEvent","QDragMoveEvent","QDropEvent"):
    req(name in qtgui,f"Qt drag/drop dependency is used but not imported: {name}")
req("QPalette.ColorRole.Highlight" in nav,"palette-aware folder drop highlight missing")
req("QPalette.ColorRole.HighlightedText" in nav,"palette-aware drop text highlight missing")
req("def dragMoveEvent(" in nav and "_set_drop_highlight" in nav,"sidebar drag-highlight path missing")
# 0.4.5 is intentionally limited to navigation/import repair plus release/QA metadata.
protected={
 'controllers/file_actions.py':'0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8',
 'widgets/editor_page.py':'2753b368d6cd3d85234bf5481a6e88299c906d81de6f89bed90143934dd9e8e3',
 'controllers/editor_manager.py':'e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4',
 'services/open_document_monitor.py':'3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db',
 'services/filesystem_watcher.py':'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
 'services/module_scanner.py':'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
 'models/module_repository.py':'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5',
 'services/file_io.py':'27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38',
 'widgets/main_window.py':'3d672de97a22874a95bf5db4c62da604c156b185913adf15db80ac288896de5d',
}
for r,h in protected.items(): req(sha(r)==h,f"protected out-of-scope 0.4.4 file changed: {r}")
if errors:
    print("Marko Plus 0.4.5 check failed:")
    [print(f"- {e}") for e in errors]; raise SystemExit(1)
print("PASS: Marko Plus 0.4.5 sidebar drag-highlight import/crash contract")
