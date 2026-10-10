#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.7 theme convergence."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import tempfile

from marko_plus.services.config_service import ConfigService

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / "widgets/main_window.py").read_text(encoding="utf-8")
page = (ROOT / "widgets/editor_page.py").read_text(encoding="utf-8")
manager = (ROOT / "controllers/editor_manager.py").read_text(encoding="utf-8")
config = (ROOT / "services/config_service.py").read_text(encoding="utf-8")
theme = (ROOT / "widgets/markopad_theme.py").read_text(encoding="utf-8")
app = (ROOT / "app.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.7"', init, "0.1.7 package identity missing")

# Items 19/20: independent Light defaults and legacy migration.
for fragment, message in (
    ('"app_theme": "light"', "Light application default missing"),
    ('"editor_canvas_light": True', "Light editor-canvas default missing"),
    ('loaded.pop("editor_canvas_follows_app_theme", None)', "retired follow key is not removed during migration"),
    ('if not isinstance(loaded.get("editor_canvas_light"), bool):', "legacy canvas validation/migration missing"),
    ('loaded["editor_canvas_light"] = True', "undefined legacy canvas does not migrate to Light"),
):
    require(fragment, config, message)

defaults_block = config.split('DEFAULTS: dict[str, Any] = {', 1)[1].split('    }', 1)[0]
if 'editor_canvas_follows_app_theme' in defaults_block:
    errors.append("retired editor_canvas_follows_app_theme remains in active defaults")
for runtime_text, label in ((main, "MainWindow"), (page, "EditorPage")):
    if 'self.config.get("editor_canvas_follows_app_theme"' in runtime_text:
        errors.append(f"{label} still reads retired editor_canvas_follows_app_theme at runtime")

for fragment, message in (
    ('stored = self.config.get("editor_canvas_light", True)', "EditorPage does not read independent canvas preference"),
    ('return stored if isinstance(stored, bool) else True', "EditorPage canvas fallback is not Light"),
):
    require(fragment, page, message)
for fragment, message in (
    ('self.config.set("editor_canvas_light", not bool(checked), save=True)', "Dark Editor does not persist only its independent canvas choice"),
    ('self.editor_manager.show_current_editor_status(', "Dark Editor feedback is not editor-scoped"),
    ('"Editor canvas switched to a dark background."', "dark editor-canvas feedback missing"),
    ('"Editor canvas switched to a light background."', "light editor-canvas feedback missing"),
    ('self.show_status(f"Theme: {label}.")', "application-theme feedback does not use Rico contract"),
):
    require(fragment, main, message)
require('def show_current_editor_status(self, message: str, timeout: int = 0) -> None:', manager, "EditorManager current-editor status router missing")
require('def show_editor_status(self, message: str, timeout: int = 0) -> None:', page, "EditorPage editor-status helper missing")

# Fresh/default startup path must prefer Light without changing explicit user choices.
require('config.get("app_theme", "light")', app, "startup app-theme fallback is not Light")
if '"editor_canvas_follows_app_theme": False' in main:
    errors.append("Dark Editor still writes retired follow-state coupling")

# Rico's softer Light surfaces, Marko's own teal accent.
for fragment, message in (
    ('QPalette.ColorRole.Window, QColor("#D4D4D4")', "soft Light Window surface missing"),
    ('QPalette.ColorRole.Base, QColor("#F4F4F4")', "soft Light Base surface missing"),
    ('QPalette.ColorRole.Button, QColor("#E4E4E4")', "soft Light Button surface missing"),
    ('QPalette.ColorRole.Highlight, QColor("#0B8781")', "Marko teal Light highlight missing"),
):
    require(fragment, theme, message)
if '#B24A3B' in theme:
    errors.append("Rico brick accent was introduced into Marko theme")
if '#F5F6F7' in theme or 'QPalette.ColorRole.Base, QColor("#FFFFFF")' in theme.split('else:', 1)[1]:
    errors.append("older aggressive Light surface colors remain in the Light branch")

# Exercise migration without importing PyQt.
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps({
        "app_theme": "dark",
        "editor_canvas_follows_app_theme": True,
        "editor_canvas_light": None,
    }), encoding="utf-8")
    cfg = ConfigService(path)
    if cfg.get("app_theme") != "dark": errors.append("migration overwrote an existing app theme")
    if cfg.get("editor_canvas_light") is not True: errors.append("legacy null canvas did not migrate to Light")
    if cfg.get("editor_canvas_follows_app_theme") is not None: errors.append("retired follow key remains live after migration")
    saved = json.loads(path.read_text(encoding="utf-8"))
    if "editor_canvas_follows_app_theme" in saved: errors.append("retired follow key remains on disk after migration")

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "config.json"
    path.write_text(json.dumps({
        "app_theme": "system",
        "editor_canvas_follows_app_theme": False,
        "editor_canvas_light": False,
    }), encoding="utf-8")
    cfg = ConfigService(path)
    if cfg.get("app_theme") != "system": errors.append("migration overwrote existing System theme")
    if cfg.get("editor_canvas_light") is not False: errors.append("migration overwrote explicit Dark Editor choice")

EXPECTED_ICONS = {
    "assets/icons/markopad.png": "22a09047102f543744843917d42c76be48cee58b360afb91b6acd2779e9dfd3c",
    "assets/icons/markopad-master.png": "9dd0597828ccd04a0ebd2db1ce39dfda9636a114042a4f37add1b9aa2e2b1870",
    "assets/icons/markopad.ico": "de50fb7b2064cd36b0083bab12a03e7df67fa1fc0284c42f9847bef71fe4ee6e",
    "assets/icons/markopad-about.png": "4f0258c22404c8016c93f0a57a606be0bd7ef540a4cd4a5ee49b1e2fa7a652e9"
}
for relative, expected in EXPECTED_ICONS.items():
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(f"current Marko Plus icon changed during 0.1.7: {relative}")

EXPECTED_HASHES = {
    "controllers/__init__.py": "67b6b35855959d36806135cd7bda92ccb7264459df4ecf3565a9035b727eee5d",
    "controllers/file_actions.py": "d2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334",
    "services/__init__.py": "70e36c5f3a0bcca0314641fe500f704d6cb8acd8a1650a3a81fcc79919d5b999",
    "services/desktop_launcher.py": "e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73",
    "services/file_io.py": "27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "services/module_scanner.py": "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "services/project_registry.py": "e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a",
    "services/resources.py": "17bfefd83894fdf4953eff9479244c78a96263f8398db84dadb97ebf62f113ec",
    "services/runtime_paths.py": "c669a348bb7d9eead2ade4839a182d4b0d226decd7e047abf3238d29dc111905",
    "models/__init__.py": "013b71bd1788ab94b541b892653c7eda361a29af03a591d19b2bdfca0e12fef3",
    "models/module.py": "54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece",
    "models/module_repository.py": "6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1",
    "models/module_state.py": "69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6",
    "models/module_state_store.py": "436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc",
    "models/workspace_folder.py": "1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576",
    "widgets/__init__.py": "8229962d72aa5e9e6973d5babff0052e6986e9e466b985aa2555d3041dafe6d2",
    "widgets/about_dialog.py": "e0bdb624ee4810c4c20cc5ce02e0c4d9bbf02b7cd79d221e617030a363f6a3ae",
    "widgets/closing_dialog.py": "6965f740940b5c5aeec9b1d4c5fd95fc859a5b4cfe64317f7acf77fd315bb9dd",
    "widgets/code_editor.py": "b0299c063a23d93bea0a9afdf4bfceb16d8843867f5382a02824cd27bbcb4831",
    "widgets/dashboard.py": "3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d",
    "widgets/dashboard_card.py": "72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf",
    "widgets/first_run_dialog.py": "6e61f2a0ed6df1a2836201ea314612a010930f4883518035e31b120395d558dd",
    "widgets/folder_dashboard.py": "9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397",
    "widgets/loading_indicator.py": "f9611642a365316089a4848ae1d7c15bf6ad5b967220933b62aeb3c98cefeca6",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/navigation.py": "0c628201fdbce6bf37dca693eee6a373849ce5a30dfc8203aabad410827e8368",
    "widgets/projects_dialog.py": "de2aaad0a74d73fa3704fba350cfa410baccac93293d565b26ca7b9b851bcd31",
    "widgets/shell_ribbon.py": "3eb4f39321876b4b2b1521e459c45b9a4201c8dc2e2e659cacb286c5e85b3897",
    "widgets/shortcuts_dialog.py": "c8b91135b3387e4d4bd38cb2b1bf65175b4f936d311b70683b7b7bf4a7f5aa37",
    "widgets/ui_styles.py": "8ffa933023cbf826ba7e340616eb60720ed7afbf1431c898e6fee6aabd53bd5d"
}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.6 runtime file missing: {relative}")
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        errors.append(f"protected 0.1.6 runtime file changed during 0.1.7 theme convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.7 theme-independence convergence check passed.")
