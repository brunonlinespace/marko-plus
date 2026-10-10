#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.5 window-title convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.5"', init, "0.1.5 package identity missing")
require('from marko_plus import APP_NAME', main, "canonical APP_NAME import missing")
for fragment, message in (
    ('workspace = self.project_registry.active_project.name.strip()', "Rico-style Workspace title source missing"),
    ('module = self.editor_manager.current_module', "current document title source missing"),
    ('lock_suffix = " — Locked Mode" if page is not None and page.view_only else ""', "Locked Mode title suffix missing"),
    ('dirty_prefix = "*" if module.dirty else ""', "dirty title prefix missing"),
    ('f"{dirty_prefix}{module.filename} — {workspace} — {APP_NAME}{lock_suffix}"', "active-document title format differs from approved Rico model"),
    ('self.setWindowTitle(f"{workspace} — {APP_NAME}")', "Dashboard/folder title format differs from approved Rico model"),
    ('current = self.editor_manager.current_module\n        if current is not None and current.path == module.path:\n            self._update_window_title()', "dirty/current tab title refresh hook missing"),
    ('self.heading_tabbed_action.setEnabled(mutable)\n        self._update_window_title()', "editor-state title refresh hook missing"),
):
    require(fragment, main, message)
if 'self.setWindowTitle(workspace_name)' in main:
    errors.append("obsolete Workspace-only title implementation remains")

normalized = main
normalized = normalized.replace('from marko_plus import APP_NAME\n', '', 1)
normalized = normalized.replace(
    '        self.runtime_paths = runtime_paths\n        self.setAcceptDrops(True)\n',
    '        self.runtime_paths = runtime_paths\n        self._update_window_title()\n        self.setAcceptDrops(True)\n',
    1,
)
normalized = normalized.replace(
    '    def _update_document_tab(self, module: Module) -> None:\n'
    '        current = self.editor_manager.current_module\n'
    '        if current is not None and current.path == module.path:\n'
    '            self._update_window_title()\n'
    '        index = self._tab_index_for_path(module.path)\n',
    '    def _update_document_tab(self, module: Module) -> None:\n'
    '        index = self._tab_index_for_path(module.path)\n',
    1,
)
normalized = normalized.replace(
    '            self.heading_tabbed_action.setEnabled(mutable)\n'
    '        self._update_window_title()\n\n'
    '    def _on_folder_renamed',
    '            self.heading_tabbed_action.setEnabled(mutable)\n\n'
    '    def _on_folder_renamed',
    1,
)
new_title = (
    '    def _update_window_title(self) -> None:\n'
    '        workspace = self.project_registry.active_project.name.strip()\n'
    '        module = self.editor_manager.current_module\n'
    '        if module is not None:\n'
    '            page = self._current_page()\n'
    '            lock_suffix = " — Locked Mode" if page is not None and page.view_only else ""\n'
    '            dirty_prefix = "*" if module.dirty else ""\n'
    '            self.setWindowTitle(\n'
    '                f"{dirty_prefix}{module.filename} — {workspace} — {APP_NAME}{lock_suffix}"\n'
    '            )\n'
    '        else:\n'
    '            self.setWindowTitle(f"{workspace} — {APP_NAME}")\n'
)
old_title = (
    '    def _update_window_title(self) -> None:\n'
    '        workspace_name = self.project_registry.active_project.name.strip()\n'
    '        self.setWindowTitle(workspace_name)\n'
)
if new_title not in normalized:
    errors.append("approved title method is missing or altered")
else:
    normalized = normalized.replace(new_title, old_title, 1)
if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != "fde41f22016fa705c4215551c860c2cf0778092b395b2968b2e4b0fce9e1ccda":
    errors.append("main_window.py changed beyond approved Item 18 title convergence")

EXPECTED_HASHES = {
    'controllers/__init__.py': '67b6b35855959d36806135cd7bda92ccb7264459df4ecf3565a9035b727eee5d',
    'controllers/editor_manager.py': '724185d8e7153c24e2cef78cbff3b760b8d3d0f56823b8d505f3e37ff0c68905',
    'controllers/file_actions.py': 'd2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334',
    'services/__init__.py': '70e36c5f3a0bcca0314641fe500f704d6cb8acd8a1650a3a81fcc79919d5b999',
    'services/config_service.py': 'fe842afd298100335652b6d1075f6e8172f14df3eaa017641a3e923a96cf793c',
    'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73',
    'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
    'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a',
    'services/resources.py': '17bfefd83894fdf4953eff9479244c78a96263f8398db84dadb97ebf62f113ec',
    'services/runtime_paths.py': 'c669a348bb7d9eead2ade4839a182d4b0d226decd7e047abf3238d29dc111905',
    'models/__init__.py': '013b71bd1788ab94b541b892653c7eda361a29af03a591d19b2bdfca0e12fef3',
    'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece',
    'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1',
    'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6',
    'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc',
    'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576',
    'widgets/__init__.py': '8229962d72aa5e9e6973d5babff0052e6986e9e466b985aa2555d3041dafe6d2',
    'widgets/about_dialog.py': 'e0bdb624ee4810c4c20cc5ce02e0c4d9bbf02b7cd79d221e617030a363f6a3ae',
    'widgets/closing_dialog.py': '6965f740940b5c5aeec9b1d4c5fd95fc859a5b4cfe64317f7acf77fd315bb9dd',
    'widgets/code_editor.py': 'b0299c063a23d93bea0a9afdf4bfceb16d8843867f5382a02824cd27bbcb4831',
    'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d',
    'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf',
    'widgets/editor_page.py': 'd9c96920ea3758de476ccbce37fba7eed0dd66505efd10d8a3f1f663f8772f74',
    'widgets/first_run_dialog.py': '6e61f2a0ed6df1a2836201ea314612a010930f4883518035e31b120395d558dd',
    'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397',
    'widgets/loading_indicator.py': 'f9611642a365316089a4848ae1d7c15bf6ad5b967220933b62aeb3c98cefeca6',
    'widgets/markopad_preview.py': 'e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965',
    'widgets/markopad_source_editor.py': 'dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830',
    'widgets/markopad_theme.py': '031ba0cce9b920365550ea357183aa1a2ac60701e1493ee671acddef1dd08ff5',
    'widgets/navigation.py': '0c628201fdbce6bf37dca693eee6a373849ce5a30dfc8203aabad410827e8368',
    'widgets/projects_dialog.py': 'de2aaad0a74d73fa3704fba350cfa410baccac93293d565b26ca7b9b851bcd31',
    'widgets/shell_ribbon.py': '3eb4f39321876b4b2b1521e459c45b9a4201c8dc2e2e659cacb286c5e85b3897',
    'widgets/shortcuts_dialog.py': 'c8b91135b3387e4d4bd38cb2b1bf65175b4f936d311b70683b7b7bf4a7f5aa37',
    'widgets/ui_styles.py': '8ffa933023cbf826ba7e340616eb60720ed7afbf1431c898e6fee6aabd53bd5d',
    'app.py': 'dc681f7c599b8622420972d362404b1db4f7784771b9e9af530733cca65ae4eb',
}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.4 file missing: {relative}")
        continue
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(f"protected 0.1.4 file changed during 0.1.5 Item 18 convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.5 window-title convergence check passed.")
