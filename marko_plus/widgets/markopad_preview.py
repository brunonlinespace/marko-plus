#!/usr/bin/env python3
"""Safe read-only Markdown preview for Markopad."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QByteArray, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QTextBrowser


class MarkdownPreview(QTextBrowser):
    external_link_requested = pyqtSignal(QUrl)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setUndoRedoEnabled(False)
        self.anchorClicked.connect(self._on_anchor_clicked)
        self._document_dir: Path | None = None

    def set_document_path(self, path: str | None) -> None:
        self._document_dir = Path(path).resolve().parent if path else None
        base = QUrl.fromLocalFile(str(self._document_dir) + "/") if self._document_dir else QUrl()
        self.document().setBaseUrl(base)

    def render_markdown(self, markdown: str) -> None:
        # QTextDocument's Markdown parser is presentation only. It never writes
        # back into the source editor or the saved file. Preserve the user's
        # Preview-only display font across re-renders.
        display_font = self.document().defaultFont()
        try:
            self.setMarkdown(str(markdown))
        except (AttributeError, TypeError):
            self.setPlainText(str(markdown))
        self.document().setDefaultFont(display_font)

    def loadResource(self, resource_type, name):  # noqa: N802 - Qt virtual
        url = QUrl(name)
        scheme = url.scheme().lower()
        if scheme in {"http", "https", "ftp", "data"}:
            # Remote/data resources are never fetched implicitly by preview.
            return QByteArray()
        return super().loadResource(resource_type, name)

    def _on_anchor_clicked(self, url: QUrl) -> None:
        if url.scheme().lower() in {"http", "https", "mailto"}:
            self.external_link_requested.emit(url)
            QDesktopServices.openUrl(url)
            return
        if url.isRelative() and self._document_dir:
            candidate = (self._document_dir / url.toString()).resolve()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(candidate)))
            return
        if url.isLocalFile():
            QDesktopServices.openUrl(url)
