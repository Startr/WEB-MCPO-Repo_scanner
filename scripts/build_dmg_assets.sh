#!/bin/bash
set -euo pipefail
# build_dmg_assets.sh — Generate polished DMG background + app icon.
# Requires Pillow (pipenv install --dev Pillow).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ASSETS="$PROJECT_ROOT/assets"

mkdir -p "$ASSETS"

# ─── App Icon (.icns — macOS rounded-rect style) ───────────────────────────

generate_icon() {
    echo "Generating todoscope.icns..."
    local ICONSET="$ASSETS/todoscope.iconset"
    rm -rf "$ICONSET"
    mkdir -p "$ICONSET"

    export ICONSET="$ICONSET"
    python3 << 'PYEOF'
import os, math
from PIL import Image, ImageDraw, ImageFont

iconset = os.environ["ICONSET"]
sizes = [16, 32, 64, 128, 256, 512, 1024]

def draw_rounded_rect(draw, xy, radius, fill):
    """Draw a rounded rectangle."""
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*radius, y0 + 2*radius], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*radius, y0, x1, y0 + 2*radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*radius, x0 + 2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*radius, y1 - 2*radius, x1, y1], 0, 90, fill=fill)

def make_icon(size):
    """Create a single icon at the given size."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # macOS icon inset (icons don't fill the full canvas)
    inset = max(1, size // 16)
    s = size - 2 * inset
    radius = max(1, int(s * 0.22))  # macOS uses ~22% corner radius

    # Gradient background: deep navy to dark blue-purple
    for y in range(s):
        t = y / max(1, s - 1)
        r = int(18 + t * 20)   # 18 → 38
        g = int(18 + t * 8)    # 18 → 26
        b = int(48 + t * 30)   # 48 → 78
        draw.line([(inset, inset + y), (inset + s - 1, inset + y)], fill=(r, g, b, 255))

    # Mask to rounded rect
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    draw_rounded_rect(mask_draw, [inset, inset, inset + s, inset + s], radius, fill=255)
    img.putalpha(mask)

    # Re-draw on masked image
    final = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    final.paste(img, (0, 0), mask=img)
    draw = ImageDraw.Draw(final)

    # Telescope symbol — use emoji font at large sizes, fallback at small
    emoji_drawn = False
    if size >= 64:
        try:
            font_size = int(s * 0.55)
            font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', font_size)
            text = '🔭'
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (size - tw) // 2
            y = (size - th) // 2 - int(s * 0.02)
            draw.text((x, y), text, font=font)
            emoji_drawn = True
        except Exception:
            pass

    if not emoji_drawn:
        # Draw a simple telescope shape with lines for small sizes
        cx, cy = size // 2, size // 2
        # Telescope body (angled line)
        lw = max(1, size // 12)
        # Main tube
        x1, y1 = inset + int(s * 0.25), inset + int(s * 0.65)
        x2, y2 = inset + int(s * 0.72), inset + int(s * 0.28)
        draw.line([(x1, y1), (x2, y2)], fill='white', width=lw)
        # Eyepiece (wider end)
        draw.ellipse([x2 - lw, y2 - lw, x2 + lw*2, y2 + lw*2], fill='#aaccff')
        # Lens (narrow end)
        draw.ellipse([x1 - lw//2, y1 - lw//2, x1 + lw, y1 + lw], fill='#6699cc')
        # Tripod legs
        base_x, base_y = cx, inset + int(s * 0.50)
        draw.line([(base_x, base_y), (inset + int(s * 0.20), inset + int(s * 0.85))], fill='#cccccc', width=max(1, lw // 2))
        draw.line([(base_x, base_y), (inset + int(s * 0.80), inset + int(s * 0.85))], fill='#cccccc', width=max(1, lw // 2))

    # Subtle inner glow at the top edge
    if size >= 128:
        for y_off in range(min(3, size // 100 + 1)):
            alpha = 30 - y_off * 10
            if alpha > 0:
                draw.line(
                    [(inset + radius, inset + y_off + 1), (inset + s - radius, inset + y_off + 1)],
                    fill=(255, 255, 255, alpha)
                )

    return final

for size in sizes:
    icon = make_icon(size)
    icon.save(os.path.join(iconset, f'icon_{size}x{size}.png'))
    if size <= 512:
        icon_2x = make_icon(size * 2)
        icon_2x.save(os.path.join(iconset, f'icon_{size}x{size}@2x.png'))

print('  Icon PNGs generated')
PYEOF

    # Convert iconset → icns
    if [ -d "$ICONSET" ] && ls "$ICONSET"/*.png >/dev/null 2>&1; then
        iconutil -c icns "$ICONSET" -o "$ASSETS/todoscope.icns" 2>/dev/null && {
            echo "  Created: $ASSETS/todoscope.icns"
            rm -rf "$ICONSET"
        } || {
            echo "  Warning: iconutil failed — keeping iconset for manual review"
        }
    fi
}

# ─── DMG Background Image ──────────────────────────────────────────────────

generate_dmg_background() {
    echo "Generating DMG background..."
    local BG="$ASSETS/dmg_background.png"
    # Standard DMG window: 660×400 fits the two-icon layout nicely
    local WIDTH=660
    local HEIGHT=400

    export BG_PATH="$BG"
    python3 << 'PYEOF'
import os
from PIL import Image, ImageDraw, ImageFont

width, height = 660, 400
bg_path = os.environ["BG_PATH"]
img = Image.new('RGBA', (width, height))
draw = ImageDraw.Draw(img)

# Gradient background — light gray to white, subtle
for y in range(height):
    t = y / (height - 1)
    v = int(245 + t * 10)  # 245 → 255
    draw.line([(0, y), (width, y)], fill=(v, v, v + min(2, int(t*3)), 255))

# Load fonts
try:
    title_font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 24)
    subtitle_font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 13)
    label_font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 12)
    arrow_font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 60)
    instr_font = ImageFont.truetype('/System/Library/Fonts/SFNS.ttf', 15)
except Exception:
    try:
        title_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 24)
        subtitle_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 13)
        label_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 12)
        arrow_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 60)
        instr_font = ImageFont.truetype('/System/Library/Fonts/SFCompact.ttf', 15)
    except Exception:
        title_font = subtitle_font = label_font = arrow_font = instr_font = ImageFont.load_default()

# ── Header area ──
draw.text((width // 2, 32), '🔭 TodoScope', font=title_font, fill='#1d1d1f', anchor='mt')
draw.text((width // 2, 64), 'See every TODO across all your projects', font=subtitle_font, fill='#86868b', anchor='mt')

# ── Thin separator line ──
draw.line([(60, 90), (width - 60, 90)], fill='#d2d2d7', width=1)

# ── Main install area ──
# Icon positions (centered vertically in the remaining space)
icon_y = 175  # center of icon area
left_x = width // 4       # app icon position
right_x = 3 * width // 4  # Applications position

# App icon placeholder circle (the actual .app icon shows in Finder)
r = 40
draw.ellipse([left_x - r, icon_y - r, left_x + r, icon_y + r], fill='#1a1a2e', outline='#2a2a4e', width=2)
# Mini telescope in the circle
try:
    emoji_font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', 36)
    draw.text((left_x, icon_y), '🔭', font=emoji_font, anchor='mm')
except Exception:
    draw.text((left_x, icon_y), 'T', font=title_font, fill='white', anchor='mm')

# Applications folder icon placeholder
draw.rounded_rectangle([right_x - 38, icon_y - 32, right_x + 38, icon_y + 28], radius=8, fill='#5aadff', outline='#3d8bda', width=2)
# Folder flap
draw.rounded_rectangle([right_x - 38, icon_y - 32, right_x - 4, icon_y - 18], radius=4, fill='#4a9def', outline='#3d8bda', width=1)
# "A" on the folder
draw.text((right_x, icon_y + 2), 'A', font=title_font, fill='white', anchor='mm')

# Labels under icons
draw.text((left_x, icon_y + r + 14), 'TodoScope', font=label_font, fill='#3c3c43', anchor='mt')
draw.text((right_x, icon_y + 36), 'Applications', font=label_font, fill='#3c3c43', anchor='mt')

# ── The arrow ──
# Draw a proper arrow: line with arrowhead
arrow_y = icon_y
arrow_left = left_x + r + 20
arrow_right = right_x - 50

# Arrow shaft
draw.line([(arrow_left, arrow_y), (arrow_right, arrow_y)], fill='#86868b', width=3)
# Arrowhead
head_size = 12
draw.polygon([
    (arrow_right + head_size, arrow_y),
    (arrow_right - 2, arrow_y - head_size),
    (arrow_right - 2, arrow_y + head_size),
], fill='#86868b')

# ── Instruction text ──
draw.text((width // 2, height - 70), 'Drag to install', font=instr_font, fill='#6e6e73', anchor='mt')

# ── Bottom branding ──
draw.text((width // 2, height - 30), 'startr.cloud', font=label_font, fill='#aeaeb2', anchor='mt')

img.save(bg_path)
print(f'  Created: {bg_path}')
PYEOF

}

# ─── Run ────────────────────────────────────────────────────────────────────

generate_icon
generate_dmg_background

echo ""
echo "Done. Assets in: $ASSETS/"
ls -lh "$ASSETS"/*.icns "$ASSETS"/*.png 2>/dev/null || true
