# Contributing to Marko Plus

Read `PROJECT_MEMORY.md`, `ARCHITECTURE.md`, and `ROADMAP.md` before changing
code. Several choices protect large-Workspace performance and file safety.

## Workflow

1. Keep each change focused and explain the user-visible outcome.
2. Preserve the protected Markopad engine files unless an explicitly named
   experimental engine revision authorizes otherwise.
3. Run the release check and applicable focused checks.
4. Perform the manual sequences in `QA.md`.
5. Record intentional deferrals and compatibility migrations.

## Principles

- Keep data models independent from widgets where practical.
- Route host files, folders, editors, and URLs through `DesktopLauncher`.
- Never block startup with a Workspace traversal or destroy a running QThread.
- Preserve canonical Module and ModuleState objects during path changes.
- Treat user files and unsaved content conservatively.
- Keep inactive Workspaces unscanned.
- Avoid desktop-environment-specific runtime dependencies.

Generated virtual environments, user Workspaces, AppImages, build output,
caches, timing logs, and local configuration do not belong in source archives.

Contributions are GPL-3.0-or-later.
