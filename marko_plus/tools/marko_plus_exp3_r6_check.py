#!/usr/bin/env python3
"""Static checks for the focused Marko Plus exp3-r6 revision."""

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


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def require_in_order(source: str, fragments: tuple[str, ...], message: str, errors: list[str]) -> None:
    cursor = -1
    for fragment in fragments:
        cursor = source.find(fragment, cursor + 1)
        if cursor < 0:
            errors.append(f"{message}: {fragment}")
            return


def main() -> int:
    errors: list[str] = []
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    config = (PACKAGE / "services/config_service.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    app = (PACKAGE / "app.py").read_text(encoding="utf-8")
    folder = (PACKAGE / "widgets/folder_dashboard.py").read_text(encoding="utf-8")
    navigation = (PACKAGE / "widgets/navigation.py").read_text(encoding="utf-8")
    editor_page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINES.items():
        actual = hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()
        require(actual == expected, f"Protected Markopad engine changed: {relative}", errors)

    require(
        'APP_REVISION = "exp3-r6"' in constants
        or 'APP_REVISION = "exp3-r7"' in constants
        or 'APP_REVISION = "exp3-r8"' in constants
        or 'APP_REVISION = "exp3-r9"' in constants
        or 'APP_REVISION = "exp3-r10"' in constants
        or 'APP_REVISION = "exp3-r11"' in constants
        or 'APP_REVISION = "0.0.1"' in constants
        or 'APP_REVISION = "0.0.1-r3"' in constants,
        "Current source revision no longer carries the r6 work",
        errors,
    )
    for fragment in (
        '"drop_open_mode": "active_window"',
        '"quick_tour_seen": False',
    ):
        require(fragment in config, f"Configuration default missing: {fragment}", errors)

    for fragment in (
        'self.rename_file_action = self._command("Rename…", self._rename_current, "F2")',
        '"Ctrl+Alt+Shift+D"',
        'self.sidebar_action = self._command("Show Sidebar", self._toggle_sidebar, "F9"',
        '"Opens on Active Window"',
        '"Opens on New Window"',
        'def _effective_drop_open_mode',
        'Qt.KeyboardModifier.ShiftModifier',
        'self.editor_manager.editor_files_dropped.connect(self._handle_app_drop)',
        'self.file_actions.module_imported.connect(self._capture_imported_drop_path)',
        'def _open_path_in_new_window',
        '"--open-file"',
        'def _show_quick_tour',
        'wizard = QWizard(self)',
        'wizard.setWizardStyle(QWizard.WizardStyle.ModernStyle)',
        'shortcuts_button = QPushButton("Open Keyboard Shortcuts…", wizard)',
    ):
        require(fragment in window, f"r6 MainWindow behavior missing: {fragment}", errors)

    require_in_order(
        window,
        (
            'view.addAction(self.fullscreen_action)',
            'view.addAction(self.view_only_action)',
            'view.addAction(self.sidebar_action)',
            'view.addAction(self.status_bar_action)',
            'view.addAction(self.word_wrap_action)',
            'view.addAction(self.line_numbers_action)',
            'view.addAction(self.editor_canvas_theme_action)',
            'zoom = view.addMenu("Editor Zoom")',
            'layout_menu = view.addMenu("Editor Layout")',
            'more_settings = view.addMenu("Editor Miscellaneous")',
        ),
        "View menu order is incomplete",
        errors,
    )

    for fragment in (
        'module = self._current_module()',
        'return module.path.parent',
        'relative_path not in {"", ".", self.folder.name}',
        'def queue_open_path',
    ):
        source = folder if fragment.startswith("relative_path") else window
        require(fragment in source, f"Context/path behavior missing: {fragment}", errors)

    for fragment in (
        'supplied_open_path = sys.argv[open_index + 1]',
        'requested_path.relative_to(library_root)',
        'window.queue_open_path(requested_path)',
        'config.set("quick_tour_seen", True, save=True)',
        'QTimer.singleShot(0, window._show_quick_tour)',
    ):
        require(fragment in app, f"Startup behavior missing: {fragment}", errors)

    require("def startDrag" in navigation and "drag.exec" in navigation,
            "Sidebar external-drag visual repair is missing", errors)
    for fragment in (
        "if current.digest != expected.digest:",
        "expected = current",
        '"File Removed Externally"',
    ):
        require(fragment in editor_page, f"Safe-save repair missing: {fragment}", errors)

    for source in (
        PACKAGE / "app_constants.py",
        PACKAGE / "services/config_service.py",
        PACKAGE / "widgets/main_window.py",
        PACKAGE / "widgets/folder_dashboard.py",
        PACKAGE / "app.py",
    ):
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    if errors:
        print("Marko Plus exp3-r6 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3-r6 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
