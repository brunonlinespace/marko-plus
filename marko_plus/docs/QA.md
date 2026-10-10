# Marko Plus QA Guide

## Bug report essentials

Include the Marko Plus version, source/AppImage mode, Linux distribution,
desktop environment, X11/Wayland session, exact steps, expected behavior,
actual behavior, and relevant terminal output.

## High-value regression sequences

### Large Workspace

- Open a Workspace containing hundreds or thousands of Markdown documents.
- Switch List/Grid repeatedly and scroll through the final row.
- Resize the sidebar and change folders while scanning or filtering.
- Confirm inactive registered Workspaces are not merged into the active view.

### Editor and preview

- Open documents in Source, Split, and Preview layouts.
- Move among files and verify view-only and editor preferences persist.
- Exercise large Select All/Paste, Replace All, Undo, and Redo operations.
- Verify preview links remain blue before and after activation in both canvas
  schemes.

### Files and folders

- Create a document in the Workspace Dashboard, a folder dashboard, and beside
  an active document; confirm each uses the intended folder.
- Rename and move documents repeatedly, including same-folder drops.
- Rename a folder with F2 and verify open pages/tree paths remain coherent.
- Drop external Markdown files on root and nested destinations; exercise
  Replace, Keep Both, and Skip.

### Save safety

- Save normally, through Save and New, Save and Dashboard, and Save and Exit.
- Modify or replace a file externally before saving and verify Marko Plus does
  not silently overwrite the changed target.
- Close an unsaved prompt using Cancel and the window close control.

### Workspace switching and shutdown

- Switch via **File > Workspace(s)** and **Open / Manage Workspaces...**.
- Verify Dashboard/folder context shows `Workspace — Marko Plus`, and an active document shows `filename — Workspace — Marko Plus` with the Rico-style dirty/locked state markers; verify the Dashboard refreshes.
- Test Dashboard and Last File launch-screen settings independently per app.
- Close during an active scan and with unsaved documents.

## Identity/provenance gate

| Check | Expected result |
| --- | --- |
| `python main.py --version` | `Marko Plus 0.0.1-r3` |
| `marko-plus.json` | Canonical name, ID, version, publisher, and desktop ID |
| `python -m marko_plus.tools.release_check` | Identity, inventory, hashes, and source checks pass |
| About dialog | Marko Plus 0.0.1-r3, the official Plus logo, and complete unclipped text |

## 0.4.2 Markopad editor-realignment gate

Run `python -m marko_plus.tools.marko_plus_0_4_2_check` to verify the restored Markopad zoom, Source/Preview split persistence, printable relative-resource Base URL, Paste as Markdown feedback, narrow legacy Ricopad stripping, Markopad defaults, preserved core editor/preview hashes, and the deliberate exclusion of Audit Item 8 and status-bar work.

## 0.4.1 icon-family gate

Run `python -m marko_plus.tools.marko_plus_0_4_1_check` to verify the 0.4.1 semantic icon mapping, 121-icon light/dark families, 64×64 RGBA assets, preserved 36×36 Ribbon geometry, and protected 0.3.10 production baseline.

