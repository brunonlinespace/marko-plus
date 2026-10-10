#!/usr/bin/env python3
"""Static contract check for the Marko Plus 0.0.2 UI/identity refinement."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
shortcuts = (ROOT / "widgets/shortcuts_dialog.py").read_text(encoding="utf-8")
about = (ROOT / "widgets/about_dialog.py").read_text(encoding="utf-8")
app = (ROOT / "app.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors: list[str] = []


def require(fragment: str, text: str, message: str) -> None:
    if fragment not in text:
        errors.append(message)


require('APP_VERSION = "0.0.2"', init, "0.0.2 package identity missing")
require('self.setMinimumSize(700, 470)', about, "About minimum size does not match Quick Tour")
require('self.resize(700, 470)', about, "About default size does not match Quick Tour")
require('QLabel("Menu:", self)', shortcuts, "Keyboard Shortcuts filter is not labelled Menu")
require('self.category.addItems(["All", *catalog.keys()])', shortcuts, "Keyboard Shortcuts lost All filter")
require('self.category.setAccessibleName("Shortcut menu")', shortcuts, "Shortcut filter accessibility name is stale")
require('app.setDesktopFileName(DESKTOP_ID)', app, "Qt desktop identity does not use canonical DESKTOP_ID")

for menu in ('File', 'Edit', 'Markdown', 'Insert', 'View', 'Settings', 'Help'):
    require(f'            "{menu}": [', main, f"Shortcut catalog missing {menu} menu group")
shortcut_start = main.index('    def _shortcut_catalog(self)')
shortcut_end = main.index('\n    def _show_shortcuts(self)', shortcut_start)
shortcut_block = main[shortcut_start:shortcut_end]
if '            "Home": [' in shortcut_block:
    errors.append("Keyboard Shortcuts still groups by Home tab")

require('self.code_tabbed_action = QAction("Code", self)', main, "Home Code group missing")
require('code_menu.addAction(self.inline_code_action)', main, "Code group missing Inline Code")
require('code_menu.addAction(self.code_fence_action)', main, "Code group missing Code Block")
require('self.link_tabbed_action = QAction("Link", self)', main, "Insert Link group missing")
require('link_tabbed_menu.addAction(self.link_action)', main, "Link group missing Insert Link")
require('link_tabbed_menu.addAction(self.edit_link_action)', main, "Link group missing Edit Link")
require('link_tabbed_menu.addAction(self.remove_link_action)', main, "Link group missing Remove Link")

home_line = '"Home": [[self.cut_action, self.copy_action, self.paste_action, self.paste_markdown_action, self.delete_text_action, self.select_all_action], [self.undo_action, self.redo_action, self.duplicate_line_action, self.delete_line_action, self.find_action, self.goto_action, self.replace_action], [self.bold_action, self.italic_action, self.strike_action, self.code_tabbed_action], [self.heading_tabbed_action], [self.bullet_action, self.number_action, self.task_action, self.quote_action, self.indent_action, self.outdent_action]]'
require(home_line, main, "Home tab command set/order does not match the 0.0.2 contract")
insert_line = '"Insert": [[self.rule_action, self.image_action, self.table_action], [self.link_tabbed_action], [self.date_time_action, self.date_action, self.time_action, self.symbol_action]]'
require(insert_line, main, "Insert tab is not Horizontal Rule/Image/Table -> Link -> date/symbols")
view_line = '"View": [[self.fullscreen_action, self.sidebar_action, self.status_bar_action], [self.word_wrap_action, self.line_numbers_action, self.editor_canvas_theme_action], [self.view_only_action], [self.zoom_in_action, self.zoom_out_action, self.zoom_reset_action], [self.source_only_action, self.split_action, self.preview_only_action], [self.tab_width_action, self.display_font_action, self.preview_font_action]]'
require(view_line, main, "View tab is not aligned to the View application menu")
settings_line = '"Settings": [[self.theme_system_action, self.theme_dark_action, self.theme_light_action], [self.list_action, self.grid_action], [self.launch_dashboard_action, self.launch_last_file_action], [self.drop_active_action, self.drop_new_window_action]]'
require(settings_line, main, "Settings tab changed unexpectedly")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.2 contract check passed.")
