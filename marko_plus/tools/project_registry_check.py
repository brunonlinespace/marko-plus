#!/usr/bin/env python3
"""Dependency-free behavior checks for the exp3 project registry."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from marko_plus.services.config_service import ConfigService
from marko_plus.services.project_registry import ProjectRegistry


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="marko-plus-projects-") as raw_root:
        root = Path(raw_root)
        first_folder = root / "Project One"
        second_folder = root / "Project Two"
        moved_folder = root / "Project Two Moved"
        first_folder.mkdir()
        second_folder.mkdir()
        moved_folder.mkdir()

        config = ConfigService(root / "config" / "marko_plus_config.json")
        config.update(
            {
                "workspace_path": str(first_folder),
                "dashboard_sort": "title_az",
                "dashboard_search": "notes",
                "dashboard_view": "grid",
                "collapsed_folders": [str(first_folder / "archive")],
            },
            save=True,
        )

        registry = ProjectRegistry(config, first_folder)
        require(len(registry.projects) == 1, "legacy workspace was not migrated once")
        require(registry.active_project.folder == first_folder.resolve(), "legacy workspace is not active")
        require(registry.active_project.state.get("dashboard_view") == "grid", "legacy project UI state was lost")

        second = registry.add_folder(second_folder, "Research")
        require(len(registry.projects) == 2, "second project was not registered")
        require(registry.add_folder(second_folder).project_id == second.project_id, "duplicate folder was registered")
        require(registry.set_active(second.project_id), "second project could not become active")
        require(
            registry.update_state(
                second.project_id,
                {"dashboard_search": "journal", "unknown": "discarded"},
                save=True,
            ),
            "per-project state was not updated",
        )
        require(not registry.remove(second.project_id), "active project registration was removed")

        first = registry.find_folder(first_folder)
        require(first is not None, "first project disappeared")
        require(registry.relink(first.project_id, moved_folder), "inactive project could not be relinked")
        require(not registry.relink(first.project_id, second_folder), "duplicate project folder was accepted")

        reloaded = ProjectRegistry(ConfigService(config.path), first_folder)
        require(reloaded.active_project.project_id == second.project_id, "active project was not persisted")
        require(reloaded.active_project.state.get("dashboard_search") == "journal", "active state was not persisted")
        require(len(reloaded.projects) == 2, "project registry did not reload cleanly")
        require(reloaded.remove(first.project_id), "inactive project registration was not removable")
        require(moved_folder.is_dir(), "removing a registration touched the project folder")

    print("Project registry checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
