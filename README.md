<p align="center">
  <a href="https://github.com/brunonlinespace/marko-plus">
    <img
      src="marko_plus/assets/icons/markopad-about.png"
      alt="Marko Plus"
      width="256"
    >
  </a>
</p>

# MawnFolio

**Friendly. Fast. Focused.**

Marko Plus is a workspace-scale Markdown editor built around Markopad's source editor and preview engine. It adds managed workspaces, folder navigation, dashboards, persistent application settings, and the shared Plus-family document lifecycle while continuing to read and write ordinary Markdown files.

Current release: **0.4.17**

0.4.17 is a single-purpose corrective release: Edit → Toggle Comment now visibly carries its Ctrl+/ keybind through the live QAction, matching Markopad, with no other command or editor behavior change.

Repository: <https://github.com/brunonlinespace/marko-plus>

## What Marko Plus is

Marko Plus is designed for people who want Markopad's source-and-preview editing inside a larger, persistent workspace. A workspace is an ordinary folder containing Markdown documents and subfolders; Marko Plus does not introduce a private document format or require documents to be stored in a database.

Only the active workspace is scanned and watched. Files opened from outside that workspace can be viewed as transient external sessions without being copied into workspace navigation.

Supported Markdown filename extensions are `.md`, `.markdown`, `.mdown`, and `.mkd`.

## Highlights

- Native **Markdown source editing and preview** powered by the Markopad editor/preview pair.
- Registered **Workspaces** with fast switching and recursive folder navigation.
- **My Workspace** sidebar with native folder/file distinction, expandable folders, Dashboard access, and adjacent-file navigation.
- Workspace and folder **Dashboards** with List and Grid views.
- Full-width **Ribbon** with File, Home, Insert, View/Configure, and Help-oriented command surfaces.
- Persistent **Tabs Enabled / Tabs Disabled** behavior with genuine document-lifecycle semantics.
- Shared multi-document resolution when disabling tabs or exiting with several at-risk documents.
- Persistent **Locked Mode** and temporary **Focused Mode**.
- Persistent **File Header**, Sidebar, Status, and Dashboard view settings, including **Left Sidebar / Right Sidebar** positioning.
- **Import File into Workspace...** and **Open External File...** as separate workflows.
- Safe create, rename, duplicate, move, import, delete, and Save As operations.
- Atomic Markdown saving, external-change detection, and protection when an open backing file is deleted or renamed away.
- System, Dark, and Light application themes with independent editor-canvas control.
- Markopad-style bottom Find / Replace panel with bounded Plus-family search safety, searchable Keyboard Shortcuts, Quick Tour, and bundled documentation.
- Complete **0.4.1 command-icon family reset** with distinct 64×64 light/dark assets rendered at the established **36×36** Ribbon size.

## Interface

### Ribbon

The Ribbon is the primary command surface and remains above the workspace sidebar and content area.

- **File** — create, save, print, export, workspace/session, import, and external-file actions.
- **Home** — clipboard, headings, Markdown formatting, lists, and editing commands.
- **Insert** — links, images, tables, code, horizontal rules, symbols, dates, and times.
- **Configure / View** — layout, editor, theme, Dashboard, launch, and tab behavior.
- **Help** — documentation, Quick Tour, shortcuts, GitHub, issues, and About.

Hover over a Ribbon command to see its name and keyboard shortcut. When Document Tabs are disabled, **Ctrl+Tab** and **Ctrl+Shift+Tab** cycle Ribbon pages; when tabs are enabled, those shortcuts navigate document/context tabs.

### AppMenu

The native application menu is organised around the same Marko Plus command vocabulary used by the Ribbon.

The Keyboard Shortcuts dialog uses the live application actions, so newly assigned shortcuts remain visible there.

## Workspaces

Marko Plus keeps workspace registration separate from the files themselves.

- **Open / Manage Workspaces...** registers, relabels, relinks, or removes workspace registrations.
- Removing a registration does **not** delete its folder or documents.
- Only the active workspace is scanned and watched.
- **Refresh Workspace** rescans the active workspace.
- The sidebar is ordered around **My Workspace**, Dashboard, tree controls, the navigation tree, and Refresh Workspace at the bottom.
- Folders retain native tree icons while file rows remain text-only, preserving the same navigation and drag/drop behavior.
- **F2** renames the active file or selected workspace subfolder according to context.

### Import and external files

Marko Plus deliberately distinguishes the two operations:

- **Import File into Workspace...** copies a supported external Markdown file into the active workspace root.
- **Open External File...** opens a supported Markdown file through the existing transient external-file lifecycle without importing it.

These commands now have dedicated shortcuts:

- `Ctrl+Alt+Shift+I` — Import File into Workspace...
- `Ctrl+Alt+Shift+O` — Open External File...

### Drag and drop

External Markdown files dropped onto workspace/navigation targets are imported into the applicable workspace folder. Managed documents dragged onto workspace folders are moved through Marko Plus's existing safe file operations.

Dropping a supported external Markdown file onto the editor surface retains Marko Plus's established external-file opening behavior rather than silently importing it.

## Editing

Marko Plus retains Markopad's three document layouts:

- **Source Only**
- **Source + Preview**
- **Preview Only**

The editing surfaces provide Markdown headings, emphasis, lists, links, images, tables, code, horizontal rules, date/time insertion, symbols, Find/Replace, Go To Line, source line numbers, and independent source/preview font settings.

New workspace documents are ordinary Markdown files. The user-facing creation command is simply **New File**.

## Document tabs

Marko Plus keeps the established user-facing setting names:

- **Tabs Enabled** — multiple documents may remain open at once.
- **Tabs Disabled** — only the active document remains open; navigating elsewhere safely closes it first.

When Tabs Enabled is switched off, the current context remains the anchor. Clean background documents close automatically, while dirty or otherwise at-risk documents are resolved before the change completes.

The same multi-document resolution path is used when exiting with several documents requiring attention.

## File safety and external changes

Marko Plus treats file safety as part of the normal document lifecycle.

Ordinary saves use guarded replacement semantics. Before replacing an existing file, Marko Plus detects whether its disk content changed externally and offers safe resolution paths rather than silently overwriting another program's changes.

Open documents also survive an externally driven delete or rename-away of their backing path. A missing-backed document remains open and protected: Reload is unavailable while no disk copy exists, Save Version As remains available, and recreating the original path requires an explicit action.

Tabs Disabled does not keep hidden editors alive, so this protection applies only to documents that are genuinely open.

## Locked Mode

**Locked Mode** (`F12`) is a persistent protection state. It prevents document mutation while preserving navigation, search, selection, and copying.

The active window title identifies Locked Mode when applicable.

## Focused Mode

**Focused Mode** (`F10`) temporarily hides surrounding application chrome and collapses the Ribbon. Leaving Focused Mode restores the independent visibility state that existed before it was entered.

Focused Mode does not overwrite the user's normal layout preferences.

## Appearance

Choose **System**, **Dark**, or **Light** for the application shell. The editor canvas can be controlled independently through **Dark Editor**.

Marko Plus uses its packaged light/dark command-icon family throughout the Ribbon and Dashboard. The Dashboard reuses the existing artwork for **New File**, **New Folder**, and the dynamic **Grid View / List View** toggle.

## Useful keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+N` | New File |
| `Ctrl+Shift+N` | New Folder |
| `Ctrl+Alt+Shift+N` | New Window |
| `Ctrl+O` | Open / Manage Workspaces |
| `Ctrl+Alt+Shift+I` | Import File into Workspace |
| `Ctrl+Alt+Shift+O` | Open External File |
| `Ctrl+Shift+F5` | Refresh Workspace |
| `Ctrl+S` | Save |
| `Ctrl+Shift+S` | Save and New |
| `Ctrl+W` | Close Tab / Dashboard |
| `Ctrl+Shift+W` | Save and Dashboard |
| `Ctrl+Shift+Q` | Save and Exit |
| `Ctrl+Up` / `Ctrl+Down` | Previous / Next File |
| `F2` | Rename File or Folder |
| `Ctrl+F` | Find; press again while Find has focus to close |
| `Ctrl+H` | Find and Replace; press again while Replace has focus to close |
| `F3` / `Shift+F3` | Next / Previous Find result |
| `Esc` | Close Find/Replace panel |
| `Ctrl+G` | Go To Line |
| `F4` | Properties |
| `F9` | Show / Hide Sidebar |
| `Shift+F9` | Toggle Sidebar Position |
| `F10` | Focused Mode |
| `F11` | Full Screen |
| `F12` | Locked Mode |
| `Ctrl+Alt+Shift+D` | Toggle List / Grid View |
| `Ctrl+Alt+Shift+E` | Dark Editor |
| `Ctrl+Alt+Shift+F` | File Header |
| `Ctrl+Alt+Shift+S` | Show / Hide Status |
| `Ctrl+Shift+/` | Keyboard Shortcuts |

The complete live shortcut inventory is available from **Help → Keyboard Shortcuts**.

## Running from source

Marko Plus requires Python 3 and PyQt6 within the supported PyQt6 6.x series.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r marko_plus/requirements.txt
python main.py
```

Other useful launch forms:

```bash
python main.py --version
python main.py --setup
python main.py document.md
python main.py --open-file document.md
```

Starting Marko Plus without an explicit file opens according to the configured launch behavior for the active workspace.

## Building the AppImage

Fedora build helpers are included in the source tree:

```bash
./marko_plus/packaging/fedora/install-build-deps.sh
./marko_plus/packaging/fedora/build-appimage.sh
```

Expected outputs include:

```text
marko_plus/dist/Marko-Plus-0.4.17-x86_64.AppImage
marko_plus/dist/Marko-Plus-0.4.17-x86_64.AppImage.sha256
marko_plus/dist/Marko-Plus-0.4.17-x86_64.build-info.txt
marko_plus/dist/Marko-Plus-0.4.17-x86_64.build-python-lock.txt
```

Run the AppImage builder as the normal desktop user. The dependency helper may invoke `sudo dnf`; the builder itself should not normally be run with `sudo`.

## Validation

Run the authoritative source-release gate with:

```bash
python -m marko_plus.tools.release_check
```

The release checks cover application identity, source architecture, bundled assets, file-safety contracts, Markdown behavior, packaging metadata, and source-manifest integrity. PyQt6 runtime behavior can additionally be exercised on a host with PyQt6 installed.

## Configuration

Marko Plus stores application configuration outside document workspaces using its per-user application identity. Documents remain ordinary Markdown files and are not embedded into the configuration.

## Scope

Marko Plus is a **Markdown workspace editor**. It deliberately keeps ordinary files on disk and uses workspaces as navigation/management boundaries rather than inventing a private project or document format.

## License

Marko Plus is licensed under the **GNU General Public License v3.0 or later**.

See `marko_plus/LICENSE` for the complete license text.

## Links

- Marko Plus: <https://github.com/brunonlinespace/marko-plus>
- Issues: <https://github.com/brunonlinespace/marko-plus/issues>
- GitHub profile: <https://github.com/brunonlinespace/>

Copyright © 2026 Bruno Machado.
