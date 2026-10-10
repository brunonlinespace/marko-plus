#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.4 App Sidebar release gate."""
from __future__ import annotations
import hashlib, struct
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]
ROOT=PACKAGE.parent
errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
def png_size(p):
    d=p.read_bytes(); return struct.unpack(">II", d[16:24]) if d[:8]==b"\x89PNG\r\n\x1a\n" else (0,0)
main=src("widgets/main_window.py")
config=src("services/config_service.py")
init=src("__init__.py")
constants=src("app_constants.py")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.3.4"' in init, "0.3.4 package identity missing")
req('APP_REVISION = "0.3.4"' in constants, "0.3.4 revision identity missing")
req('"sidebar_position": "left"' in config, "left sidebar default missing")
for frag in ('addMenu("App Sidebar")','("left", "Left Sidebar")','("right", "Right Sidebar")','def _set_sidebar_position(','self.splitter.insertWidget(target_index, self.navigation)','def _logical_splitter_sizes(','"left_sidebar_action":"show-sidebar"','"right_sidebar_action":"show-sidebar-right"'):
    req(frag in main, f"sidebar contract missing: {frag}")
req(main.index('addMenu("App Dashboard")') < main.index('addMenu("App Sidebar")') < main.index('addMenu("App Launch Screen")'), "App Sidebar is not directly after App Dashboard")
for scheme in ('light','dark'):
    left=PACKAGE/'assets'/'toolbar-icons'/scheme/'show-sidebar.png'
    right=PACKAGE/'assets'/'toolbar-icons'/scheme/'show-sidebar-right.png'
    req(left.is_file(), f"missing left sidebar icon: {left}")
    req(right.is_file(), f"missing right sidebar icon: {right}")
    if right.is_file(): req(png_size(right)==(64,64), f"wrong right-sidebar PNG size: {right}")
req('Current release: **0.3.4**' in readme, "root README current release is stale")
protected={'widgets/dashboard_card.py': '77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4', 'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'controllers/editor_manager.py': 'bc51f34fb2937f45ca7b8389f1354cde00a3aaa9d823b8cad80f24fdbe7137d8', 'widgets/editor_page.py': 'cf2dbbbcbf98168561e3bf6431d7bcb3f07cc372e506320241e64051e1ab940f', 'models/module_repository.py': 'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5', 'widgets/resolve_open_documents_dialog.py': '38657cbfaf21ab286cb58dc2cd8fac43b2b562d270629d98276274d68c17047e', 'widgets/shell_ribbon.py': 'e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1'}
for r,h in protected.items(): req(sha(r)==h, f"protected out-of-scope file changed: {r}")
if errors:
    print("Marko Plus 0.3.4 check failed:")
    [print("- "+e) for e in errors]
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.4 App Sidebar contract")
