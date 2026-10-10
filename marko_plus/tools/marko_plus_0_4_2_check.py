#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.4.2 Markopad editor-realignment gate."""
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


init = src("__init__.py")
constants = src("app_constants.py")
config = src("services/config_service.py")
editor = src("widgets/editor_page.py")
main = src("widgets/main_window.py")
legacy = src("legacy_ricopad.py")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

req('APP_VERSION = "0.4.2"' in init, "0.4.2 package identity missing")
req('APP_REVISION = "0.4.2"' in constants, "0.4.2 revision identity missing")
req('Current release: **0.4.2**' in readme, "README current release stale")

# Audit item 1: restore Markopad's single percentage zoom model without touching
# the inherited source-editor implementation that calls window().adjust_zoom_from_wheel().
for fragment in (
    '"markopad_zoom": 100',
    'self.config.get_int("markopad_zoom", 100, minimum=50, maximum=300)',
    'font.setPointSizeF(max(6.0, size * zoom_percent / 100.0))',
    'font.setPointSizeF(max(6.0, font.pointSizeF() * zoom_percent / 100.0))',
    'def _set_editor_zoom(self, percent: int) -> None:',
    'clamped = max(50, min(300, int(percent)))',
    'self.config.set("markopad_zoom", clamped, save=True)',
    'self.editor_manager.apply_editor_preferences()',
    'current + (10 * int(steps))',
    'self._set_editor_zoom(100)',
    'def adjust_zoom_from_wheel(self, delta: int) -> None:',
):
    req(fragment in config + editor + main, f"0.4.2 zoom contract missing: {fragment}")
req('page.editor.zoomIn(steps); page.preview.zoomIn(steps)' not in main,
    "pre-0.4.2 independent Qt zoom path survived")

# Audit item 1: Source/Preview split ratio is separate from the application sidebar splitter.
for fragment in (
    '"markopad_editor_splitter_sizes": [3, 2]',
    'self.content_splitter.splitterMoved.connect(self._remember_splitter_sizes)',
    'def _remember_splitter_sizes(self, *_args) -> None:',
    'self.config.set("markopad_editor_splitter_sizes", list(sizes), save=False)',
    'self.content_splitter.setSizes(self._last_splitter_sizes)',
):
    req(fragment in config + editor, f"0.4.2 editor-split contract missing: {fragment}")
req('self.content_splitter.setSizes([3, 2])' not in editor,
    "Split mode still hard-resets to 3:2 instead of restoring the remembered ratio")

# Audit item 1: Print/PDF resolve resources relative to the Markdown document.
req('doc.setBaseUrl(QUrl.fromLocalFile(str(page.module.path.parent) + "/"))' in main,
    "printable Markdown Base URL restoration missing")
req('from PyQt6.QtCore import QEvent, QTimer, Qt, QUrl' in main,
    "QUrl import for printable Base URL missing")

# Audit item 1: no more silent empty Paste-as-Markdown path.
req('Clipboard does not contain text that can be pasted as Markdown.' in main,
    "empty Paste-as-Markdown feedback missing")

# Audit item 4: exact narrow legacy Ricopad envelope technology is present and wired.
for fragment in (
    'PROFILE_MARKER = "<!-- ricopad: rich-markdown-v1 -->"',
    'def strip_legacy_envelope(text: str) -> tuple[str, bool]:',
):
    req(fragment in legacy, f"legacy Ricopad stripper missing: {fragment}")
req(sha("legacy_ricopad.py") == "2984a424345666509420bd8d9825394e6d8b6b70620d1eb3c50e519be71cdc40",
    "legacy Ricopad stripper is not byte-for-byte Markopad 0.1.0-r2 technology")
req('from marko_plus.legacy_ricopad import strip_legacy_envelope' in editor,
    "legacy Ricopad stripper not wired into EditorPage")
req('portable_text, legacy = strip_legacy_envelope(text)' in editor,
    "legacy Ricopad envelope not stripped during load")
req('Marko Plus will edit only the portable Markdown content.' in editor,
    "legacy Ricopad user warning missing")
req(editor.count('self.legacy_ricopad_loaded = False') >= 3,
    "legacy Ricopad state is not cleared after clean save/rebind")

# Audit item 5: only defaults change; persisted values still override ConfigService.DEFAULTS.
req('"editor_word_wrap": True' in config, "Word Wrap default is not Markopad-aligned On")
req('"editor_font_size": 11' in config, "Source font default is not Markopad-aligned 11 pt")
req('self.config.get("editor_word_wrap", True)' in editor,
    "EditorPage fallback Word Wrap default is not On")
req('self.config.get("editor_word_wrap", True)' in main,
    "MainWindow fallback Word Wrap default is not On")
req('self.config.get_int("editor_font_size", 11' in editor,
    "EditorPage fallback Source font is not 11 pt")

# Audit item 8 is explicitly excluded by user decision.
req('self.save_as_action = self._command("Save As…", self._save_current_as)' in main,
    "Save As shortcut policy changed unexpectedly")
req('self.save_new_action = self._command("Save and New", self._save_and_new, "Ctrl+Shift+S")' in main,
    "Save and New Ctrl+Shift+S policy changed unexpectedly")

# Preserve the pristine inherited Markopad cores and critical Plus lifecycle/scaffolding.
protected = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
    "controllers/editor_manager.py": "e6da8cc6fd8b6157e0e92d95d9e06f8f28b3e874b5ae96c7fa2c20a66be71fa4",
    "controllers/file_actions.py": "8c10f6551e7d75580289c7048c86ebf70006ebbb753de8cbcaec84a9da1eb241",
    "services/file_io.py": "27cbcdd099455a995a171fedd0c5553a7aa53a0de2f253404c47f3ab4fb80d38",
    "services/open_document_monitor.py": "3229ec763455d359fa9a9f3a7947e3da60357d6170c18007dc8519cbabaf02db",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "services/module_scanner.py": "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "widgets/navigation.py": "cbd24979804f1326bdc111fd8eed1d545acff8140a45b404d0ba25d7bb3ab7ef",
    "widgets/shell_ribbon.py": "dd4f555f893923a26cd5429a082bd15acba8017946302fa950cd5394f2ce95b0",
    "widgets/code_editor.py": "b0299c063a23d93bea0a9afdf4bfceb16d8843867f5382a02824cd27bbcb4831",
    "models/module_repository.py": "bd3f669104b32b089f4f7d403114ab5605f8328310aa473365129da1093705d5",
}
for relative, expected in protected.items():
    req(sha(relative) == expected, f"out-of-scope 0.4.1 production file changed: {relative}")

if errors:
    print("Marko Plus 0.4.2 check failed:")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)

print("PASS: Marko Plus 0.4.2 Markopad editor realignment repair contract")
