#!/usr/bin/env python3
"""Static contract check for Marko Plus 0.0.1-r6 About correction."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
about = (ROOT / "widgets/about_dialog.py").read_text(encoding="utf-8")
init = (ROOT / "__init__.py").read_text(encoding="utf-8")
manifest = (ROOT / "marko-plus.json").read_text(encoding="utf-8")
errors = []

def require(fragment, text, message):
    if fragment not in text:
        errors.append(message)

require('APP_VERSION = "0.0.1-r6"', init, "r6 identity missing")
require('APP_TAGLINE = "Friendly. Fast. Focused."', about, "new slogan missing")
require('"tagline": "Friendly. Fast. Focused."', manifest, "manifest slogan missing")
require("f\"<a href='{GITHUB_URL}'>{GITHUB_URL}</a><br>\"", about, "Marko Plus repository link missing from primary About position")
require("[<a href='https://github.com/brunonlinespace/'>", about, "brunonlinespace profile link missing")
require('f"<b>Configuration:</b> {configuration_path}<br><br>"', about, "Configuration label missing")
if '<b>Preferences:</b>' in about:
    errors.append("About dialog regressed to Preferences label")

if errors:
    for error in errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)
print("Marko Plus 0.0.1-r6 About contract check passed.")
