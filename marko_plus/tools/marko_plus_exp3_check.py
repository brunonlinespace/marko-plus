#!/usr/bin/env python3
"""Static checks for the surgical Marko Plus exp3 project switcher."""

from __future__ import annotations

import ast
import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "marko_plus"
PROTECTED_ENGINE_FILES = {
    "widgets/markopad_source_editor.py": "dcfe40ef1149945427fda6555f7a6e5eadf6aca8ce01c2cc3a6cb726fcb33830",
    "widgets/markopad_preview.py": "e9fa111f4119402e7f4396c9b39d5ec5fdf19627e45e907be036cbd555bb8965",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    app = (PACKAGE / "app.py").read_text(encoding="utf-8")
    registry = (PACKAGE / "services/project_registry.py").read_text(encoding="utf-8")
    window = (PACKAGE / "widgets/main_window.py").read_text(encoding="utf-8")
    projects = (PACKAGE / "widgets/projects_dialog.py").read_text(encoding="utf-8")
    editor_manager = (PACKAGE / "controllers/editor_manager.py").read_text(encoding="utf-8")
    file_actions = (PACKAGE / "controllers/file_actions.py").read_text(encoding="utf-8")
    navigation = (PACKAGE / "widgets/navigation.py").read_text(encoding="utf-8")

    for relative, expected in PROTECTED_ENGINE_FILES.items():
        require(
            sha256(PACKAGE / relative) == expected,
            f"Protected Markopad engine changed: {relative}",
            errors,
        )

    require("class ProjectRegistry" in registry, "project registry service missing", errors)
    require('"projects"' in registry and '"active_project_id"' in registry, "registry persistence fields missing", errors)
    require("PROJECT_STATE_KEYS" in registry and "dashboard_search" in registry, "per-project Dashboard state missing", errors)
    for forbidden in ("ModuleScanner", "FilesystemWatcher", ".rglob(", "os.walk("):
        require(forbidden not in registry and forbidden not in projects,
                f"Inactive-project surface performs filesystem discovery: {forbidden}", errors)

    require("ProjectRegistry(config, requested_workspace)" in app, "registry is not created at startup", errors)
    require("project_registry.active_project" in app, "startup does not resolve the active project", errors)
    require("Workspace Folder Unavailable" in app and "relink it" in app, "missing-folder recovery is absent", errors)

    require('self.manage_workspaces_action = self._command("Manage Workspaces…"' in window,
            "Manage Workspaces command missing", errors)
    file_page = next((line for line in window.splitlines() if line.strip().startswith('"File":')), "")
    require("new_action" in file_page and "manage_workspaces_action" in file_page,
            "Manage Workspaces is not on the File tab", errors)
    view_page = next((line for line in window.splitlines() if line.strip().startswith('"View":')), "")
    require("manage_workspaces_action" not in view_page, "Manage Workspaces leaked into the View tab", errors)
    require("def _switch_project" in window and "def _install_watcher" in window,
            "project-switch lifecycle is incomplete", errors)
    switch_body = window[window.find("    def _switch_project"):window.find("    def _selected_folder")]
    require(
        switch_body.find("can_close_application") < switch_body.find("self.watcher.stop")
        < switch_body.find("self.repository.clear()") < switch_body.find("set_active"),
        "project switch does not follow prompt/stop/reset/activate order",
        errors,
    )
    require("_save_active_project_state(save=True)" in window,
            "active project state is not persisted", errors)

    require(not (PACKAGE / "widgets/preferences_dialog.py").exists(),
            "Preferences dialog still exists", errors)
    require("PreferencesDialog" not in window and "preferences_action" not in window,
            "Preferences dialog still has a MainWindow entry point", errors)
    require("Add Existing Folder…" in projects and "Relink Folder…" in projects,
            "project registration controls are incomplete", errors)
    require("will not be deleted" in projects,
            "project removal does not promise file preservation", errors)
    for forbidden_label in (
        "Change Project", "Open Project", "Project Folder", "Project Name",
        "Project label", "Project Registration", "another project",
    ):
        require(forbidden_label not in projects and forbidden_label not in window,
                f"Visible Project terminology remains: {forbidden_label}", errors)

    require("def switch_workspace_root" in editor_manager,
            "editor manager cannot reset its project root", errors)
    require("def switch_workspace_root" in file_actions,
            "file actions cannot rebind to the active project", errors)
    require("def switch_workspace_root" in navigation,
            "folder navigation cannot reset its project root", errors)

    for source in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in source.parts:
            continue
        try:
            ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (SyntaxError, UnicodeDecodeError) as exc:
            errors.append(f"Could not parse {source.relative_to(ROOT)}: {exc}")

    behavior = subprocess.run(
        [sys.executable, str(PACKAGE / "tools/project_registry_check.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        behavior.returncode == 0,
        "Project registry behavior check failed: " + (behavior.stderr.strip() or behavior.stdout.strip()),
        errors,
    )

    if errors:
        print("Marko Plus exp3 checks FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Marko Plus exp3 checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
