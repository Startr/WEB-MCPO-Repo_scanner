#!/bin/bash
set -euo pipefail
# generate_menu_icon.sh — Render 🔭 on transparent background for menu bar.
# Uses the same canvas+receiver pattern as generate_emoji_icon.sh.
# Output: assets/todoscope_menu_icon.png (64x64, transparent bg)

EMOJI="${1:-🔭}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT="${2:-$PROJECT_ROOT/assets/todoscope_menu_icon.png}"
PORT=9998

echo "  🔭 Menu Bar Icon Generator"

python3 << PYEOF
import http.server, os, sys, threading, time, webbrowser

PORT = $PORT
OUTPUT = "$OUTPUT"
received = threading.Event()

# HTML: emoji on TRANSPARENT background — no navy rect, just the emoji
HTML_PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  body { margin:0; display:flex; align-items:center; justify-content:center;
         height:100vh; background:transparent; }
  canvas { display:none; }
</style></head><body>
<canvas id="c" width="128" height="128"></canvas>
<script>
(async () => {
  const c = document.getElementById('c');
  const ctx = c.getContext('2d');
  // Transparent background — just the emoji
  ctx.clearRect(0, 0, 128, 128);
  ctx.font = '100px "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('$EMOJI', 64, 68);
  c.toBlob(async (blob) => {
    await fetch('/receive', { method: 'POST', body: blob });
  }, 'image/png');
})();
</script></body></html>"""

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())
    def do_POST(self):
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        with open(OUTPUT, 'wb') as f: f.write(data)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<script>window.close()</script>')
        received.set()
    def log_message(self, *a): pass

server = http.server.HTTPServer(('127.0.0.1', PORT), H)
threading.Thread(target=server.serve_forever, daemon=True).start()
webbrowser.open(f'http://127.0.0.1:{PORT}/')
if not received.wait(timeout=15):
    print('  ✗ Timeout'); sys.exit(1)
server.shutdown()
print(f'  ✓ {OUTPUT} ({os.path.getsize(OUTPUT)} bytes)')
PYEOF
