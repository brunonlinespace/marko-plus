## 0.4.17 — Toggle Comment shortcut visibility

- Corrected Edit → Toggle Comment to carry the live `Ctrl+/` QAction shortcut, matching Markopad and restoring the visible keybind in the AppMenu.
- Removed the now-obsolete menu-less Toggle Comment shortcut-catalog exception so the Keyboard Shortcuts dialog derives it from the live AppMenu action.
- No other command, editor, Ribbon, file/workspace, Preview, or UI behavior changed.

## 0.4.16 — Edit restoration and File Ribbon ordering

- Restored Toggle Comment to Edit in Markopad order.
- Gave Import File/Open External File their own File Ribbon group immediately after New Window.
- Moved Workspaces before Dashboard in the File Ribbon.
- Reordered File Ribbon More Actions buttons to match File → More Actions AppMenu.
- No unrelated behavior changes.

## 0.4.15 — Quick Tour persistence and Sidebar presentation

- Adopted Rico Plus persistent Quick Tour suppression behavior and ellipsis wording.
- Moved Show Sidebar into App Sidebar in AppMenu and immediately before Dock to Left in the Modern toolbar.
- Focused Mode remains in its previous position.
- No unrelated behavior changes.

## 0.4.14 — 2026-10-10

- Remember Source Only / Source + Preview separately as the last editable document layout.
- New File opens in that remembered editable layout instead of Preview Only.
- Preview Only remains valid for ordinary document opening and cannot overwrite the remembered editable choice.
- Existing New File no-clobber creation and all unrelated Plus behavior remain unchanged.

## 0.4.13 — 2026-10-09

- Corrected **Editor Layout** to use the existing `toolbar-tabbed` icon.
- Retained all existing Editor Layout child-command icons.
- Preserved shortcut-free App Theme commands and all 0.4.12 behavior.
- No icon-asset, editor/Preview, workspace/file-lifecycle, status-bar, Find/Replace, Item 31/33, or external-session changes.

## 0.4.12 — 2026-10-09

- Wired **Editor Layout** to the existing `toolbar-classic` asset while retaining its existing child-command icons.
- Removed keyboard shortcuts from Light, Dark and System App Theme commands.
- Preserved 0.4.11 Toggle Comment/Heading UI work and the `Ctrl+Alt+Shift+V` List/Grid shortcut.
- No icon-asset, editor/Preview, workspace/file-lifecycle, status-bar, Find/Replace, Item 31/33, or external-session changes.

## 0.4.11 — 2026-10-09

- UI backlog release: added the approved Toggle Comment light/dark icon pair and a Home Ribbon button without moving Ctrl+/ shortcut ownership.
- AppMenu Heading now uses the same `heading-group` icon as the Ribbon flyout.
- Added Light/Dark/System shortcuts on `Ctrl+Alt+Shift+1/2/3`.
- Rebound Toggle List/Grid View from `Ctrl+Alt+Shift+D` to `Ctrl+Alt+Shift+V`.
- Preserved 0.4.10 Markopad source-editor authority and all audit-item behavior.

## 0.4.10 — 2026-10-09

- Audit Item 1: replaced the frozen Markopad r8.2 source-editor snapshot with the exact Markopad 0.2.4 source-editor authority.
- Removed only redundant `CodeEditor` catch-up ownership for gutter sizing, Insert/overwrite mode and Toggle Comment; these now inherit directly from Markopad.
- Retained all genuine Plus-specific editor adapters, including Ctrl+G/Ctrl+D routing and EditorPage helper APIs.
- Rebased the integration checker from historical r8.2 source authority to exact Markopad 0.2.4 source authority.
- No intended user-facing editor behavior change and no Item 2/16, status-bar, Item 31/33, Find/Replace, Preview, Paste, workspace/file lifecycle, external-session, Ribbon/AppMenu, theme or icon changes.

## 0.4.9 — 2026-10-09

- Audit Item 32: routed Copy and Select All to the active Source/Preview text surface.
- Prevented source-only mutations from operating on Source while Preview owns interaction focus in Split mode, including Undo/Redo state re-enablement.
- Added double-click reset of the Source/Preview divider to the persisted canonical 3:2 position.
- Find/Replace remains deliberately untouched.
- No Item 1/2/16, Item 31/33, status-bar, Paste, workspace/file lifecycle or external-session changes.

## 0.4.8 — 2026-10-09

- Converged `CodeEditor.toggle_comment()` with the Markopad 0.2.3 authority implementation.
- Restored Markopad's document-growth guard for both selected-text and current-line HTML comment wrapping.
- Restored the current-line cursor reapplication performed by Markopad after the transformation.
- Kept comment syntax, Ctrl+/, read-only behavior, Paste semantics, status bars, file/workspace lifecycle, external sessions, toolbar surfaces and all unrelated Plus scaffolding unchanged.
- No Item 1 refactor or Item 31 formatting-toggle experiment.

## 0.4.7 — 2026-10-09

- Audit Item 30: corrected Paste semantics without rewriting the proven paste engines.
- Ordinary **Paste** (`Ctrl+V`) now performs the existing smart HTML/rich-to-Markdown conversion.
- Added **Paste as Plain Text** (`Ctrl+Shift+V`) for the existing literal guarded-text path.
- Remapped the second command to the canonical `paste-plain` icon while leaving `paste-markdown` packaged but unwired.
- No Item 1/2/16 work, editor-engine changes, file/workspace lifecycle changes, external-session changes, or icon deletions.

## 0.4.6 — 2026-10-08

- Replaced Marko Plus's manually maintained Keyboard Shortcuts QAction inventory with recursive discovery of the live AppMenu tree.
- Fixed the demonstrated drift where `Refresh Workspace` (`Ctrl+Shift+F5`) was active in File but absent from the Keyboard Shortcuts dialog.
- Retained explicit catalogue entries only for shortcuts that intentionally have no AppMenu QAction.
- Added a dependency-free 0.4.6 regression gate covering live-menu discovery, menu-category ownership, Refresh Workspace visibility, and protection against restoration of the old manual inventory.
- No shortcut bindings, AppMenu placement, Ribbon behavior, editor/file lifecycle, drag/drop behavior, or Markopad engine code changed.

## 0.4.5 — 2026-10-08

- Fixed the fatal sidebar drag/move crash caused by `navigation.py` using `QPalette` without importing it.
- Added the corresponding missing `QDragLeaveEvent` import used by the same drag/drop implementation.
- Added a regression gate for the required Qt drag/drop imports; no move semantics or unrelated application behavior changed.

## 0.4.4 — 2026-10-08

- Audit Item 6: deleting an open document now deletes its backing file but retains the live Markdown editor/model in the existing missing-backed lifecycle.
- Managed documents and transient external sessions use the same retained-page rule; unopened documents keep the existing full-removal path.
- No repository, EditorManager, EditorPage, monitor, scanner, watcher, shell, editor-engine, import, or unrelated file-action redesign.

## 0.4.3 — 2026-10-08

- Audit 4: Rename/Delete now stop when an open document still has an unresolved changed or missing backing state.
- Audit 5: an open clean document uses Current Document semantics; if its backing copy changed externally, Duplicate serializes the live editor instead of copying the changed disk version.
- No watcher, monitor, repository, scanner, EditorPage, EditorManager, shell, build-flow, or unrelated file-action changes.

## 0.4.2 — 2026-10-07

- Repaired Markopad editor contracts lost in the Plus wrapper: persisted synchronized 50–300% zoom with Ctrl+mouse-wheel, remembered Source/Preview split ratio, printable relative-resource Base URL, and explicit empty Paste-as-Markdown feedback.
- Restored Markopad's narrow one-way legacy Ricopad Markdown envelope stripping without reviving retired rich metadata.
- Realigned new/unconfigured defaults to Word Wrap On and Source font 11 pt while preserving existing persisted user choices.
- Kept Audit Item 8 shortcut policy, status bars, Plus file/lifecycle/workspace policies, Locked Mode, Properties, Find/Replace, Symbols, and 0.4.1 icon-family work unchanged.
- Kept the inherited Markopad source editor and preview cores byte-for-byte unchanged.

## 0.3.9 — 2026-10-06

## 0.4.1 — 2026-10-07

Toolbar icon-family reset rebased onto the 0.3.10 baseline.

- Replaced both packaged 64×64 light/dark toolbar icon families with the approved 0.4.0 artwork.
- Added dedicated semantic icons and remapped commands that previously shared or borrowed unrelated artwork.
- Preserved the established 36×36 Ribbon rendering and 52×52 button geometry.
- Preserved 0.3.10 sidebar navigation rollback behavior and all non-icon production code except the QAction icon-name mapping.

## 0.3.10 — 2026-10-06

- Corrected sidebar selection rollback when Tabs Disabled navigation to another document is cancelled because the active document is dirty.
- Sidebar document requests now use a transactional shell wrapper; rejected opens reselect the editor manager's still-active internal document.
- Coordinated with Rico Plus 0.2.9 using the same method.

- Corrected Find/Replace shortcut ownership so F3 and Shift+F3 work from the live editor page.
- Kept Esc as Close Find/Replace and added focus-aware Ctrl+F / Ctrl+H toggling: pressing the active field's shortcut again closes the panel.
- Restored the X/Y positional counter with bounded Y+ display and immediate 1/Y first-result state.
- Kept the 0.3.8 Markopad-derived panel/search model and all non-search behavior unchanged.

## 0.3.8 — 2026-10-06

- Restored Markopad's bottom two-row Find/Replace panel and exact Ctrl+F / Ctrl+H / Esc interaction model.
- Returned search rendering to one gold match-decoration class with the active hit represented by the editor's real selection, eliminating the 0.3.6/0.3.7 active/passive compositor conflict.
- Preserved bounded search inventory, correct wraparound, selected-text initialization, Locked Mode and document-size protections, and one-edit-block Replace All.
- Standardized Theme, Dashboard, Sidebar, Launch Screen, and File Launch tooltip wording and relabeled App Sidebar radios to Dock to Left / Dock to Right.
- Kept status-bar, lifecycle, scanner/watcher, drag/drop, Grid, workspace, and file-format behavior out of scope.

## 0.3.7 — 2026-10-06

- Restored the distinct gold active Find highlight immediately after a successful Find; 0.3.6 had left the active-match index unset until Next/Previous navigation.
- Expanded the curated Symbols grid from 34 to 40 entries with **♥, ♦, ♣, ♠, ☐, ☑**.
- Left the wider 0.3.6 Find/Replace architecture and all unrelated behavior unchanged.

## 0.3.6 — 2026-10-06

- Split Tabs Enabled / Tabs Disabled into separate Ribbon commands and added separate Left / Right Sidebar commands plus Shift+F9.
- Replaced the Ribbon Open / Manage Workspaces button with the shared Workspace(s) menu, added Import File and Open External File, and removed the separator between the two file-policy selectors.
- Restored Normal Paragraph to the Heading menu and made heading-0 the group icon.
- Fixed Dark Editor dirty-state leakage and added presentation-state preservation around editor preference application.
- Aligned Properties and Symbols presentation to Rico Plus while keeping Marko-specific content and insertion safety.
- Reworked Find / Find and Replace around Rico's stronger search model while retaining Marko's size and Locked Mode guards.

## 0.3.5 — 2026-10-06

- Removed redundant file icons from the Workspace tree while preserving the existing native Qt folder icons.
- Added lightweight palette-aware drop-target feedback for folder rows, Workspace-root Dashboard targets, the main Dashboard import surface, and Folder Dashboard import surfaces.
- Wired `show-sidebar.png` to the **App Sidebar** group icon while preserving the existing Left/Right option artwork.
- Kept folder moving, system-aware native AppMenu icons, scanners/watchers, open-document monitoring, tabs lifecycle, Grid View, mouse Back navigation, and editor/file workflows out of scope.

## 0.3.4 — 2026-10-06

- Added **Settings → App Sidebar → Left Sidebar / Right Sidebar** directly below App Dashboard, with Left remaining the default.
- Sidebar side changes live by moving the existing NavigationWidget inside the existing splitter; saved sidebar width remains logically stable across Left/Right positions.
- Added the supplied light/dark `show-sidebar-right.png` artwork; Left Sidebar continues to use the existing light/dark `show-sidebar.png`.
- Kept Grid View, mouse Back navigation, scanners/watchers, open-document monitoring, tabs lifecycle, drag/drop, editor behavior, and all file workflows unchanged.

## 0.3.3 — 2026-10-06

- Refined Grid View document controls to 44 × 44 icon-only buttons with 28 × 28 existing icons, preserving tooltips and accessibility names while leaving List View unchanged.
- Added application-wide handling for the dedicated mouse Back button with bounded Dashboard/folder/document navigation history.
- Coalesced synchronous internal Dashboard transitions so Tabs Disabled document changes produce user-visible Back history.
- Kept drag/drop feedback, folder moving, Left/Right sidebar, keyboard Backspace navigation, and all file/scanner/watcher lifecycle work out of scope.

## 0.3.2 — 2026-10-06

- Added `Ctrl+Alt+Shift+I` for **Import File into Workspace...** and `Ctrl+Alt+Shift+O` for **Open External File...** without changing either workflow.
- Reduced the creation wording to **New File** and reused the existing New/New Folder icon assets on Dashboard and Folder Dashboard controls.
- Reused the packaged Grid/List artwork on the Dashboard view-toggle button and reordered the right-side controls to View / Refresh / Sort.
- Added native folder/file icons to the Workspace tree so folders and files are visually distinct without changing navigation or drag/drop semantics.
- Renamed **Remove Folder** user-facing wording to **Delete Folder** while leaving the underlying safe folder-removal implementation unchanged.
- Reordered the sidebar to **My Workspace → Dashboard → Expand/Collapse → tree → Refresh Workspace**.
- Added a current, GitHub-facing root `README.md` matching the supplied Rico/Nuxpad documentation style.
- Deliberately left Grid-card presentation, Left/Right sidebar support, scanners/watchers, open-document monitoring, document lifecycle, editor engines, and file-safety behavior unchanged.

## 0.3.1 — 2026-10-05

- Corrected Tabs Disabled from a hidden-tab presentation state into a true single-document lifecycle.
- Added shared multi-document resolution for disabling tabs and application exit.
- Preserved protected missing/external-conflict workflows and prevented background Save Version As from stealing current context.
- Left the 0.3.0 monitor/scanner architecture unchanged.

## 0.3.0 — 2026-10-05

- Added synchronized Plus-family open-document survival for external delete/rename-away.
- Added one deduplicated shared live-path monitor without external-folder crawling or extra workspace scans.
- Protected clean missing-backed editors on close/exit and retained loaded repository entries until safe close/rebind.
- Kept the ordinary workspace watcher/scanner unchanged.

# Changelog

## [0.2.6] — 2026-10-05

- Aligned the unavailable-Workspace startup warning with Rico Plus by using **Open / Manage Workspaces** without ellipsis inside that warning only.
- Removed the stale **Show Dashboard** label from the live Keyboard Shortcuts catalog; the command is now listed as **Dashboard**.
- Corrected Quick Tour Help wording from the Markopad GitHub repository to the **Marko Plus GitHub repository**.
- Changed Help → Documentation / F1 from desktop-launching `docs/README.md` to opening it in a new Marko Plus window through the existing external-file lifecycle.
- Refreshed the bundled F1 `docs/README.md` to document the current Workspace, external-open, import, drag/drop, tabs, Locked/Focused Mode, file-safety, and Help behavior.
- Deliberately deferred the wider stale-documentation/QA cleanup and AppImage/packaging-QA parity work.

## [0.2.5] — 2026-10-05

- Extended internal managed-file sidebar drops to use the same explicit destination mapping already used by external imports.
- Managed file → folder row moves into that folder.
- Managed file → file row moves into that file's containing folder.
- Managed file → empty sidebar tree moves to Workspace root.
- Preserved the Dashboard-button root move and same-folder no-op protection.
- Left external import routing, editor external-open drops, import/file-safety infrastructure, and all unrelated behavior unchanged.

## [0.2.4] — 2026-10-05

- Reconciled external Markdown drag/drop around explicit targets rather than a MainWindow-wide fallback.
- Main Dashboard and Dashboard sidebar button import to Workspace root; Folder Dashboard imports to its folder.
- Sidebar tree now resolves external imports as: empty tree → Workspace root, folder row → folder, file row → file's containing folder.
- Unrelated sidebar/application chrome no longer acquires an inferred import destination.
- Editor-surface file drops no longer import; they launch the existing new-window file-open lifecycle so external files use the established Preview Only + Locked + Focused session.
- Preserved internal managed-file moves as folder-only and left `FileActionsController.import_files()` and all unrelated lifecycle/file-safety infrastructure unchanged.

## [0.2.3] — 2026-10-05

- Ported Rico Plus 0.1.5's new-document **Duplicate Last Saved Version** staging model: saved Markdown is now read as guarded payload and written into a fresh staged file instead of using `shutil.copy2()`.
- Both duplicate branches now use the same fresh-payload staging path, restore only source permission bits, and retain the existing exclusive/no-replace destination installer.
- Added the 25 MiB duplicate reopen guard used by the common Plus file lifecycle.
- Corrected stale scan-failure wording from **Library** to **Workspace**, matching Rico Plus.
- Preserved 0.2.2 File-menu/discoverability/icon/Ctrl+F/external Preview behavior and all unrelated lifecycle, import, scanner/watcher, editor, Ribbon, and Suite-routing behavior.

## [0.2.2] — 2026-10-05

- Aligned the File AppMenu with Rico Plus 0.1.4: Dashboard, Next/Previous, Refresh Workspace, Workspace(s), Import File into Workspace, Open External File, and New Window now follow the agreed common order and separators.
- Added **Import File into Workspace...** as a thin front end to the existing safe drag/drop import path; it imports to the Workspace root and does not auto-open.
- Reordered **More Actions** to Duplicate / Rename / Delete, External Editor / Containing Folder, then Properties; relabelled **Rename File…** and **Delete File** according to the agreed ellipsis convention.
- Updated the main Dashboard tip to reference **File → Import File into Workspace...**.
- Rewired existing assets only: Tabs Disabled → `drop-new-window.png`, Editor Layout → `toolbar-tabbed.png`, Open External File → `open.png`, Import File into Workspace → `drop-active.png`.
- Changed editor-context `Ctrl+F` to toggle/retract the existing Find bar while preserving Dashboard/Folder Dashboard search focusing.
- External Markdown verification sessions now open in existing Preview Only mode without persisting that layout choice, while retaining Locked + Focused startup.
- Preserved all 0.2.1 external-session lifecycle, Phase-1 touch/import behavior, exact Markdown MIME/extension contract, and Suite Pythoine non-routing identity.

## [0.2.1] — 2026-10-05

- Completed the Phase 2 external-open lifecycle without changing the 0.2.0 external-session model/repository architecture.
- External OS/file-manager launches now mark startup as explicitly file-directed, preventing the normal startup Dashboard/context tab from appearing afterward.
- Converged Marko's managed pending-open lifecycle on Rico Plus's dedicated `_pending_open_path` / `_open_pending_if_ready()` pattern, including explicit post-scan resolution.
- External-launch windows start in transient Locked Mode and Focused Mode for quick verification without rewriting saved view preferences.
- Added **File → Open External File...** using the same standalone new-window/file-open lifecycle; supported file types remain exactly `.md`, `.markdown`, `.mdown`, and `.mkd`.
- Moved the existing **New Window...** action immediately below **Open External File...**, with separators between Workspace(s), the two standalone-window commands, and Save.
- Aligned **Open Containing Folder** for external sessions with Rico Plus by allowing the external file's real parent folder to open.
- Corrected the unavailable-Workspace instruction to the actual **Open / Manage Workspaces...** command and fixed singular/plural dirty-document status wording.
- Preserved Phase 1 import-only desktop drops, touch scrolling, Suite Pythoine non-routing identity, exact `text/markdown` MIME support, and single-file `%f` routing.

## [0.2.0] — 2026-10-05

- Phase 2 convergence release closing original audit Items 23, 25, and 26 by porting Rico Plus 0.1.1's transient external-session architecture to Markdown.
- Added standalone single-file desktop opening with `Exec=marko-plus %f` and the Markopad-authoritative `text/markdown` MIME declaration; supported Markdown extensions remain exactly `.md`, `.markdown`, `.mdown`, and `.mkd`.
- Files opened by the operating system from outside the active Workspace now remain transient external working documents rather than being copied or registered into the Workspace.
- Workspace rescans preserve live external documents, while Dashboard, Folder Dashboard, navigation, workspace counts, creation-folder selection, and last-opened Workspace state exclude them.
- Extended the existing live Save As rebind lifecycle so destinations inside the Workspace are managed and destinations outside it are external, matching Rico Plus's method and repository contract.
- Preserved Phase 1 semantics: external mouse drops still import into the Workspace and stop; main-Dashboard touch scrolling and mouse managed-file drag/move are unchanged.
- Preserved Suite Pythoine identity as a non-routing Extension with empty routing extensions and `routing/open/create` capabilities all false.
- Rewired existing command icons only: `app-drag-and-drop.png` to App File Launch and Tabs Enabled, `drop-active.png` to Tabs Disabled, and `drop-new-window.png` to Editor Layout.

## [0.1.10] — 2026-10-05

- Added Rico-derived `QScroller.TouchGesture` kinetic scrolling to the main Dashboard in both List and Grid views.
- Locked the Phase 1 touch contract: finger movement on a main-Dashboard document card scrolls the Dashboard and cannot start managed-document `QDrag`; genuine mouse drag-to-move remains unchanged.
- Kept Folder Dashboard, navigation/sidebar, and Marko's Ribbon/toolbars free of QScroller kinetic behavior.
- Simplified external Markdown desktop drops to import-only: copy into the targeted workspace/folder, refresh normally, and leave the imported file closed for the user to open or manage.
- Retired the Active Window / New Window drop policy, Settings/Ribbon controls, Shift inversion, and persisted `drop_open_mode` preference while retaining the existing icon assets.
- Deliberately excluded transient external working-document sessions and richer long-press touch dynamics from this Phase 1 release.

## [0.1.9] — 2026-10-04

Polish, icon-family completion, control-tab refresh, and shortcut audit.

- Relabeled **Manage Workspaces…** to **Open / Manage Workspaces...**.
- Added **Ctrl+Shift+[** for Source Font and **Ctrl+Shift+]** for Preview Font.
- Made **Ctrl+F** context-sensitive: document Find in editor context, main Dashboard search on the root Dashboard, and folder search on Folder Dashboard.
- Reordered Markdown, Insert, View, and App Theme to the approved 0.1.9 command taxonomy.
- Installed eight supplied Marko icon designs in both light/dark runtime families: New Folder, Open/Manage Workspaces, Save and New, Save and Dashboard, File Header, Focused Mode, Edit Link, and Remove Link.
- Reclaimed and correctly wired the existing New Window, Save As, Previous File, Next File, and Save and Exit icons.
- Refreshed ShellRibbon/control tabs so newly converged commands with completed icons are visibly available, including New Window, Save As, Previous/Next File, distinct link controls, File Header, and Focused Mode.
- Refreshed the Keyboard Shortcuts catalog ordering and corrected stale Quick Tour wording from the pre-0.1.7 theme-coupling model.
- Preserved the 0.1.8 desktop/runtime identity split and all established file-safety/editor/workspace behavior.
- No touch/kinetic scrolling or transient external-file-session architecture is included.

## [0.1.8] — 2026-10-04

Desktop/runtime identity correction matching Rico Plus's proven Plasma/Wayland contract.

- Changed the canonical runtime `DESKTOP_ID` from the reverse-DNS AppStream ID to `marko-plus`.
- Added `APP_RUNTIME_DESKTOP_ID = DESKTOP_ID` and routed Qt through `app.setDesktopFileName(APP_RUNTIME_DESKTOP_ID)`, matching Rico Plus.
- Aligned `marko-plus.json` desktop identity with `marko-plus.desktop`, `StartupWMClass=marko-plus`, and the Suite component manifest.
- Kept `io.github.brunonlinespace.marko_plus` exclusively as the AppStream metadata ID.
- Updated the Fedora/AppImage project-manifest validation so runtime desktop identity is no longer confused with AppStream identity.
- Added a dedicated regression gate for the runtime/AppStream identity split.
- No editor, theme, file lifecycle, workspace, navigation, touch, drag/drop, icon, command, or other convergence behavior is changed.

## [0.1.7] — 2026-10-04

Theme architecture convergence with Rico Plus 0.0.8, limited to Audit Items 19, 20, and 30.

- Changed the fresh-install application theme default from System to **Light**.
- Retired the older `editor_canvas_follows_app_theme` contract: application chrome and the Markdown source/preview canvas now persist independently.
- Preserved valid existing application-theme and Dark Editor choices during migration; undefined legacy canvas state migrates to Light.
- Ported Rico Plus's softer Light-shell surface treatment (`#D4D4D4` Window, `#F4F4F4` Base, `#E4E4E4` Button) while retaining Marko's teal highlight accent.
- Changing System/Dark/Light no longer changes Dark Editor, and toggling Dark Editor no longer changes the application theme.
- Added explicit editor-canvas status feedback and aligned application-theme feedback to `Theme: Light/Dark/System.`
- Preserved Marko's Markdown source/preview pairing: Dark Editor still changes both canvases together.
- No touch/kinetic scrolling, external drag/drop/import, file lifecycle, tabs, Locked Mode, navigation, workspace, icon, or Rico external-file work is included.

## [0.1.6] — 2026-10-04

Locked Mode implementation convergence with Rico Plus 0.0.8, limited to Audit Item 17.

- Made Locked Mode application-wide and persistent through EditorManager, applying the resulting state to every live Markdown EditorPage.
- Added Rico Plus's persisted **Don't ask again when disabling Locked Mode** unlock-confirmation flow.
- Newly opened/reopened locked documents reset to the top while Marko's Source/Split/Preview and Markdown editing mechanics remain unchanged.
- Retained the 0.1.5 title-state model and synchronized the ` — Locked Mode` suffix after state changes.
- Migrated the legacy `editor_view_only` preference to the common `lock_editor` key.
- Preserved the current Marko Plus application icon byte-for-byte.
- No tabs, ShellRibbon, Focused Mode, Save As, workspace mechanics, navigation, drag/drop, external-path, theme, desktop-identity, or unrelated convergence work is included.

## [0.1.5] — 2026-10-04

Window-title state-model convergence with Rico Plus 0.0.8, limited to Audit Item 18.

- Replaced the Workspace-only main-window title with Rico Plus's precise managed-document title model.
- An active document now shows `filename — Workspace — Marko Plus`; dirty documents prefix the filename with `*`; a locked active editor appends ` — Locked Mode`.
- Dashboard/folder context shows `Workspace — Marko Plus`.
- Title refresh follows the same current-document, repository-change, and editor-state update paths as Rico Plus.
- No Lock Editor behavior, terminology, settings, editor lifecycle, tabs, ShellRibbon, workspace mechanics, or other convergence work is included.

## [0.1.4] — 2026-10-04

Navigation robustness parity with Rico Plus 0.0.8, limited to Audit Item 13.

- Added Rico Plus's exact sidebar long-path overflow configuration: non-stretching `ResizeToContents` tree column, as-needed horizontal scrollbar, per-pixel horizontal scrolling, and `ElideNone`.
- Existing Marko Plus navigation, drag/drop/import, repository, scanner, tabs, and workspace behavior remain unchanged.
- No other convergence or feature work is included.

## [0.1.3] — 2026-10-04

Document Tabs implementation convergence with Rico Plus 0.0.8, built on the 0.1.2 live-page lifecycle.

- **Item 2:** added persistent document tabs plus one temporary Dashboard/folder navigation tab using the Rico Plus QTabBar behavior.
- Added persisted **Tabs Enabled / Tabs Disabled** controls, enabled by default, with the same contextual tab behavior as Rico Plus.
- **Ctrl+T** now opens the current navigation context as a tab; **Ctrl+W** closes the active document contextually or returns to Dashboard; Task List and Show Dashboard intentionally lose those shortcuts pending later reassignment.
- **Ctrl+Tab / Ctrl+Shift+Tab** cycle document/navigation tabs while tabs are enabled and fall back to ShellRibbon pages while tabs are disabled.
- **Item 28:** EditorManager now emits close/reset lifecycle signals required by tabs; the existing 0.1.2 `module_path_rebound` signal updates the same live tab after Save As.
- **Item 7:** ShellRibbon itself is not redesigned; its existing `cycle_tab()` interface is used only for the tabs-disabled fallback.
- No Save As redesign, Focused Mode changes, watcher/scanner/repository changes, drag/drop changes, external-path work, or unrelated convergence work are included.

## [0.1.2] — 2026-10-04

Preparatory EditorPage lifecycle convergence with Rico Plus 0.0.8 for future Document Tabs.

- **Item 9:** Save As and conflict **Save Version As…** now keep the existing EditorPage alive and rebind it to the successfully written Markdown target instead of closing the page and waiting for a workspace rescan.
- Added the Rico-style EditorManager path-rebind lifecycle while retaining Marko Plus workspace-only Markdown targets, encoding/newline preservation, and existing safe-write rules.
- Removed the temporary external-editor saved-path bridge made necessary by the old close/rescan/reopen Save As lifecycle; the live page now owns the preserved target directly.
- **Item 10:** a newly created EditorPage is registered as loaded only when its initial Markdown load succeeds; failed loads are discarded instead of being cached as open pages.
- No Document Tabs, ShellRibbon changes, Focused Mode changes, watcher/scanner/repository/state-store changes, or unrelated convergence work are included.

## [0.1.1] — 2026-10-04

Focused Mode implementation convergence with Rico Plus 0.0.8 on the shared ShellRibbon architecture.

- Added **Focused Mode** on **F10** using Rico Plus's temporary state-capture/restore behavior.
- Focused Mode hides Sidebar, Status, and File Header and collapses ShellRibbon without persisting those temporary states.
- Leaving Focused Mode restores the exact captured states; shutdown while focused preserves the pre-Focused splitter geometry.
- Editor pages opened/switched while Focused Mode is active keep their status/header surfaces hidden.
- Moved **File Header** to the first item in **View → Editor Layout**, with a separator before the existing Source Only / Source + Preview / Preview Only radio choices.
- `ShellRibbon` itself remains byte-for-byte 0.1.0; no Document Tabs or other convergence work is included.

## [0.1.0] — 2026-10-03

ShellRibbon implementation-convergence experiment, based directly on 0.0.9.

- Extracted the Marko command-surface presentation from MainWindow into `widgets/shell_ribbon.py`.
- Adopted the Rico Plus ShellRibbon ownership/lifecycle boundary (`collapsed_changed`, `set_collapsed()`, `cycle_tab()`, `refresh_theme()`).
- Preserved the Marko 0.0.9 visual command surface and command behavior.
- Did not include Focused Mode or Document Tabs.
- 0.0.10 remains a rejected experimental branch and is not an ancestor of 0.1.0.

## [0.0.9] — 2026-10-03

### File Header convergence
- Added the persisted **File Header** view control from Rico Plus 0.0.8.
- Added **Ctrl+Alt+Shift+F** for File Header.
- Added **View → Editor Miscellaneous → File Header** as the first miscellaneous editor option.
- Existing and newly opened EditorPages follow the same persisted header visibility state.
- Marko Plus retains its existing Markdown filename/path header contents unchanged.
- No Focused Mode, document tabs, Save As lifecycle, external-path, drag/drop, or unrelated convergence work is included.

## [0.0.8] — 2026-10-03

### Plus shell convergence
- Aligned AppMenu and command-toolbar View ordering to **Full Screen → Show Status → Show Sidebar**.
- Added **Ctrl+Shift+F5** and the sidebar **Refresh Workspace** button using the existing Marko Plus refresh path; retained Marko Plus's established **Refreshing… / Refreshed…** status feedback.
- Made the native/global AppMenu contract explicit with `setNativeMenuBar(True)`, matching Rico Plus.
- Moved **New Window…** into **File → Workspace(s)** directly after **Manage Workspaces…** and assigned **Ctrl+Alt+Shift+N**, matching Rico Plus command placement and shortcut.
- Reassigned **Line Numbers** to **Ctrl+Alt+Shift+L** to remove the shortcut collision.
- No document tabs, Focused Mode, File Header, Save As lifecycle, external-path, drag/drop, editor-format, or other convergence work is included.

## [0.0.7] — 2026-10-03

No-clobber New File convergence with Rico Plus 0.0.8 only.

- Keeps Marko Plus's existing New Markdown File workflow and empty-document semantics unchanged.
- New empty Markdown data is staged in a synchronized temporary file in the destination directory.
- Final installation uses the existing exclusive/no-replace `install_new_file_from_temp()` helper.
- Existing files, symlinks, and destinations appearing during the final race window are preserved rather than overwritten.
- No later Plus-Plus convergence work is included.

## [0.0.6] — 2026-10-03

No-clobber Duplicate convergence with Rico Plus 0.0.8 only.

- Keeps Marko Plus's existing Duplicate File workflow and dirty-document policy unchanged.
- Duplicate data is staged in a synchronized temporary file in the destination directory.
- Final installation uses the existing exclusive/no-replace `install_new_file_from_temp()` helper.
- Existing files, symlinks, and destinations appearing during the final race window are preserved rather than overwritten.
- No later Phase 1 convergence work is included.

## [0.0.5] — 2026-10-03

Dirty Open in External Editor convergence with Rico Plus 0.0.8 only.

- Dirty Open in External Editor now offers **Save Changes and Open / Open Last Saved Version / Cancel**.
- **Save Changes and Open** uses Marko Plus's existing protected save path before launching the host editor.
- If that save resolves an external-change conflict through **Save Version As…**, the preserved Markdown version is the one opened externally.
- **Open Last Saved Version** opens the disk copy without saving the live editor buffer.
- The choice can be remembered with the same Ask / Save / Saved policy as Rico Plus.
- Added **Settings → Open Externally with Unsaved Changes** immediately after the 0.0.4 Duplicate policy entry.
- Added the same radio-choice submenu as the next Settings-toolbar flyout using the existing External Editor icon.
- No later Phase 1 convergence work is included.

## [0.0.4] — 2026-10-03

Dirty Duplicate File convergence with Rico Plus 0.0.8 only.

- Dirty Duplicate now offers **Duplicate Current Document / Duplicate Last Saved Version / Cancel**.
- The Current Document choice serializes the live unsaved Markdown buffer without saving the source.
- The Last Saved Version choice retains the existing disk-copy behavior.
- The choice can be remembered with the same Ask / Current / Saved policy as Rico Plus.
- Added **Settings → Duplicate File with Unsaved Changes** as the final Settings item with a separator above.
- Added the same radio-choice submenu as the final Settings-toolbar flyout using the existing Duplicate File icon.
- No later Phase 1 convergence work is included.

## [0.0.3] — 2026-10-03

External-change conflict convergence with Rico Plus 0.0.8 only.

- Replaces **Keep My Version** with protected **Save Version As…**.
- Save conflicts now offer **Reload / Save Version As… / Overwrite / Cancel**.
- External-change warnings confirm exact file content rather than treating timestamp-only changes as conflicts.
- **Overwrite** is the only conflict choice that may replace the changed disk copy.
- Save Version As preserves the externally changed source and uses Marko Plus's existing managed Save As lifecycle for the preserved Markdown version.
- No other Phase 1 convergence work is included.


## [0.0.2-r1] — 2026-09-24

### Packaging
- Align the Portable/AppImage tree with the current Suite Pythoine component contract.
- Add a root `suite-pythoine-component.json` declaring Marko Plus as an Extension.
- Move pinned PyInstaller build requirements to `packaging/pyinstaller/build-requirements.txt`.
- Harden the Fedora AppImage builder with non-privileged host checks, safe build-root cleanup,
  native x86_64/aarch64 handling, isolated dependency validation/locking, metadata validation,
  controlled appimagetool acquisition, checksums/provenance, and final-AppImage version testing.
- Preserve Marko Plus's own dependency profile: QtPrintSupport is required for printing/PDF output;
  no QtPdf reader or cross-application negative payload policy is added.

## [0.0.2] — 2026-09-17

- Matched the About dialog's default size to Quick Tour.
- Regrouped Keyboard Shortcuts by application menu and relabelled the filter from Tab to Menu while retaining All.
- Adopted the canonical desktop ID for the running Marko Plus window identity.
- Restored Select All, Duplicate Line / Selection and Delete Line to Home; grouped Inline Code and Code Block under Code.
- Reordered Insert and realigned View to their application-menu structures; Settings remains unchanged.

## [0.0.1-r6] — 2026-09-17

- Corrected the About dialog to restore separate Marko Plus repository and brunonlinespace profile links, following Markopad's established layout.
- Changed the Marko Plus slogan to **Friendly. Fast. Focused.**
- Retained the user-facing **Configuration:** label; it is not **Preferences:**.

## [0.0.1-r5] — 2026-09-17

- Adopted Rico Plus's Lock Editor warning/information dialog workflow and status messages while retaining Marko Plus's persistent shared editor lock state.
- Restored New Window, Save As, Previous File, Next File, and Refresh Workspace to the requested File-menu positions.
- Restored Ctrl+Shift+N to New Folder; New Window intentionally has no shortcut.
- Corrected More Actions separators and the exact View-menu ordering.

## [0.0.1-r3] — 2026-09-16

- Moved **Italicize block quotations** into Qt's existing Preview Font Effects
  box instead of presenting a duplicate box.
- Corrected the Marko Plus repository and issue links.
- Increased the About dialog's default size so its full contents are visible.

## [0.0.1] — 2026-09-16

- Established Marko Plus as a workspace-scale Markopad for Markdown documents.
- Added registered Workspaces with lightweight per-Workspace UI state.
- Added recursive navigation, root/folder dashboards, persistent List/Grid
  views, background scanning, and drag-and-drop organization.
- Integrated Markopad Source, Source + Preview, and Preview layouts plus its
  command surface, themes, editing actions, and help links.
- Added safe file/folder creation, duplication, rename, move, removal, external
  opening, external-change handling, and atomic saving.
- Added the first-run Quick Tour, searchable shortcut dialog, launch-screen and
  drag-and-drop settings, editor preferences, and theme-following canvas.
- Added persistent blue preview links, gutter/scrollbar geometry correction,
  persistent View Only, and fuzzy shortcut searching.
- Extended Preview Font with an optional **Italicize block quotations** effect.
- Adopted the approved official Marko Plus logo.
- Removed the obsolete interpreter, execution, terminal supervision,
  executable-permission, and Python-oriented packaging surface.
- Kept preview colour themes, folder-tree keyboard experiments, and source-list
  renumbering outside this release.
