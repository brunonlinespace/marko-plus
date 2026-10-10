# Marko Plus Packaging

## Fedora 43/44 native x86_64/aarch64 AppImage

```bash
./marko_plus/packaging/fedora/install-build-deps.sh
./marko_plus/packaging/fedora/build-appimage.sh
```

Run the build as your normal user. The dependency installer uses `sudo`
internally; do not invoke `build-appimage.sh` with `sudo`.

Expected artifacts:

```text
marko_plus/dist/Marko-Plus-0.4.17-x86_64.AppImage
marko_plus/dist/Marko-Plus-0.4.17-x86_64.AppImage.sha256
marko_plus/dist/Marko-Plus-0.4.17-x86_64.build-info.txt
marko_plus/dist/Marko-Plus-0.4.17-x86_64.build-python-lock.txt
```

Test an artifact with:

```bash
./marko_plus/packaging/fedora/test-appimage.sh marko_plus/dist/Marko-Plus-0.4.17-x86_64.AppImage
```

The build uses a clean virtual environment and pinned PyInstaller and
PyInstaller-hooks versions from `packaging/pyinstaller/build-requirements.txt`. Runtime PyQt6 constraints are
in `marko_plus/requirements.txt`.

Read `BUILDING.md` before creating a public release. Build-host desktop
integration must not be allowed to become an undeclared application dependency.

The shared Fedora scripts recognize releases 43 and 44. The `fedora43` and
`fedora44` directories contain compatibility wrappers only.

The source release check runs before creation of the build virtual environment.
Generated build areas and ordinary local Python caches are excluded from
working-tree hygiene failures. Cache files still fail validation if they are
actually tracked by Git.
