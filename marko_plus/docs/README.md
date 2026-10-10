# Marko Plus

**Marko Plus 0.3.1** is a workspace-scale Markdown application for Linux. It combines Markopad's source editor and preview with registered Workspaces, folder navigation, document tabs, dashboards, safe file management, and transient external-document viewing.

Marko Plus works with ordinary Markdown files. Supported Markdown filename extensions are `.md`, `.markdown`, `.mdown`, and `.mkd`.

## Workspaces

A Workspace is an ordinary folder registered with Marko Plus. Only the active Workspace is scanned and watched. Use **File → Workspace(s)** to switch between registered Workspaces. **Open / Manage Workspaces...** adds, renames, relinks, or removes Workspace registrations without moving the underlying folder.

The main Dashboard represents the Workspace root. Folder dashboards represent individual folders. The sidebar mirrors the active Workspace tree.

## Creating and opening files

Use **New Markdown File** to create a document in the current folder context. The destination is the open folder dashboard, the active managed document's containing folder, or the Workspace root when the main Dashboard is active.

Use **File → Import File into Workspace...** to copy an external Markdown file into the Workspace root. Imported files remain managed Workspace documents.

Use **File → Open External File...** to inspect a Markdown file without importing it. External documents open in their own Marko Plus window using the established verification presentation: **Preview Only + Locked Mode + Focused Mode**. They are not added to the Workspace tree, Dashboard, counts, or last-opened Workspace state.

**Help → Documentation** / **F1** opens this bundled README through that same external-document lifecycle, so the Plus-family external-file capability is visible without altering your Workspace.

## Drag and drop

Marko Plus distinguishes between **workspace/navigation targets** and the **editor surface**.

External Markdown files dragged from the file manager behave as follows:

- **Editor surface** → open the dragged file in its own Marko Plus window through the external-file lifecycle; do not import it.
- **Dashboard button** → import to the Workspace root.
- **Main Dashboard** → import to the Workspace root.
- **Empty sidebar tree** → import to the Workspace root.
- **Sidebar folder row** → import into that folder.
- **Sidebar file row** → import into that file's containing folder.
- **Folder Dashboard** → import into that folder.
- **Unrelated application/sidebar chrome** → reject the drop rather than infer a destination.

Managed files already inside the Workspace can also be reorganized by mouse drag:

- **folder row** → move into that folder;
- **file row** → move into that file's containing folder;
- **empty sidebar tree** → move to the Workspace root;
- **Dashboard button** → move to the Workspace root.

Same-folder moves are ignored.

## Editing and preview

Marko Plus retains Markopad's three document layouts:

- **Source Only**
- **Source + Preview**
- **Preview Only**

The Home and Insert command surfaces provide Markdown formatting, headings, lists, links, images, tables, code, horizontal rules, date/time insertion, and symbols. Source and preview fonts are configurable independently.

**Ctrl+F** opens the bottom Find/Replace panel and focuses Find in editor context; **Ctrl+H** opens the same panel and focuses Replace; **Esc** closes it. On the main Dashboard or a Folder Dashboard, Ctrl+F focuses the relevant search box instead.

## Document tabs and navigation

Document Tabs can be enabled or disabled. When enabled, open documents remain available as tabs and Dashboard/folder navigation can occupy a temporary context tab.

Useful navigation commands include:

- **Ctrl+T** — open the current navigation context as a tab.
- **Ctrl+W** — close the active document contextually or return to Dashboard.
- **Ctrl+Tab / Ctrl+Shift+Tab** — cycle document/navigation tabs when Document Tabs are enabled; otherwise cycle command-bar pages.
- **Ctrl+Up / Ctrl+Down** — previous / next Markdown file.
- **Ctrl+Shift+F5** — Refresh Workspace.

## Locked Mode and Focused Mode

**Locked Mode** (`F12`) is an application-wide persisted protection state. It prevents document mutation while preserving navigation, selection, copying, and search.

**Focused Mode** (`F10`) is temporary. It hides surrounding interface elements and collapses the command surface while remembering their previous states. Leaving Focused Mode restores those states.

## Saving and file safety

Marko Plus writes directly to ordinary Markdown files and includes the shared Plus-family safeguards around save, duplicate, rename, delete, external-editor launch, and external-change conflicts.

When an open file changes on disk, Marko Plus verifies the actual content before presenting a conflict. The available resolution paths include reloading from disk, saving a version elsewhere, or an explicit overwrite where appropriate.

**Duplicate File...** distinguishes between the current in-memory document and the last saved version when unsaved edits exist. Both choices use the common new-document staging and exclusive no-clobber destination installer.

## Appearance

Application theme and editor canvas are independent. **App Theme** controls the Marko Plus shell; **Dark Editor** controls the source/preview canvas. File Header, Sidebar, Status, document tabs, and command-surface collapse are independently controllable.

## Help

The Help menu provides:

- **Documentation** (`F1`)
- **Quick Tour**
- **Keyboard Shortcuts**
- **Marko Plus GitHub repository**
- issue reporting
- **About Marko Plus**

The Keyboard Shortcuts dialog is the authoritative live shortcut inventory for the current build.

## Running from source

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

Starting Marko Plus without an explicit file opens according to the configured App Launch Screen for the active Workspace.

## Configuration and diagnostics

Marko Plus stores application configuration outside document Workspaces using its per-user application identity. Optional shutdown timing can be enabled with:

```bash
MARKO_PLUS_PROFILE_SHUTDOWN=1 python main.py
```

## Packaging

Fedora/AppImage packaging helpers remain included with the source. Packaging-specific maintenance is documented separately under `packaging/` and `BUILDING.md`.

## License and links

Marko Plus is licensed under **GPL-3.0-or-later**. See `LICENSE`.

- Marko Plus: https://github.com/brunonlinespace/marko-plus
- Issues: https://github.com/brunonlinespace/marko-plus/issues
- Publisher: https://github.com/brunonlinespace/
