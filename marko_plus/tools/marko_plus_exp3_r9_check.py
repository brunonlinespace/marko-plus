#!/usr/bin/env python3
"""Static checks for the surgical Marko Plus exp3-r9 icon revision."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"
PROTECTED_ENGINES = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
}
APPROVED_ICONS = {
    "dark/show-dashboard.png": "1809fb983b70f980c35a150942dac6b05840ebfca9dc72c5ce378cd010a287c6",
    "dark/full-screen.png": "0d532888b80422ef63772bd74a1a7f79b496927571ce4dde8e04fbcf5732c1d0",
    "dark/show-sidebar.png": "34c027a2cc28ef20619166a5eddadae6a47d55dda6912041acfcbc68e3391b3f",
    "dark/app-theme.png": "70ba219d3d9475a738155aff2b1447e01a711655eac307c773eb6e166e6efd0d",
    "dark/app-dashboard.png": "374ec5a15003c04f4fd07688525be187c66e9c3eb1d09eed6f3fda178a2d5636",
    "dark/app-launch-screen.png": "0750548f18f0c15364301368623d42efbd60a8b09e51fcc9faa2be7a27ea8064",
    "dark/app-drag-and-drop.png": "975840c365fd4b742ac860ee830c6b704b6c8857305027c1cbae6c20d2c01aa1",
    "dark/system-theme.png": "93744069d0bf10000f76edfd74b0d02692ba2ded24ec89f2ee0276b4484db537",
    "dark/light-theme.png": "237f755a900ba343ac989e76343efd7cf7fafae4a2d048a523c0699379e63850",
    "dark/list-view.png": "fc586c9696f31378ac5e95d164c489e2c419b4633e56712005a425ac4d90bfa9",
    "dark/grid-view.png": "3afea513b7636450706f881ffa6902b9565c2ef52143600e409226d0a1f4806c",
    "dark/launch-dashboard.png": "d2f28f66db8c716a29f67f4d70ed404bf5cd374c14ced9fe01606a19e4541f9b",
    "dark/launch-last-file.png": "2d26e17996c9740b05f1758927c4937b22f3d149098cd608993d04d0f9973873",
    "light/show-dashboard.png": "1289d50ed550ca38a1f9f9da410f3fffeffeb568724ffaf025b6d517ef501af4",
    "light/full-screen.png": "f0193a2040d70680d623edaac59feac290cc04c7680613e88c5f2a9fc60121a1",
    "light/show-sidebar.png": "4e6ee7e26343c0122b9ff9ed0ecf5e76192539a2141b1aec5ee04c267f386c81",
    "light/app-theme.png": "d5fbe126aa26fefa1a79e7b90fb467597d3edbea6f54107512efd126f04b2227",
    "light/app-dashboard.png": "af59a0b9d01e537fe122fa412b7db6f84dba7bb8e7b211ad5966e90a47ec32eb",
    "light/app-launch-screen.png": "43293a91bca2cf97d61786b92136dc0e6f0db232534421938907a57074278f29",
    "light/app-drag-and-drop.png": "4ad0271b908342716dd8eed46638e1fb7cdc784cb3b34144eb4215f00504bb12",
    "light/system-theme.png": "4feeab9b89a1c17515325de6d44d53c7bc36e02d4f0db775fff15f48338762ef",
    "light/light-theme.png": "2549c89383fed3cb75c09d13906cc5b80b15de0a9fc3ee0685fff379c6b9b6ca",
    "light/list-view.png": "c53e3e1baada5a7d9bc1e7780d7dfed51f7e95e3ebe86aba2ac8d88dc95a9e29",
    "light/grid-view.png": "b5120b1996a0df93d327b982838173ff7d53d945f6172eefeb8f56be0e8c0cf9",
    "light/launch-dashboard.png": "4ccce4fb5bf5dd861d736a310b2a01202a5a861ee65b144c2b5e140b43b42db3",
    "light/launch-last-file.png": "1858194d51eff356f25cd34e51c4c04b24ec951e48cf1bdf317541e5a44b7527",
}
UNCHANGED_MARKOPAD_ICONS = {
    "dark/dark-mode.png": "fdcef0eabb35c6e2dc79dc2f6b08dc5ef419da40b6c171404cecc3914373cd2a",
    "dark/drop-active.png": "62f28296f65215f63a1a35eefae4f1d6c6caca438cdf870f47e928b3ce9def87",
    "dark/drop-new-window.png": "b149a04b3d49daec932e740d52e7e24fde1b965725f0eccb51d8a424440d4fed",
    "light/dark-mode.png": "d8143d652b0b040cb79593ea2ec009d650645fb2a32247f9bc0048a972fd52be",
    "light/drop-active.png": "fd7e97e545473113aff54de101d3934e8cabe19a93c054038a22c42ebd1c8669",
    "light/drop-new-window.png": "aeb8a0f3ba18c3ee03caea065df4778ff71ba8dfd737f7607719e66a3c7a2ceb",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    icon_root = PACKAGE / "assets/toolbar-icons"

    if ('APP_REVISION = "exp3-r9"' not in constants and
            'APP_REVISION = "exp3-r10"' not in constants and
            'APP_REVISION = "exp3-r11"' not in constants and
            'APP_REVISION = "0.0.1"' not in constants and
            'APP_REVISION = "0.0.1-r3"' not in constants):
        errors.append("Current source revision predates exp3-r9")

    for relative, expected in PROTECTED_ENGINES.items():
        if digest(PACKAGE / relative) != expected:
            errors.append(f"Protected Markopad engine changed: {relative}")
    for relative, expected in {**APPROVED_ICONS, **UNCHANGED_MARKOPAD_ICONS}.items():
        path = icon_root / relative
        if not path.is_file() or digest(path) != expected:
            errors.append(f"Icon is missing or changed: {relative}")

    expected_settings = (
        '"Settings": [[self.theme_system_action, self.theme_dark_action, '
        'self.theme_light_action], [self.list_action, self.grid_action], '
        '[self.launch_dashboard_action, self.launch_last_file_action], '
        '[self.drop_active_action, self.drop_new_window_action]],'
    )
    if expected_settings not in window:
        errors.append("Settings Tabbed page is not flattened into four direct groups")
    tabbed_body = window[
        window.index("        pages = {"):
        window.index("        for name, groups in pages.items()")
    ]
    for wrapper in (
        "theme_tabbed_action",
        "dashboard_tabbed_action",
        "launch_screen_tabbed_action",
        "drop_tabbed_action",
    ):
        if wrapper in tabbed_body:
            errors.append(f"Compact submenu wrapper remains in Tabbed page: {wrapper}")

    for fragment in (
        'theme_menu = settings.addMenu("App Theme")',
        'dashboard_menu = settings.addMenu("App Dashboard")',
        'launch_screen_menu = settings.addMenu("App Launch Screen")',
        'drop_menu = settings.addMenu("App Drag-and-Drop")',
        '"dashboard_action":"show-dashboard"',
        '"fullscreen_action":"full-screen"',
        '"sidebar_action":"show-sidebar"',
        '"theme_tabbed_action":"app-theme"',
        '"dashboard_tabbed_action":"app-dashboard"',
        '"launch_screen_tabbed_action":"app-launch-screen"',
        '"drop_tabbed_action":"app-drag-and-drop"',
        '"theme_system_action":"system-theme"',
        '"theme_dark_action":"dark-mode"',
        '"theme_light_action":"light-theme"',
        '"list_action":"list-view"',
        '"grid_action":"grid-view"',
        '"launch_dashboard_action":"launch-dashboard"',
        '"launch_last_file_action":"launch-last-file"',
        '"drop_active_action":"drop-active"',
        '"drop_new_window_action":"drop-new-window"',
    ):
        if fragment not in window:
            errors.append(f"Menu/icon wiring is missing: {fragment}")

    for source in (PACKAGE / "app_constants.py", PACKAGE / "widgets/main_window.py"):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r9 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Marko Plus exp3-r9 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
