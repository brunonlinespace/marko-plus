# Marko Plus — Project Memory

## Identity

- Name and version: **Marko Plus 0.0.1-r3**
- Toolkit: PyQt6
- Formats: `.md`, `.markdown`, `.mdown`, `.mkd`
- License: GPL-3.0-or-later
- Repository/help links: https://github.com/brunonlinespace/marko-plus

The title bar follows the Plus-family document-state model: Dashboard/folder context shows `Workspace — Marko Plus`; an active document shows `filename — Workspace — Marko Plus`, prefixed with `*` when dirty and suffixed with ` — Locked Mode` when the active editor is locked.

## Product boundary

Marko Plus is a workspace-scale Markopad. It edits, previews, discovers, and
organizes Markdown documents. It is not a Python runner or general-purpose IDE.

## Invariants

- Preserve the protected Markopad source and preview engines byte-for-byte.
- Put Plus-specific behavior in adapters/controllers around those engines.
- Keep only the active Workspace scanned and represented in memory.
- Preserve persistent List/Grid cards and incremental repository signals for
  large-Workspace performance.
- Keep file identity checks, bounded reads, atomic writes, and conservative
  unsaved/external-change decisions.
- Internal mouse drag-and-drop moves; external mouse drag-and-drop copies/imports and never auto-opens the imported document.
- Main Dashboard touch movement is kinetic scrolling only; it never initiates document QDrag.
- Never rebuild established UI or invent commands while making a focused fix.

## Current architecture

```text
main.py
  └─ RuntimePaths / ConfigService / ProjectRegistry
      └─ MainWindow
          ├─ ModuleRepository / ModuleStateStore
          ├─ ModuleScanner / FilesystemWatcher
          ├─ DesktopLauncher / FileActionsController
          └─ Navigation / Dashboards / EditorManager / EditorPage
              └─ Markopad source + preview engines
```

## Completed revision work

- exp3-r10 completed the gutter geometry correction in the Marko Plus adapter.
- Marko Plus exp3-r11 completed the controlled fuzzy search for shortcut names
  and modifier spellings/order.
- 0.0.1 added the narrow Preview Font quote-italics effect.
- 0.0.1-r3 placed that setting inside Qt's existing Effects box, corrected the
  Marko Plus repository links, and enlarged About to reveal all text.
- The approved official logo is the Markopad page enlarged at the lower-right,
  with an orange plus on an `#f1f3f4` counter-page.

## Deferred Markopad backports

- Shortcut-dialog fuzzy matching is still to be backported to Markopad.
- Editor canvas following the System/Dark/Light app theme by default is still
  to be backported to Markopad.
- Port relevant approved icons where Markopad exposes the matching commands.
- Port the permanent theme-aware blue preview-link correction to Markopad.
- Remap Markopad's Dark Editor shortcut to Ctrl+Alt+Shift+E.
- Backport the View labels Editor Zoom, Editor Layout, and Editor Miscellaneous
  to Markopad. The Plus-only Settings tab/menu must not be copied.
- Investigate the gutter correction in Markopad and port it only if the Pad
  exhibits the same horizontal-scrollbar overlap.

## Deferred experimental lines

- The experimental folder-tree keyboard/navigation line may now begin, but it
  remains deferred from the normal revision line and must be tested separately.
- Ordered-list numbering in Source view remains a Marko-family issue. Do not
  alter the protected editor engine in the normal line; revisit it in a named
  experimental line and remind the user about the blue-link Markopad backport
  at that point.

## Resume instruction

Continue from Marko Plus 0.0.1-r3. Read this file and `ARCHITECTURE.md` before
changing code. Preserve the invariants and keep revisions surgical.
