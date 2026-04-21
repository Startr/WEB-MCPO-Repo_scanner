# Release Pipeline Design

> Research notes — 2026-04-21

## What We're Building

A single `make release_finish` (or `scripts/release.sh`) that produces
all distribution artifacts across every channel:

```
git tag v1.0.0
    │
    ├── Docker image → GHCR (ghcr.io/sage-is/repo_scanner:1.0.0)
    ├── Binary (macOS arm64) → GitHub Release attachment
    ├── Binary (macOS x86_64) → GitHub Release attachment
    ├── Mac .app (.dmg) → GitHub Release attachment
    ├── Brew formula SHA256 → homebrew-apps updated
    ├── Brew cask SHA256 → homebrew-apps updated
    └── PyPI package → pypi.org/project/repo-scanner/
```

---

## Git Flow (Already Exists — Extend)

Current flow in Makefile:
```
make patch_release     → git flow release start X.Y.Z+1
  (do work)
make release_finish    → git flow release finish, tag, push
```

**What to add**: Post-tag artifact builds, triggered by GitHub Actions
on tag push, OR locally via Makefile targets.

---

## Phase 1: Prerequisites (Do First)

### 1.1 Add pyproject.toml

```toml
[project]
name = "repo-scanner"
version = "0.1.0"  # or dynamic from git tag
description = "Scan Git repos for TODOs, generate kanban boards"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "flask>=3.1.0",
    "pyyaml",
]

[project.scripts]
repo-scanner = "scanner.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

This unlocks: PyPI publishing, PyInstaller builds, `uv tool install`.

### 1.2 Add CLI entry point

Create `scanner/cli.py`:
```python
"""CLI entry point for repo-scanner."""
import webbrowser
from scanner.app import app

def main():
    port = 5000  # TODO: find free port
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="127.0.0.1", port=port)
```

### 1.3 Handle frozen app paths

Update `scanner/app.py` to detect PyInstaller's frozen state:
```python
import sys, os
if getattr(sys, 'frozen', False):
    # Running as PyInstaller bundle
    _base = sys._MEIPASS
    template_folder = os.path.join(_base, 'scanner', 'templates')
    static_folder = os.path.join(_base, 'scanner', 'static')
else:
    template_folder = None  # use defaults
    static_folder = None
```

### 1.4 Create repo-scanner CLI wrapper script

A bash script for the Docker-based Homebrew formula (like ai-ui):
```bash
#!/bin/bash
# repo-scanner — Docker-wrapped CLI
VERSION="1.0.0"
IMAGE="ghcr.io/sage-is/repo_scanner:latest"
CONTAINER="repo-scanner"
# ... start/stop/update/logs/open/dev/status/nuke commands
```

---

## Phase 2: Local Build Targets (Makefile)

### New Makefile targets:

```makefile
# --- Binary Build Targets ---
PYINSTALLER_ARGS ?= --name repo-scanner \
    --add-data "scanner/templates:scanner/templates" \
    --add-data "scanner/static:scanner/static" \
    --hidden-import=yaml

binary:
    @echo "Building standalone binary with PyInstaller..."
    pipenv run pyinstaller -F $(PYINSTALLER_ARGS) app.py
    @echo "Binary at: dist/repo-scanner"

binary_dir:
    @echo "Building standalone directory with PyInstaller..."
    pipenv run pyinstaller -D $(PYINSTALLER_ARGS) app.py
    @echo "App directory at: dist/repo-scanner/"

# --- Mac .app Target ---
app: binary_dir
    @echo "Wrapping in .app bundle with Platypus..."
    /usr/local/bin/platypus \
        -a "RepoScanner" \
        -o "Web" \
        -i assets/icon.icns \
        -V "$(IMAGE_TAG)" \
        -u "Sage.is" \
        -f dist/repo-scanner/ \
        scripts/launch_app.sh \
        "dist/RepoScanner.app"
    @echo "App at: dist/RepoScanner.app"

# --- DMG Target ---
dmg: app
    @echo "Creating DMG..."
    hdiutil create -volname "RepoScanner" \
        -srcfolder dist/RepoScanner.app \
        -ov -format UDZO \
        "dist/RepoScanner-$(IMAGE_TAG).dmg"
    @echo "DMG at: dist/RepoScanner-$(IMAGE_TAG).dmg"

# --- PyPI Target ---
pypi_build:
    pipenv run python -m build

pypi_publish: pypi_build
    pipenv run twine upload dist/*.whl dist/*.tar.gz
```

---

## Phase 3: GitHub Actions CI/CD

### .github/workflows/release.yml

Triggered on tag push (`v*`). Builds all artifacts in parallel.

```yaml
name: Release
on:
  push:
    tags: ["v*"]

jobs:
  # --- Docker ---
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          push: true
          tags: |
            ghcr.io/sage-is/repo_scanner:${{ github.ref_name }}
            ghcr.io/sage-is/repo_scanner:latest

  # --- macOS Binary ---
  binary-macos:
    strategy:
      matrix:
        os: [macos-14]  # ARM64 (M1+)
        # Add macos-13 for x86_64 if needed
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pyinstaller flask pyyaml
      - run: |
          pyinstaller -F \
            --name repo-scanner \
            --add-data "scanner/templates:scanner/templates" \
            --add-data "scanner/static:scanner/static" \
            --hidden-import=yaml \
            app.py
      - uses: actions/upload-artifact@v4
        with:
          name: repo-scanner-macos-${{ runner.arch }}
          path: dist/repo-scanner

  # --- macOS .app ---
  app-macos:
    runs-on: macos-14
    needs: []  # can run in parallel
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pyinstaller flask pyyaml
      - run: brew install --cask platypus
      # Build onedir first (for .app bundling)
      - run: |
          pyinstaller -D \
            --name repo-scanner \
            --add-data "scanner/templates:scanner/templates" \
            --add-data "scanner/static:scanner/static" \
            --hidden-import=yaml \
            app.py
      # Wrap in .app with Platypus CLI
      - run: |
          /usr/local/bin/platypus \
            -a "RepoScanner" -o "Web" \
            -V "${{ github.ref_name }}" \
            -f dist/repo-scanner/ \
            scripts/launch_app.sh \
            dist/RepoScanner.app
      # Create DMG
      - run: |
          hdiutil create -volname "RepoScanner" \
            -srcfolder dist/RepoScanner.app \
            -ov -format UDZO \
            dist/RepoScanner-${{ github.ref_name }}.dmg
      - uses: actions/upload-artifact@v4
        with:
          name: RepoScanner-dmg
          path: dist/RepoScanner-*.dmg

  # --- PyPI ---
  pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install build twine
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}

  # --- GitHub Release ---
  release:
    needs: [docker, binary-macos, app-macos, pypi]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            repo-scanner-macos-*/repo-scanner
            RepoScanner-dmg/RepoScanner-*.dmg
          generate_release_notes: true

  # --- Update Homebrew Tap ---
  update-brew:
    needs: [release]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: Sage-is/homebrew-apps
          token: ${{ secrets.HOMEBREW_TAP_TOKEN }}
      # Update formula SHA256 and version
      - run: |
          VERSION="${{ github.ref_name }}"
          SHA=$(curl -sL "https://github.com/Sage-is/repo_scanner/archive/refs/tags/${VERSION}.tar.gz" | shasum -a 256 | cut -d' ' -f1)
          sed -i "s|url .*|url \"https://github.com/Sage-is/repo_scanner/archive/refs/tags/${VERSION}.tar.gz\"|" Formula/repo-scanner.rb
          sed -i "s|sha256 .*|sha256 \"${SHA}\"|" Formula/repo-scanner.rb
      # Update cask SHA256 and version
      - run: |
          VERSION="${{ github.ref_name }}"
          DMG_SHA=$(curl -sL "https://github.com/Sage-is/repo_scanner/releases/download/${VERSION}/RepoScanner-${VERSION}.dmg" | shasum -a 256 | cut -d' ' -f1)
          sed -i "s|version .*|version \"${VERSION#v}\"|" Casks/repo-scanner.rb
          sed -i "s|sha256 .*|sha256 \"${DMG_SHA}\"|" Casks/repo-scanner.rb
      - run: |
          git add -A
          git commit -m "Update repo-scanner to ${{ github.ref_name }}"
          git push
```

---

## Phase 4: Homebrew Tap Updates

### Add to homebrew-apps:

1. `Formula/repo-scanner.rb` — Docker CLI wrapper
2. `Casks/repo-scanner.rb` — Mac .app distribution
3. Update `find-formula-candidates` to recognize repo_scanner
4. Add `repo-scanner` to `nuke-sage` KNOWN_PROJECTS array

### Add to homebrew-apps/Makefile:

Extend `scripts/formula-helpers.sh` or add repo-scanner-specific helpers
for SHA256 computation and version bumping.

---

## Release Checklist (Manual Flow)

```
1. make patch_release          # Create release branch
2. (bump version, test)
3. make release_finish         # Tag, merge, push
4. (GitHub Actions runs automatically on tag push)
5. Wait for CI:
   - [ ] Docker image pushed to GHCR
   - [ ] macOS binary built and attached to release
   - [ ] .dmg built and attached to release
   - [ ] PyPI package published
   - [ ] homebrew-apps formula + cask updated
6. Verify:
   - brew install sage-is/apps/repo-scanner
   - brew install --cask sage-is/apps/repo-scanner
   - uv tool install repo-scanner
   - docker run ghcr.io/sage-is/repo_scanner:latest
```

---

## Open Questions

1. **Code signing**: Do we need an Apple Developer ID for notarization?
   (Required for Gatekeeper on macOS 10.15+. Without it, users get
   "unidentified developer" warning. Cost: $99/year Apple Developer Program.)

2. **Universal binary**: Build both ARM64 and x86_64, or ARM64 only?
   (Most new Macs are ARM. Rosetta 2 handles x86_64 binaries on ARM.)

3. **Production WSGI server**: Flask's dev server isn't production-grade.
   Should the binary use Waitress or Gunicorn instead?
   (Waitress is pure Python, cross-platform — good fit.)

4. **Auto-update mechanism**: Should the CLI or .app check for updates?
   (Homebrew handles this for brew-installed versions.)

5. **Linux binary**: Do we also build for Linux? (GitHub Actions can do it
   in the same workflow with an ubuntu runner.)

6. **Windows**: Out of scope for now? (PyInstaller can build .exe on
   Windows runner if needed later.)

---

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Create | Package metadata, entry points |
| `scanner/cli.py` | Create | CLI entry point (start server + open browser) |
| `scanner/app.py` | Modify | Add frozen app path detection |
| `scripts/launch_app.sh` | Create | Platypus launch script |
| `scripts/repo-scanner` | Create | Docker CLI wrapper (like ai-ui) |
| `assets/icon.icns` | Create | App icon |
| `Makefile` | Modify | Add binary/app/dmg/pypi targets |
| `.github/workflows/release.yml` | Create | CI/CD for all artifacts |
| `RepoScanner.platypus` | Create | Platypus profile for reproducible builds |
| (homebrew-apps) `Formula/repo-scanner.rb` | Create | Brew formula |
| (homebrew-apps) `Casks/repo-scanner.rb` | Create | Brew cask |
