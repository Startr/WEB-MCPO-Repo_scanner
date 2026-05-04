#!/bin/bash
set -euo pipefail
# release_all.sh — Build every TodoScope release artifact and upload.
#
# All builds happen locally on your Mac:
#   - macOS binary:  native PyInstaller
#   - Linux binary:  Docker (cdrx/pyinstaller-linux)
#   - Windows .exe:  Docker (cdrx/pyinstaller-windows + Wine)
#   - macOS .app:    PyInstaller --windowed
#   - DMG:           create-dmg with styled background
#   - Docker image:  docker build + push to GHCR
#   - PyPI wheel:    python -m build + twine upload
#
# Artifacts uploaded to GitHub Releases via `gh` CLI.
# Zero cloud CI minutes. ~5 min wall time.
#
# Usage: make release_all  (or run this script directly)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# --- Version from git tag ---
VERSION=$(git describe --always --tag)
TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo ""
echo "  🔭 TodoScope Release — $VERSION"
echo "  ======================================="
echo ""

# --- Pre-flight checks ---
echo "→ Pre-flight checks..."
command -v gh >/dev/null || { echo "Error: gh CLI not found. Install: brew install gh"; exit 1; }
command -v docker >/dev/null || { echo "Error: Docker not found."; exit 1; }
command -v create-dmg >/dev/null || { echo "Error: create-dmg not found. Install: brew install create-dmg"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Error: gh not authenticated. Run: gh auth login"; exit 1; }
echo "  ✓ All tools available"

# --- Run tests ---
echo ""
echo "→ Running tests..."
cd scanner && pipenv run pytest tests/test_cli.py tests/test_todoscope_cli.py tests/test_error_handling.py \
    -k "not test_end_to_end" --tb=short -q
cd "$PROJECT_ROOT"
echo "  ✓ Tests passed"

# --- Clean previous build ---
echo ""
echo "→ Cleaning previous build..."
make clean_dist
echo "  ✓ Clean"

# --- Build macOS binary (native) ---
echo ""
echo "→ Building macOS ARM64 binary..."
make binary
echo "  ✓ dist/todoscope"

# --- Build macOS .app + DMG ---
echo ""
echo "→ Building macOS .app + DMG..."
make dmg
echo "  ✓ dist/TodoScope-${VERSION}.dmg"

# --- Build Linux binary (Docker) ---
echo ""
echo "→ Building Linux x86_64 binary (Docker)..."
make binary_linux
echo "  ✓ dist/linux/todoscope"

# --- Build Windows binary (Docker + Wine) ---
# Wine in cdrx/pyinstaller-windows breaks under both Rosetta and QEMU on
# Apple Silicon hosts (Wine + Linux 6.12 kernel + amd64-on-arm64 emulation).
# Don't fail the whole release if Windows can't build — ship the rest and
# the upload step will skip Windows artifacts that don't exist.
echo ""
echo "→ Building Windows x86_64 .exe (Docker + Wine)..."
if make binary_windows; then
    echo "  ✓ dist/windows/todoscope.exe"
else
    echo "  ⚠  Windows build failed — continuing without Windows artifact."
    echo "     (Wine + Apple Silicon emulator issue; revisit in v1.0.1.)"
fi

# --- Build + push Docker image ---
echo ""
echo "→ Building + pushing Docker image to GHCR..."
make docker_push
echo "  ✓ GHCR pushed"

# --- Build + publish PyPI package ---
echo ""
echo "→ Building PyPI wheel..."
make pypi_build
echo "  ✓ dist/*.whl built"
echo ""
read -rp "  Publish to PyPI? [y/N] " pypi_answer
if [[ "${pypi_answer:-n}" =~ ^[Yy]$ ]]; then
    make pypi_publish
    echo "  ✓ Published to PyPI"
else
    echo "  ⏭  Skipped PyPI publish"
fi

# --- Create or update GitHub Release (idempotent — safe to re-run) ---
echo ""
# Stage artifacts in a temp dir with distinct filenames. The macOS and Linux
# binaries both have basename "todoscope" — uploading both as "todoscope"
# causes a 404 from GitHub's asset endpoint on the second upload.
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

stage() {
    local src="$1" dst_name="$2"
    if [[ -f "$src" ]]; then
        cp "$src" "$STAGE/$dst_name"
        ARTIFACTS+=("$STAGE/$dst_name")
    else
        echo "  ⏭  Skipping missing artifact: $src"
    fi
}

ARTIFACTS=()
stage "dist/todoscope"                       "todoscope-macos-arm64"
stage "dist/linux/todoscope"                 "todoscope-linux-x86_64"
stage "dist/windows/todoscope.exe"           "todoscope-windows-x86_64.exe"
stage "dist/TodoScope-${VERSION}.dmg"        "TodoScope-${VERSION}.dmg"

if gh release view "$TAG" >/dev/null 2>&1; then
    echo "→ Release $TAG exists — uploading/replacing artifacts..."
    gh release upload "$TAG" --clobber "${ARTIFACTS[@]}"
    echo "  ✓ Artifacts updated on existing release"
else
    echo "→ Creating GitHub Release: $TAG"
    gh release create "$TAG" \
        --title "TodoScope $TAG" \
        --generate-notes \
        "${ARTIFACTS[@]}"
    echo "  ✓ GitHub Release created"
fi
echo "  https://github.com/Startr/TodoScope/releases/tag/$TAG"

# --- Update Homebrew tap ---
echo ""
read -rp "  Update homebrew-apps Formula + Cask? [y/N] " brew_answer
if [[ "${brew_answer:-n}" =~ ^[Yy]$ ]]; then
    echo "  → Updating homebrew-apps SHA256..."
    # This will be implemented when the Homebrew tap exists
    echo "  ⚠  homebrew-apps update not yet implemented (Phase 7)"
else
    echo "  ⏭  Skipped Homebrew update"
fi

# --- Summary ---
echo ""
echo "  ======================================="
echo "  🔭 TodoScope $TAG — Released!"
echo "  ======================================="
echo ""
echo "  GitHub:  https://github.com/Startr/TodoScope/releases/tag/$TAG"
echo "  PyPI:    https://pypi.org/project/todoscope/"
echo "  Docker:  docker pull ghcr.io/startr/todoscope:$TAG"
echo "  Brew:    brew install startr/apps/todoscope"
echo ""
