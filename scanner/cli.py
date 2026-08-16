"""TodoScope CLI — start the server and open a browser."""
import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser


def find_free_port(start=5000, attempts=20):
    """Return *start* if available, otherwise probe upward."""
    for offset in range(attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start  # fall back; Flask will error if truly taken


def wait_for_server(host, port, timeout=10):
    """Block until the server responds or timeout expires."""
    import urllib.request
    url = f"http://{host}:{port}/"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def open_browser(url):
    """Open *url* in the default browser after a brief delay."""
    time.sleep(0.8)  # let Flask finish startup output
    webbrowser.open(url)


def start_tunnel(kind, port):
    """Spawn a cloudflared or tailscale tunnel and return the Popen handle."""
    if kind == "cloudflared":
        return subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=sys.stdout, stderr=sys.stderr,
        )
    elif kind == "tailscale":
        return subprocess.Popen(
            ["tailscale", "funnel", str(port)],
            stdout=sys.stdout, stderr=sys.stderr,
        )
    return None


def resolve_tunnel(args):
    """Return 'cloudflared', 'tailscale', or None based on CLI flags."""
    if args.tunnel:
        return "cloudflared"
    if args.tailscale:
        return "tailscale"
    if args.share:
        # prefer tailscale if installed
        for cmd in ("tailscale", "cloudflared"):
            if subprocess.run(["which", cmd], capture_output=True).returncode == 0:
                return cmd
        print("--share needs tailscale or cloudflared on your PATH. Install one, then rerun.", file=sys.stderr)
        sys.exit(1)
    return None


def setup_app_mode_logging():
    """When running inside a .app bundle (no tty), redirect output to a log file.
    Output viewable via: tail -f ~/.todoscope/todoscope.log"""
    if sys.stdout is not None and sys.stdout.isatty():
        return  # Running in a terminal — output goes to terminal as normal

    log_dir = os.path.expanduser("~/.todoscope")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "todoscope.log")
    log_file = open(log_path, "a")
    sys.stdout = log_file
    sys.stderr = log_file


def main():
    # Auto-detect .app mode: no tty AND no CLI args means Finder launch.
    # If there are CLI args (--version, --help, etc.), let argparse handle them
    # even when stdout is captured (e.g. pytest, pipes).
    if (sys.stdout is None or not sys.stdout.isatty()) and len(sys.argv) == 1:
        setup_app_mode_logging()
        from scanner.tray import main as tray_main
        tray_main()
        return

    from scanner import __version__

    parser = argparse.ArgumentParser(
        prog="todoscope",
        description="TodoScope — See every TODO across all your repos.",
    )
    parser.add_argument("--version", action="version", version=f"todoscope {__version__}")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000, auto-finds free port if taken)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser — headless mode for tmux/SSH/phone")
    parser.add_argument("--exact-port", action="store_true", help="Bind exactly --port and fail if taken (desktop shell handshake)")
    parser.add_argument("--tunnel", action="store_true", help="Expose via cloudflared quick tunnel")
    parser.add_argument("--tailscale", action="store_true", help="Expose via tailscale funnel")
    parser.add_argument("--share", action="store_true", help="Expose via best available tunnel (prefers tailscale)")
    parser.add_argument("--tray", action="store_true", help="Run as menu bar app (🔭 icon in menu bar, no terminal output)")
    args = parser.parse_args()

    # --tray flag: launch menu bar mode from Terminal
    if args.tray:
        from scanner.tray import main as tray_main
        tray_main()
        return

    port = args.port
    if not args.exact_port:
        # Check if already running — don't launch a second instance
        if wait_for_server(args.host, port, timeout=1):
            url = f"http://{args.host}:{port}"
            print(f"  TodoScope already running on {url}")
            if not args.no_browser:
                webbrowser.open(url)
            return

        # Find a free port
        port = find_free_port(args.port)
        if port != args.port:
            print(f"Port {args.port} in use, using {port} instead.")

    # Ensure data dir exists
    data_dir = os.path.expanduser("~/.todoscope")
    os.makedirs(os.path.join(data_dir, "repositories"), exist_ok=True)

    # Set env vars so scanner.app picks up the data dir
    os.environ["TODOSCOPE_DATA_DIR"] = data_dir

    url = f"http://{args.host}:{port}"

    # Banner
    print()
    print("  🔭 TodoScope")
    print(f"  Version {__version__}")
    print()
    print(f"  → {url}")
    print()
    if args.no_browser:
        print("  (headless mode — open the URL above in your browser)")
    print("  Press Ctrl+C to stop.")
    print()

    # Open browser (unless headless)
    if not args.no_browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Start tunnel if requested
    tunnel_proc = None
    tunnel_kind = resolve_tunnel(args)
    if tunnel_kind:
        tunnel_proc = start_tunnel(tunnel_kind, port)

    # Clean shutdown
    def shutdown(signum, frame):
        print("\nShutting down...")
        if tunnel_proc:
            tunnel_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Import and run Flask
    from scanner.app import app
    app.run(host=args.host, port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
