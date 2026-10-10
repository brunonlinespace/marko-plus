#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.4.1 toolbar-icon family gate."""
from __future__ import annotations
import hashlib
import struct
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []

def req(cond: bool, message: str) -> None:
    if not cond:
        errors.append(message)

def src(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")

def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()

def png_ihdr(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG with IHDR")
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type

main = src("widgets/main_window.py")
shell = src("widgets/shell_ribbon.py")
card = src("widgets/dashboard_card.py")
init = src("__init__.py")
constants = src("app_constants.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.4.1"' in init, "0.4.1 package identity missing")
req('APP_REVISION = "0.4.1"' in constants, "0.4.1 revision identity missing")
req('Current release: **0.4.1**' in readme, "README current release stale")

# Keep the established 0.3.10/Plus Ribbon geometry.
for fragment in (
    'button.setIconSize(QSize(36, 36))',
    'toolbar.setIconSize(QSize(36, 36))',
    'button.setFixedSize(52, 52)',
):
    req(fragment in shell, f"0.4.1 Ribbon geometry missing: {fragment}")
req('QSize(38, 38)' not in shell, "38 px experimental Ribbon icon geometry returned")
req('button.setIconSize(QSize(28, 28))' in card, "Dashboard-card 28 px icon geometry changed")

expected_mappings = (
    '"import_file_action":"import-file"',
    '"open_external_file_action":"open-external-file"',
    '"paste_markdown_action":"paste-markdown"',
    '"quote_action":"quote-block"',
    '"inline_code_action":"inline-code"',
    '"code_fence_action":"code-block"',
    '"left_sidebar_action":"dock-left"',
    '"right_sidebar_action":"dock-right"',
    '"app_sidebar_menu_action":"sidebar-settings"',
    '"app_file_launch_menu_action":"file-launch"',
    '"tabs_enabled_action":"tabs-enabled"',
    '"tabs_disabled_action":"tabs-disabled"',
    '"dirty_duplicate_tabbed_action":"dirty-duplicate-policy"',
    '"dirty_external_tabbed_action":"dirty-external-policy"',
    '"heading_tabbed_action":"heading-group"',
    '"code_tabbed_action":"code-group"',
    '"link_tabbed_action":"link-group"',
    'self._toolbar_icon_path("tabs-enabled" if self._tabs_enabled() else "tabs-disabled")',
)
for fragment in expected_mappings:
    req(fragment in main, f"new semantic icon mapping missing: {fragment}")

for retired in (
    '"paste_markdown_action":"paste-plain"',
    '"inline_code_action":"markdown-source"',
    '"code_fence_action":"markdown-source"',
    '"left_sidebar_action":"show-sidebar"',
    '"tabs_enabled_action":"app-drag-and-drop"',
    '"dirty_duplicate_tabbed_action":"duplicate-file"',
    '"dirty_external_tabbed_action":"external-editor"',
    '"heading_tabbed_action":"heading-0"',
    '"code_tabbed_action":"markdown-source"',
    '"link_tabbed_action":"insert-link"',
):
    req(retired not in main, f"retired duplicated icon mapping returned: {retired}")

required_new = {
    "import-file", "open-external-file", "paste-markdown", "inline-code", "code-block",
    "code-group", "quote-block", "dock-left", "dock-right", "tabs-enabled",
    "tabs-disabled", "dirty-duplicate-policy", "dirty-external-policy", "link-group",
    "heading-group", "file-launch", "sidebar-settings",
}
expected_count = 121
icon_root = PACKAGE / "assets" / "toolbar-icons"
for scheme in ("light", "dark"):
    directory = icon_root / scheme
    pngs = sorted(directory.glob("*.png"))
    req(len(pngs) == expected_count, f"{scheme} family count is {len(pngs)}, expected {expected_count}")
    names = {p.stem for p in pngs}
    req(required_new <= names, f"{scheme} family missing new semantic assets: {sorted(required_new - names)}")
    digests: dict[str, str] = {}
    for path in pngs:
        try:
            width, height, color_type = png_ihdr(path)
        except (OSError, ValueError) as exc:
            errors.append(f"invalid {scheme} toolbar icon {path.name}: {exc}")
            continue
        req((width, height) == (64, 64), f"{scheme}/{path.name} is {width}x{height}, expected 64x64")
        req(color_type == 6, f"{scheme}/{path.name} is not RGBA PNG (color type {color_type})")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in digests:
            errors.append(f"duplicate rendered icon in {scheme}: {path.name} == {digests[digest]}")
        digests[digest] = path.name

protected = {'controllers/editor_manager.py': 'e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4', 'controllers/file_actions.py': '8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241', 'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'models/module_repository.py': 'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5', 'services/config_service.py': '5d5af506f37b9c26c6a3d3fe4f98bdae66f77c62b0ac949aa58035a2f35326f3', 'widgets/editor_page.py': 'c01d9119dff00942f65c4b24d30ec01b5304e9cdf799e70aeac966edd2ee5970', 'widgets/dashboard_card.py': '77059cf803d56373d8c7e3c145410ae8216212f77a96256e01543ea6552580a4', 'widgets/navigation.py': 'cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef', 'widgets/dashboard.py': 'b75d978aa0c6f1c01a3ca8eae586eda0b646398b20f4b993fc75e8ce70a6c773', 'widgets/folder_dashboard.py': 'eea55c93f245529926d0727dca4ceebce61975c3d0343a41d5978a56bee474f6', 'widgets/shell_ribbon.py': 'dd4f555f893923a26cd5429a082bd15acba8017946302fa950cd5394f2ce95b0'}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"out-of-scope 0.3.10 production file changed: {relative}")

if errors:
    print("Marko Plus 0.4.1 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("PASS: Marko Plus 0.4.1 toolbar icon family + preserved 36 px Ribbon contract")
