#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.3 Document Tabs convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
manager = (ROOT / "controllers/editor_manager.py").read_text(encoding="utf-8")
config = (ROOT / "services/config_service.py").read_text(encoding="utf-8")
shell = (ROOT / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.3"', init, "0.1.3 package identity missing")
require('"tabs_enabled": True', config, "Tabs Enabled default missing")
for fragment, message in (
    ('self.document_tabs = QTabBar(self.content_host)', 'document QTabBar missing'),
    ('self.document_tabs.setTabsClosable(True)', 'document tabs are not closable'),
    ('self.content_layout.addWidget(self.document_tabs)', 'tab strip is not above content stack'),
    ('def _sync_tabs_mode_ui(', 'tabs mode synchronization missing'),
    ('def _open_context_tab(', 'Ctrl+T context-tab behavior missing'),
    ('def _close_context(', 'Ctrl+W contextual close behavior missing'),
    ('def _cycle_context_tab(', 'context-sensitive Ctrl+Tab routing missing'),
    ('def _show_navigation_tab(', 'temporary navigation-tab implementation missing'),
    ('def _ensure_document_tab(', 'persistent document-tab implementation missing'),
    ('def _rebind_document_tab(', 'Save As tab rebind support missing'),
    ('"Close Tab / Dashboard", self._close_context, "Ctrl+W"', 'Ctrl+W parity binding missing'),
    ('"Open Context Tab", self._open_context_tab, "Ctrl+T"', 'Ctrl+T parity binding missing'),
    ('"Next Tab", lambda: self._cycle_context_tab(1), "Ctrl+Tab"', 'Ctrl+Tab parity binding missing'),
    ('"Previous Tab", lambda: self._cycle_context_tab(-1), "Ctrl+Shift+Tab"', 'Ctrl+Shift+Tab parity binding missing'),
    ('(False, "Tabs Disabled")', 'Tabs Disabled radio missing'),
    ('"Ctrl+Alt+Shift+T"', 'Tabs disable shortcut missing'),
    ('file_launch_menu = settings.addMenu("App File Launch")', 'App File Launch settings submenu missing'),
    ('self.editor_manager.module_path_rebound.connect(self._rebind_document_tab)', 'live-page path rebind is not connected to tabs'),
    ('self.editor_manager.module_closed.connect(self._remove_document_tab)', 'module-close lifecycle is not connected to tabs'),
    ('self.editor_manager.modules_reset.connect(self._reset_document_tabs)', 'workspace reset lifecycle is not connected to tabs'),
    ('self.repository.module_changed.connect(self._update_document_tab)', 'dirty/metadata tab updates missing'),
): require(fragment, main, message)

for fragment, message in (
    ('module_closed = pyqtSignal(object)', 'EditorManager module_closed signal missing'),
    ('modules_reset = pyqtSignal()', 'EditorManager modules_reset signal missing'),
    ('self.module_closed.emit(closed_path)', 'normal close does not announce tab lifecycle'),
    ('self.modules_reset.emit()', 'workspace reset does not announce tab lifecycle'),
    ('self.module_path_rebound.emit(old_path, new_path)', '0.1.2 path-rebind lifecycle regressed'),
): require(fragment, manager, message)

# Agreed shortcut repurposing: no replacement shortcuts are invented here.
if 'self.task_action = self._command("Task List", lambda: self._editor_call("toggle_task_list"), "Ctrl+T")' in main:
    errors.append("Task List still owns Ctrl+T")
if 'self.dashboard_action = self._command("Show Dashboard", self.editor_manager.show_dashboard, "Ctrl+W")' in main:
    errors.append("Show Dashboard still owns Ctrl+W")
if 'next_tabbed_tab_action' in main or 'previous_tabbed_tab_action' in main:
    errors.append("old command-tab shortcut actions remain after contextual tab routing")

# ShellRibbon change is exactly one Marko-presentation action insertion.
normalized_shell = shell.replace('                [("app_tabs_toggle_action")],\n', '', 1)
if hashlib.sha256(normalized_shell.encode("utf-8")).hexdigest() != '45d56187f52a657d4fc68bdd6308fdc455c62a45bbca84239e16a1f656dd49f0':
    errors.append("ShellRibbon changed beyond the approved Tabs toggle action insertion")

EXPECTED_HASHES = {'controllers/file_actions.py': 'd2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a', 'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38', 'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73', 'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece', 'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1', 'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6', 'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc', 'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576', 'widgets/editor_page.py': 'd9c96920ea3758de476ccbce37fba7eed0dd66505efd10d8a3f1f663f8772f74', 'widgets/navigation.py': 'af0f5e3febf97ed351869f40772858f00d5c38abce9ebb13d65299dcc37daa30', 'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d', 'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397', 'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf', 'widgets/closing_dialog.py': '6965f740940b5c5aeec9b1d4c5fd95fc859a5b4cfe64317f7acf77fd315bb9dd', 'widgets/first_run_dialog.py': '6e61f2a0ed6df1a2836201ea314612a010930f4883518035e31b120395d558dd', 'widgets/loading_indicator.py': 'f9611642a365316089a4848ae1d7c15bf6ad5b967220933b62aeb3c98cefeca6'}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.2 file missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        errors.append(f"protected 0.1.2 file changed during 0.1.3 Document Tabs convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.3 Document Tabs convergence check passed.")
