# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Low-cost monitoring for backing paths of live editor pages only.

This service is deliberately separate from the workspace scanner. It never
walks a directory and never requests a workspace rescan. A single
QFileSystemWatcher is shared by all open documents, parent-directory watches
are deduplicated, and parent events perform only cheap stat() comparisons on
registered children before asking an EditorPage to do an exact content check.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QObject, QFileSystemWatcher, QTimer, pyqtSignal


Fingerprint = tuple[int, int, int, int] | None


class OpenDocumentMonitor(QObject):
    """Watch only the backing paths of currently open documents."""

    path_changed = pyqtSignal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        debounce_ms: int = 125,
    ) -> None:
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watcher.directoryChanged.connect(self._on_directory_changed)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(max(50, int(debounce_ms)))
        self._timer.timeout.connect(self._drain_pending)

        self._fingerprints: dict[Path, Fingerprint] = {}
        self._paths_by_parent: dict[Path, set[Path]] = {}
        self._pending_direct: set[Path] = set()
        self._pending_parent: set[Path] = set()

    @staticmethod
    def _normalize(path: str | Path) -> Path:
        return Path(path).expanduser().resolve(strict=False)

    @staticmethod
    def _fingerprint(path: Path) -> Fingerprint:
        """Return cheap identity/metadata only; never read or hash file content."""
        try:
            info = os.stat(path, follow_symlinks=True)
        except OSError:
            return None
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)

    def register(self, path: str | Path) -> None:
        """Start protecting one live document path."""
        normalized = self._normalize(path)
        if normalized not in self._fingerprints:
            self._fingerprints[normalized] = self._fingerprint(normalized)
            self._paths_by_parent.setdefault(normalized.parent, set()).add(normalized)
        else:
            self._fingerprints[normalized] = self._fingerprint(normalized)
        self._ensure_parent_watch(normalized.parent)
        self._ensure_file_watch(normalized)

    def unregister(self, path: str | Path) -> None:
        normalized = self._normalize(path)
        self._fingerprints.pop(normalized, None)
        self._pending_direct.discard(normalized)
        self._pending_parent.discard(normalized)

        direct = str(normalized)
        if direct in self._watcher.files():
            self._watcher.removePath(direct)

        parent = normalized.parent
        children = self._paths_by_parent.get(parent)
        if children is not None:
            children.discard(normalized)
            if not children:
                self._paths_by_parent.pop(parent, None)
                parent_text = str(parent)
                if parent_text in self._watcher.directories():
                    self._watcher.removePath(parent_text)

    def rebind(self, old_path: str | Path, new_path: str | Path) -> None:
        old_normalized = self._normalize(old_path)
        new_normalized = self._normalize(new_path)
        if old_normalized == new_normalized:
            self.refresh(new_normalized)
            return
        self.unregister(old_normalized)
        self.register(new_normalized)

    def refresh(self, path: str | Path) -> None:
        """Refresh the cheap baseline after an intentional in-app file change."""
        normalized = self._normalize(path)
        if normalized not in self._fingerprints:
            return
        self._fingerprints[normalized] = self._fingerprint(normalized)
        self._ensure_parent_watch(normalized.parent)
        self._ensure_file_watch(normalized)

    def clear(self) -> None:
        active = self._watcher.files() + self._watcher.directories()
        if active:
            self._watcher.removePaths(active)
        self._fingerprints.clear()
        self._paths_by_parent.clear()
        self._pending_direct.clear()
        self._pending_parent.clear()
        self._timer.stop()

    def _ensure_parent_watch(self, parent: Path) -> None:
        text = str(parent)
        if parent.is_dir() and text not in self._watcher.directories():
            self._watcher.addPath(text)

    def _ensure_file_watch(self, path: Path) -> None:
        text = str(path)
        if path.is_file() and text not in self._watcher.files():
            self._watcher.addPath(text)

    def _on_file_changed(self, raw_path: str) -> None:
        path = self._normalize(raw_path)
        if path not in self._fingerprints:
            return
        # A direct file notification always earns an exact page-level check.
        self._pending_direct.add(path)
        self._timer.start()

    def _on_directory_changed(self, raw_parent: str) -> None:
        parent = self._normalize(raw_parent)
        for path in self._paths_by_parent.get(parent, ()):
            self._pending_parent.add(path)
        if self._pending_parent:
            self._timer.start()

    def _drain_pending(self) -> None:
        direct = set(self._pending_direct)
        candidates = direct | self._pending_parent
        self._pending_direct.clear()
        self._pending_parent.clear()

        for path in tuple(candidates):
            if path not in self._fingerprints:
                continue
            before = self._fingerprints[path]
            current = self._fingerprint(path)
            self._fingerprints[path] = current

            # QFileSystemWatcher commonly drops a file watch after delete,
            # rename-away, or atomic replacement. The parent watch lets us
            # restore it as soon as the exact pathname exists again.
            self._ensure_parent_watch(path.parent)
            self._ensure_file_watch(path)

            if path in direct or current != before:
                self.path_changed.emit(path)
