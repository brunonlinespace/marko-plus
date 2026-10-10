# Marko Plus
# Copyright (C) 2026 Bruno Machado
# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared application identity and metadata."""

from marko_plus import (
    APP_ID,
    APP_NAME as SUITE_APP_NAME,
    APP_VERSION,
    DESKTOP_ID,
    PUBLISHER_ID,
)

# Visible product branding and canonical Suite/package identity are Marko Plus.
APP_INTERNAL_NAME = "marko-plus"
APP_BRAND_NAME = "Marko Plus"
APP_DISPLAY_NAME = APP_BRAND_NAME
APP_WINDOW_TITLE = APP_DISPLAY_NAME
APP_RUNTIME_DESKTOP_ID = DESKTOP_ID
APP_REVISION = "0.4.17"

ORGANIZATION_NAME = "brunonlinespace"
ORGANIZATION_DOMAIN = "github.com/brunonlinespace"

MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown", ".mdown", ".mkd"})
MARKDOWN_FILE_GLOB = "*.md *.markdown *.mdown *.mkd"

GITHUB_URL = "https://github.com/brunonlinespace/marko-plus"
ISSUES_URL = f"{GITHUB_URL}/issues"
