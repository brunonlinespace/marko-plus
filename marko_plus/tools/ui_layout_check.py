#!/usr/bin/env python3
"""Static Marko Plus exp2 command-surface/dashboard checks."""
from pathlib import Path


def require(source: str, fragments: tuple[str, ...], label: str) -> None:
    missing = [item for item in fragments if item not in source]
    if missing:
        raise SystemExit(f"Missing {label}: {missing}")


def main() -> int:
    package = Path(__file__).resolve().parents[1]
    window = (package / "widgets/main_window.py").read_text(encoding="utf-8")
    shell = (package / "widgets/shell_ribbon.py").read_text(encoding="utf-8")
    page = (package / "widgets/editor_page.py").read_text(encoding="utf-8")
    card = (package / "widgets/dashboard_card.py").read_text(encoding="utf-8")
    folder = (package / "widgets/folder_dashboard.py").read_text(encoding="utf-8")

    require(window, (
        'self.shell_ribbon = ShellRibbon(',
        'bar.addMenu("&Markdown")',
        'bar.addMenu("&Insert")',
        'apply_theme(QApplication.instance(), theme)',
    ), "Markopad MainWindow action/menu/theme wiring")
    require(shell, (
        '"File": [', '"Home": [', '"Insert": [', '"View": [', '"Settings": [', '"Help": [',
        'button.setFixedSize(52, 52)', 'button.setIconSize(QSize(36, 36))',
        'self.tabs.tabBar().installEventFilter(self)',
        'toolbar.setMinimumHeight(56)', 'toolbar.setMaximumHeight(56)',
    ), "Markopad ShellRibbon presentation")
    if 'addMenu("&Run")' in window or 'addMenu("Run")' in window:
        raise SystemExit("The obsolete Run menu must not remain in Marko Plus.")

    require(page, (
        'self.preview = MarkdownPreview(self)',
        'self.content_splitter.addWidget(self.editor)',
        'self.content_splitter.addWidget(self.preview)',
        'def set_view_mode(self, mode: str',
        'self.preview.render_markdown(self.editor.toPlainText())',
        'self.search_frame.hide()',
    ), "Markopad editor/preview surface")
    for obsolete in ('QPushButton("Launch")', 'QPushButton("In Terminal")', 'QPushButton("As Admin")', 'QPushButton("Make Exec")'):
        if obsolete in page:
            raise SystemExit(f"Obsolete editor-page control remains: {obsolete}")

    require(card, (
        'self.edit_button = self._button("Edit"',
        'self.split_button = self._button("Split View"',
        'self.preview_button = self._button("Preview"',
        'selected_requested = pyqtSignal(object)',
        'def mouseDoubleClickEvent',
        'self.open_requested.emit(self.module)',
    ), "Dashboard Edit/Split/Preview controls")
    order = [card.index(x) for x in (
        'self.edit_button = self._button("Edit"',
        'self.split_button = self._button("Split View"',
        'self.preview_button = self._button("Preview"',
    )]
    if order != sorted(order):
        raise SystemExit("Dashboard controls must be Edit | Split View | Preview.")
    if 'QPushButton("Open Terminal")' in folder:
        raise SystemExit("Folder-dashboard terminal control must not remain in Marko Plus.")

    print("Marko Plus exp2 UI layout checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
