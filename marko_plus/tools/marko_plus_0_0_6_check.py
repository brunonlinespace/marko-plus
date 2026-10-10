#!/usr/bin/env python3
"""Static/runtime-light contract check for Marko Plus 0.0.6 no-clobber Duplicate convergence."""
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


require('APP_VERSION = "0.0.6"', init, "0.0.6 package identity missing")
require('if path_lexists(destination):', controller, "Duplicate does not reject lexisting destinations")
require('suffix=".duplicating"', controller, "Duplicate staging temporary is missing")
require('install_new_file_from_temp(temporary, destination)', controller, "exclusive/no-replace Duplicate install is missing")
require('fsync_directory(destination.parent)', controller, "Duplicate destination directory synchronization is missing")
require('payload = page.current_markdown_payload()', controller, "live dirty Duplicate payload path changed")
require('shutil.copy2(stored.path, temporary)', controller, "last-saved Duplicate path no longer stages the stored Markdown file")

# Phase 1 Point 5 remains parked: New File must still be the 0.0.5 implementation.
create_start = controller.index('    def create_file(')
create_end = controller.index('    def create_folder(', create_start)
create_block = controller[create_start:create_end]
require('destination.write_text("", encoding="utf-8")', create_block, "New File implementation changed in 0.0.6")
if 'install_new_file_from_temp' in create_block:
    errors.append("later no-clobber New File implementation was pulled into 0.0.6")

# Exercise the already-shared installer directly: an occupied destination must survive unchanged.
with tempfile.TemporaryDirectory(prefix="marko-plus-006-") as raw:
    folder = Path(raw)
    temporary = folder / ".copy.duplicating"
    destination = folder / "copy.md"
    temporary.write_bytes(b"new duplicate bytes")
    destination.write_bytes(b"existing bytes")
    try:
        install_new_file_from_temp(temporary, destination)
    except FileStateChangedError:
        pass
    else:
        errors.append("exclusive installer did not refuse an existing destination")
    if destination.read_bytes() != b"existing bytes":
        errors.append("existing destination bytes were changed")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.6 no-clobber Duplicate convergence check passed.")
