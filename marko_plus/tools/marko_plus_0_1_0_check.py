#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.0 ShellRibbon migration experiment."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
shell = (ROOT / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.0"', init, "0.1.0 package identity missing")
require('from marko_plus.widgets.shell_ribbon import ShellRibbon', main, "MainWindow does not import ShellRibbon")
require('self.shell_ribbon = ShellRibbon(', main, "MainWindow does not instantiate ShellRibbon")
require('self.shell_ribbon.collapsed_changed.connect(', main, "collapse preference is not signal-driven")
require('self.shell_ribbon.set_collapsed(True, emit=False)', main, "persisted collapse state is not restored through ShellRibbon")
require('self.shell_ribbon.cycle_tab(step)', main, "command-tab cycling is not delegated to ShellRibbon")
require('self.shell_ribbon.refresh_theme()', main, "theme refresh is not delegated to ShellRibbon")

for forbidden, label in (
    ('QTabWidget,', 'MainWindow-owned QTabWidget'),
    ('QToolBar,', 'MainWindow-owned QToolBar'),
    ('QToolButton,', 'MainWindow-owned QToolButton'),
    ('def _style_command_button(', 'MainWindow button styling'),
    ('def _tabbed_add_action(', 'MainWindow toolbar action insertion'),
    ('def set_tabbed_collapsed(', 'MainWindow collapse implementation'),
    ('def eventFilter(', 'MainWindow tab-bar event filter'),
):
    if forbidden in main:
        errors.append(f"0.1.0 retained {label}")

for fragment, message in (
    ('class ShellRibbon(QWidget):', 'ShellRibbon component missing'),
    ('collapsed_changed = pyqtSignal(bool)', 'ShellRibbon collapsed_changed signal missing'),
    ('def set_collapsed(self, collapsed: bool, *, emit: bool = True)', 'ShellRibbon collapse API missing'),
    ('def cycle_tab(self, step: int)', 'ShellRibbon tab cycling API missing'),
    ('def refresh_theme(self)', 'ShellRibbon theme refresh API missing'),
    ('button.setFixedSize(52, 52)', '0.0.9 52x52 button geometry not preserved'),
    ('button.setIconSize(QSize(36, 36))', '0.0.9 36x36 icon geometry not preserved'),
    ('toolbar.setMinimumHeight(56)', '0.0.9 toolbar height not preserved'),
    ('toolbar.setMaximumHeight(56)', '0.0.9 toolbar height not preserved'),
    ('QToolButton.ToolButtonPopupMode.InstantPopup', '0.0.9 flyout behavior not preserved'),
    ('if action.icon().isNull():', '0.0.9 text-only menu fallback not preserved'),
    ('if self.tabs.tabText(i) == "Home"', 'Home startup tab not preserved'),
):
    require(fragment, shell, message)

# Exact Marko tab vocabulary and representative group ordering must remain.
for fragment in (
    '"File": [', '"Home": [', '"Insert": [', '"View": [', '"Settings": [', '"Help": [',
    '[("fullscreen_action"), ("status_bar_action"), ("sidebar_action")]',
    '[("source_only_action"), ("split_action"), ("preview_only_action")]',
    '[("dirty_duplicate_tabbed_action")]', '[("dirty_external_tabbed_action")]',
):
    require(fragment, shell, f"Marko 0.0.9 presentation fragment missing: {fragment}")

# Strict experimental boundary: do not import Rico's visual/RTF Ribbon or later work.
for text, fragment, label in (
    (shell, 'RibbonScrollArea', 'Rico scroll/group visual Ribbon'),
    (shell, 'QFontComboBox', 'Rico RTF font selector'),
    (shell, 'heading_selected', 'Rico RTF heading selector signal'),
    (shell, 'line_spacing_selected', 'Rico RTF line-spacing selector signal'),
    (main, '_toggle_collapsed_mode', 'Focused Mode'),
    (main, 'document_tabs', 'Document Tabs'),
):
    if fragment in text:
        errors.append(f"0.1.0 unexpectedly introduced {label}")

EXPECTED_HASHES = {'controllers/editor_manager.py': '0e1f2177753f2999007a0b9b121f15b1f62512496308730ea43938fa049d0895', 'controllers/file_actions.py': '3bdedaf92977c792ff43f6f05ce61a568a1f3f295e5ad668f89eab4323c82cc0', 'services/config_service.py': '28353bf4003d93b8b50904bd70cedc4dc9ca4b742b4ce93f4b2585825c4fcb3b', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a', 'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38', 'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73', 'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece', 'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1', 'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6', 'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc', 'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576', 'widgets/editor_page.py': '711fb194d5093149ac50640f4ff267b8bdde2417dea7e2cc0d8aaeb78e2c6c32', 'widgets/navigation.py': 'af0f5e3febf97ed351869f40772858f00d5c38abce9ebb13d65299dcc37daa30', 'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d', 'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397', 'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf'}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.0.9 file missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        errors.append(f"protected 0.0.9 file changed during ShellRibbon experiment: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.0 ShellRibbon migration check passed.")
