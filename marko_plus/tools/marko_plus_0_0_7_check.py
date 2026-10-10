#!/usr/bin/env python3
"""Static/runtime-light contract check for Marko Plus 0.0.7 no-clobber New File convergence."""
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from marko_plus.services.file_io import FileStateChangedError, install_new_file_from_temp

ROOT = Path(__file__).resolve().parents[1]
controller = (ROOT / "controllers/file_actions.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
errors: list[str] = []


def require(fragment: str, text: str, message: str) -> None:
    if fragment not in text:
        errors.append(message)


require('APP_VERSION = "0.0.7"', init, "0.0.7 package identity missing")
create_start = controller.index('    def create_file(')
create_end = controller.index('    def create_folder(', create_start)
create_block = controller[create_start:create_end]

# Exact Rico-derived New File installation pattern, adapted only to an empty Markdown payload.
require('if destination.exists():', create_block, "existing New File pre-check changed")
require('temporary: Path | None = None', create_block, "New File temporary staging is missing")
require('descriptor: int | None = None', create_block, "New File descriptor lifecycle is missing")
require('suffix=".creating"', create_block, "New File .creating staging suffix is missing")
require('with os.fdopen(descriptor, "wb") as handle:', create_block, "New File staging write is missing")
require('handle.flush()', create_block, "New File staging flush is missing")
require('os.fsync(handle.fileno())', create_block, "New File staging fsync is missing")
require('install_new_file_from_temp(temporary, destination)', create_block, "exclusive/no-replace New File install is missing")
require('fsync_directory(folder)', create_block, "New File destination directory synchronization is missing")
if 'destination.write_text("", encoding="utf-8")' in create_block:
    errors.append("unsafe exists() -> write_text() New File path remains")

# 0.0.6 Duplicate convergence remains in place.
duplicate_start = controller.index('    def duplicate_module(')
duplicate_end = controller.index('    def create_file(', duplicate_start)
duplicate_block = controller[duplicate_start:duplicate_end]
require('suffix=".duplicating"', duplicate_block, "0.0.6 Duplicate staging changed")
require('install_new_file_from_temp(temporary, destination)', duplicate_block, "0.0.6 no-clobber Duplicate install changed")

# Exercise the shared exclusive installer with the exact empty payload used by New File.
with tempfile.TemporaryDirectory(prefix="marko-plus-007-") as raw:
    folder = Path(raw)
    temporary = folder / ".new.md.creating"
    destination = folder / "new.md"
    temporary.write_bytes(b"")
    install_new_file_from_temp(temporary, destination)
    if destination.read_bytes() != b"":
        errors.append("New File no longer installs an empty Markdown payload")

    raced_temp = folder / ".raced.md.creating"
    raced_destination = folder / "raced.md"
    raced_temp.write_bytes(b"")
    raced_destination.write_bytes(b"existing bytes")
    try:
        install_new_file_from_temp(raced_temp, raced_destination)
    except FileStateChangedError:
        pass
    else:
        errors.append("exclusive New File installer did not refuse an occupied destination")
    if raced_destination.read_bytes() != b"existing bytes":
        errors.append("existing New File destination bytes were changed")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.7 no-clobber New File convergence check passed.")
