# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""List/grid Markdown dashboard cards with Markopad-style document actions."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from PyQt6.QtCore import QMimeData, QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QIcon, QInputDevice, QMouseEvent, QPalette
from PyQt6.QtWidgets import QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from marko_plus.models.module import Module
from marko_plus.widgets.ui_styles import style_button


class DashboardCard(QFrame):
    """Persistent Markdown card shared by the root and folder dashboards."""

    open_requested = pyqtSignal(object)          # Edit / Source Only
    split_requested = pyqtSignal(object)         # Source + Preview
    preview_requested = pyqtSignal(object)       # Preview Only
    selected_requested = pyqtSignal(object)      # one click selects only
    remove_requested = pyqtSignal(object)

    VALID_MODES = {"list", "grid"}

    def __init__(
        self,
        module: Module,
        parent=None,
        *,
        view_mode: str = "list",
        touch_moves_scroll_only: bool = False,
    ) -> None:
        super().__init__(parent)
        self.module = module
        self._view_mode = view_mode if view_mode in self.VALID_MODES else "list"
        self._touch_moves_scroll_only = bool(touch_moves_scroll_only)
        self._drag_start = QPoint()
        self._drag_active = False
        self._drag_performed = False
        self._selected = False

        self.setObjectName("dashboardCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)

        self._build_labels()
        self._build_buttons()
        self._build_fixed_layout()
        self.refresh()

    def _build_labels(self) -> None:
        self.title_label = QLabel()
        self.title_label.setTextFormat(Qt.TextFormat.RichText)
        self.title_label.setWordWrap(True)
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.metadata_label = QLabel()
        self.metadata_label.setWordWrap(True)

    def _build_buttons(self) -> None:
        grid = self._view_mode == "grid"
        self.edit_button = self._button("Edit", role="primary", grid=grid)
        self.split_button = self._button("Split View", role="neutral", grid=grid)
        self.preview_button = self._button("Preview", role="neutral", grid=grid)

        self.edit_button.setToolTip("Open this Markdown file in Source Only")
        self.split_button.setToolTip("Open this Markdown file in Source + Preview")
        self.preview_button.setToolTip("Open this Markdown file in Preview Only")
        self.edit_button.clicked.connect(lambda: self.open_requested.emit(self.module))
        self.split_button.clicked.connect(lambda: self.split_requested.emit(self.module))
        self.preview_button.clicked.connect(lambda: self.preview_requested.emit(self.module))
        self.refresh_icons()

    def refresh_icons(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        scheme = "light" if app.palette().color(QPalette.ColorRole.Base).lightness() >= 140 else "dark"
        root = Path(__file__).resolve().parent.parent / "assets" / "toolbar-icons" / scheme
        for button, name in (
            (self.edit_button, "source-only"),
            (self.split_button, "source-preview"),
            (self.preview_button, "preview-only"),
        ):
            path = root / f"{name}.png"
            button.setIcon(QIcon(str(path)) if path.is_file() else QIcon())

    def _build_fixed_layout(self) -> None:
        if self._view_mode == "grid":
            self._build_grid_layout()
        else:
            self._build_list_layout()

    def _build_list_layout(self) -> None:
        self.setMinimumSize(0, 118)
        self.setMaximumWidth(16777215)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(8)
        header = QHBoxLayout(); header.setSpacing(8)
        header.addWidget(self.title_label, 1); header.addWidget(self.status_label)
        outer.addLayout(header); outer.addWidget(self.metadata_label)
        actions = QHBoxLayout(); actions.setSpacing(7); actions.addStretch(1)
        for button in (self.edit_button, self.split_button, self.preview_button):
            actions.addWidget(button)
        outer.addLayout(actions)

    def _build_grid_layout(self) -> None:
        self.setMinimumSize(300, 245)
        self.setMaximumWidth(380)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        outer = QGridLayout(self)
        outer.setContentsMargins(14, 12, 12, 12)
        outer.setHorizontalSpacing(12); outer.setVerticalSpacing(8)
        outer.setColumnStretch(0, 1); outer.setColumnStretch(1, 0)
        content = QVBoxLayout(); content.setSpacing(8)
        header = QHBoxLayout(); header.setSpacing(8)
        header.addWidget(self.title_label, 1); header.addWidget(self.status_label)
        content.addLayout(header); content.addWidget(self.metadata_label); content.addStretch(1)
        actions = QVBoxLayout(); actions.setSpacing(6); actions.setAlignment(Qt.AlignmentFlag.AlignTop)
        for button in (self.edit_button, self.split_button, self.preview_button):
            actions.addWidget(button, alignment=Qt.AlignmentFlag.AlignRight)
        actions.addStretch(1)
        outer.addLayout(content, 0, 0)
        outer.addLayout(actions, 0, 1, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

    @staticmethod
    def _button(text: str, *, role: str, grid: bool) -> QPushButton:
        button = style_button(
            QPushButton("" if grid else text),
            role=role,
            size="compact",
            minimum_width=None if grid else 96,
        )
        if grid:
            button.setFixedSize(44, 44)
            button.setIconSize(QSize(28, 28))
            button.setAccessibleName(text)
        return button

    @staticmethod
    def format_size(size: int) -> str:
        if size < 1024: return f"{size} B"
        if size < 1024 * 1024: return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.setFrameShadow(QFrame.Shadow.Sunken if self._selected else QFrame.Shadow.Plain)
        self.setLineWidth(2 if self._selected else 1)
        self.update()

    def refresh(self) -> None:
        display_name = escape(self.module.display_name)
        self.title_label.setText(f"<b>{display_name}</b>")
        self.status_label.setText("● Unsaved" if self.module.dirty else "")
        modified = datetime.fromtimestamp(self.module.modified).strftime("%Y-%m-%d %H:%M")
        folder = escape(self.module.folder or ".")
        filename = escape(self.module.filename)
        self.metadata_label.setText(
            f"{folder}/{filename}<br>Modified: {modified} · Size: {self.format_size(self.module.size)}"
        )

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.module)
            event.accept(); return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._drag_active:
            self._drag_start = event.position().toPoint()
            self._drag_performed = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._drag_active and not self._drag_performed:
                self.selected_requested.emit(self.module)
            self._drag_start = QPoint()
            self._drag_performed = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # QScroller.TouchGesture owns finger movement on the root Dashboard.
        # Qt 6 preserves the originating input device on synthesized mouse
        # events, so a touchscreen-originated move can never start QDrag.
        if (
            self._touch_moves_scroll_only
            and event.deviceType() != QInputDevice.DeviceType.Mouse
        ):
            event.ignore()
            return
        if self._drag_active:
            event.accept(); return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        if self._drag_start.isNull():
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 10:
            return super().mouseMoveEvent(event)
        self._drag_active = True
        self._drag_performed = True
        try:
            mime = QMimeData()
            mime.setData("application/x-marko-plus-document", str(self.module.path).encode("utf-8"))
            drag = QDrag(self); drag.setMimeData(mime); drag.exec(Qt.DropAction.MoveAction)
        finally:
            self._drag_active = False; self._drag_start = QPoint()
        event.accept()
