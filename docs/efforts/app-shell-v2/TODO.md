# App Shell v2 — Chart

## Destination

A go/no-go decision on Tauri as TodoScope's desktop shell, recorded as a one-page
decision record. No full spec — a "go" spawns a fresh implementation effort.

## Notes

Domain: macOS-first desktop shell around a Flask server with a server-rendered live
UI (SSE + idiomorph). Current shell: 18MB PyInstaller onefile, pystray menu bar,
opens the default browser, unsigned.

Decision criteria from the charting interview (2026-08-01, weights in order):

1. Native-app feel — a browser tab is not an app (top pain).
2. Gatekeeper/signing cost — Tauri's built-in signing/notarization vs building the
   PyInstaller codesign + notarytool pipeline by hand.
3. Size and startup — 18MB onefile with ~10s first-launch extraction hurts.
4. Rust surface must stay thin — Tauri as chrome, Flask as brain; appetite sits
   between reluctant and fine, so a fat Rust surface is a no-go on its own.
5. Horizon: next quarter. The verdict gates whether notarizing the PyInstaller
   path is worth building at all.

Auto-update was explicitly not a driving pain.

Decision records live in `decisions/` beside this chart.

## In Progress

## TODO

## Backlog

<!-- Chart complete — destination reached 2026-08-15. Remaining fog transfers
to the Tauri shell implementation effort (not yet charted): v1.x coexistence,
Windows/Linux parity, any Python-to-Rust migration. -->

## Out of scope

- Full v2 implementation spec — the destination is the go/no-go only.
- Rewriting the web UI as a Tauri-native frontend — the server-rendered SSE + idiomorph UI is a settled decision from the live-board effort.
- Auto-update design — not a driving pain per the charting interview; it returns only inside a "go" implementation effort.

## Done

- [x] **The verdict**: **GO on Tauri** — signing automation is decisive, the web UI ships unchanged via `frontendDist: http://localhost:PORT`, Rust stays a thin lifecycle shell; the manual PyInstaller notarization pipeline will not be built, and the sidecar moves to onedir regardless — [decision](decisions/the-verdict.md)
- [x] **Tauri sidecar mechanics**: Python sidecars are a first-class, proven pattern (`bundle.externalBin` + shell plugin), but lifecycle is DIY — kill-on-quit by hand, process-group kill to avoid orphaning Flask behind the onefile bootloader, bind-:0-and-report for ports; SSE works in WKWebView, and pointing the whole window at `http://localhost:PORT` is a supported same-origin pattern that avoids CORS — [decision](decisions/tauri-sidecar-mechanics.md)
- [x] **pywebview reality check**: real option, not a trap — SSE over plain `http://localhost` has no known WKWebView blocker (spike still warranted); but pywebview and pystray both demand the macOS main thread, so tray + window means a two-process split with IPC; signing is the same manual PyInstaller pipeline; actively maintained, bus factor 1 — [decision](decisions/pywebview-reality-check.md)
- [x] **Tauri distribution story**: Tauri's bundler automates the whole macOS chain (hardened-runtime codesign, entitlements, DMG, notarytool + staple, auto-signed sidecars — watch tauri#11992); PyInstaller onefile is not notarization-viable, onedir is; menu-bar-only apps are first-class; shell overhead ~3–10 MB — [decision](decisions/tauri-distribution-story.md)
