# The verdict — go on Tauri

**Date:** 2026-08-15 · **Decided by:** Alexander Somma ("A Rusty knife will cut through our problems quickly") · **Type:** interview

## Question

Go or no-go on Tauri as TodoScope's desktop shell, weighed against the chart's
criteria: native-app feel, Gatekeeper/signing cost, size and startup, a thin-Rust
ceiling, next-quarter horizon.

## Decision

**Go.** Tauri v2 becomes the target shell for the TodoScope desktop app.

## Rationale against the criteria

1. **Native-app feel** — real window over the existing server-rendered SSE UI;
   `frontendDist` pointed at `http://localhost:PORT` is a supported same-origin
   pattern, so the web UI ships unchanged, no CORS.
2. **Gatekeeper cost** — decisive. Tauri's bundler automates hardened-runtime
   codesign, entitlements, DMG, notarytool submission, stapling, and sidecar
   signing. The alternative was building that pipeline by hand for PyInstaller.
3. **Size/startup** — shell overhead ~3–10 MB; switching the Python sidecar to
   onedir removes the ~10s onefile extraction delay.
4. **Thin-Rust ceiling holds** — the Rust surface is bounded to shell lifecycle:
   spawn sidecar, process-group kill on quit, port handshake, readiness poll.
   The brain stays Python; the UI stays server-rendered.
5. **pywebview** was a real option but loses on two counts: the tray/window
   main-thread conflict forces a two-process IPC split, and it does nothing
   about the signing pipeline.

## Consequences

- The manual PyInstaller codesign + notarytool Makefile pipeline will **not** be
  built. Signing effort moves into the Tauri shell effort. (D-U-N-S, Apple
  Developer enrollment, and the Developer ID certificate are still required —
  Tauri consumes the same credentials.)
- The Python sidecar moves to a **onedir** PyInstaller build regardless — onefile
  is not notarization-viable (no post-hoc signing of embedded binaries) and
  Tauri's process management can only see the bootloader pid in onefile form.
- Interim distribution stays Homebrew formula + PyPI + Docker (no quarantine
  friction); the unsigned PyInstaller .app remains a stopgap only.
- Known risks to carry into implementation: tauri#11992 (sidecar signature
  invalidation during notarization — pre-sign and test early on a pinned
  version), DIY sidecar lifecycle (plugins-workspace#3062), SSE heartbeats
  under 60s.
- A fresh implementation effort charts the build; this chart's Backlog fog
  (v1.x coexistence, Windows/Linux parity, any Rust migration) transfers there.

## Sources

- [Tauri sidecar mechanics](tauri-sidecar-mechanics.md)
- [Tauri distribution story](tauri-distribution-story.md)
- [pywebview reality check](pywebview-reality-check.md)
