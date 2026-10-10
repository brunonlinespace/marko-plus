#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.10 sidebar navigation rollback gate."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]
ROOT=PACKAGE.parent
errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding="utf-8")
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
main=src("widgets/main_window.py")
init=src("__init__.py")
constants=src("app_constants.py")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
req('APP_VERSION = "0.3.10"' in init, "0.3.10 package identity missing")
req('APP_REVISION = "0.3.10"' in constants, "0.3.10 revision identity missing")
req('Current release: **0.3.10**' in readme, "README current release stale")
pattern=re.search(r'def _open_sidebar_module\(self, path\):.*?return page', main, re.S)
req(pattern is not None, "transactional sidebar wrapper missing")
if pattern:
    body=pattern.group(0)
    for fragment in (
        'page = self.editor_manager.open_module(path)',
        'if page is None:',
        'current = self.editor_manager.current_module',
        'if current is not None and not current.external:',
        'self.navigation.select_module(current.path)',
        'return page',
    ): req(fragment in body, f"sidebar rollback method incomplete: {fragment}")
req('self.navigation.module_requested.connect(self._open_sidebar_module)' in main, "sidebar request does not use transactional wrapper")
req('self.navigation.module_requested.connect(self.editor_manager.open_module)' not in main, "direct optimistic sidebar routing returned")
# This correction must not mutate the navigation widget, move engine, editor manager, search UI, or watcher/scanner core.
protected={
    'widgets/navigation.py': 'cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef',
    'controllers/editor_manager.py': 'e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4',
    'controllers/file_actions.py': '8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241',
    'widgets/editor_page.py': 'c01d9119dff00942f65c4b24d30ec01b5304e9cdf799e70aeac966edd2ee5970',
    'widgets/markopad_source_editor.py': 'dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830',
    'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
}
for r,h in protected.items(): req(sha(r)==h, f"protected out-of-scope file changed: {r}")
if errors:
    print("Marko Plus 0.3.10 check failed:")
    for e in errors: print(f"- {e}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.10 transactional sidebar navigation rollback contract")
