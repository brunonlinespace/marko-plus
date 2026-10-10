#!/usr/bin/env python3
from pathlib import Path
import sys
P=Path(__file__).resolve().parents[1]
main=(P/'widgets/main_window.py').read_text(encoding='utf-8')
app=(P/'app.py').read_text(encoding='utf-8')
rib=(P/'widgets/shell_ribbon.py').read_text(encoding='utf-8')
init=(P/'__init__.py').read_text(encoding='utf-8')
errs=[]
def req(c,m):
    if not c: errs.append(m)
req('APP_VERSION = "0.4.15"' in init,'version identity missing')
for frag in (
 'self.quick_start_action = self._command("Quick Tour…", self._show_quick_tour, "Shift+F1")',
 'self.quick_start_action.setToolTip("Quick Tour… — Shift+F1")',
 'QCheckBox("Don\'t show Quick Tour on startup again", wizard)',
 'startup_checkbox.setChecked(bool(self.config.get("quick_tour_seen", False)))',
 'lambda checked: self.config.set("quick_tour_seen", bool(checked), save=True)',
): req(frag in main,f'Quick Tour contract missing: {frag}')
req('config.set("quick_tour_seen", True, save=True)' not in app,'startup still auto-suppresses Quick Tour')
req('if not bool(config.get("quick_tour_seen", False)):\n        QTimer.singleShot(0, window._show_quick_tour)' in app,'startup trigger mismatch')
# AppMenu Sidebar placement
block=main[main.index('sidebar_menu = settings.addMenu("App Sidebar")'):main.index('self.app_sidebar_menu_action = sidebar_menu.menuAction()')]
req(block.index('sidebar_menu.addAction(self.sidebar_action)') < block.index('sidebar_menu.addSeparator()') < block.index('sidebar_menu.addAction(self.left_sidebar_action)') < block.index('sidebar_menu.addAction(self.right_sidebar_action)'), 'App Sidebar ordering mismatch')
# View menu no longer owns Show Sidebar
view=main[main.index('self.view_menu = bar.addMenu("&View")'):main.index('self.settings_menu = bar.addMenu("&Settings")')]
req('view.addAction(self.sidebar_action)' not in view,'Show Sidebar still in View AppMenu')
# Ribbon position and Focused Mode retained
req('[("fullscreen_action"), ("status_bar_action")]' in rib,'View ribbon group not corrected')
req('[("sidebar_action"), ("left_sidebar_action"), ("right_sidebar_action")]' in rib,'Sidebar ribbon ordering mismatch')
req('[("collapsed_mode_action")]' in rib,'Focused Mode moved unexpectedly')
if errs:
 print('Marko Plus 0.4.15 check failed:'); [print('-',e) for e in errs]; sys.exit(1)
print('PASS: Marko Plus 0.4.15 Quick Tour/Sidebar contract')
