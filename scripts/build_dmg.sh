#!/bin/bash
set -euo pipefail
# build_dmg.sh — Create a styled DMG with drag-to-Applications layout.
# Usage: ./scripts/build_dmg.sh [path/to/TodoScope.app]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ASSETS="$PROJECT_ROOT/assets"
APP_PATH="${1:-$PROJECT_ROOT/dist/TodoScope.app}"
VERSION=$(git -C "$PROJECT_ROOT" describe --always --tag 2>/dev/null || echo "dev")
DMG_NAME="TodoScope-${VERSION}.dmg"
DMG_PATH="$PROJECT_ROOT/dist/$DMG_NAME"
VOLUME_NAME="TodoScope"
STAGING="$PROJECT_ROOT/dist/dmg_staging"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run 'make app' first."
    exit 1
fi

echo "Building DMG: $DMG_NAME"

# Clean staging
rm -rf "$STAGING"
mkdir -p "$STAGING"

# Copy app
cp -R "$APP_PATH" "$STAGING/"

# Create Applications symlink
ln -s /Applications "$STAGING/Applications"

# Copy background if it exists
if [ -f "$ASSETS/dmg_background.png" ]; then
    mkdir -p "$STAGING/.background"
    cp "$ASSETS/dmg_background.png" "$STAGING/.background/background.png"
fi

# Create the DMG
rm -f "$DMG_PATH"
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    "$DMG_PATH"

# Clean staging
rm -rf "$STAGING"

echo ""
echo "  ✓ $DMG_PATH"
ls -lh "$DMG_PATH"
