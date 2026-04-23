"""TodoScope menu bar app — runs Flask server with a 🔭 status icon.

Shows a telescope icon in the macOS menu bar (or system tray on Linux/Windows)
with a dropdown menu to open the browser, view logs, or quit. Flask runs in a
background thread; pystray's icon.run() provides the Cocoa event loop that
keeps the app alive and the icon visible.

Usage:
    todoscope --tray          # from Terminal
    (auto-detected when running as .app bundle)
"""

import os
import sys
import threading
import webbrowser

import pystray
from PIL import Image, ImageDraw

from scanner.cli import find_free_port, setup_app_mode_logging, wait_for_server


def _create_icon_image(size=64):
    """Load the 🔭 telescope icon for the menu bar.

    Sources (in priority order):
    1. assets/todoscope.icns — the real Apple Color Emoji rendered via canvas+receiver
    2. assets/todoscope_menu_icon.png — fallback pre-rendered PNG
    3. Programmatic fallback — simple dark circle (last resort)
    """
    # Determine base path — works both in dev and in PyInstaller bundles
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

    # Prefer the transparent PNG (🔭 on clear background — proper for menu bar)
    png_path = os.path.join(base, "assets", "todoscope_menu_icon.png")
    if os.path.exists(png_path):
        return Image.open(png_path).resize((size, size), Image.LANCZOS)

    # Last resort: draw a simple icon
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([1, 1, size - 2, size - 2], fill=(26, 26, 46, 255))
    return img


def _run_flask(host, port):
    """Start the Flask server in the current thread (blocking)."""
    os.environ["TODOSCOPE_DATA_DIR"] = os.path.expanduser("~/.todoscope")
    os.makedirs(os.path.join(os.environ["TODOSCOPE_DATA_DIR"], "repositories"), exist_ok=True)

    from scanner.app import app
    app.run(host=host, port=port, threaded=True, use_reloader=False)


def _open_log():
    """Open a Terminal window tailing the TodoScope log."""
    log_path = os.path.expanduser("~/.todoscope/todoscope.log")
    if sys.platform == "darwin":
        os.system(f'''osascript -e 'tell app "Terminal" to activate' -e 'tell app "Terminal" to do script "tail -f {log_path}"' ''')
    else:
        # Linux: try common terminals
        for term in ("gnome-terminal", "xterm", "konsole"):
            if os.system(f"which {term} > /dev/null 2>&1") == 0:
                os.system(f"{term} -e 'tail -f {log_path}' &")
                break


def main():
    """Entry point for the menu bar app."""
    setup_app_mode_logging()
    from scanner import __version__

    host = "127.0.0.1"
    port = find_free_port(5000)

    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=_run_flask, args=(host, port), daemon=True)
    flask_thread.start()

    url = f"http://{host}:{port}"

    # Wait for server to be ready, then open browser
    if wait_for_server(host, port, timeout=15):
        webbrowser.open(url)
    else:
        print("Warning: server did not start within 15s", file=sys.stderr)

    # Build the menu bar icon + menu
    icon_image = _create_icon_image()

    def on_open_browser(icon, item):
        webbrowser.open(url)

    def on_show_log(icon, item):
        _open_log()

    def on_quit(icon, item):
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(f"TodoScope {__version__}", None, enabled=False),
        pystray.MenuItem(f"Running on port {port}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open Browser", on_open_browser),
        pystray.MenuItem("Show Log", on_show_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    icon = pystray.Icon("todoscope", icon_image, "TodoScope", menu)

    # icon.run() blocks — this IS the Cocoa event loop.
    # The icon stays in the menu bar until Quit is clicked.
    icon.run()


if __name__ == "__main__":
    main()
