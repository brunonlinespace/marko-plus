# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
"""Explorer-style navigation sidebar with pinned Dashboard access."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path, PurePath

from PyQt6 import sip
from PyQt6.QtCore import QMimeData, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import (
    QDrag, QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent, QPainter,
    QPalette,
)
from PyQt6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget, QSizePolicy, QStyle,
)

from marko_plus.app_constants import MARKDOWN_EXTENSIONS
from marko_plus.models.module import Module
from marko_plus.widgets.loading_indicator import LoadingIndicator
from marko_plus.widgets.ui_styles import style_button

MODULE_MIME_TYPE = "application/x-marko-plus-document"
SIDEBAR_MINIMUM_WIDTH = 205


def external_markdown_paths(mime_data: QMimeData) -> list[Path]:
    """Return local external Markdown files carried by a desktop drag."""
    if not mime_data.hasUrls():
        return []
    paths: list[Path] = []
    for url in mime_data.urls():
        if not url.isLocalFile():
            continue
        path = Path(url.toLocalFile()).expanduser().resolve(strict=False)
        if path.is_file() and path.suffix.casefold() in MARKDOWN_EXTENSIONS:
            paths.append(path)
    return paths


class NavigationTree(QTreeWidget):
    keyboard_item_activated = pyqtSignal(object)
    module_move_dropped = pyqtSignal(object, object)
    external_files_dropped = pyqtSignal(object, object)

    PATH_ROLE = Qt.ItemDataRole.UserRole
    KIND_ROLE = Qt.ItemDataRole.UserRole + 2
    KIND_FOLDER = "folder"
    MIME_TYPE = MODULE_MIME_TYPE

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._drop_highlight_item = None

    def _drop_folder_item(self, item):
        """Return the folder row that represents the current drop destination."""
        if item is None:
            return None
        if item.data(0, self.KIND_ROLE) == self.KIND_FOLDER:
            return item
        parent = item.parent()
        if parent is not None and parent.data(0, self.KIND_ROLE) == self.KIND_FOLDER:
            return parent
        return None

    def _set_root_drop_highlight(self, active: bool) -> None:
        parent = self.parent()
        button = getattr(parent, "dashboard_button", None)
        if button is not None:
            button._set_drop_highlight(active)

    def _clear_drop_highlight(self) -> None:
        self._set_root_drop_highlight(False)
        item = self._drop_highlight_item
        self._drop_highlight_item = None
        if item is None:
            return
        try:
            item.setData(0, Qt.ItemDataRole.BackgroundRole, None)
            item.setData(0, Qt.ItemDataRole.ForegroundRole, None)
        except RuntimeError:
            pass

    def _set_drop_highlight(self, item, *, root: bool = False) -> None:
        if item is self._drop_highlight_item:
            self._set_root_drop_highlight(root)
            return
        self._clear_drop_highlight()
        self._set_root_drop_highlight(root)
        if item is None:
            return
        item.setData(
            0, Qt.ItemDataRole.BackgroundRole,
            self.palette().brush(QPalette.ColorRole.Highlight),
        )
        item.setData(
            0, Qt.ItemDataRole.ForegroundRole,
            self.palette().brush(QPalette.ColorRole.HighlightedText),
        )
        self._drop_highlight_item = item

    def _internal_move_changes_folder(self, mime_data: QMimeData, destination: Path) -> bool:
        if not mime_data.hasFormat(self.MIME_TYPE):
            return False
        source = Path(
            bytes(mime_data.data(self.MIME_TYPE)).decode(
                "utf-8", errors="replace"
            )
        ).expanduser().resolve(strict=False)
        target = destination.expanduser().resolve(strict=False)
        source_parent = source.parent
        if source_parent == target:
            return False
        try:
            return not (source_parent.exists() and target.exists() and source_parent.samefile(target))
        except OSError:
            return True

    @staticmethod
    def _depth(index) -> int:
        depth = 0
        parent = index.parent()
        while parent.isValid():
            depth += 1
            parent = parent.parent()
        return depth

    def drawBranches(self, painter: QPainter, rect, index) -> None:
        """Use the active Qt platform style for tree branches."""
        super().drawBranches(painter, rect, index)

    def mimeTypes(self) -> list[str]:
        return [self.MIME_TYPE]

    def mimeData(self, items) -> QMimeData:
        mime = QMimeData()
        if items:
            item = items[0]
            if item.data(0, self.KIND_ROLE) == "module":
                path = item.data(0, self.PATH_ROLE)
                if path:
                    mime.setData(self.MIME_TYPE, str(path).encode("utf-8"))
        return mime

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def startDrag(self, supported_actions) -> None:
        """Start a module drag without letting Qt delete the source row.

        QAbstractItemView treats an accepted external ``MoveAction`` as a
        request to remove the dragged model row.  Marko Plus moves files only
        through ``module_move_dropped`` and the repository, so that default
        cleanup could hide a file which still existed at its original path.
        Owning the QDrag here leaves all tree mutations to repository signals.
        """
        items = self.selectedItems()
        if not items:
            return
        mime = self.mimeData(items)
        if not mime.hasFormat(self.MIME_TYPE):
            return
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(supported_actions, Qt.DropAction.MoveAction)
        self._clear_drop_highlight()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        super().keyPressEvent(event)
        if event.key() in {
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End,
            Qt.Key.Key_PageUp, Qt.Key.Key_PageDown, Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            item = self.currentItem()
            if item is not None:
                self.keyboard_item_activated.emit(item)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if (
            event.mimeData().hasFormat(self.MIME_TYPE)
            or external_markdown_paths(event.mimeData())
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _external_drop_destination(self, item) -> Path | None:
        """Resolve only explicit tree targets for external imports.

        Empty tree space means Workspace root. A folder means that folder, and
        a file means the file's containing folder. Other/unknown tree items are
        rejected instead of being guessed.
        """
        if item is None:
            return Path(self.parent().library_root).resolve(strict=False)

        kind = item.data(0, self.KIND_ROLE)
        raw_path = item.data(0, self.PATH_ROLE)
        if not raw_path:
            return None

        path = Path(raw_path).expanduser().resolve(strict=False)
        if kind == self.KIND_FOLDER:
            return path
        if kind == "module":
            return path.parent
        return None

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        destination = self._external_drop_destination(item)

        if event.mimeData().hasFormat(self.MIME_TYPE) and destination is not None:
            visual_target = (
                self._drop_folder_item(item)
                if self._internal_move_changes_folder(event.mimeData(), destination)
                else None
            )
            root_target = (
                visual_target is None
                and self._internal_move_changes_folder(event.mimeData(), destination)
                and destination == Path(self.parent().library_root).resolve(strict=False)
            )
            self._set_drop_highlight(visual_target, root=root_target)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return

        if external_markdown_paths(event.mimeData()) and destination is not None:
            visual_target = self._drop_folder_item(item)
            root_target = (
                visual_target is None
                and destination == Path(self.parent().library_root).resolve(strict=False)
            )
            self._set_drop_highlight(visual_target, root=root_target)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return

        self._clear_drop_highlight()
        event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._clear_drop_highlight()
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        self._clear_drop_highlight()
        external_paths = external_markdown_paths(event.mimeData())
        if external_paths:
            destination = self._external_drop_destination(item)
            if destination is None:
                event.ignore()
                return
            QTimer.singleShot(
                0,
                lambda paths=external_paths, dst=destination:
                    self.external_files_dropped.emit(paths, dst),
            )
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return

        if not event.mimeData().hasFormat(self.MIME_TYPE):
            event.ignore()
            return

        destination = self._external_drop_destination(item)
        if destination is None:
            event.ignore()
            return

        source = Path(
            bytes(event.mimeData().data(self.MIME_TYPE)).decode(
                "utf-8", errors="replace"
            )
        )

        target_folder = destination.resolve(strict=False)
        source_parent = source.expanduser().resolve(strict=False).parent
        same_folder = source_parent == target_folder
        if not same_folder:
            try:
                same_folder = (
                    source_parent.exists()
                    and target_folder.exists()
                    and source_parent.samefile(target_folder)
                )
            except OSError:
                same_folder = False
        if same_folder:
            event.setDropAction(Qt.DropAction.IgnoreAction)
            event.accept()
            return

        QTimer.singleShot(
            0,
            lambda src=source, dst=destination:
                self.module_move_dropped.emit(src, dst),
        )
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()


class DashboardNavigationButton(QPushButton):
    """Pinned Dashboard action that also accepts drops to workspace root."""

    module_move_dropped = pyqtSignal(object)
    external_files_dropped = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Dashboard", parent)
        self.setCheckable(False)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def _set_drop_highlight(self, active: bool) -> None:
        self.setDown(bool(active))

    def _internal_move_changes_folder(self, mime_data: QMimeData) -> bool:
        if not mime_data.hasFormat(MODULE_MIME_TYPE):
            return False
        mime_type = MODULE_MIME_TYPE
        source = Path(
            bytes(mime_data.data(mime_type)).decode("utf-8", errors="replace")
        ).expanduser().resolve(strict=False)
        root = Path(self.parent().library_root).resolve(strict=False)
        if source.parent == root:
            return False
        try:
            return not (source.parent.exists() and root.exists() and source.parent.samefile(root))
        except OSError:
            return True

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if (
            event.mimeData().hasFormat(MODULE_MIME_TYPE)
            or external_markdown_paths(event.mimeData())
        ):
            self._set_drop_highlight(
                bool(external_markdown_paths(event.mimeData()))
                or self._internal_move_changes_folder(event.mimeData())
            )
            event.acceptProposedAction()
        else:
            self._set_drop_highlight(False)
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(MODULE_MIME_TYPE):
            self._set_drop_highlight(
                self._internal_move_changes_folder(event.mimeData())
            )
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        elif external_markdown_paths(event.mimeData()):
            self._set_drop_highlight(True)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            self._set_drop_highlight(False)
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self._set_drop_highlight(False)
        event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_drop_highlight(False)
        external_paths = external_markdown_paths(event.mimeData())
        if external_paths:
            QTimer.singleShot(
                0,
                lambda paths=external_paths:
                    self.external_files_dropped.emit(paths),
            )
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return

        if not event.mimeData().hasFormat(MODULE_MIME_TYPE):
            event.ignore()
            return

        source = Path(
            bytes(event.mimeData().data(MODULE_MIME_TYPE)).decode(
                "utf-8", errors="replace"
            )
        )
        QTimer.singleShot(
            0,
            lambda src=source: self.module_move_dropped.emit(src),
        )
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()


class NavigationWidget(QFrame):
    dashboard_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    folder_requested = pyqtSignal(object)
    module_requested = pyqtSignal(object)
    module_move_requested = pyqtSignal(object, object)
    external_files_import_requested = pyqtSignal(object, object)

    PATH_ROLE = Qt.ItemDataRole.UserRole
    FOLDER_ROLE = Qt.ItemDataRole.UserRole + 1
    KIND_ROLE = Qt.ItemDataRole.UserRole + 2
    KIND_DASHBOARD = "dashboard"
    KIND_FOLDER = "folder"
    KIND_MODULE = "module"

    def __init__(self, library_root, repository, state_store, parent=None) -> None:
        super().__init__(parent)
        # Keep the sidebar border native
        # so the Pure PyQt branch gains the subtle themed edge without QSS.
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
        # Match the actual minimum imposed by the two compact tree controls,
        # their spacing, the layout margins, and the frame edge.
        self.setMinimumWidth(SIDEBAR_MINIMUM_WIDTH)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )
        self.library_root = Path(library_root).expanduser().resolve(strict=False)
        self.repository = repository
        self.state_store = state_store
        self._folder_items: dict[str, QTreeWidgetItem] = {}
        self._disk_folder_keys: set[str] = set()
        self._collapsed_folders: set[str] = set()
        self._selected_kind = self.KIND_DASHBOARD
        self._selected_path: Path | None = None
        self._selecting_programmatically = False
        self._build_interface()
        self._connect_signals()
        self._load_initial_modules(repository.all())

    def _build_interface(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(0)

        # Keep the Workspace identity first, followed by Dashboard and tree controls.
        self.workspace_label = QLabel("<h3>My Workspace</h3>")
        self.workspace_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.workspace_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        layout.addWidget(self.workspace_label)

        layout.addSpacing(10)

        # Dashboard stays outside the scrolling tree so it is always visible.
        self.dashboard_button = DashboardNavigationButton(self)
        layout.addWidget(self.dashboard_button)

        layout.addSpacing(10)

        tree_controls = QHBoxLayout()
        tree_controls.setSpacing(6)
        self.expand_all_button = style_button(
            QPushButton('Expand all'),
            size='compact',
            minimum_width=88,
        )
        self.collapse_all_button = style_button(
            QPushButton('Collapse all'),
            size='compact',
            minimum_width=88,
        )
        self.expand_all_button.setToolTip('Expand every workspace folder')
        self.collapse_all_button.setToolTip('Collapse every workspace folder')
        tree_controls.addWidget(self.expand_all_button)
        tree_controls.addWidget(self.collapse_all_button)
        layout.addLayout(tree_controls)

        layout.addSpacing(18)

        self.loading_indicator = LoadingIndicator(self, compact=True)
        self.loading_indicator.start(
            "Building folder tree…",
            "Scanning workspace",
        )
        layout.addWidget(self.loading_indicator)

        layout.addSpacing(8)

        self.tree = NavigationTree(self)
        self.tree.setHeaderHidden(True)
        # Preserve the real width of long workspace paths instead of forcing
        # the sole tree column to the sidebar viewport.  This restores native
        # horizontal overflow/scrolling for deeply nested folders and files.
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.tree.setIndentation(18)
        self.tree.setRootIsDecorated(True)
        self.tree.setItemsExpandable(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.tree.setDropIndicatorShown(True)
        layout.addWidget(self.tree, 1)

        layout.addSpacing(10)
        self.refresh_button = style_button(
            QPushButton("Refresh Workspace"),
            size="compact",
        )
        self.refresh_button.setToolTip("Refresh Workspace (Ctrl+Shift+F5)")
        layout.addWidget(self.refresh_button)

    def set_loading(self, loading: bool, message: str | None = None) -> None:
        """Communicate folder-tree preparation without hiding Dashboard."""
        self.refresh_button.setEnabled(not loading)
        self.expand_all_button.setEnabled(not loading)
        self.collapse_all_button.setEnabled(not loading)
        self.tree.setEnabled(not loading)
        if loading:
            self.loading_indicator.start(
                message or "Building folder tree…",
                "Scanning workspace",
            )
        else:
            self.loading_indicator.stop()

    def set_loading_detail(self, detail: str) -> None:
        if self.loading_indicator.isVisible():
            self.loading_indicator.set_detail(detail)

    def _connect_signals(self) -> None:
        self.dashboard_button.clicked.connect(self._show_dashboard)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        self.dashboard_button.module_move_dropped.connect(
            lambda source: self.module_move_requested.emit(
                source, self.library_root
            )
        )
        self.dashboard_button.external_files_dropped.connect(
            lambda paths: self.external_files_import_requested.emit(
                paths, self.library_root
            )
        )
        self.expand_all_button.clicked.connect(self.expand_all_folders)
        self.collapse_all_button.clicked.connect(self.collapse_all_folders)
        self.tree.itemActivated.connect(self._activate_item)
        self.tree.itemClicked.connect(self._activate_item)
        self.tree.keyboard_item_activated.connect(self._activate_item)
        self.tree.module_move_dropped.connect(self._forward_module_move)
        self.tree.external_files_dropped.connect(
            self.external_files_import_requested
        )
        self.tree.itemCollapsed.connect(self._remember_collapsed_folder)
        self.tree.itemExpanded.connect(self._remember_expanded_folder)
        self.repository.module_added.connect(self._on_module_added)
        self.repository.module_removed.connect(self._on_module_removed)
        self.repository.module_changed.connect(self._on_module_changed)
        self.repository.module_path_changed.connect(self._on_module_path_changed)
        self.repository.repository_reset.connect(self._on_repository_reset)

    def _show_dashboard(self) -> None:
        self.select_dashboard()
        self.dashboard_requested.emit()

    def expand_all_folders(self) -> None:
        self.tree.expandAll()
        self._collapsed_folders.clear()

    def collapse_all_folders(self) -> None:
        self.tree.collapseAll()
        self._collapsed_folders = set(self._folder_items)

    def _forward_module_move(self, source, destination) -> None:
        self.module_move_requested.emit(source, destination or self.library_root)

    def set_disk_folders(self, folders) -> None:
        """Synchronize real folder nodes from the scanner's cached result."""
        keys: set[str] = set()
        for folder in folders:
            try:
                key = (
                    Path(folder)
                    .resolve(strict=False)
                    .relative_to(self.library_root)
                    .as_posix()
                )
            except (OSError, ValueError):
                continue
            normalized = self._normalize_folder(key)
            if normalized:
                keys.add(normalized)

        self._disk_folder_keys = keys

        # Add missing folders in shallow-to-deep order.
        for key in sorted(
            keys,
            key=lambda value: (value.count("/"), value.casefold()),
        ):
            self._ensure_folder_chain(key)

        # Remove stale empty folder nodes without touching folders that still
        # contain module or subfolder items.
        for key in sorted(
            set(self._folder_items) - keys,
            key=lambda value: value.count("/"),
            reverse=True,
        ):
            item = self._folder_items.get(key)
            if not self._item_is_alive(item):
                self._folder_items.pop(key, None)
                continue
            try:
                if item.childCount() != 0:
                    continue
            except RuntimeError:
                self._folder_items.pop(key, None)
                continue
            removed = self._take_item(item)
            self._folder_items.pop(key, None)
            self._collapsed_folders.discard(key)
            if removed is not None:
                del removed

    def _load_disk_folders(self) -> None:
        """Recreate cached real folders without touching the filesystem."""
        for key in sorted(
            self._disk_folder_keys,
            key=lambda value: (value.count("/"), value.casefold()),
        ):
            self._ensure_folder_chain(key)

    def _load_initial_modules(self, modules: Iterable[Module]) -> None:
        for module in self.repository.sorted(modules, mode="title_az"):
            if not module.external:
                self._insert_module(module)

    @staticmethod
    def _normalize_folder(folder: str) -> str:
        value = folder.strip().replace("\\", "/")
        return "" if value in {"", "."} else value.strip("/")

    def _folder_absolute_path(self, key: str) -> Path:
        return (self.library_root / Path(key)).resolve(strict=False)

    def _ensure_folder_chain(self, folder: str):
        normalized = self._normalize_folder(folder)
        if not normalized:
            return None
        parent = None
        accumulated = []
        for part in PurePath(normalized).parts:
            accumulated.append(part)
            key = "/".join(accumulated)
            item = self._folder_items.get(key)
            if item is None:
                item = QTreeWidgetItem([part])
                item.setData(0, self.KIND_ROLE, self.KIND_FOLDER)
                item.setData(0, self.FOLDER_ROLE, key)
                item.setData(0, self.PATH_ROLE, str(self._folder_absolute_path(key)))
                item.setToolTip(0, str(self._folder_absolute_path(key)))
                item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
                self._insert_sorted(parent, item)
                item.setExpanded(key not in self._collapsed_folders)
                self._folder_items[key] = item
            parent = item
        return parent

    def _insert_module(self, module: Module):
        if module.external:
            return None
        state = self.state_store.ensure(module.path)
        if self._item_is_alive(state.tree_item):
            updated = self._update_module_item(module, state.tree_item)
            if updated is not None:
                state.tree_item = updated
                return updated
        state.tree_item = None
        parent = self._ensure_folder_chain(module.folder)
        item = QTreeWidgetItem([self._module_label(module)])
        item.setToolTip(0, str(module.path))
        item.setData(0, self.KIND_ROLE, self.KIND_MODULE)
        item.setData(0, self.PATH_ROLE, str(module.path))
        self._apply_module_appearance(item, module)
        self._insert_sorted(parent, item)
        state.tree_item = item
        return item

    def _insert_sorted(self, parent, item) -> None:
        count = parent.childCount() if parent else self.tree.topLevelItemCount()
        start = 0
        key = self._sort_key(item)
        index = count
        for i in range(start, count):
            sibling = parent.child(i) if parent else self.tree.topLevelItem(i)
            if key < self._sort_key(sibling):
                index = i
                break
        if parent is None: self.tree.insertTopLevelItem(index, item)
        else: parent.insertChild(index, item)

    def _sort_key(self, item):
        kind = item.data(0, self.KIND_ROLE)
        group = 0 if kind == self.KIND_FOLDER else 1
        text = item.text(0)
        return group, text.casefold()

    def _module_label(self, module: Module) -> str:
        marks = []
        if module.dirty:
            marks.append("edited")
        return module.display_name + (f"  [{' · '.join(marks)}]" if marks else "")

    @staticmethod
    def _apply_module_appearance(item, module: Module) -> None:
        """Keep state in the label and let Qt choose native text colors."""
        item.setData(0, Qt.ItemDataRole.ForegroundRole, None)

    @staticmethod
    def _item_is_alive(item) -> bool:
        """Return False when Qt has already deleted the C++ tree item."""
        if item is None:
            return False
        try:
            return not sip.isdeleted(item)
        except RuntimeError:
            return False

    def _take_item(self, item):
        """Detach and return the exact Qt-owned item wrapper safely.

        PyQt transfers ownership when takeChild()/takeTopLevelItem() is used.
        Ignoring the returned wrapper can leave cached references pointing
        at a deleted C++ object, which caused the repeated-move crash.
        """
        if not self._item_is_alive(item):
            return None

        try:
            parent = item.parent()
            if parent is None:
                index = self.tree.indexOfTopLevelItem(item)
                return self.tree.takeTopLevelItem(index) if index >= 0 else None

            index = parent.indexOfChild(item)
            return parent.takeChild(index) if index >= 0 else None
        except RuntimeError:
            return None

    def _detach_item(self, item):
        """Compatibility wrapper returning the detached item."""
        return self._take_item(item)

    def _update_module_item(self, module, item):
        """Update and reposition one live module item, returning its wrapper."""
        if not self._item_is_alive(item):
            return None

        try:
            old_parent = item.parent()
            expected = self._ensure_folder_chain(module.folder)
            item.setText(0, self._module_label(module))
            item.setToolTip(0, str(module.path))
            item.setData(0, self.PATH_ROLE, str(module.path))
            self._apply_module_appearance(item, module)
        except RuntimeError:
            return None

        detached = self._take_item(item)
        if detached is None:
            return None

        self._insert_sorted(expected, detached)
        if old_parent is not expected and self._item_is_alive(old_parent):
            self._prune_empty_folders(old_parent)
        return detached

    def _prune_empty_folders(self, item) -> None:
        current = item
        while self._item_is_alive(current):
            try:
                if current.childCount() != 0:
                    break
                parent = current.parent()
                key = current.data(0, self.FOLDER_ROLE)
            except RuntimeError:
                break

            # Keep a genuinely empty folder visible when it still exists on
            # disk. Folder nodes are now first-class workspace entries rather
            # than merely containers inferred from documents.
            if key and str(key) in self._disk_folder_keys:
                break

            if key:
                self._folder_items.pop(str(key), None)
                self._collapsed_folders.discard(str(key))

            removed = self._take_item(current)
            if removed is None:
                break
            # The empty folder is intentionally discarded here. Holding the
            # returned wrapper until this point prevents premature C++ deletion.
            del removed
            current = parent

    def _activate_item(self, item, _column=0) -> None:
        if self._selecting_programmatically: return
        kind = item.data(0, self.KIND_ROLE)
        raw = item.data(0, self.PATH_ROLE)
        if kind == self.KIND_FOLDER and raw:
            self._selected_kind = kind
            self._selected_path = Path(raw).resolve(strict=False)
            self.folder_requested.emit(self._selected_path)
        elif kind == self.KIND_MODULE and raw:
            self._selected_kind = kind
            self._selected_path = self.repository.normalize_path(raw)
            self.module_requested.emit(self._selected_path)

    def select_dashboard(self) -> None:
        self._selected_kind, self._selected_path = self.KIND_DASHBOARD, None
        self._selecting_programmatically = True
        try:
            self.tree.clearSelection()
            self.tree.setCurrentItem(None)
        finally:
            self._selecting_programmatically = False

    def select_folder(self, path) -> bool:
        normalized = Path(path).expanduser().resolve(strict=False)
        try: key = normalized.relative_to(self.library_root).as_posix()
        except ValueError: return False
        item = self._folder_items.get(key)
        if item is None: return False
        self._selected_kind, self._selected_path = self.KIND_FOLDER, normalized
        self._expand_ancestors(item)
        self._set_current_item(item)
        return True

    def select_module(self, path) -> bool:
        module = self.repository.get(path)
        if module is None: return False
        state = self.state_store.get(module.path)
        if state is None or state.tree_item is None: return False
        self._selected_kind, self._selected_path = self.KIND_MODULE, module.path
        self._expand_ancestors(state.tree_item)
        self._set_current_item(state.tree_item)
        return True

    def navigate_adjacent_module(self, step: int) -> bool:
        """Open the visible Markdown file above or below the current one."""
        if step not in {-1, 1}:
            return False
        item = self.tree.currentItem()
        if item is None:
            item = (
                self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)
                if step < 0 and self.tree.topLevelItemCount()
                else self.tree.topLevelItem(0)
            )
        else:
            index = self.tree.indexFromItem(item)
            index = (
                self.tree.indexAbove(index)
                if step < 0
                else self.tree.indexBelow(index)
            )
            item = self.tree.itemFromIndex(index) if index.isValid() else None

        while item is not None:
            if item.data(0, self.KIND_ROLE) == self.KIND_MODULE:
                self._set_current_item(item)
                self._activate_item(item)
                return True
            index = self.tree.indexFromItem(item)
            index = (
                self.tree.indexAbove(index)
                if step < 0
                else self.tree.indexBelow(index)
            )
            item = self.tree.itemFromIndex(index) if index.isValid() else None
        return False

    def collapsed_folders(self): return frozenset(self._collapsed_folders)

    def switch_workspace_root(self, library_root: str | Path) -> None:
        """Clear cached paths/items before the repository changes project."""
        self.library_root = Path(library_root).expanduser().resolve(strict=False)
        self._disk_folder_keys.clear()
        self._collapsed_folders.clear()
        self._selected_kind = self.KIND_DASHBOARD
        self._selected_path = None
        self.tree.clear()
        self._folder_items.clear()
        self.select_dashboard()

    def restore_collapsed_folders(self, folders) -> None:
        self._collapsed_folders = {self._normalize_folder(x) for x in folders if self._normalize_folder(x)}
        for key, item in self._folder_items.items(): item.setExpanded(key not in self._collapsed_folders)

    def _set_current_item(self, item) -> None:
        if not self._item_is_alive(item):
            return
        self._selecting_programmatically = True
        try:
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)
        except RuntimeError:
            pass
        finally:
            self._selecting_programmatically = False

    @staticmethod
    def _expand_ancestors(item) -> None:
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True); parent = parent.parent()

    def _remember_collapsed_folder(self, item) -> None:
        key = item.data(0, self.FOLDER_ROLE)
        if key: self._collapsed_folders.add(str(key))

    def _remember_expanded_folder(self, item) -> None:
        key = item.data(0, self.FOLDER_ROLE)
        if key: self._collapsed_folders.discard(str(key))

    def _on_module_added(self, module) -> None:
        if not module.external:
            self._insert_module(module)

    def _on_module_removed(self, module) -> None:
        state = self.state_store.get(module.path)
        item = state.tree_item if state is not None else None
        if not self._item_is_alive(item):
            item = self._find_module_item(module.path)
        if not self._item_is_alive(item):
            if state is not None:
                state.tree_item = None
            return

        try:
            parent = item.parent()
        except RuntimeError:
            parent = None
        selected = self._selected_path == module.path
        removed = self._take_item(item)
        if state is not None:
            state.tree_item = None
        if removed is not None:
            del removed
        if self._item_is_alive(parent):
            self._prune_empty_folders(parent)
        if selected:
            self.select_dashboard()
            self.dashboard_requested.emit()

    def _on_module_changed(self, module) -> None:
        state = self.state_store.ensure(module.path)
        item = state.tree_item
        if not self._item_is_alive(item):
            state.tree_item = None
            item = self._find_module_item(module.path)

        if self._item_is_alive(item):
            item = self._update_module_item(module, item)

        if item is None:
            state.tree_item = None
            item = self._insert_module(module)
        else:
            state.tree_item = item

        if (
            self._selected_kind == self.KIND_MODULE
            and self._selected_path == module.path
            and self._item_is_alive(item)
        ):
            self._set_current_item(item)

    def _on_module_path_changed(self, module, old_path) -> None:
        """Atomically migrate one live tree item to the new path."""
        old_normalized = self.repository.normalize_path(old_path)
        state = self.state_store.ensure(module.path)
        item = state.tree_item
        if not self._item_is_alive(item):
            state.tree_item = None
            item = self._find_module_item(old_normalized)

        if self._item_is_alive(item):
            item = self._update_module_item(module, item)

        if item is None:
            state.tree_item = None
            item = self._insert_module(module)
        else:
            state.tree_item = item

        if self._selected_kind == self.KIND_MODULE and self._selected_path == old_normalized:
            self._selected_path = module.path
            if self._item_is_alive(item):
                self._set_current_item(item)

    def rebuild_from_repository(self) -> None:
        """Rebuild the sidebar index from canonical repository data.

        This is intentionally used by the manual Refresh action as a repair
        operation. It preserves collapsed folders and selection while
        clearing stale QTreeWidgetItem wrappers and recreating missing nodes.
        """
        selected_kind = self._selected_kind
        selected_path = self._selected_path
        collapsed = set(self._collapsed_folders)

        # Clear all cached tree references before QTreeWidget deletes items.
        for _path, state in self.state_store:
            state.tree_item = None

        self.tree.clear()
        self._folder_items.clear()
        self._collapsed_folders = collapsed

        self._load_disk_folders()
        self._load_initial_modules(self.repository.all())
        self.restore_collapsed_folders(collapsed)

        restored = False
        if selected_kind == self.KIND_MODULE and selected_path is not None:
            restored = self.select_module(selected_path)
        elif selected_kind == self.KIND_FOLDER and selected_path is not None:
            restored = self.select_folder(selected_path)
        if not restored:
            self.select_dashboard()

    def _on_repository_reset(self) -> None:
        self.tree.clear()
        self._folder_items.clear()
        self.select_dashboard()

    def _find_module_item(self, path):
        normalized = str(self.repository.normalize_path(path))
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            item = stack.pop()
            if item.data(0, self.KIND_ROLE) == self.KIND_MODULE and item.data(0, self.PATH_ROLE) == normalized:
                return item
            stack.extend(item.child(i) for i in range(item.childCount()))
        return None
