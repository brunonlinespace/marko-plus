#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.4.3 Audit 4/5 gate."""
from __future__ import annotations
import hashlib
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]; ROOT=PACKAGE.parent; errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
init=src("__init__.py"); constants=src("app_constants.py"); actions=src("controllers/file_actions.py"); readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.4.3"' in init,"0.4.3 package identity missing")
req('APP_REVISION = "0.4.3"' in constants,"0.4.3 revision identity missing")
req('Current release: **0.4.3**' in readme,"README current release stale")
for fragment in ('self._prepare_open_editor(stored, operation="rename")','self._prepare_open_editor(stored, operation="remove")','page.handle_backing_path_event()','if page.backing_state == "normal":','if page.backing_state == "missing":','The Markdown file changed outside Marko Plus.','if page.module is not module:'):
    req(fragment in actions,f"Audit 4 contract missing: {fragment}")
for fragment in ('else ("current" if page is not None else "saved")','if page is not None and not dirty:','and choice == "current"','and (dirty or page.backing_state != "normal")','payload = page.current_markdown_payload()','payload, _snapshot = read_regular_file('):
    req(fragment in actions,f"Audit 5 contract missing: {fragment}")
for fragment in ('install_new_file_from_temp(temporary, destination)','dirty_duplicate_action','{"ask", "current", "saved"}'):
    req(fragment in actions,f"existing Duplicate contract changed: {fragment}")
protected={'widgets/editor_page.py': '2753b368d6cd3d85234bf5481a6e88299c906d81de6f89bed90143934dd9e8e3', 'controllers/editor_manager.py': 'e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4', 'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'models/module_repository.py': 'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5', 'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc', 'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38', 'widgets/main_window.py': '3d672de97a22874a95bf5db4c62da604c156b185913adf15db80ac288896de5d', 'widgets/navigation.py': 'cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef', 'widgets/dashboard.py': 'b75d978aa0c6f1c01a3ca8eae586eda0b646398b20f4b993fc75e8ce70a6c773', 'widgets/folder_dashboard.py': 'eea55c93f245529926d0727dca4ceebce61975c3d0343a41d5978a56bee474f6', 'widgets/shell_ribbon.py': 'dd4f555f893923a26cd5429a082bd15acba8017946302fa950cd5394f2ce95b0', 'widgets/code_editor.py': 'b0299c063a23d93bea0a9afdf4bfceb16d8843867f5382a02824cd27bbcb4831', 'widgets/markopad_source_editor.py': 'dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830', 'widgets/markopad_preview.py': 'e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965', 'legacy_ricopad.py': '2984a424345666509420bd8d9825394e6d8b6b70620d1eb3c50e519be71cdc40'}
for r,h in protected.items(): req(sha(r)==h,f"protected out-of-scope 0.4.2 file changed: {r}")
if errors:
    print("Marko Plus 0.4.3 check failed:")
    [print(f"- {e}") for e in errors]; raise SystemExit(1)
print("PASS: Marko Plus 0.4.3 Audit 4/5 Plus-family file-action convergence contract")
