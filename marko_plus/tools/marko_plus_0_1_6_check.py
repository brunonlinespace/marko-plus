#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.6 Locked Mode convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
page = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
manager = (ROOT / "controllers/editor_manager.py").read_text(encoding="utf-8")
config = (ROOT / "services/config_service.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.6"', init, "0.1.6 package identity missing")

# Rico Plus 0.0.8 application-wide Locked Mode contract.
for fragment, message in (
    ('self.view_only_action = self._command("Locked Mode", self._toggle_lock_editor_current, "F12", checkable=True)', "shell Locked Mode command differs from Rico contract"),
    ('def _toggle_lock_editor_current(self, checked: bool) -> None:', "Rico-style shell lock owner missing"),
    ('self.editor_manager.set_lock_editor(resulting)', "shell does not delegate resulting state to EditorManager"),
    ('bool(self.config.get("lock_editor", False))', "shell does not use common lock_editor preference"),
    ('lock_suffix = " — Locked Mode" if page is not None and page.view_only else ""', "Locked Mode title-state synchronization missing"),
    ('("Locked Mode", self.view_only_action)', "shortcut reference does not expose Locked Mode"),
):
    require(fragment, main, message)

for fragment, message in (
    ('def set_lock_editor(self, enabled: bool) -> None:', "EditorManager application-wide lock method missing"),
    ('self.config.set("lock_editor", enabled, save=True)', "EditorManager does not persist lock_editor"),
    ('for _path, state in tuple(self.states):', "EditorManager does not enumerate live pages"),
    ('page.set_view_only(enabled)', "EditorManager does not apply lock to every live EditorPage"),
    ('page.set_view_only(bool(self.config.get("lock_editor", False)))', "new/reopened pages do not inherit persisted lock"),
    ('if page.view_only:\n            page.scroll_to_top()', "locked document opening does not reset to top"),
):
    require(fragment, manager, message)

for fragment, message in (
    ('self.view_only_action = self._menu_action(view_menu, "Locked Mode", self.toggle_view_only, checkable=True)', "EditorPage Locked Mode action missing"),
    ('should_confirm = bool(self.config.get("confirm_locked_mode_disable", True))', "persisted unlock-confirmation preference is not consulted"),
    ('dialog.setWindowTitle("Disable Locked Mode? — Marko Plus")', "approved disable dialog title missing"),
    ('dialog.setText("Locked Mode protects files from accidental changes.")', "approved Locked Mode protection text missing"),
    ('"Don\'t ask again when disabling Locked Mode", dialog', "Rico-style don't-ask-again checkbox missing"),
    ('self.config.set(\n                    "confirm_locked_mode_disable", False, save=True\n                )', "don't-ask-again choice is not persisted"),
    ('def scroll_to_top(self) -> None:', "Rico-style locked-open scroll helper missing"),
    ('cursor.movePosition(QTextCursor.MoveOperation.Start)', "locked-open cursor reset missing"),
    ('bar.setValue(bar.minimum())', "locked-open viewport reset missing"),
    ('def set_view_only(self, enabled: bool) -> None:', "managed EditorPage lock setter missing"),
    ('"Locked Mode enabled." if enabled else "Editing mode enabled."', "managed lock status message differs from Rico contract"),
    ('message = "Editing is disabled while Locked Mode is enabled."', "blocked-edit status uses obsolete terminology"),
    ('"Locked Mode — Marko Plus"', "blocked-edit dialog uses obsolete terminology"),
    ('("Locked Mode:", "On" if self.view_only else "Off")', "Properties does not use Locked Mode terminology"),
):
    require(fragment, page, message)

for fragment, message in (
    ('"lock_editor": False', "lock_editor default missing"),
    ('"confirm_locked_mode_disable": True', "unlock-confirmation default missing"),
    ('legacy_lock = loaded.pop("editor_view_only", None)', "legacy editor_view_only migration missing"),
    ('loaded["lock_editor"] = legacy_lock', "legacy lock value is not migrated"),
):
    require(fragment, config, message)

# Obsolete Marko-only lock contract must be gone from runtime code.
for fragment, text, message in (
    ('"Lock Editor"', main, "obsolete Lock Editor shell terminology remains"),
    ('"Lock Editor"', page, "obsolete Lock Editor EditorPage terminology remains"),
    ('config.get("editor_view_only"', main, "obsolete editor_view_only read remains in MainWindow"),
    ('config.get("editor_view_only"', page, "obsolete editor_view_only read remains in EditorPage"),
    ('config.set("editor_view_only"', page, "obsolete EditorPage-owned lock persistence remains"),
):
    if fragment in text:
        errors.append(message)

# Protect the current app icon exactly as requested.
EXPECTED_ICONS = {
    'assets/icons/markopad.png': '22a09047102f543744843917d42c76be48cee58b360afb91b6acd2779e9dfd3c',
    'assets/icons/markopad-master.png': '9dd0597828ccd04a0ebd2db1ce39dfda9636a114042a4f37add1b9aa2e2b1870',
    'assets/icons/markopad.ico': 'de50fb7b2064cd36b0083bab12a03e7df67fa1fc0284c42f9847bef71fe4ee6e',
    'assets/icons/markopad-about.png': '4f0258c22404c8016c93f0a57a606be0bd7ef540a4cd4a5ee49b1e2fa7a652e9',
}
for relative, expected in EXPECTED_ICONS.items():
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(f"current Marko Plus icon changed during 0.1.6: {relative}")

# All unrelated runtime scaffold must remain byte-for-byte 0.1.5.
EXPECTED_HASHES = {
    'controllers/__init__.py': '67b6b35855959d36806135cd7bda92ccb7264459df4ecf3565a9035b727eee5d',
    'controllers/file_actions.py': 'd2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334',
    'services/__init__.py': '70e36c5f3a0bcca0314641fe500f704d6cb8acd8a1650a3a81fcc79919d5b999',
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
        errors.append(f"protected 0.1.5 runtime file missing: {relative}")
        continue
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(f"protected 0.1.5 runtime file changed during 0.1.6 Item 17 convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.6 Locked Mode convergence check passed.")
