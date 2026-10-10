#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.2 EditorPage lifecycle convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
page = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
manager = (ROOT / "controllers/editor_manager.py").read_text(encoding="utf-8")
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
file_actions = (ROOT / "controllers/file_actions.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.2"', init, "0.1.2 package identity missing")

# Item 10: failed-load boundary copied from Rico lifecycle.
require('self.loaded_successfully = self.load_from_disk(show_errors=False)', page, "EditorPage does not record initial load success")
require('if not page.loaded_successfully:', manager, "EditorManager does not reject failed initial loads")
require('state.clear_editor()', manager, "failed-load path does not clear editor state")
require('module.loaded = False', manager, "failed-load path does not leave Module unloaded")

# Item 9: live-page Save As rebinding.
require('path_changed = pyqtSignal(object, object, object)', page, "EditorPage path-change signal missing")
require('def save_as_file(self, target: str | Path) -> bool:', page, "live-page Save As method missing")
require('self.path_changed.emit(self, old_path, destination)', page, "Save As does not announce path rebind")
require('module_path_rebound = pyqtSignal(object, object)', manager, "EditorManager rebind signal missing")
require('page.path_changed.connect(self._rebind_page_path)', manager, "EditorPage path change is not owned by EditorManager")
require('def _rebind_page_path(', manager, "EditorManager live-page rebind method missing")
require('target_state.editor_page = page', manager, "target Module state does not retain the live page")
require('old_state.clear_editor()', manager, "old Module state is not detached from live page")
require('old_module.loaded = False', manager, "old Module remains marked loaded after Save As")
require('self.module_path_rebound.emit(old_path, new_path)', manager, "rebind lifecycle signal not emitted")
require('self.current_module_changed.emit(target)', manager, "current Module does not move to Save As target")
require('page.save_as_file(target)', main, "MainWindow Save As does not use live-page rebind writer")
require('target = page.module.path', file_actions, "External Editor still depends on obsolete saved-path bridge")

for forbidden, label in (
    ('mark_clean_for_save_as', 'old Save As page-retirement helper'),
    ('_external_version_saved_path', 'old external-editor Save Version As bridge'),
):
    for text, where in ((page, 'EditorPage'), (main, 'MainWindow'), (file_actions, 'FileActionsController')):
        if forbidden in text:
            errors.append(f"{where} still contains {label}")

# The two Save As methods must not retain scanner-dependent close/reopen completion.
for method_name, next_name in (("_save_external_change_version_as", "_save_current_as"), ("_save_current_as", "_undo")):
    start = main.index(f"    def {method_name}")
    end = main.index(f"    def {next_name}", start)
    block = main[start:end]
    for forbidden in ('self.editor_manager.close_module(', 'self._queue_created_module_open(', 'self.watcher.request_rescan()'):
        if forbidden in block:
            errors.append(f"{method_name} still uses old scanner-dependent Save As lifecycle: {forbidden}")

# Tabs remain deliberately absent from this preparatory release.
for forbidden in ('_ensure_document_tab(', 'document_closed = pyqtSignal', 'documents_reset = pyqtSignal', 'tabs_enabled'):
    if forbidden in manager or forbidden in main:
        errors.append(f"Document Tabs work was pulled into 0.1.2: {forbidden}")

EXPECTED_HASHES = {'widgets/shell_ribbon.py': '45d56187f52a657d4fc68bdd6308fdc455c62a45bbca84239e16a1f656dd49f0', 'services/config_service.py': '28353bf4003d93b8b50904bd70cedc4dc9ca4b742b4ce93f4b2585825c4fcb3b', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a', 'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38', 'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73', 'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece', 'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1', 'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6', 'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc', 'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576', 'widgets/navigation.py': 'af0f5e3febf97ed351869f40772858f00d5c38abce9ebb13d65299dcc37daa30', 'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d', 'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397', 'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf', 'widgets/closing_dialog.py': '6965f740940b5c5aeec9b1d4c5fd95fc859a5b4cfe64317f7acf77fd315bb9dd', 'widgets/first_run_dialog.py': '6e61f2a0ed6df1a2836201ea314612a010930f4883518035e31b120395d558dd', 'widgets/loading_indicator.py': 'f9611642a365316089a4848ae1d7c15bf6ad5b967220933b62aeb3c98cefeca6'}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.1 file missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        errors.append(f"protected 0.1.1 file changed during 0.1.2 lifecycle convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.2 EditorPage lifecycle convergence check passed.")
