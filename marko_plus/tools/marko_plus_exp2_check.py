#!/usr/bin/env python3
"""Static release checks for the Marko Plus exp2 integration surface."""
from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"
EXPECTED_SOURCE = "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830"
EXPECTED_PREVIEW = "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965"
EXPECTED_MARKO_PLUS_ICONS = {
    "markopad.png": "22a09047102f543744843917d42c76be48cee58b360afb91b6acd2779e9dfd3c",
    "markopad-about.png": "4f0258c22404c8016c93f0a57a606be0bd7ef540a4cd4a5ee49b1e2fa7a652e9",
    "markopad-master.png": "9dd0597828ccd04a0ebd2db1ce39dfda9636a114042a4f37add1b9aa2e2b1870",
    "markopad.ico": "de50fb7b2064cd36b0083bab12a03e7df67fa1fc0284c42f9847bef71fe4ee6e",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []

    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    constants = (PACKAGE / "app_constants.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    page = (PACKAGE / "widgets/editor_page.py").read_text(encoding="utf-8")
    card = (PACKAGE / "widgets/dashboard_card.py").read_text(encoding="utf-8")
    manager = (PACKAGE / "controllers/editor_manager.py").read_text(encoding="utf-8")
    actions = (PACKAGE / "controllers/file_actions.py").read_text(encoding="utf-8")
    navigation = (PACKAGE / "widgets/navigation.py").read_text(encoding="utf-8")
    theme = (PACKAGE / "widgets/markopad_theme.py").read_text(encoding="utf-8")

    require('APP_NAME = "Marko Plus"' in init, "Marko Plus package identity missing", errors)
    require(PACKAGE.is_dir(), "Marko Plus source package is missing", errors)
    for extension in (".md", ".markdown", ".mdown", ".mkd"):
        require(extension in constants, f"Markdown extension missing: {extension}", errors)

    require(sha256(PACKAGE / "widgets/markopad_source_editor.py") == EXPECTED_SOURCE,
            "Embedded Markopad r8.2 source editor differs from canonical source", errors)
    require(sha256(PACKAGE / "widgets/markopad_preview.py") == EXPECTED_PREVIEW,
            "Embedded Markopad r8.2 preview differs from canonical source", errors)
    for filename, expected in EXPECTED_MARKO_PLUS_ICONS.items():
        require(sha256(PACKAGE / "assets/icons" / filename) == expected,
                f"Official Marko Plus logo asset differs: {filename}", errors)

    for page_name in ("File", "Home", "Insert", "View", "Help"):
        require(f'addTab' in window and page_name in window,
                f"Tabbed command page missing: {page_name}", errors)
    require('addMenu("&Run")' not in window and "addMenu('&Run')" not in window,
            "Legacy Run menu is still visible", errors)
    require('addMenu("&Markdown")' in window or "addMenu('&Markdown')" in window,
            "Markdown menu missing", errors)
    require('addMenu("&Insert")' in window or "addMenu('&Insert')" in window,
            "Insert menu missing", errors)

    require("QSplitter(Qt.Orientation.Horizontal" in page,
            "Source/preview split view host missing", errors)
    require("MarkdownPreview" in page, "Markopad preview is not hosted by EditorPage", errors)
    require('set_view_mode' in page, "Document view-mode controller missing", errors)
    require("QTextCursor.MoveOperation.Start" in page and "verticalScrollBar().minimum()" in page,
            "Newly loaded source does not start at the top", errors)
    require('page.set_view_mode(mode, persist=False)' in manager and
            'page.refresh_preview_now(force=True)' in manager,
            "Tree navigation does not keep Preview Only current across files", errors)
    require("module_created.emit(destination)" in actions and
            "_open_created_module_if_ready" in window,
            "Newly created Markdown files are not opened automatically", errors)
    require("def navigate_adjacent_module" in navigation and
            '"Ctrl+Up"' in window and '"Ctrl+Down"' in window,
            "Folder-tree previous/next file shortcuts are missing", errors)
    require('self.save_dashboard_action = self._command("Save and Dashboard", self._save_and_dashboard, "Ctrl+Shift+W")' in window and
            'self.save_exit_action = self._command("Save and Exit", self._save_and_exit, "Ctrl+Shift+Q")' in window,
            "Requested save/dashboard and save/exit shortcuts are missing", errors)

    edit_at = card.find('self._button("Edit"')
    split_at = card.find('self._button("Split View"')
    preview_at = card.find('self._button("Preview"')
    require(-1 not in (edit_at, split_at, preview_at) and edit_at < split_at < preview_at,
            "Dashboard buttons are not Edit | Split View | Preview", errors)
    require("mouseDoubleClickEvent" in card and "self.open_requested.emit(self.module)" in card,
            "Dashboard double-click Edit behavior missing", errors)
    require("selected_requested" in card, "Dashboard single-click selection behavior missing", errors)

    for color in ("#202326", "#151719", "#158B86", "#F5F6F7", "#0B8781"):
        require(color in theme, f"Canonical Markopad palette value missing: {color}", errors)

    # Parse every source file without importing PyQt6.
    for path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"Could not parse {path.relative_to(ROOT)}: {exc}")

    version = subprocess.run(
        [sys.executable, str(ROOT / "main.py"), "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(version.returncode == 0 and version.stdout.strip() == "Marko Plus 0.0.1-r3",
            f"Unexpected --version result: {version.stdout.strip()!r}", errors)

    if errors:
        print("Marko Plus exp2 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp2 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
