#!/bin/bash
set -euo pipefail
# build_dmg_assets.sh — Generate DMG background image + app icon using macOS native tools.
# No external dependencies required (uses sips, iconutil, Python/Pillow fallback).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ASSETS="$PROJECT_ROOT/assets"

mkdir -p "$ASSETS"

# ─── App Icon (.icns from telescope emoji) ──────────────────────────────────

generate_icon() {
    echo "Generating todoscope.icns from 🔭 emoji..."
    local ICONSET="$ASSETS/todoscope.iconset"
    mkdir -p "$ICONSET"

    # Use Python to render the emoji at various sizes
    python3 -c "
import subprocess, os

iconset = '$ICONSET'
sizes = [16, 32, 64, 128, 256, 512, 1024]

for size in sizes:
    # Create an HTML page with the emoji centered, then screenshot it
    # Simpler approach: use sips to create colored squares, overlay text
    pass

# Fallback: create simple colored icon with text
try:
    from PIL import Image, ImageDraw, ImageFont
    for size in sizes:
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Dark blue circle background
        margin = size // 10
        draw.ellipse([margin, margin, size-margin, size-margin], fill='#1a1a2e')
        # Try to render emoji or fallback to 'T'
        try:
            font_size = int(size * 0.55)
            font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', font_size)
            text = '🔭'
        except Exception:
            font_size = int(size * 0.5)
            try:
                font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', font_size)
            except Exception:
                font = ImageFont.load_default()
            text = 'T'
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (size - tw) // 2
        y = (size - th) // 2
        draw.text((x, y), text, font=font, fill='white')

        # Save standard and @2x versions
        img.save(os.path.join(iconset, f'icon_{size}x{size}.png'))
        if size <= 512:
            img_2x = img.resize((size*2, size*2), Image.LANCZOS)
            img_2x.save(os.path.join(iconset, f'icon_{size}x{size}@2x.png'))
    print('  Icon PNGs generated via Pillow')
except ImportError:
    # No Pillow — create simple solid color icons with sips
    import subprocess
    for size in sizes:
        # Create a blank PNG
        subprocess.run([
            'python3', '-c',
            f'''
import struct, zlib, os
def create_png(w, h, color, path):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(\">I\", len(data)) + c + struct.pack(\">I\", zlib.crc32(c) & 0xffffffff)
    raw = b\"\"
    for y in range(h):
        raw += b\"\\x00\" + bytes(color) * w
    return b\"\\x89PNG\\r\\n\\x1a\\n\" + chunk(b\"IHDR\", struct.pack(\">IIBBBBB\", w, h, 8, 2, 0, 0, 0)) + chunk(b\"IDAT\", zlib.compress(raw)) + chunk(b\"IEND\", b\"\")
with open(\"{iconset}/icon_{size}x{size}.png\", \"wb\") as f:
    f.write(create_png({size}, {size}, (26, 26, 46), f.name))
'''
        ], check=True)
    print('  Icon PNGs generated via raw PNG (no Pillow)')
"

    # Convert iconset to icns
    if [ -d "$ICONSET" ] && ls "$ICONSET"/*.png >/dev/null 2>&1; then
        iconutil -c icns "$ICONSET" -o "$ASSETS/todoscope.icns" 2>/dev/null && {
            echo "  Created: $ASSETS/todoscope.icns"
            rm -rf "$ICONSET"
        } || {
            echo "  Warning: iconutil failed — keeping iconset directory"
        }
    fi
}

# ─── DMG Background Image ──────────────────────────────────────────────────

generate_dmg_background() {
    echo "Generating DMG background image..."
    local BG="$ASSETS/dmg_background.png"
    local WIDTH=660
    local HEIGHT=400

    python3 -c "
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print('  Pillow not installed — skipping DMG background.')
    print('  Install with: pipenv install --dev Pillow')
    exit(0)

width, height = $WIDTH, $HEIGHT
img = Image.new('RGBA', (width, height), '#f5f5f7')
draw = ImageDraw.Draw(img)

# Title
try:
    title_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 22)
    small_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 14)
    arrow_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 48)
except Exception:
    title_font = ImageFont.load_default()
    small_font = title_font
    arrow_font = title_font

# Header
draw.text((width // 2, 40), '🔭 TodoScope', font=title_font, fill='#1a1a2e', anchor='mt')
draw.text((width // 2, 70), 'See every TODO across all your projects', font=small_font, fill='#666', anchor='mt')

# Arrow in the center pointing right
draw.text((width // 2, height // 2 + 10), '⟶', font=arrow_font, fill='#999', anchor='mm')

# Labels under icon positions
draw.text((width // 4, height - 60), 'TodoScope.app', font=small_font, fill='#333', anchor='mt')
draw.text((3 * width // 4, height - 60), 'Applications', font=small_font, fill='#333', anchor='mt')

# Subtle border
draw.rectangle([0, 0, width-1, height-1], outline='#e0e0e0')

img.save('$BG')
print('  Created: $BG')
"
}

# ─── Run ────────────────────────────────────────────────────────────────────

generate_icon
generate_dmg_background

echo ""
echo "Done. Assets in: $ASSETS/"
ls -lh "$ASSETS"/*.icns "$ASSETS"/*.png 2>/dev/null || true
