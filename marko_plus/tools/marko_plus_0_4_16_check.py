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
req('APP_VERSION = "0.4.16"' in init, '0.4.16 package identity missing')
# Edit menu must match Markopad around comment/line commands.
edit=main[main.index('self.edit_menu = bar.addMenu("&Edit")'):main.index('self.markdown_menu = bar.addMenu("&Markdown")')]
order=[
    'edit.addAction(self.delete_text_action)',
    'edit.addAction(self.comment_action)',
    'edit.addAction(self.duplicate_line_action)',
    'edit.addAction(self.delete_line_action)',
    'edit.addAction(self.select_all_action)',
]
req(all(x in edit for x in order), 'Edit inventory missing Toggle Comment/line commands')
req([edit.index(x) for x in order] == sorted(edit.index(x) for x in order), 'Edit Toggle Comment ordering mismatch')
# Preserve editor-owned Ctrl+/ contract; do not invent QAction shortcut ownership.
req('self.comment_action.setToolTip("Toggle Comment — Ctrl+/")' in main, 'Toggle Comment tooltip contract missing')
# File Ribbon exact approved groups.
for frag in (
    '[("new_action"), ("new_folder_action"), ("new_window_action")]',
    '[("import_file_action"), ("open_external_file_action")]',
    '[("workspace_tabbed_action"), ("dashboard_action"), ("previous_file_action"), ("next_file_action")]',
    '[("duplicate_action"), ("rename_file_action"), ("delete_file_action"), ("external_editor_action"), ("open_document_folder_action"), ("properties_action")]',
): req(frag in rib, f'File Ribbon group/order missing: {frag}')
# AppMenu More Actions remains the ordering authority.
more=main[main.index('more = file_menu.addMenu("More Actions")'):main.index('file_menu.addSeparator(); file_menu.addAction(self.print_action)')]
menu_order=[
    'for action in (self.duplicate_action, self.rename_file_action, self.delete_file_action): more.addAction(action)',
    'more.addAction(self.external_editor_action)',
    'more.addAction(self.open_document_folder_action)',
    'more.addAction(self.properties_action)',
]
req(all(x in more for x in menu_order), 'More Actions AppMenu inventory changed')
req([more.index(x) for x in menu_order] == sorted(more.index(x) for x in menu_order), 'More Actions AppMenu order changed')
if errs:
    print('Marko Plus 0.4.16 check failed:')
    [print('-', e) for e in errs]
    sys.exit(1)
print('PASS: Marko Plus 0.4.16 Edit/Ribbon ordering contract')
