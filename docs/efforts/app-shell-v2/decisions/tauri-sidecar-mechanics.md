# Decision record: Tauri v2 sidecar mechanics for a PyInstaller-frozen Flask server

Date: 2026-08-15. Researched by Sage.is AI.

## Question

Can Tauri v2 bundle and manage a PyInstaller-frozen Flask binary as a sidecar — start on launch, kill on quit, port selection, clean shutdown — and does SSE/EventSource from `http://localhost` work reliably in the macOS webview (WKWebView)?

## Findings

**Sidecar bundling: yes, first-class.** Declare the binary under `bundle.externalBin` in `tauri.conf.json`; binaries carry a target-triple filename suffix (`todoscope-server-aarch64-apple-darwin`), stripped at runtime. Spawn via `tauri-plugin-shell`: Rust `app.shell().sidecar("name")` or JS `Command.sidecar(...)`, gated by a capability (`shell:allow-execute` with `"sidecar": true`). [tauri.app sidecar guide](https://v2.tauri.app/develop/sidecar/)

**Lifecycle: entirely DIY.** Official docs warn the developer must kill the child or orphan processes pollute the machine. No built-in health check, restart, or port management — an open feature request for a lifecycle plugin catalogues exactly these gaps ([plugins-workspace#3062](https://github.com/tauri-apps/plugins-workspace/issues/3062)). Working pattern: hold the `CommandChild`, kill it in `RunEvent::ExitRequested`/`Exit`; on macOS, closing the last window must explicitly kill the sidecar then `app_handle.exit(0)` or the process lingers in the Dock ([zudo-tauri lifecycle notes](https://zudo-tauri-wisdom.takazudomodular.com/docs/architecture/process-lifecycle/)).

**PyInstaller one-file trap.** Tauri holds the pid of the PyInstaller *bootloader*, not the Python child; `child.kill()` orphans the server ([dieharders example, README](https://github.com/dieharders/example-tauri-v2-python-server-sidecar)). Fixes: spawn with `process_group(0)` and signal the group (`kill(-pid, SIGTERM)`, `SIGKILL` after ~500 ms grace), or an in-band shutdown route/stdin command, or build one-dir instead of one-file.

**Port selection: no built-in mechanism.** Community patterns: (a) fixed port plus pre-spawn cleanup via `lsof` + SIGTERM; (b) bind port 0 in the server, print the chosen port on stdout, Rust reads the line before navigating; either way, poll a `/ready` endpoint with a timeout that also `try_wait()`s the child so a dead sidecar fails fast ([zudo-tauri](https://zudo-tauri-wisdom.takazudomodular.com/docs/architecture/process-lifecycle/), [Magny, Medium](https://medium.com/@samuelint/tauri-how-to-start-stop-a-sidecar-and-pipe-sidecar-stdout-stderr-to-app-logs-from-rust-8f81a92111ad)).

**Prior art exists.** [dieharders/example-tauri-v2-python-server-sidecar](https://github.com/dieharders/example-tauri-v2-python-server-sidecar) (FastAPI, PyInstaller `-F`, fixed port 8008, HTTP between webview and server) and [AlanSynn/vue-tauri-fastapi-sidecar-template](https://github.com/AlanSynn/vue-tauri-fastapi-sidecar-template). Flask is the same mechanics ([discussion #6529](https://github.com/tauri-apps/tauri/discussions/6529)).

**SSE on macOS: works, with two caveats.** WKWebView is the Safari engine; EventSource is supported. No macOS-specific Tauri SSE breakage surfaced — the documented failures are Windows WebView2 silently dropping streams ([opencode#13655](https://github.com/anomalyco/opencode/issues/13655)). That same issue records WKWebView's ~60 s idle timeout: send heartbeat comments (they use 30 s) to keep streams alive. Caveat two is origin: on macOS Tauri serves the app from `tauri://localhost`, so `http://localhost:PORT` is cross-origin — Flask must emit CORS headers (flask-cors), including on the SSE response; alternatively [tauri-plugin-cors-fetch](https://crates.io/crates/tauri-plugin-cors-fetch) proxies fetch through Rust and explicitly supports streaming/SSE.

**Whole-window-at-localhost: supported.** `frontendDist` accepts "a remote URL (for example: `https://site.com/app`)" — an `http://localhost:PORT` value is legal, making the server same-origin and dissolving CORS entirely ([config reference](https://v2.tauri.app/reference/config/)). Trade-off: Tauri IPC is not exposed to remote URLs unless the capability's `remote` URLPattern grants it, and `__TAURI__` injection from localhost has an open bug ([tauri#11934](https://github.com/tauri-apps/tauri/issues/11934)); dev-mode handling of URL-form `frontendDist` has had rough edges ([#12333](https://github.com/tauri-apps/tauri/issues/12333), [#9629](https://github.com/tauri-apps/tauri/issues/9629)).

## Facts later cards depend on

- Sidecar = `bundle.externalBin` + target-triple suffix + shell-plugin spawn; capability required.
- Kill-on-quit is our job: `RunEvent::ExitRequested` handler; macOS last-window-close must kill + `exit(0)`.
- PyInstaller one-file: Tauri sees only the bootloader pid — kill the process group or use an in-band shutdown; naive `kill()` orphans Flask.
- No built-in port handling: bind :0 + report via stdout, or fixed port + pre-spawn cleanup; always poll readiness with child-exit short-circuit.
- SSE fine in WKWebView; keep heartbeats under 60 s.
- `tauri://localhost` origin → CORS headers needed on Flask, or point the whole window at `http://localhost:PORT` (supported via URL-form `frontendDist`; costs easy Tauri IPC access).

## Confidence / gaps

- High: sidecar bundling, DIY lifecycle, PyInstaller pid trap, CORS/origin model — all first-party docs or maintainer statements.
- Medium: WKWebView SSE reliability — inferred from Safari engine plus one project's heartbeat note; no direct macOS-Tauri SSE failure *or* success report located. Prototype early.
- Untested: PyInstaller bootloader signal forwarding on macOS (may make plain SIGTERM sufficient); URL-form `frontendDist` behaviour in `tauri dev` on current Tauri.
