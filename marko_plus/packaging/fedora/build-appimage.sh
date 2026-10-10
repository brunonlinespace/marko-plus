#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

# Marko Plus Fedora AppImage builder aligned with Suite Pythoine's current
# non-privileged packaging contract. System dependencies are checked here but
# never installed by the builder; use the separate dependency helper manually.

APP_NAME="Marko Plus"
APP_ID="marko-plus"
APP_VERSION="0.4.17"
PUBLISHER_ID="brunonlinespace"
SUITE_DESKTOP_ID="marko-plus"
APPSTREAM_ID="io.github.brunonlinespace.marko_plus"
OUTPUT_STEM="Marko-Plus"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROGRAM_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
PROJECT_ROOT="$(cd -- "$PROGRAM_ROOT/.." && pwd -P)"
SOURCE_ENTRY="$PROJECT_ROOT/main.py"
COMPONENT_MANIFEST="$PROJECT_ROOT/suite-pythoine-component.json"
PROJECT_MANIFEST="$PROGRAM_ROOT/marko-plus.json"
SOURCE_MANIFEST="$PROGRAM_ROOT/SOURCE_MANIFEST.sha256"
RUNTIME_REQUIREMENTS="$PROGRAM_ROOT/requirements.txt"
BUILD_REQUIREMENTS="$PROGRAM_ROOT/packaging/pyinstaller/build-requirements.txt"
PYINSTALLER_SPEC="$PROGRAM_ROOT/packaging/pyinstaller/marko-plus.spec"
APPIMAGE_PAYLOAD="$PROGRAM_ROOT/packaging/appimage"
RELEASE_CHECK="$PROGRAM_ROOT/tools/release_check.py"
MAIN_WINDOW="$PROGRAM_ROOT/widgets/main_window.py"

HOST_ARCH_RAW="$(uname -m)"
case "$HOST_ARCH_RAW" in
    x86_64) HOST_ARCH="x86_64" ;;
    aarch64|arm64) HOST_ARCH="aarch64" ;;
    *) printf 'Error: unsupported build architecture: %s\n' "$HOST_ARCH_RAW" >&2; exit 2 ;;
esac
ARCH="${ARCH:-$HOST_ARCH}"

FEDORA_RELEASE="unknown"
HOST_NAME="unknown Linux"
OS_ID="unknown"
if [[ -r /etc/os-release ]]; then
    mapfile -d '' -t OS_RELEASE_VALUES < <(
        set +u
        # shellcheck disable=SC1091
        source /etc/os-release
        printf '%s\0%s\0%s\0' "${ID:-unknown}" "${VERSION_ID:-unknown}" "${PRETTY_NAME:-unknown Linux}"
    )
    OS_ID="${OS_RELEASE_VALUES[0]:-unknown}"
    FEDORA_RELEASE="${OS_RELEASE_VALUES[1]:-unknown}"
    HOST_NAME="${OS_RELEASE_VALUES[2]:-unknown Linux}"
fi

BUILD_ROOT="${BUILD_ROOT:-$PROGRAM_ROOT/build/appimage-fedora${FEDORA_RELEASE}-${ARCH}}"
VENV="$BUILD_ROOT/venv"
PYI_DIST="$BUILD_ROOT/pyinstaller-dist"
PYI_WORK="$BUILD_ROOT/pyinstaller-work"
APPDIR="$BUILD_ROOT/MarkoPlus.AppDir"
SMOKE_HOME="$BUILD_ROOT/smoke-home"
DIST_DIR="${OUTPUT_DIR:-$PROGRAM_ROOT/dist}"
CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/marko-plus-appimage-tools"
APPIMAGE="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.AppImage"
SHA_FILE="${APPIMAGE}.sha256"
BUILD_INFO="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.build-info.txt"
PYTHON_LOCK="$DIST_DIR/${OUTPUT_STEM}-${APP_VERSION}-${ARCH}.build-python-lock.txt"
APPIMAGETOOL_RESOLVED=""
MAX_TOOL_BYTES=$((200 * 1024 * 1024))

export PYTHONDONTWRITEBYTECODE=1

log() { printf '\n==> %s\n' "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
require_file() { [[ -f "$1" ]] || die "Missing file: $1"; }

validate_build_root() {
    local allowed_root resolved_root
    allowed_root="$(readlink -m -- "$PROGRAM_ROOT/build")"
    resolved_root="$(readlink -m -- "$BUILD_ROOT")"
    [[ "$resolved_root" != "$allowed_root" ]] \
        || die "BUILD_ROOT must be a child directory beneath ${allowed_root}; refusing to remove the build root itself."
    case "$resolved_root" in
        "$allowed_root"/*) ;;
        *) die "Unsafe BUILD_ROOT outside ${allowed_root}: ${resolved_root}" ;;
    esac
}

clean_source_python_caches() {
    while IFS= read -r -d '' cache_dir; do
        rm -rf -- "$cache_dir"
    done < <(
        find "$PROJECT_ROOT" \
            \( -path "$PROJECT_ROOT/.git" -o -path "$PROJECT_ROOT/.venv" -o -path "$PROJECT_ROOT/venv" \
               -o -path "$PROGRAM_ROOT/build" -o -path "$PROGRAM_ROOT/dist" \) -prune \
            -o -type d -name '__pycache__' -print0
    )
    while IFS= read -r -d '' bytecode_file; do
        rm -f -- "$bytecode_file"
    done < <(
        find "$PROJECT_ROOT" \
            \( -path "$PROJECT_ROOT/.git" -o -path "$PROJECT_ROOT/.venv" -o -path "$PROJECT_ROOT/venv" \
               -o -path "$PROGRAM_ROOT/build" -o -path "$PROGRAM_ROOT/dist" \) -prune \
            -o -type f \( -name '*.pyc' -o -name '*.pyo' \) -print0
    )
}

cleanup() {
    rm -rf "$SMOKE_HOME"
    clean_source_python_caches
}
trap cleanup EXIT

check_non_privileged_policy() {
    if grep -Eq '^[[:space:]]*(sudo|dnf|pkexec|su)([[:space:]]|$)' "$0"; then
        die "Privilege-elevation or host-package-install command detected in builder."
    fi
}

check_host_prerequisites() {
    log "Checking non-privileged host prerequisites"
    local missing=() command_name
    for command_name in python3 bash timeout sha256sum od stat find grep cp ln chmod install mktemp \
        rm mkdir mv tr awk date uname readlink sort env; do
        command -v "$command_name" >/dev/null 2>&1 || missing+=("$command_name")
    done
    if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
        missing+=("curl-or-wget")
    fi
    if ((${#missing[@]})); then
        die "Missing required host command(s): ${missing[*]}. The builder will not install system packages; provide them and rerun."
    fi
    python3 - <<'PYVENV' >/dev/null 2>&1 || \
        die "This Python cannot create virtual environments. Provide Python with venv/ensurepip support and rerun."
import ensurepip, venv
PYVENV
}

validate_component_manifest() {
    python3 - "$COMPONENT_MANIFEST" "$APP_ID" "$APP_NAME" "$APP_VERSION" "$SUITE_DESKTOP_ID" <<'PYMANIFEST'
import json
from pathlib import Path
import sys
path = Path(sys.argv[1])
expected_id, expected_name, expected_version, expected_desktop = sys.argv[2:]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Invalid Suite Pythoine component manifest: {exc}")
expected = {
    "id": expected_id,
    "name": expected_name,
    "version": expected_version,
    "component_kind": "extension",
    "desktop_id": expected_desktop,
    "publisher_id": "brunonlinespace",
    "repository": "https://github.com/brunonlinespace/marko-plus",
    "tagline": "Friendly. Fast. Focused.",
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit(f"Suite component manifest mismatch for {key}: {data.get(key)!r} != {value!r}")
if data.get("portable_command") != ["main.py"]:
    raise SystemExit('Suite component manifest must declare portable_command ["main.py"]')
if data.get("extensions") != []:
    raise SystemExit("Marko Plus is a Suite Extension and must not declare document-routing extensions")
if data.get("capabilities") != {"routing": False, "open": False, "create": False}:
    raise SystemExit("Marko Plus Suite capabilities must remain routing/open/create false")
PYMANIFEST
}

validate_project_manifest() {
    python3 - "$PROJECT_MANIFEST" "$APP_NAME" "$APP_ID" "$APP_VERSION" "$PUBLISHER_ID" "$SUITE_DESKTOP_ID" <<'PYIDENT'
import json
from pathlib import Path
import sys
path = Path(sys.argv[1])
name, app_id, version, publisher, desktop_id = sys.argv[2:]
data = json.loads(path.read_text(encoding="utf-8"))
expected = {
    "name": name,
    "id": app_id,
    "version": version,
    "publisher_id": publisher,
    "desktop_id": desktop_id,
    "repository": "https://github.com/brunonlinespace/marko-plus",
    "tagline": "Friendly. Fast. Focused.",
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit(f"Project manifest mismatch for {key}: {data.get(key)!r} != {value!r}")
PYIDENT
}

check_inputs() {
    validate_build_root
    if (( EUID == 0 )) && [[ "${MARKO_PLUS_ALLOW_ROOT_BUILD:-0}" != "1" ]]; then
        die "Do not run the Marko Plus AppImage builder with sudo/root."
    fi
    case "$ARCH" in x86_64|aarch64) ;; *) die "Unsupported AppImage architecture: ${ARCH}" ;; esac
    [[ "$ARCH" == "$HOST_ARCH" ]] \
        || die "Requested ${ARCH}, but host is ${HOST_ARCH_RAW}; cross-building is unsupported."
    if [[ "$OS_ID" != "fedora" || ! "$FEDORA_RELEASE" =~ ^(43|44)$ ]]; then
        if [[ "${MARKO_PLUS_ALLOW_UNSUPPORTED_HOST:-0}" != "1" ]]; then
            die "Validated for Fedora 43/44. Detected ${HOST_NAME}. Set MARKO_PLUS_ALLOW_UNSUPPORTED_HOST=1 only for intentional testing."
        fi
        printf 'Warning: continuing on unsupported host: %s\n' "$HOST_NAME" >&2
    fi

    for path in \
        "$SOURCE_ENTRY" "$COMPONENT_MANIFEST" "$PROJECT_MANIFEST" "$SOURCE_MANIFEST" \
        "$RUNTIME_REQUIREMENTS" "$BUILD_REQUIREMENTS" "$PYINSTALLER_SPEC" "$RELEASE_CHECK" "$MAIN_WINDOW" \
        "$APPIMAGE_PAYLOAD/AppRun" "$APPIMAGE_PAYLOAD/marko-plus.desktop" \
        "$APPIMAGE_PAYLOAD/${APPSTREAM_ID}.metainfo.xml" \
        "$PROGRAM_ROOT/LICENSE" "$PROGRAM_ROOT/docs/README.md" "$PROGRAM_ROOT/docs/RELEASE_NOTES.md" \
        "$PROGRAM_ROOT/assets/icons/markopad.png"; do
        require_file "$path"
    done

    validate_component_manifest
    validate_project_manifest

    grep -Fq 'from PyQt6.QtPrintSupport import QPrintDialog, QPrinter' "$MAIN_WINDOW" \
        || die "Marko Plus PrintSupport dependency contract changed; review AppImage bundle validation."
    grep -Fq 'QPrinter.OutputFormat.PdfFormat' "$MAIN_WINDOW" \
        || die "Marko Plus Export PDF implementation changed; review AppImage bundle validation."
}

run_source_release_qa() {
    log "Running Marko Plus source release gate"
    PYTHONDONTWRITEBYTECODE=1 python3 "$RELEASE_CHECK"
}

validate_desktop_entry_basic() {
    local desktop="$1"
    grep -Fqx '[Desktop Entry]' "$desktop" || die "Invalid desktop entry: $desktop"
    grep -Eq '^Type=Application$' "$desktop" || die "Desktop Entry requires Type=Application"
    grep -Eq '^Name=Marko Plus$' "$desktop" || die "Desktop Entry requires Name=Marko Plus"
    grep -Eq '^Exec=marko-plus %f$' "$desktop" || die "Desktop Entry requires single-file Exec=marko-plus %f"
    grep -Eq '^Icon=marko-plus$' "$desktop" || die "Desktop Entry requires Icon=marko-plus"
    grep -Eq '^MimeType=text/markdown;$' "$desktop" || die "Desktop Entry must advertise only text/markdown"
}

validate_appstream_basic() {
    local metainfo="$1"
    python3 - "$metainfo" "$APP_VERSION" <<'PYXML'
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
root = ET.parse(Path(sys.argv[1])).getroot()
version = sys.argv[2]
def text(tag):
    node = root.find(tag)
    return (node.text or "").strip() if node is not None else ""
assert text("id") == "io.github.brunonlinespace.marko_plus"
assert text("name") == "Marko Plus"
assert text("project_license") == "GPL-3.0-or-later"
assert text("launchable[@type='desktop-id']") == "marko-plus.desktop"
developer = root.find("developer[@id='io.github.brunonlinespace']")
assert developer is not None and (developer.findtext("name") or "").strip() == "Bruno Machado"
urls = {node.attrib.get("type"): (node.text or "").strip() for node in root.findall("url")}
assert urls.get("homepage") == "https://github.com/brunonlinespace/marko-plus"
assert urls.get("bugtracker") == "https://github.com/brunonlinespace/marko-plus/issues"
assert root.find("content_rating[@type='oars-1.1']") is not None
binaries = {(node.text or "").strip() for node in root.findall("./provides/binary")}
assert binaries == {"marko-plus"}, binaries
assert {(node.text or "").strip() for node in root.findall("./provides/mediatype")} == {"text/markdown"}
releases = root.findall("./releases/release")
assert len(releases) == 1 and releases[0].attrib.get("version") == version
PYXML
}

prepare_environment() {
    log "Preparing isolated build environment"
    rm -rf "$BUILD_ROOT"
    clean_source_python_caches
    mkdir -p "$BUILD_ROOT" "$DIST_DIR" "$CACHE_DIR"
    chmod 0700 "$CACHE_DIR"
    python3 -m venv "$VENV"
    "$VENV/bin/python" -m pip install --disable-pip-version-check --upgrade pip wheel setuptools
    "$VENV/bin/python" -m pip install --disable-pip-version-check \
        -r "$RUNTIME_REQUIREMENTS" -r "$BUILD_REQUIREMENTS"
    PYTHONPYCACHEPREFIX="$BUILD_ROOT/pycache" \
        "$VENV/bin/python" -m compileall -q -x '/(build|dist)/' "$SOURCE_ENTRY" "$PROGRAM_ROOT"
    "$VENV/bin/python" -m pip check
    "$VENV/bin/python" -m pip freeze --all > "$PYTHON_LOCK"
}

freeze_application() {
    log "Freezing Marko Plus with PyInstaller"
    "$VENV/bin/python" -m PyInstaller \
        --clean --noconfirm \
        --distpath "$PYI_DIST" \
        --workpath "$PYI_WORK" \
        "$PYINSTALLER_SPEC"
    [[ -x "$PYI_DIST/marko-plus/marko-plus" ]] \
        || die "PyInstaller executable was not created: $PYI_DIST/marko-plus/marko-plus"

    local version_output
    version_output="$(QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "$PYI_DIST/marko-plus/marko-plus" --version)"
    [[ "$version_output" == "${APP_NAME} ${APP_VERSION}" ]] \
        || die "Frozen executable version mismatch: ${version_output}"
}

assemble_appdir() {
    log "Assembling AppDir"
    rm -rf "$APPDIR"
    mkdir -p \
        "$APPDIR/usr/bin" \
        "$APPDIR/usr/lib/marko-plus" \
        "$APPDIR/usr/share/applications" \
        "$APPDIR/usr/share/icons/hicolor/512x512/apps" \
        "$APPDIR/usr/share/metainfo" \
        "$APPDIR/usr/share/doc/marko-plus"

    cp -a "$PYI_DIST/marko-plus/." "$APPDIR/usr/lib/marko-plus/"
    ln -s ../lib/marko-plus/marko-plus "$APPDIR/usr/bin/marko-plus"

    install -m 0755 "$APPIMAGE_PAYLOAD/AppRun" "$APPDIR/AppRun"
    install -m 0644 "$APPIMAGE_PAYLOAD/marko-plus.desktop" "$APPDIR/marko-plus.desktop"
    install -m 0644 "$APPIMAGE_PAYLOAD/marko-plus.desktop" "$APPDIR/usr/share/applications/marko-plus.desktop"
    install -m 0644 "$APPIMAGE_PAYLOAD/${APPSTREAM_ID}.metainfo.xml" \
        "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"
    install -m 0644 "$PROGRAM_ROOT/assets/icons/markopad.png" \
        "$APPDIR/usr/share/icons/hicolor/512x512/apps/marko-plus.png"
    install -m 0644 "$PROGRAM_ROOT/assets/icons/markopad.png" "$APPDIR/marko-plus.png"
    ln -s marko-plus.png "$APPDIR/.DirIcon"

    install -m 0644 "$PROGRAM_ROOT/LICENSE" "$APPDIR/usr/share/doc/marko-plus/LICENSE"
    install -m 0644 "$PROGRAM_ROOT/docs/README.md" "$APPDIR/usr/share/doc/marko-plus/README.md"
    install -m 0644 "$PROGRAM_ROOT/docs/RELEASE_NOTES.md" "$APPDIR/usr/share/doc/marko-plus/RELEASE_NOTES.md"
    chmod 0755 "$APPDIR/usr/lib/marko-plus/marko-plus"

    validate_desktop_entry_basic "$APPDIR/marko-plus.desktop"
    validate_desktop_entry_basic "$APPDIR/usr/share/applications/marko-plus.desktop"
    validate_appstream_basic "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"
    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$APPDIR/marko-plus.desktop"
        desktop-file-validate "$APPDIR/usr/share/applications/marko-plus.desktop"
    else
        printf 'Info: desktop-file-validate unavailable; built-in checks passed.\n' >&2
    fi
    if command -v appstreamcli >/dev/null 2>&1; then
        appstreamcli validate --no-net "$APPDIR/usr/share/metainfo/${APPSTREAM_ID}.metainfo.xml"
    else
        printf 'Info: appstreamcli unavailable; built-in AppStream checks passed.\n' >&2
    fi
}

prepare_smoke_home() {
    rm -rf "$SMOKE_HOME"
    mkdir -p "$SMOKE_HOME/.config" "$SMOKE_HOME/.cache" "$SMOKE_HOME/.local/share" "$SMOKE_HOME/Documents"
}

run_version_smoke_test() {
    local label="$1"; shift
    local log_file status expected="${APP_NAME} ${APP_VERSION}"
    prepare_smoke_home
    log_file="$(mktemp "${TMPDIR:-/tmp}/marko-plus-version.XXXXXX.log")"
    log "Running ${label} version smoke test"
    set +e
    timeout 30s env \
        HOME="$SMOKE_HOME" \
        XDG_CONFIG_HOME="$SMOKE_HOME/.config" \
        XDG_CACHE_HOME="$SMOKE_HOME/.cache" \
        XDG_DATA_HOME="$SMOKE_HOME/.local/share" \
        QT_QPA_PLATFORM=offscreen \
        QT_QUICK_BACKEND=software \
        "$@" --version >"$log_file" 2>&1
    status=$?
    set -e
    if [[ "$status" -ne 0 ]] || ! grep -Fxq "$expected" "$log_file"; then
        cat "$log_file" >&2
        rm -f "$log_file"
        die "${label} version smoke test failed with exit code ${status}."
    fi
    rm -f "$log_file"
}

validate_bundle() {
    log "Validating Marko Plus Qt bundle"
    find "$APPDIR/usr/lib/marko-plus" -name 'libqxcb.so' -print -quit | grep -q . \
        || die "Qt XCB platform plugin was not bundled."
    find "$APPDIR/usr/lib/marko-plus" \
        \( -name 'libqwayland*.so' -o -name '*wayland*.so' \) -print -quit | grep -q . \
        || printf 'Warning: Qt Wayland plugin was not detected; test XWayland carefully.\n' >&2
    find "$APPDIR/usr/lib/marko-plus" \
        \( -name '*Qt6PrintSupport*' -o -name '*QtPrintSupport*' \) -print -quit | grep -q . \
        || die "Qt PrintSupport was not bundled; Marko Plus Print/Export PDF requires it."

    # Do not transplant negative payload rules from other Pythoine applications.
    # Marko Plus has no QtPdf reader or QtWebEngine dependency contract; incidental
    # transitive Qt libraries are not treated as a functional build failure here.
    run_version_smoke_test "AppDir" "$APPDIR/AppRun"
}

elf_sanity_check() {
    local tool="$1" magic size
    require_file "$tool"
    size="$(stat -c %s "$tool")"
    [[ "$size" -gt 0 && "$size" -le "$MAX_TOOL_BYTES" ]] \
        || die "appimagetool invalid size: ${size} bytes."
    magic="$(od -An -tx1 -N4 "$tool" | tr -d ' \n')"
    [[ "$magic" == "7f454c46" ]] || die "appimagetool is not an ELF executable: $tool"
}

download_tool() {
    local url="$1" destination="$2" part="${2}.part"
    [[ "$url" == https://* ]] || die "appimagetool URL must use HTTPS."
    rm -f "$part"
    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 --fail --location --retry 3 --retry-all-errors \
            --connect-timeout 30 --max-time 300 --max-filesize "$MAX_TOOL_BYTES" \
            --output "$part" "$url"
    else
        wget --https-only --tries=3 --timeout=30 --output-document="$part" "$url"
    fi
    [[ -f "$part" ]] || die "appimagetool download produced no file."
    elf_sanity_check "$part"
    chmod 0755 "$part"
    mv -f "$part" "$destination"
}

prepare_appimagetool() {
    local tool url
    mkdir -p "$CACHE_DIR"
    chmod 0700 "$CACHE_DIR"
    if [[ -n "${APPIMAGETOOL_PATH:-}" ]]; then
        tool="$(readlink -f -- "$APPIMAGETOOL_PATH")"
        [[ -x "$tool" ]] || die "APPIMAGETOOL_PATH is not executable: $tool"
        log "Using appimagetool supplied through APPIMAGETOOL_PATH"
    elif [[ -n "${APPIMAGETOOL:-}" ]]; then
        tool="$(readlink -f -- "$APPIMAGETOOL")"
        [[ -x "$tool" ]] || die "APPIMAGETOOL is not executable: $tool"
        log "Using appimagetool supplied through APPIMAGETOOL"
    elif command -v appimagetool >/dev/null 2>&1; then
        tool="$(command -v appimagetool)"
        log "Using appimagetool from PATH"
    else
        tool="$CACHE_DIR/appimagetool-${ARCH}.AppImage"
        url="${APPIMAGETOOL_URL:-https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage}"
        if [[ ! -x "$tool" ]]; then
            log "Downloading official appimagetool"
            download_tool "$url" "$tool"
        else
            log "Using cached appimagetool"
        fi
    fi
    elf_sanity_check "$tool"
    if [[ -n "${APPIMAGETOOL_SHA256:-}" ]]; then
        [[ "$APPIMAGETOOL_SHA256" =~ ^[[:xdigit:]]{64}$ ]] \
            || die "APPIMAGETOOL_SHA256 must be 64 hexadecimal characters."
        printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$tool" | sha256sum --check --status \
            || die "appimagetool SHA-256 verification failed."
    elif [[ "${MARKO_PLUS_RELEASE_BUILD:-0}" == "1" ]]; then
        die "MARKO_PLUS_RELEASE_BUILD=1 requires APPIMAGETOOL_SHA256."
    else
        printf 'Warning: APPIMAGETOOL_SHA256 not supplied; resolved hash will be recorded.\n' >&2
    fi
    APPIMAGETOOL_RESOLVED="$tool"
}

build_appimage() {
    prepare_appimagetool
    log "Creating ${APPIMAGE##*/}"
    rm -f "$APPIMAGE" "$SHA_FILE"
    ARCH="$ARCH" VERSION="$APP_VERSION" \
        "$APPIMAGETOOL_RESOLVED" --appimage-extract-and-run "$APPDIR" "$APPIMAGE"
    [[ -s "$APPIMAGE" ]] || die "appimagetool did not create expected output."
    chmod 0755 "$APPIMAGE"
    run_version_smoke_test "final AppImage" "$APPIMAGE" --appimage-extract-and-run
    (cd "$DIST_DIR" && sha256sum "${APPIMAGE##*/}" > "${SHA_FILE##*/}")
}

write_build_info() {
    {
        echo "Marko Plus AppImage build"
        echo "Version: ${APP_VERSION}"
        echo "Architecture: ${ARCH}"
        echo "Release mode: ${MARKO_PLUS_RELEASE_BUILD:-0}"
        echo "Built: $(date --iso-8601=seconds)"
        echo "Host: ${HOST_NAME}"
        echo "Fedora release: ${FEDORA_RELEASE}"
        echo "Privilege policy: non-privileged; no sudo/dnf/su/pkexec in builder"
        echo "System Python: $(python3 --version 2>&1)"
        echo "Build Python: $("$VENV/bin/python" --version 2>&1)"
        echo "PyInstaller: $("$VENV/bin/python" -m PyInstaller --version)"
        "$VENV/bin/python" - <<'PYVERS'
from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
print(f"PyQt6: {PYQT_VERSION_STR}")
print(f"Qt: {QT_VERSION_STR}")
PYVERS
        echo "main.py SHA-256: $(sha256sum "$SOURCE_ENTRY" | awk '{print $1}')"
        echo "Suite component manifest SHA-256: $(sha256sum "$COMPONENT_MANIFEST" | awk '{print $1}')"
        echo "Project manifest SHA-256: $(sha256sum "$PROJECT_MANIFEST" | awk '{print $1}')"
        echo "SOURCE_MANIFEST.sha256 SHA-256: $(sha256sum "$SOURCE_MANIFEST" | awk '{print $1}')"
        echo "Runtime requirements SHA-256: $(sha256sum "$RUNTIME_REQUIREMENTS" | awk '{print $1}')"
        echo "Build requirements SHA-256: $(sha256sum "$BUILD_REQUIREMENTS" | awk '{print $1}')"
        echo "PyInstaller spec SHA-256: $(sha256sum "$PYINSTALLER_SPEC" | awk '{print $1}')"
        echo "Builder SHA-256: $(sha256sum "$0" | awk '{print $1}')"
        echo "appimagetool: ${APPIMAGETOOL_RESOLVED}"
        echo "appimagetool SHA-256: $(sha256sum "$APPIMAGETOOL_RESOLVED" | awk '{print $1}')"
        echo "Output: ${APPIMAGE##*/}"
        echo "Output SHA-256: $(sha256sum "$APPIMAGE" | awk '{print $1}')"
        echo "Suite classification: Extension; no routing/open/create capabilities"
        echo "Qt dependency check: XCB + PrintSupport required; no QtPdf reader/WebEngine dependency rule imposed"
        echo "Runtime QA: frozen executable, AppDir, and final AppImage exact-version smoke PASS"
        echo "Interactive GUI QA: available separately through packaging/fedora/test-appimage.sh"
        echo "Source cleanliness: __pycache__/pyc/pyo removed before QA/build and at exit"
    } > "$BUILD_INFO"
}

main() {
    check_non_privileged_policy
    check_host_prerequisites
    check_inputs
    clean_source_python_caches
    run_source_release_qa
    clean_source_python_caches
    prepare_environment
    freeze_application
    assemble_appdir
    validate_bundle
    build_appimage
    write_build_info
    clean_source_python_caches
    log "Build complete"
    printf 'AppImage: %s\nChecksum: %s\nBuild information: %s\nPython lock: %s\n' \
        "$APPIMAGE" "$SHA_FILE" "$BUILD_INFO" "$PYTHON_LOCK"
}

main "$@"
