#!/usr/bin/env python3
from pathlib import Path
import sys
P=Path(__file__).resolve().parents[1]
main=(P/'widgets/main_window.py').read_text(encoding='utf-8')
rib=(P/'widgets/shell_ribbon.py').read_text(encoding='utf-8')
init=(P/'__init__.py').read_text(encoding='utf-8')
errs=[]
def req(c,m):
    if not c: errs.append(m)
req('APP_VERSION = "0.4.17"' in init, '0.4.17 package identity missing')
# Toggle Comment must be a real Ctrl+/ QAction so the AppMenu visibly shows the keybind.
req('self.comment_action = self._command("Toggle Comment", self._toggle_comment, "Ctrl+/")' in main,
    'Toggle Comment does not carry the live Ctrl+/ QAction shortcut')
req('self.comment_action = self._command("Toggle Comment", self._toggle_comment)\n' not in main,
    'old shortcutless Toggle Comment QAction remains')
# Edit placement remains exactly the 0.4.16/Markopad ordering.
edit=main[main.index('self.edit_menu = bar.addMenu("&Edit")'):main.index('self.markdown_menu = bar.addMenu("&Markdown")')]
order=[
    'edit.addAction(self.delete_text_action)',
    'edit.addAction(self.comment_action)',
    'edit.addAction(self.duplicate_line_action)',
    'edit.addAction(self.delete_line_action)',
    'edit.addAction(self.select_all_action)',
]
req(all(x in edit for x in order), 'Edit inventory missing Toggle Comment/line commands')
req([edit.index(x) for x in order] == sorted(edit.index(x) for x in order), 'Edit Toggle Comment ordering changed')
# The live AppMenu action now supplies the Shortcuts-dialog entry; no duplicate exception remains.
shortcut_tail=main[main.index('# These shortcuts are intentionally not represented by AppMenu QActions.'):main.index('def _show_shortcuts', main.index('# These shortcuts are intentionally not represented by AppMenu QActions.'))]
req('("Toggle Comment", "Ctrl+/"),' not in shortcut_tail, 'obsolete menu-less Toggle Comment shortcut entry remains')
# Preserve 0.4.16 File Ribbon ordering verbatim.
for frag in (
    '[("new_action"), ("new_folder_action"), ("new_window_action")]',
    '[("import_file_action"), ("open_external_file_action")]',
    '[("workspace_tabbed_action"), ("dashboard_action"), ("previous_file_action"), ("next_file_action")]',
    '[("duplicate_action"), ("rename_file_action"), ("delete_file_action"), ("external_editor_action"), ("open_document_folder_action"), ("properties_action")]',
): req(frag in rib, f'0.4.16 File Ribbon group/order changed: {frag}')
if errs:
    print('Marko Plus 0.4.17 check failed:')
    [print('-', e) for e in errs]
    sys.exit(1)
print('PASS: Marko Plus 0.4.17 Toggle Comment shortcut-visibility contract')
