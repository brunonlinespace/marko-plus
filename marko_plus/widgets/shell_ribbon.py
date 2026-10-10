# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shell-owned Markopad command surface for Marko Plus.

The ownership boundary follows Rico Plus: MainWindow owns QAction objects while
ShellRibbon owns their tab/page/button presentation and collapse lifecycle.
Marko Plus 0.0.9 presentation remains authoritative for this migration.
"""
from __future__ import annotations

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QSizePolicy, QTabWidget, QToolBar, QToolButton, QVBoxLayout, QWidget,
)


class ShellRibbon(QWidget):
    """Persistent Plus-owned command surface preserving Marko's existing UX."""

    collapsed_changed = pyqtSignal(bool)

    def __init__(self, actions: dict[str, QAction], parent=None) -> None:
        super().__init__(parent)
        self.actions = actions
        self._collapsed = False
        self._expanded_minimum_height = 0
        self._expanded_maximum_height = 16777215
        self.buttons: list[QToolButton] = []
        self.toolbars: list[QToolBar] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("markoPlusShellRibbon")
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setUsesScrollButtons(True)
        self.tabs.tabBar().installEventFilter(self)
        self.tabs.currentChanged.connect(self._sync_collapsed_page)
        layout.addWidget(self.tabs)

        self._build_pages()
        self.tabs.setCurrentIndex(
            next((i for i in range(self.tabs.count()) if self.tabs.tabText(i) == "Home"), 0)
        )

    def _a(self, name: str) -> QAction:
        return self.actions[name]

    @staticmethod
    def _style_button(button: QToolButton) -> None:
        # Preserve Marko Plus 0.0.9 command-button presentation exactly.
        button.setIconSize(QSize(36, 36))
        button.setFixedSize(52, 52)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.setAutoRaise(False)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setStyleSheet("")
        action = button.defaultAction()
        if action is not None and action.menu() is not None:
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            if action.icon().isNull():
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
                button.setFixedSize(132, 52)

    def _add_action(self, toolbar: QToolBar, action: QAction) -> None:
        toolbar.addAction(action)
        button = toolbar.widgetForAction(action)
        if isinstance(button, QToolButton):
            self._style_button(button)
            button.setAccessibleName(
                action.text().split("\t", 1)[0].replace("&", "").replace("…", "").strip()
            )
            self.buttons.append(button)

    def _build_pages(self) -> None:
        pages = {
            "File": [
                [("new_action"), ("new_folder_action"), ("new_window_action")],
                [("import_file_action"), ("open_external_file_action")],
                [("workspace_tabbed_action"), ("dashboard_action"), ("previous_file_action"), ("next_file_action")],
                [("save_action"), ("save_as_action"), ("save_new_action"), ("save_dashboard_action"), ("save_exit_action")],
                [("duplicate_action"), ("rename_file_action"), ("delete_file_action"), ("external_editor_action"), ("open_document_folder_action"), ("properties_action")],
                [("print_action"), ("export_pdf_action")],
            ],
            "Home": [
                [("cut_action"), ("copy_action"), ("paste_action"), ("paste_plain_action"), ("delete_text_action"), ("select_all_action")],
                [("undo_action"), ("redo_action"), ("duplicate_line_action"), ("delete_line_action"), ("comment_action"), ("find_action"), ("goto_action"), ("replace_action")],
                [("bold_action"), ("italic_action"), ("strike_action"), ("code_tabbed_action")],
                [("bullet_action"), ("number_action"), ("task_action"), ("quote_action"), ("indent_action"), ("outdent_action")],
                [("heading_tabbed_action")],
            ],
            "Insert": [
                [("image_action"), ("link_action"), ("edit_link_action"), ("remove_link_action")],
                [("table_action")],
                [("date_time_action"), ("date_action"), ("time_action")],
                [("rule_action"), ("symbol_action")],
            ],
            "View": [
                [("fullscreen_action"), ("status_bar_action")],
                [("word_wrap_action"), ("line_numbers_action"), ("editor_canvas_theme_action"), ("view_only_action"), ("file_header_action")],
                [("source_only_action"), ("split_action"), ("preview_only_action")],
                [("zoom_in_action"), ("zoom_out_action"), ("zoom_reset_action")],
                [("tab_width_action"), ("display_font_action"), ("preview_font_action")],
            ],
            "Settings": [
                [("collapsed_mode_action")],
                [("theme_light_action"), ("theme_dark_action"), ("theme_system_action")],
                [("list_action"), ("grid_action")],
                [("sidebar_action"), ("left_sidebar_action"), ("right_sidebar_action")],
                [("launch_dashboard_action"), ("launch_last_file_action")],
                [("tabs_enabled_action"), ("tabs_disabled_action")],
                [("dirty_duplicate_tabbed_action"), ("dirty_external_tabbed_action")],
            ],
            "Help": [
                [("docs_action"), ("quick_start_action"), ("shortcuts_action")],
                [("github_action"), ("issue_action")],
                [("about_action")],
            ],
        }

        for name, groups in pages.items():
            page = QWidget(self.tabs)
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(2, 2, 2, 2)
            page_layout.setSpacing(0)
            page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

            toolbar = QToolBar(name, page)
            toolbar.setObjectName(f"markopadTabbed{name}Toolbar")
            toolbar.setMovable(False)
            toolbar.setFloatable(False)
            toolbar.setOrientation(Qt.Orientation.Horizontal)
            toolbar.setIconSize(QSize(36, 36))
            toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            toolbar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            toolbar.setMinimumHeight(56)
            toolbar.setMaximumHeight(56)
            if toolbar.layout() is not None:
                toolbar.layout().setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                toolbar.layout().setContentsMargins(2, 2, 2, 2)
                toolbar.layout().setSpacing(2)

            for index, action_names in enumerate(groups):
                if index:
                    toolbar.addSeparator()
                for action_name in action_names:
                    self._add_action(toolbar, self._a(action_name))

            page_layout.addWidget(toolbar, 0, Qt.AlignmentFlag.AlignTop)
            self.toolbars.append(toolbar)
            self.tabs.addTab(page, name)

    def refresh_theme(self) -> None:
        """Re-polish the persistent command surface without rebuilding it."""
        for button in tuple(self.buttons):
            try:
                self._style_button(button)
                style = button.style()
                style.unpolish(button)
                style.polish(button)
                button.update()
            except RuntimeError:
                continue
        for widget in (self, self.tabs, *self.toolbars):
            try:
                style = widget.style()
                style.unpolish(widget)
                style.polish(widget)
                widget.update()
            except RuntimeError:
                continue

    def cycle_tab(self, step: int) -> None:
        if self.tabs.count():
            self.tabs.setCurrentIndex((self.tabs.currentIndex() + step) % self.tabs.count())

    def set_collapsed(self, collapsed: bool, *, emit: bool = True) -> None:
        collapsed = bool(collapsed)
        if collapsed == self._collapsed:
            return
        self._collapsed = collapsed
        current = self.tabs.currentWidget()
        if collapsed:
            if current is not None:
                current.setVisible(False)
            self._expanded_minimum_height = self.tabs.minimumHeight()
            self._expanded_maximum_height = self.tabs.maximumHeight()
            height = max(self.tabs.tabBar().height(), self.tabs.tabBar().sizeHint().height(), 1) + 2
            self.tabs.setMinimumHeight(height)
            self.tabs.setMaximumHeight(height)
        else:
            self.tabs.setMaximumHeight(self._expanded_maximum_height)
            self.tabs.setMinimumHeight(self._expanded_minimum_height)
            if current is not None:
                current.setVisible(True)
        self.tabs.updateGeometry()
        if emit:
            self.collapsed_changed.emit(collapsed)

    def _sync_collapsed_page(self, _index=None) -> None:
        if self._collapsed and self.tabs.currentWidget() is not None:
            self.tabs.currentWidget().setVisible(False)

    def eventFilter(self, obj, event) -> bool:
        if obj is self.tabs.tabBar():
            if event.type() == QEvent.Type.MouseButtonPress and self._collapsed and event.button() == Qt.MouseButton.LeftButton:
                index = self.tabs.tabBar().tabAt(event.position().toPoint())
                if index >= 0:
                    self.tabs.setCurrentIndex(index)
                    self.set_collapsed(False)
                    return True
            if event.type() == QEvent.Type.MouseButtonDblClick and not self._collapsed and event.button() == Qt.MouseButton.LeftButton and self.tabs.tabBar().tabAt(event.position().toPoint()) >= 0:
                self.set_collapsed(True)
                return True
            if event.type() == QEvent.Type.Wheel:
                delta = event.angleDelta().y()
                if delta and self.tabs.count() > 0:
                    self.cycle_tab(-1 if delta > 0 else 1)
                    return True
        return super().eventFilter(obj, event)
