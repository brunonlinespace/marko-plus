#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.10 Phase 1 kinetic convergence."""
from __future__ import annotations

import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []

def require(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

main = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
dashboard = (PACKAGE / "widgets/dashboard.py").read_text(encoding="utf-8")
card = (PACKAGE / "widgets/dashboard_card.py").read_text(encoding="utf-8")
folder = (PACKAGE / "widgets/folder_dashboard.py").read_text(encoding="utf-8")
navigation = (PACKAGE / "widgets/navigation.py").read_text(encoding="utf-8")
shell = (PACKAGE / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
desktop = (PACKAGE / "packaging/appimage/marko-plus.desktop").read_text(encoding="utf-8")
metainfo = (PACKAGE / "packaging/appimage/io.github.brunonlinespace.marko_plus.metainfo.xml").read_text(encoding="utf-8")
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

require('APP_VERSION = "0.1.10"' in init, "0.1.10 package identity missing")
require('APP_REVISION = "0.1.10"' in constants, "0.1.10 revision identity missing")
require(component.get("version") == "0.1.10", "Suite component version mismatch")
require(manifest.get("version") == "0.1.10", "component manifest version mismatch")
require('X-AppImage-Version=0.1.10' in desktop, "desktop release version mismatch")
require('<release version="0.1.10" date="2026-10-05">' in metainfo, "AppStream current release mismatch")

# Main Dashboard only: Rico-derived kinetic touch.
require('QScroller,' in dashboard, "Dashboard does not import QScroller")
require('QScroller.grabGesture(' in dashboard, "Dashboard does not grab a scroll gesture")
require('QScroller.ScrollerGestureType.TouchGesture' in dashboard, "Dashboard is not TouchGesture based")
require(dashboard.count('touch_moves_scroll_only=True') == 2, "List/Grid root cards are not both touch-scroll-only")
require('QScroller' not in folder, "Folder Dashboard gained forbidden kinetic scrolling")
require('QScroller' not in navigation, "Navigation/sidebar gained forbidden kinetic scrolling")
require('QScroller' not in shell, "ShellRibbon gained forbidden kinetic scrolling")

# Root-card touch movement cannot initiate QDrag; genuine mouse QDrag remains.
require('QInputDevice' in card, "Dashboard card lacks input-device discrimination")
require('event.deviceType() != QInputDevice.DeviceType.Mouse' in card, "touch-origin mouse movement is not blocked")
require('self._touch_moves_scroll_only' in card, "root-card touch contract flag missing")
require('drag = QDrag(self)' in card, "genuine mouse managed-document drag was removed")
require('application/x-marko-plus-document' in card, "managed-document drag MIME was removed")

# External drops import only.
require('def _handle_app_drop(' in main, "external desktop drop handler missing")
require('self.file_actions.import_files(' in main, "external drop no longer imports")
handler = main.split('def _handle_app_drop(', 1)[1].split('def _delete_current_file', 1)[0]
for forbidden in ('_open_path_in_new_window', '_queue_created_module_open', 'drop_open_mode', 'ShiftModifier'):
    require(forbidden not in handler, f"import-only handler still contains {forbidden}")
for retired in ('drop_active_action', 'drop_new_window_action', 'App Drag-and-Drop', '_effective_drop_open_mode', '_set_drop_open_mode'):
    require(retired not in main, f"retired drop policy remains in MainWindow: {retired}")
require('"drop_open_mode":' not in config, "drop_open_mode still has a live default")
require('if "drop_open_mode" in loaded:' in config, "legacy drop_open_mode migration missing")
require('drop_active_action' not in shell and 'drop_new_window_action' not in shell, "retired drop controls remain in ShellRibbon")

# Existing assets are deliberately retained.
for scheme in ('light', 'dark'):
    base = PACKAGE / 'assets' / 'toolbar-icons' / scheme
    require((base / 'drop-active.png').is_file(), f"{scheme} drop-active asset was removed")
    require((base / 'drop-new-window.png').is_file(), f"{scheme} drop-new-window asset was removed")
    require((base / 'app-drag-and-drop.png').is_file(), f"{scheme} app-drag-and-drop asset was removed")

# Phase 2 external-session routing remains excluded.
require('Exec=marko-plus %F' not in desktop, "external-session %F routing leaked into 0.1.10")
require('external=True' not in (PACKAGE / 'models/module.py').read_text(encoding='utf-8'), "transient external module state leaked into 0.1.10")

if errors:
    print('Marko Plus 0.1.10 check failed:')
    for error in errors:
        if error:
            print(f'- {error}')
    raise SystemExit(1)
print('Marko Plus 0.1.10 Phase 1 kinetic/import-only check passed.')
