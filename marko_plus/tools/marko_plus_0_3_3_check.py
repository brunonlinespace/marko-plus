#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.3 Grid/mouse-navigation release gate."""
from __future__ import annotations

import hashlib
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []

def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)

def src(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")

def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()

main = src("widgets/main_window.py")
card = src("widgets/dashboard_card.py")
init = src("__init__.py")
constants = src("app_constants.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.3.3"' in init, "0.3.3 package identity missing")
req('APP_REVISION = "0.3.3"' in constants, "0.3.3 revision identity missing")

for fragment in (
    'QPushButton("" if grid else text)',
    'button.setFixedSize(44, 44)',
    'button.setIconSize(QSize(28, 28))',
    'button.setAccessibleName(text)',
    'minimum_width=None if grid else 96',
):
    req(fragment in card, f"Grid icon-button contract missing: {fragment}")
req('button.setMinimumHeight(32)' not in card, "old Grid minimum-height treatment remains")

for fragment in (
    'app.installEventFilter(self)',
    'event.button() == Qt.MouseButton.BackButton',
    'self._navigation_history: list[str] = []',
    'if len(self._navigation_history) > 64:',
    'self._navigation_pending = target',
    'QTimer.singleShot(0, self._commit_navigation_record)',
    'target.startswith("folder:")',
    'target.startswith("document:")',
):
    req(fragment in main, f"mouse Back navigation contract missing: {fragment}")
req('Qt.Key.Key_Backspace' not in main, "keyboard Backspace navigation was added out of scope")

req('Current release: **0.3.3**' in readme, "root README current release is stale")

protected = {'services/open_document_monitor.py': '3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db', 'services/filesystem_watcher.py': 'cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893', 'services/module_scanner.py': 'a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f', 'controllers/editor_manager.py': 'bc51f34fb2937f45ca7b8389f1354cde00a3aaa9d823b8cad80f24fdbe7137d8', 'widgets/editor_page.py': 'cf2dbbbcbf98168561e3bf6431d7bcb3f07cc372e506320241e64051e1ab940f', 'models/module_repository.py': 'bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5', 'widgets/resolve_open_documents_dialog.py': '38657cbfaf21ab286cb58dc2cd8fac43b2b562d270629d98276274d68c17047e', 'widgets/shell_ribbon.py': 'e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1', 'services/config_service.py': '29385073d9de6708301d50bb7ba590304dbedd44c8af549c191fd83105e341a5'}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"protected out-of-scope file changed: {relative}")

if errors:
    print("Marko Plus 0.3.3 check failed:")
    for error in errors:
        print("- " + error)
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.3 Grid/mouse-navigation contract")
