# Marko Plus Architecture

## Startup

1. `main.py` delegates to the dependency-free application entry point.
2. `RuntimePaths` resolves source, frozen, or AppImage locations.
3. `ConfigService` safely loads user settings.
4. `ProjectRegistry` resolves the active registered Workspace.
5. `MainWindow` creates the persistent shell and paints immediately.
6. `FilesystemWatcher` runs one cancellable `ModuleScanner` traversal.
7. The resulting snapshot updates documents, folders, and watched paths.

## Data and state

- `Module` stores metadata and editor state for one Markdown document.
- `ModuleRepository` owns canonical document objects and emits incremental
  add/remove/change/path signals.
- `ModuleStateStore` keeps lazy Qt widgets outside the pure data model.
- `ProjectRegistry` stores Workspace folder records and small per-Workspace UI
  state. Inactive Workspaces are not scanned.

`Module` is the inherited generic class name; it does not imply executable or
language-runtime behavior.

## Services

- `RuntimePaths`: resources, configuration, and writable Workspace defaults.
- `ConfigService`: bounded JSON reading and atomic replacement.
- `ModuleScanner`: iterative Markdown discovery with ignore rules and
  cancellation.
- `FilesystemWatcher`: threaded scans, change debouncing, and safe shutdown.
- `DesktopLauncher`: sanitized host opening for files, folders, editors, and
  web links.
- `file_io`: stable identity checks, bounded reads, race detection, and atomic
  save helpers.

Marko Plus has no interpreter, script runner, terminal-session supervisor, or
executable-permission subsystem.

## Controllers and widgets

- `EditorManager` owns the workspace Dashboard, folder dashboards, and lazy
  editor pages.
- `MainWindow` owns application QActions; `ShellRibbon` owns their persistent
  Marko command-tab/toolbar presentation, collapse lifecycle, and command-tab
  cycling. The 0.0.9 Marko presentation remains authoritative.
- `MainWindow` also owns the temporary **Focused Mode** state snapshot. Focused
  Mode hides surrounding shell surfaces and collapses `ShellRibbon` through its
  shared non-persisting API, then restores the captured state exactly.
- `FileActionsController` owns safe document/folder mutation and import
  conflict handling.
- `NavigationWidget` owns the Dashboard destination and recursive folder tree.
- `DashboardWidget` keeps separate persistent List and Grid card sets.
- `EditorPage` owns source/preview layout, search, preferences, safe load/save,
  and external-change handling.
- `CodeEditor` is the thin adapter around the protected Markopad source editor.
- `MarkdownPreview` is the protected Markopad preview engine.

## Protected engine boundary

The embedded `markopad_source_editor.py` and `markopad_preview.py` remain
canonical Markopad engines. Marko Plus-specific compatibility belongs in the
adapter or editor page, not in those files.

## Shutdown contract

1. Resolve unsaved documents.
2. Save window and active-Workspace state.
3. Display closing feedback.
4. Cancel and join an active scan.
5. Exit only after those prerequisites complete.
