#!/bin/bash
set -euo pipefail
# generate_emoji_icon.sh — Render an emoji as a macOS .icns app icon.
#
# Uses a canvas-to-receiver pattern: a tiny Python HTTP server serves an HTML
# page that renders the emoji on a <canvas>, then POSTs the PNG blob back to
# the server. The browser auto-closes after sending. No screen recording
# permissions, no Playwright, no npm. Just Python stdlib + any browser.
#
# Reusable for any browser-rendered asset (social cards, badges, OG images).
#
# Usage: ./scripts/generate_emoji_icon.sh [emoji] [output.icns]
#   Default: 🔭 → assets/todoscope.icns

EMOJI="${1:-🔭}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT="${2:-$PROJECT_ROOT/assets/todoscope.icns}"
PORT=9999
TMPDIR="$(mktemp -d)"
RAW_PNG="$TMPDIR/icon_raw.png"
ICONSET="$TMPDIR/todoscope.iconset"

# Cleanup temp dir on exit
trap "rm -rf '$TMPDIR'" EXIT

echo ""
echo "  🔭 Emoji Icon Generator"
echo "  ========================"
echo "  Emoji:  $EMOJI"
echo "  Output: $OUTPUT"
echo ""

# ── The Python server + HTML renderer (all in one file) ───────────────────
# Serves the canvas page, receives the PNG blob, processes into .icns.

python3 << PYEOF
"""
Tiny HTTP server that:
  GET  /         → serves HTML page (renders emoji on canvas, POSTs blob back)
  POST /receive  → saves PNG, responds with window.close(), shuts down
"""
import http.server
import os
import subprocess
import sys
import threading
import time
import webbrowser

PORT = $PORT
EMOJI = "$EMOJI"
RAW_PNG = "$RAW_PNG"
ICONSET = "$ICONSET"
OUTPUT = "$OUTPUT"

# ── Flag: set when we receive the PNG ──
received = threading.Event()

# ── HTML page: renders emoji on canvas, POSTs blob to /receive ──
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Generating icon...</title>
<style>
  body { margin:0; display:flex; align-items:center; justify-content:center;
         height:100vh; background:#1a1a2e; font-family:system-ui; color:#fff; }
  canvas { display:none; }
  .status { text-align:center; }
</style>
</head>
<body>
<div class="status" id="status">Rendering icon...</div>
<canvas id="c" width="1024" height="1024"></canvas>
<script>
(async () => {
  const c = document.getElementById('c');
  const ctx = c.getContext('2d');
  const size = 1024;
  const radius = Math.round(size * 0.22);  // macOS icon corner radius

  // --- Navy gradient background with rounded rect ---
  ctx.beginPath();
  ctx.moveTo(radius, 0);
  ctx.lineTo(size - radius, 0);
  ctx.quadraticCurveTo(size, 0, size, radius);
  ctx.lineTo(size, size - radius);
  ctx.quadraticCurveTo(size, size, size - radius, size);
  ctx.lineTo(radius, size);
  ctx.quadraticCurveTo(0, size, 0, size - radius);
  ctx.lineTo(0, radius);
  ctx.quadraticCurveTo(0, 0, radius, 0);
  ctx.closePath();
  ctx.clip();

  const grad = ctx.createLinearGradient(0, 0, 0, size);
  grad.addColorStop(0, '#121230');
  grad.addColorStop(1, '#262650');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);

  // --- Subtle inner glow at top ---
  const glowGrad = ctx.createLinearGradient(0, 0, 0, size * 0.15);
  glowGrad.addColorStop(0, 'rgba(255,255,255,0.08)');
  glowGrad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = glowGrad;
  ctx.fillRect(0, 0, size, size * 0.15);

  // --- Emoji centered ---
  ctx.font = '560px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('""" + EMOJI + """', size / 2, size / 2 - 10);

  // --- POST the canvas as PNG to our receiver ---
  document.getElementById('status').textContent = 'Sending to icon builder...';
  c.toBlob(async (blob) => {
    try {
      const resp = await fetch('/receive', { method: 'POST', body: blob });
      const text = await resp.text();
      document.getElementById('status').innerHTML = text;
    } catch (e) {
      document.getElementById('status').textContent = 'Error: ' + e.message;
    }
  }, 'image/png');
})();
</script>
</body>
</html>"""


class IconHandler(http.server.BaseHTTPRequestHandler):
    """Handle GET / (serve page) and POST /receive (save PNG)."""

    def do_GET(self):
        """Serve the HTML canvas renderer."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode('utf-8'))

    def do_POST(self):
        """Receive the PNG blob from the canvas, save it, tell browser to close."""
        length = int(self.headers.get('Content-Length', 0))
        png_data = self.rfile.read(length)

        with open(RAW_PNG, 'wb') as f:
            f.write(png_data)

        # Respond with HTML that closes the browser tab
        response = """
        <div style="text-align:center">
            <p>✓ Icon received! This tab will close.</p>
        </div>
        <script>
            // Close this tab after a brief moment
            setTimeout(() => { window.close(); }, 500);
        </script>
        """.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

        # Signal that we're done
        received.set()

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


# ── Start server, open browser, wait for PNG ──

server = http.server.HTTPServer(('127.0.0.1', PORT), IconHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

print(f"  → Server listening on http://127.0.0.1:{PORT}")
print(f"  → Opening browser...")
webbrowser.open(f"http://127.0.0.1:{PORT}/")

# Wait for the PNG (timeout 30s)
if not received.wait(timeout=30):
    print("  ✗ Timed out waiting for browser to render. Is a browser available?")
    server.shutdown()
    sys.exit(1)

server.shutdown()
print(f"  ✓ PNG received ({os.path.getsize(RAW_PNG)} bytes)")

# ── Process: sips to resize, iconutil to .icns ──

os.makedirs(ICONSET, exist_ok=True)
sizes = [16, 32, 64, 128, 256, 512]

for s in sizes:
    # Standard
    subprocess.run(['sips', '-z', str(s), str(s), RAW_PNG,
                    '--out', f'{ICONSET}/icon_{s}x{s}.png'],
                   capture_output=True, check=True)
    # @2x (Retina)
    s2 = s * 2
    subprocess.run(['sips', '-z', str(s2), str(s2), RAW_PNG,
                    '--out', f'{ICONSET}/icon_{s}x{s}@2x.png'],
                   capture_output=True, check=True)

# 512@2x = 1024
subprocess.run(['sips', '-z', '1024', '1024', RAW_PNG,
                '--out', f'{ICONSET}/icon_512x512@2x.png'],
               capture_output=True, check=True)

print(f"  ✓ Resized to {len(sizes) * 2 + 1} iconset sizes")

# Convert to .icns
subprocess.run(['iconutil', '-c', 'icns', ICONSET, '-o', OUTPUT], check=True)
print(f"  ✓ Created: {OUTPUT}")
print()
PYEOF

echo "  Done. Run 'make app && make dmg' to rebuild with the new icon."
ls -lh "$OUTPUT"
