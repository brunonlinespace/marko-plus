# Building Marko Plus

## Source environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r marko_plus/requirements.txt
python main.py
```

## Static validation

```bash
python -m marko_plus.tools.release_check
```

The release check does not import PyQt6, so it can run before the build
environment is created.

## Fedora 43/44 AppImage

```bash
./marko_plus/packaging/fedora/install-build-deps.sh
./marko_plus/packaging/fedora/build-appimage.sh
```

Run the builder as the normal desktop user. The dependency helper invokes
`sudo dnf`; do not invoke the builder itself with `sudo`. Controlled root-based
CI containers may explicitly set `MARKO_PLUS_ALLOW_ROOT_BUILD=1`.

Expected output:

```text
marko_plus/dist/Marko-Plus-0.0.9-x86_64.AppImage
marko_plus/dist/Marko-Plus-0.0.9-x86_64.AppImage.sha256
marko_plus/dist/Marko-Plus-0.0.9-x86_64.build-info.txt
marko_plus/dist/Marko-Plus-0.0.9-x86_64.build-python-lock.txt
```

The builder validates source identity and provenance, creates an isolated
virtual environment, builds a PyInstaller one-folder bundle, assembles and
validates the AppDir, then emits the AppImage and checksums.

Test the identical artifact on the intended XFCE, Plasma, and Wayland targets.
