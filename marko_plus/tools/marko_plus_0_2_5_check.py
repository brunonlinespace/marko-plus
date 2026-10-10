#!/usr/bin/env python3
# Marko Plus
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static contract check for Marko Plus 0.2.5 managed tree-drop hotfix."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
PACKAGE=Path(__file__).resolve().parents[1]; ROOT=PACKAGE.parent; errors=[]
def req(c,m):
    if not c: errors.append(m)
def src(r): return (PACKAGE/r).read_text(encoding='utf-8')
def sha(r): return hashlib.sha256((PACKAGE/r).read_bytes()).hexdigest()
init=src('__init__.py'); const=src('app_constants.py'); nav=src('widgets/navigation.py')
component=json.loads((ROOT/'suite-pythoine-component.json').read_text()); manifest=json.loads((PACKAGE/'marko-plus.json').read_text())
req('APP_VERSION = "0.2.5"' in init,'0.2.5 package identity missing')
req('APP_REVISION = "0.2.5"' in const,'0.2.5 revision identity missing')
req(component.get('version')=='0.2.5','Suite version mismatch'); req(manifest.get('version')=='0.2.5','manifest version mismatch')
resolver=nav.split('    def _external_drop_destination',1)[1].split('    def dragMoveEvent',1)[0]
for f in ('if item is None:','return Path(self.parent().library_root).resolve(strict=False)','if kind == self.KIND_FOLDER:','return path','if kind == "module":','return path.parent'):
    req(f in resolver,f'destination rule missing: {f}')
move=nav.split('    def dragMoveEvent',1)[1].split('    def dropEvent',1)[0]
req('event.mimeData().hasFormat(self.MIME_TYPE)' in move,'managed MIME drag acceptance missing')
req('self._external_drop_destination(item) is not None' in move,'managed drag does not accept explicit file/root destinations')
drop=nav.split('    def dropEvent',1)[1].split('\n\nclass DashboardNavigationButton',1)[0]
req('destination = self._external_drop_destination(item)' in drop,'managed drop does not resolve file/root destination')
req('source_parent == target_folder' in drop and 'samefile(target_folder)' in drop,'same-folder no-op guard changed')
req('self.module_move_dropped.emit(src, dst)' in drop,'managed move signal changed')
# protect 0.2.4 runtime outside navigation
expected={
'controllers/file_actions.py':'46f4a4c273461f348a0300b2cdfddf394b2145ffe34439fab23f737dd42fc3a8',
'models/module_repository.py':'b95a8d5a788ca7add46d5bfa176c5ad4844b81be8ea210f3b1e8af0857403ffc',
'services/filesystem_watcher.py':'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
'widgets/folder_dashboard.py':'8abdceadae1159b7f9cfdc7e11299dc943793fafb4457d2796770f3c7c93dcbb',
'widgets/shell_ribbon.py':'e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1',
}
for r,h in expected.items(): req(sha(r)==h,f'protected 0.2.4 implementation changed: {r}')
if errors:
    print('Marko Plus 0.2.5 check failed:'); [print('- '+e) for e in errors]; raise SystemExit(1)
print('Marko Plus 0.2.5 managed tree-drop hotfix check passed.')
