# pywebview reality check

## Question

Is pywebview a real third option for wrapping the local Flask server (server-rendered UI,
SSE/EventSource + DOM morphing) in a native macOS window — or a trap?

## Findings

**1. SSE over http://localhost — no known blocker.** pywebview on macOS is a thin wrapper
around WKWebView, which has native EventSource support (same engine as Safari). Loading a
plain `http://localhost:PORT` URL bypasses the one place WKWebView does break streaming —
custom `WKURLSchemeHandler` responses, which buffer. No GitHub issue reporting SSE failure
under Cocoa/WKWebView was found; historical localhost socket bugs (#241 WebSocket 1006) were
Linux-side and are closed as resolved. ATS exempts loopback connections, so no plist
exception is needed. Caveat: no positive evidence either — no documented shipped app using
Flask + SSE + pywebview was found; treat as "should work, verify with a spike."
The Flask-in-a-thread + `webview.start()` pattern is the documented first-class architecture
([pywebview.flowrl.com/guide/architecture.html](https://pywebview.flowrl.com/guide/architecture.html)).

**2. Threading — pywebview and pystray both demand the macOS main thread.** Cocoa forces
`webview.start()` onto the main thread ([FAQ](https://pywebview.flowrl.com/guide/faq));
pystray's `run()` on macOS "will fail unless called from the main thread" and needs the
runloop ([pystray docs](https://pystray.readthedocs.io/en/latest/usage.html)). They cannot
share one process's main thread. The official escape hatch
([pystray_icon example](https://pywebview.flowrl.com/examples/pystray_icon.html)) runs
pystray on the main thread and launches pywebview in a **separate process**
(`multiprocessing.get_context('spawn')` on Darwin) — meaning the window process is not the
server process, so the Flask port, scan state, and lock file all need IPC or a
detached-server design. pywebview 6.1 added macOS **application menu** support but has no
system-tray/status-item API, so the tray cannot "move into pywebview."

**3. Signing/notarization — same manual PyInstaller pipeline, not worse.** PyInstaller
ships a pywebview hook; the renderer is the OS's WKWebView, so unlike QtWebEngine/Electron
there is no bundled browser framework to deep-sign. Standard recipe applies: sign all
collected dylibs, hardened runtime (`-o runtime`), notarize, staple
([haim.dev walkthrough](https://haim.dev/posts/2020-08-08-python-macos-app)).

**4. Project health — alive.** Verified via GitHub API 2026-08-15: latest release 6.2.1
(2026-04-15), 6.2 (2026-04-13) includes an explicit **macOS Tahoe** memory-leak fix
("release retained instances on window close") and ARM64 use-after-free fixes; commits as
recent as 2026-08-10; ~6k stars, 12 open issues. Single primary maintainer (r0x0r /
Roman Sirokov) — bus factor 1.

## Facts later cards depend on

- WKWebView EventSource works over plain localhost HTTP; the streaming trap is custom
  scheme handlers, which this architecture avoids.
- pywebview owns the main thread on macOS; Flask runs in a daemon thread. That part is
  stock.
- Tray + window in one process is impossible with pystray. Choices: (a) pystray main
  thread + pywebview subprocess (official pattern, needs IPC), (b) drop the tray, use
  pywebview's native app menu (6.1+), (c) keep pystray, drop pywebview.
- Notarization cost is identical to the current PyInstaller pipeline; no extra frameworks
  to sign.
- Active upstream through mid-2026, Tahoe-aware; single maintainer.

## Confidence / gaps

- High: threading conflict, main-thread rules, release/maintenance data (API-verified),
  signing story.
- Medium: SSE reliability — inferred from WKWebView/Safari behavior plus absence of
  contrary issues, not from a shipped reference app. A half-day spike (Flask thread + SSE
  page in `webview.start()`) settles it.
- Unverified: behavior of long-idle SSE connections when the window occludes/App Nap kicks
  in; worth including in the spike.
