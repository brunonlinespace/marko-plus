#!/usr/bin/env python3
"""One-way compatibility helper for old Ricopad Rich Markdown envelopes.

Markopad never creates this metadata and never decodes the hidden rich snapshot.
It only exposes the portable Markdown body so saving can produce a clean file.
"""
from __future__ import annotations

import re

PROFILE_MARKER = "<!-- ricopad: rich-markdown-v1 -->"
_PAYLOAD_RE = re.compile(
    r"(?:\n{0,2})<!-- ricopad-rich-payload-v1\s*\n"
    r"sha256:[0-9a-fA-F]{64}\s*\n"
    r"encoding:zlib\+base64\s*\n"
    r"[A-Za-z0-9+/=\r\n]+?\s*\n-->\s*$",
    re.DOTALL,
)


def strip_legacy_envelope(text: str) -> tuple[str, bool]:
    value = str(text)
    found = False
    if value.startswith(PROFILE_MARKER):
        found = True
        value = value[len(PROFILE_MARKER):]
        if value.startswith("\n"):
            value = value[1:]
    match = _PAYLOAD_RE.search(value)
    if match:
        found = True
        value = value[:match.start()]
        # Ricopad's portable body convention ended with one LF.
        value = value.rstrip("\n") + "\n"
    return value, found
