#!/usr/bin/env python3
"""Dependency-light Marko Plus 0.4.9 Item 32 Split/Preview routing gate."""
from __future__ import annotations
import ast, hashlib, json, sys
from pathlib import Path
PKG=Path(__file__).resolve().parents[1]; ROOT=PKG.parent
MAIN_PATH=PKG/'widgets/main_window.py'; PAGE_PATH=PKG/'widgets/editor_page.py'
MAIN=MAIN_PATH.read_text(encoding='utf-8'); PAGE=PAGE_PATH.read_text(encoding='utf-8')
errors=[]
def req(c,m):
    if not c: errors.append(m)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def fn_hashes(path,names):
    src=path.read_text(encoding='utf-8'); lines=src.splitlines(True); tree=ast.parse(src); out={}
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            out[node.name]=hashlib.sha256(''.join(lines[node.lineno-1:node.end_lineno]).encode()).hexdigest()
    return out
init=(PKG/'__init__.py').read_text(); constants=(PKG/'app_constants.py').read_text(); readme=(ROOT/'README.md').read_text()
req('APP_VERSION = "0.4.9"' in init,'0.4.9 package identity missing')
req('APP_REVISION = "0.4.9"' in constants,'0.4.9 revision identity missing')
req('Current release: **0.4.9**' in readme,'README current release stale')
for frag in (
 'def _active_text_surface(self, page: EditorPage | None = None) -> str:',
 'def _source_interaction_active(self, page: EditorPage | None = None) -> bool:',
 'if self._active_text_surface(page) == "preview":\n            page.preview.copy()',
 'if self._active_text_surface(page) == "preview":\n            page.preview.selectAll()',
 'event.type() == QEvent.Type.FocusIn',
 'page._active_text_surface = surface',
 'watched is page.content_splitter.handle(1)',
 'page.reset_content_splitter()',
 'source_active = self._source_interaction_active(page)',
 'self.undo_action.setEnabled(undo_available and source_active)',
 'self.redo_action.setEnabled(redo_available and source_active)',
): req(frag in MAIN,f'missing Item 32 MainWindow contract: {frag}')
for frag in (
 'def reset_content_splitter(self) -> None:',
 'self.content_splitter.setSizes([3, 2])',
 '"markopad_editor_splitter_sizes"',
 'save=True',
): req(frag in PAGE,f'missing Item 32 EditorPage contract: {frag}')
# Find/Replace was explicitly excluded; preserve 0.4.8 EditorPage implementation exactly.
expected={
 'toggle_find_panel':'63d54ff9a801765c4e0e5a4f000a866aacdbc7ac41a01752d06912755a879d89',
 'show_find_panel':'1e7025502a3cd23d60f419d6ed08370b421d3ed94363aecd5a0cc50974ec24c4',
 'hide_find_panel':'e016ca68cd9291bf59e3334eb4c136c741f5b840ea63db034069e6beae6b4560',
 'show_replace_dialog':'f2de353ef8d2cff50fdddfb1c7c02febc48cc287911815e64b96ae6ca6b07e03',
 '_replace_flags':'cc9e519f44d3ea23a61ebfd716319587754d6d46a6507eef263b40be95a20852',
 '_selection_matches_replace_query':'792e1f51a1ec1571990b4581f50efad064e688f40c84fed24f616a3d8ae45afd',
 '_find_replace_match':'582ae75225cd194c106eb60c9386cce24981122a5aab2704bf82c0f7d0e54eb5',
 'find_text':'274b82648c3eb316df5a045c92ba9039059a105f9e906023f3cbfc398d347ea0',
 'find_text_and_refocus':'a6411c827cf3fd74742440b58aa560f767ce51c773f5854e23e7c0ec6790c0ba',
 'find_next':'02dd0ed642eac78346b45b1838272af907fe1c13b4032230662041e8de4046b2',
 'find_previous':'7c5287263d9b261493dda25596ea6d02f00652252f13b3108f6a6f5851e58b4b',
 'replace_current':'ae25f5d4e2efa6bc642602fd657586693b9270a4732ec5d305cad665c888cd67',
 'replace_all':'041db47e97aca5c078e916e31de0d61368fe1c37dd868cb34390ab93cbae874e',
}
actual=fn_hashes(PAGE_PATH,set(expected))
for name,digest in expected.items(): req(actual.get(name)==digest,f'Find/Replace exclusion drifted: {name}')
# Protect editor engine, preview engine and file/workspace lifecycle implementation.
for rel,digest in {
 'widgets/code_editor.py':'bcecbc3c3bb5e744dce5683ab508578bec85901e323b313500745b27a48efb87',
 'widgets/markopad_preview.py':'e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965',
 'controllers/file_actions.py':'0a851fc5fef4e6ca982d0ffd17a607217c22b7404491104b555dc64ab6ae58a8',
 'controllers/editor_manager.py':'e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4',
}.items(): req(sha(PKG/rel)==digest,f'protected implementation changed: {rel}')
if errors:
    print('Marko Plus 0.4.9 check failed:')
    for e in errors: print('-',e)
    sys.exit(1)
print('PASS: Marko Plus 0.4.9 Item 32 Split/Preview interaction contract')
