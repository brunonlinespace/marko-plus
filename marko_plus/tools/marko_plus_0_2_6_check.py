#!/usr/bin/env python3
# Marko Plus
# SPDX-License-Identifier: GPL-3.0-or-later
"""Static contract check for Marko Plus 0.2.6 final convergence cleanup."""
from __future__ import annotations

import hashlib
import json
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
const = src("app_constants.py")
app = src("app.py")
main = src("widgets/main_window.py")
readme = src("docs/README.md")
component = json.loads((ROOT / "suite-pythoine-component.json").read_text(encoding="utf-8"))
manifest = json.loads((PACKAGE / "marko-plus.json").read_text(encoding="utf-8"))

req('APP_VERSION = "0.2.6"' in init, "0.2.6 package identity missing")
req('APP_REVISION = "0.2.6"' in const, "0.2.6 revision identity missing")
req(component.get("version") == "0.2.6", "Suite version mismatch")
req(manifest.get("version") == "0.2.6", "manifest version mismatch")

req(
    "File > Workspace(s) > Open / Manage Workspaces to relink it." in app,
    "unavailable-Workspace warning does not match Rico Plus no-ellipsis wording",
)
req(
    "File > Workspace(s) > Open / Manage Workspaces... to relink it." not in app,
    "old unavailable-Workspace warning ellipsis remains",
)
req('(\"Dashboard\", self.dashboard_action),' in main, "shortcut catalog does not use Dashboard")
req('(\"Show Dashboard\", self.dashboard_action),' not in main, "stale Show Dashboard remains in shortcut catalog")
req("the Marko Plus GitHub repository" in main, "Quick Tour does not name Marko Plus GitHub repository")
req("the Markopad GitHub repository" not in main, "stale Markopad GitHub repository wording remains")

method = main.split("    def _open_documentation(self) -> None:", 1)[1].split("    def _shortcut_catalog", 1)[0]
req('readme = self.runtime_paths.package_root / "docs" / "README.md"' in method, "Documentation path changed")
req("if not readme.is_file():" in method, "missing Documentation existence guard")
req('"Documentation — Marko Plus"' in method, "missing Marko Plus Documentation failure title")
req("self._launch_new_window(readme)" in method, "Documentation does not use Marko Plus new-window lifecycle")
req("desktop_launcher.open_path(readme)" not in method, "Documentation still opens through desktop launcher")

for required in (
    "**Marko Plus 0.2.6**",
    "**Help → Documentation** / **F1**",
    "**Editor surface** → open the dragged file in its own Marko Plus window",
    "**Empty sidebar tree** → import to the Workspace root.",
    "**Sidebar file row** → import into that file's containing folder.",
    "**Preview Only + Locked Mode + Focused Mode**",
    "**Marko Plus GitHub repository**",
):
    req(required in readme, f"F1 README missing current contract text: {required}")
req("0.0.1-r3" not in readme, "F1 README still advertises the obsolete 0.0.1-r3 line")

# Protect the accepted 0.2.5 runtime outside the two explicitly changed runtime files.
expected = {
    "controllers/file_actions.py": "46f4a4c273461f348a0300b2cdfddf394b2145ffe34439fab23f737dd42fc3a8",
    "widgets/navigation.py": "8ae46620986882e3e9890ec57ba2b45de068cda408492244753eda064252c2c2",
    "controllers/editor_manager.py": "358c3663ecef8a762d24c4ef04f794e465c9986bb3027fe378c2e18be4d574e7",
    "widgets/editor_page.py": "20079a37e0f2c18067f2353c2aa13de92198004a895f9a55624156237a958224",
    "models/module_repository.py": "b95a8d5a788ca7add46d5bfa176c5ad4844b81be8ea210f3b1e8af0857403ffc",
    "services/filesystem_watcher.py": "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "widgets/folder_dashboard.py": "8abdceadae1159b7f9cfdc7e11299dc943793fafb4457d2796770f3c7c93dcbb",
    "widgets/shell_ribbon.py": "e46bf786306c716b90a2dd043b315f054669657309464c5e8d4b27701bfc9ad1",
}
for relative, expected_hash in expected.items():
    req(sha(relative) == expected_hash, f"protected 0.2.5 implementation changed: {relative}")

if errors:
    print("Marko Plus 0.2.6 check failed:")
    for error in errors:
        print("- " + error)
    raise SystemExit(1)
print("Marko Plus 0.2.6 final convergence cleanup check passed.")
