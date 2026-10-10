#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.1.4 navigation robustness convergence."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parents[1]
navigation = (ROOT / "widgets/navigation.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.1.4"', init, "0.1.4 package identity missing")
for fragment, message in (
    ("QHeaderView", "QHeaderView import missing"),
    ("self.tree.header().setStretchLastSection(False)", "tree last-section stretching is still enabled"),
    ("self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)", "ResizeToContents tree-column policy missing"),
    ("self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)", "as-needed horizontal scrollbar policy missing"),
    ("self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)", "per-pixel horizontal scrolling missing"),
    ("self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)", "tree text elision is not disabled"),
):
    require(fragment, navigation, message)

# Prove Navigation changed only by the exact Item 13 Rico Plus configuration.
normalized = navigation
normalized = normalized.replace("    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTreeWidget,\n", "    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QPushButton, QTreeWidget,\n", 1)
exact_block = (
    "        # Preserve the real width of long workspace paths instead of forcing\n"
    "        # the sole tree column to the sidebar viewport.  This restores native\n"
    "        # horizontal overflow/scrolling for deeply nested folders and files.\n"
    "        self.tree.header().setStretchLastSection(False)\n"
    "        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)\n"
    "        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)\n"
    "        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)\n"
    "        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)\n"
)
if exact_block not in normalized:
    errors.append("exact Rico Plus Item 13 navigation block is missing or altered")
else:
    normalized = normalized.replace(exact_block, "", 1)
if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != "af0f5e3febf97ed351869f40772858f00d5c38abce9ebb13d65299dcc37daa30":
    errors.append("navigation.py changed beyond the approved Item 13 long-path configuration")

EXPECTED_HASHES = {
    'controllers/editor_manager.py': '724185d8e7153c24e2cef78cbff3b760b8d3d0f56823b8d505f3e37ff0c68905',
    'controllers/file_actions.py': 'd2bf6b3e170d44fb08ceb3e3e5c2fba9b4563bb64a53ef3e7c111994dc273334',
    'services/config_service.py': 'fe842afd298100335652b6d1075f6e8172f14df3eaa017641a3e923a96cf793c',
    'services/desktop_launcher.py': 'e4c79d3476d5770611a0f4cfc77549d2cf5fa798f5adc52eff1605dd5b7e1b73',
    'services/file_io.py': '27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38',
    'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893',
    'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f',
    'services/project_registry.py': 'e85f6911cec4fb217408a7be4c021813edf9917e41e7182c10dc3331f2f3813a',
    'services/resources.py': '17bfefd83894fdf4953eff9479244c78a96263f8398db84dadb97ebf62f113ec',
    'services/runtime_paths.py': 'c669a348bb7d9eead2ade4839a182d4b0d226decd7e047abf3238d29dc111905',
    'models/module.py': '54eb7b0d3dbfb9f26e45dd8788c7aa583e9802d042c1531fe58ef1969bc08ece',
    'models/module_repository.py': '6926b8f2e9a413bf66cf703bbea8d8763beaf616611afec3f97b405aa4f1cab1',
    'models/module_state.py': '69f5044fb913dfde4c3b45f874a713dbc25906d52c1af1a57bfda8e40bc7bad6',
    'models/module_state_store.py': '436b746333ad39fe1c34e4ef01f558efbf3a918d338a6e970eb88f9b87ac4ddc',
    'models/workspace_folder.py': '1b6ba6d32a0f9f3dbb103a3e9408925398ff0fd3db38f6b4d4aff46837db0576',
    'widgets/main_window.py': 'fde41f22016fa705c4215551c860c2cf0778092b395b2968b2e4b0fce9e1ccda',
    'widgets/editor_page.py': 'd9c96920ea3758de476ccbce37fba7eed0dd66505efd10d8a3f1f663f8772f74',
    'widgets/shell_ribbon.py': '3eb4f39321876b4b2b1521e459c45b9a4201c8dc2e2e659cacb286c5e85b3897',
    'widgets/dashboard.py': '3302a3936771b8240877f692e1ee219bbaeb354ec5d71eb01210cfb30585700d',
    'widgets/folder_dashboard.py': '9cd1da5ddbc7b1dbc360a5d19f206ed404d14ad6af7bf706c7b03c3e8951f397',
    'widgets/dashboard_card.py': '72d401cedfc4ca4a65787203ef0757edf1ed9ffddae33347f7614ee5d2bc23bf',
    'widgets/closing_dialog.py': '6965f740940b5c5aeec9b1d4c5fd95fc859a5b4cfe64317f7acf77fd315bb9dd',
    'widgets/first_run_dialog.py': '6e61f2a0ed6df1a2836201ea314612a010930f4883518035e31b120395d558dd',
    'widgets/loading_indicator.py': 'f9611642a365316089a4848ae1d7c15bf6ad5b967220933b62aeb3c98cefeca6',
    'widgets/projects_dialog.py': 'de2aaad0a74d73fa3704fba350cfa410baccac93293d565b26ca7b9b851bcd31',
    'widgets/shortcuts_dialog.py': 'c8b91135b3387e4d4bd38cb2b1bf65175b4f936d311b70683b7b7bf4a7f5aa37',
    'widgets/ui_styles.py': '8ffa933023cbf826ba7e340616eb60720ed7afbf1431c898e6fee6aabd53bd5d',
    'app.py': 'dc681f7c599b8622420972d362404b1db4f7784771b9e9af530733cca65ae4eb',
}
for relative, expected in EXPECTED_HASHES.items():
    path = ROOT / relative
    if not path.is_file():
        errors.append(f"protected 0.1.3 file missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        errors.append(f"protected 0.1.3 file changed during 0.1.4 Item 13 convergence: {relative}")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.1.4 navigation robustness convergence check passed.")
