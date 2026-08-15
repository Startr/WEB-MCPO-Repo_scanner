# Shell build choices — the Tauri implementation's settled points

Date: 2026-08-15. Decided by Alexander Somma (brew route, tap, app style) and
Sage.is AI (mechanics), during the first Tauri shell build.

## Decisions

**No `externalBin` — onedir via `bundle.macOS.files`.** The sidecar is the
PyInstaller onedir folder mapped whole into the bundle:
`"MacOS/todoscope-server": "../dist/todoscope"` →
`Contents/MacOS/todoscope-server/{todoscope, _internal/}`. The exe stays
adjacent to `_internal/`, Rust sees the real Python pid, no shell plugin is
needed, and the tauri#11992 sidecar-signing bug is sidestepped entirely.
Runtime insurance: Rust sets 0o755 on the exe before first spawn in case the
bundler drops the exec bit.

**Port: OS-assigned, sticky.** No hardcoded port. First launch binds
`127.0.0.1:0`, takes what the OS gives, and remembers it in
`~/.todoscope/desktop-port`; later launches reuse that port while it stays
free, falling back to a fresh OS-assigned one when it doesn't. Rationale for
the memory: WKWebView localStorage is origin-scoped and origins include the
port — a random port every launch would silently wipe UI state. The sidecar is
spawned with `--port N --host 127.0.0.1 --no-browser --exact-port`: passing
args keeps cli.py out of its Finder-launch tray branch, `--no-browser` gates
its `webbrowser.open` calls, and `--exact-port` (added for this handshake)
makes cli.py bind exactly the given port or fail loudly instead of silently
hunting forward — a drifted port would leave the shell polling a dead one.

**Readiness = `GET /health`.** New public route (added to `_PUBLIC_ROUTES`)
returning `{status, app, version}`. Rust polls it with a raw TCP HTTP/1.0
request — no HTTP client dependency — short-circuiting if the child exits,
15 s deadline, error dialog pointing at `~/.todoscope/desktop-sidecar.log` on
failure.

**Shutdown = SIGTERM, 2 s grace, SIGKILL.** Onedir means the pid is the real
Python process, and cli.py installs a SIGTERM handler that exits cleanly. The
kill runs from `RunEvent::Exit`, idempotent via `Option::take`.

**Identifier `com.startr.todoscope`.** Matches the legacy hand-rolled .app's
Info.plist, so Launch Services treats the Tauri app as its successor. The
orphaned root `todoscope.spec` said `com.sage-is.todoscope`; that spec is not
part of the build path.

**Window created programmatically; no `frontendDist`.** `tauri.conf.json`
declares zero windows; after `/health` passes, Rust opens the window on the
main thread at `http://127.0.0.1:PORT/`. This avoids URL-form `frontendDist`
dev-mode rough edges and means no window ever shows a dead server.

**Dock app + tray.** `MENU_BAR_ONLY = false` in main.rs: real window, Dock
icon, Cmd-Tab presence; the menu-bar icon stays for Open/Quit. Flipping the
one const restores today's accessory-style presence.

**DMG replaces the legacy artifact.** Release asset keeps the name
`TodoScope-<ver>.dmg` but is now Tauri-built. `make dmg` (create-dmg over the
hand-rolled .app) remains as a manual fallback; `release_all.sh` no longer
calls it.

**Distribution: cask + dequarantine in Sage-is/homebrew-apps.** Unsigned
interim route: `brew install --cask sage-is/apps/todoscope`, where the cask's
postflight strips `com.apple.quarantine` — legal in a third-party tap, and
necessary since macOS Sequoia removed the right-click-Open bypass. The
postflight block is deleted the day releases are signed. Version/sha256 are
maintained by the tap-update step in `scripts/release_all.sh`.

**Version sync.** The Makefile extracts `__version__` from
`scanner/__init__.py` and injects it with
`cargo tauri build --config '{"version":"..."}'`. Nothing rewrites
`tauri.conf.json`; its committed version is a fallback.

**Zoom is menu-driven.** macOS routes Cmd-key shortcuts through menu
accelerators; WKWebView has no built-in hotkey zoom and `zoom_hotkeys_enabled`
alone does nothing for Cmd+/−. The shell therefore ships a real menu bar:
View → Zoom In (Cmd+=), Zoom Out (Cmd+−), Actual Size (Cmd+0) driving
`WebviewWindow::set_zoom`, with the factor persisted in
`~/.todoscope/desktop-zoom` and re-applied on window creation. A custom menu
replaces the macOS default entirely, so the App menu (quit/hide) and the Edit
menu (undo/cut/copy/paste — without which the webview loses Cmd+C/V) are
re-declared alongside View.

**Network sharing is a tray toggle with an auth gate.** "Share on Network" in
the tray restarts the sidecar bound to `0.0.0.0` on the same port (window and
localStorage untouched, since the window stays on `127.0.0.1`), shows the LAN
URL, and persists the choice in `~/.todoscope/desktop-share`. The gate: the
shell refuses to enable sharing while `/health` reports `auth: false` — an
un-keyed board must never face the network — and on startup a persisted share
setting is reverted to loopback if the key has since been removed. `/health`
gained the `auth` field for exactly this check. macOS's application firewall
still prompts to allow incoming connections; the share dialog says so.

**No `strip = true` in the release profile.** Stripping the release binary
made the webview window silently never appear (Objective-C metadata that
tao/wry need is removed). Found empirically: debug and unstripped release
builds show the window, the stripped release build does not, same source.
`lto = true` stays; the comment in Cargo.toml guards the footgun.

**Secret-key persistence.** With `TODOSCOPE_DATA_DIR` set and no `SECRET_KEY`
env, the app persists a generated key at `~/.todoscope/.secret_key` (0600) so
Flask sessions survive relaunches of the desktop app.

## Consequences

- `make tauri_dmg` is the desktop build entry; `make tauri_dev` the dev loop
  (`TODOSCOPE_DEV_PORT=5723` attaches to an external `pipenv run todoscope`).
- The PyPI leg stays blocked: the name `todoscope` on PyPI belongs to an
  unrelated project (Zelmari/todoscope 0.9.4) — separate decision needed.
- `kill -9` of the shell orphans the sidecar (no parent watchdog). Accepted;
  cheapest later fix is a parent-pid poll in cli.py.

## Sources

- [The verdict](the-verdict.md)
- [Tauri sidecar mechanics](tauri-sidecar-mechanics.md)
- [Tauri distribution story](tauri-distribution-story.md)
