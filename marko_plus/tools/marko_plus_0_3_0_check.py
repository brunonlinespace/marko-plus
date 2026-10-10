#!/usr/bin/env python3
"""Dependency-free Marko Plus 0.3.0 open-document survival release gate."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import types
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent
errors: list[str] = []


def req(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def src(relative: str) -> str:
    return (PACKAGE / relative).read_text(encoding="utf-8")


def sha(relative: str) -> str:
    return hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest()


repo = src("models/module_repository.py")
manager = src("controllers/editor_manager.py")
page = src("widgets/editor_page.py")
monitor = src("services/open_document_monitor.py")
init = src("__init__.py")
constants = src("app_constants.py")

req('APP_VERSION = "0.3.0"' in init, "0.3.0 package identity missing")
req('APP_REVISION = "0.3.0"' in constants, "0.3.0 revision identity missing")
req("if current is not None and current.loaded:" in repo, "loaded scan-retention rule missing")
req("Workspace discovery does not own the lifetime of a live editor" in repo, "retention rationale missing")

for fragment in (
    "class OpenDocumentMonitor(QObject):",
    "self._watcher = QFileSystemWatcher(self)",
    "self._paths_by_parent: dict[Path, set[Path]]",
    "self._pending_direct: set[Path]",
    "self._pending_parent: set[Path]",
    "info = os.stat(path, follow_symlinks=True)",
    "if path in direct or current != before:",
    "self.path_changed.emit(path)",
):
    req(fragment in monitor, f"shared monitor contract missing: {fragment}")
for forbidden in ("os.scandir(", ".iterdir(", ".rglob(", "request_rescan("):
    req(forbidden not in monitor, f"open-document monitor performs forbidden scanning: {forbidden}")
req(monitor.count("QFileSystemWatcher(self)") == 1, "monitor must own exactly one QFileSystemWatcher")

for fragment in (
    "self.open_document_monitor = OpenDocumentMonitor(self)",
    "self.open_document_monitor.register(module.path)",
    "self.open_document_monitor.rebind(old_path, target.path)",
    "self.open_document_monitor.unregister(closed_path)",
    "repository.module_path_changed.connect(self._on_managed_path_changed)",
    "for _path, state in tuple(self.states):",
    "page.handle_backing_path_event()",
    "if not module.external and not module.path.exists():",
):
    req(fragment in manager, f"EditorManager survival lifecycle missing: {fragment}")

for fragment in (
    'self._backing_state = "normal"',
    'if self._backing_state == "missing":',
    "def handle_backing_path_event(self) -> None:",
    'self._set_backing_state("missing")',
    'self.reload_external_button.setEnabled(False)',
    "This file is no longer available at its original disk path.",
    "def _confirm_close_missing_backing(self) -> bool:",
    '"Save Version As…"',
    '"Recreate Original…"',
    '"Close Without Saving"',
):
    req(fragment in page, f"EditorPage missing-backing contract missing: {fragment}")

# Existing workspace scanning remains untouched from 0.2.6.
req(sha("services/filesystem_watcher.py") == "cfc9d7575eacb67a8323e8e11cf561afe22fbee10427c4d3eb3ab1971e20c893",
    "workspace filesystem watcher changed during 0.3.0")
req(sha("services/module_scanner.py") == "a84b710caa66b69754169852c80706ce0ac4b1394d117be80c91a526ae10dc2f",
    "workspace scanner changed during 0.3.0")

sys.path.insert(0, str(ROOT))
try:
    import PyQt6.QtCore  # noqa: F401
except ModuleNotFoundError:
    class _SignalInstance:
        def __init__(self): self._slots = []
        def connect(self, slot): self._slots.append(slot)
        def emit(self, *args):
            for slot in tuple(self._slots): slot(*args)
    class _SignalDescriptor:
        def __set_name__(self, owner, name): self._name = f"__qa_signal_{name}"
        def __get__(self, obj, owner):
            if obj is None: return self
            signal = getattr(obj, self._name, None)
            if signal is None:
                signal = _SignalInstance(); setattr(obj, self._name, signal)
            return signal
    class _QObject:
        def __init__(self, parent=None): self.parent = parent
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtcore.QObject = _QObject
    qtcore.pyqtSignal = lambda *_a, **_k: _SignalDescriptor()
    pyqt6 = types.ModuleType("PyQt6"); pyqt6.QtCore = qtcore
    sys.modules["PyQt6"] = pyqt6; sys.modules["PyQt6.QtCore"] = qtcore

from marko_plus.models.module import Module
from marko_plus.models.module_repository import ModuleRepository

with tempfile.TemporaryDirectory(prefix="marko-plus-030-") as directory:
    path = Path(directory) / "survivor.md"
    path.write_text("survivor\n", encoding="utf-8")
    info = path.stat()
    repository = ModuleRepository()
    module = repository.add(Module(
        path=path, filename=path.name, display_name="Survivor", folder="",
        created=info.st_ctime, modified=info.st_mtime, size=info.st_size,
    ))
    module.loaded = True
    path.unlink()
    repository.replace_all([])
    req(repository.get(path) is module, "actual scan removed a loaded missing document")
    module.loaded = False
    repository.replace_all([])
    req(repository.get(path) is None, "closed missing document did not retire on discovery")

if errors:
    print("Marko Plus 0.3.0 check failed:")
    for error in errors: print("- " + error)
    raise SystemExit(1)
print("PASS: Marko Plus 0.3.0 open-document survival contract")
