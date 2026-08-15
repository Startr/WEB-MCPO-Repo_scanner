# Tauri distribution story — signing, notarization, tray, size

2026-08-15. Research by Sage.is AI (web sources cited inline).

## Question

For macOS distribution, what do code signing, notarization, tray/menu-bar
support, and bundle size actually cost in Tauri v2 vs a hand-built
PyInstaller + codesign + notarytool pipeline?

## Findings

**Signing/notarization — Tauri v2.** The bundler automates the whole chain
given a Developer ID cert: codesign with hardened runtime (`hardenedRuntime`
defaults to `true` in `MacConfig`), custom entitlements via
`bundle.macOS.entitlements` plist path, DMG creation, and notarytool
submission + stapling — triggered purely by env vars
(`APPLE_SIGNING_IDENTITY` / `APPLE_CERTIFICATE` for signing; `APPLE_ID` +
`APPLE_PASSWORD` + `APPLE_TEAM_ID` or App Store Connect API key for
notarization). Manual work is limited to cert provisioning and config.
[tauri.app/distribute/sign/macos](https://tauri.app/distribute/sign/macos/),
[config reference](https://v2.tauri.app/reference/config/).

**Signing/notarization — PyInstaller manual path.** You own every step:
sign all nested Mach-O binaries inside the bundle, apply hardened runtime,
write entitlements, build the DMG/zip, run `xcrun notarytool submit --wait`,
staple. Python needs relaxed entitlements —
`com.apple.security.cs.allow-unsigned-executable-memory` and
`com.apple.security.cs.disable-library-validation` are the standard pair
([haim.dev](https://haim.dev/posts/2020-08-08-python-macos-app),
[pyinstaller#5743](https://github.com/pyinstaller/pyinstaller/issues/5743)).
Onefile mode is a trap: embedded binaries extract at runtime and cannot be
signed post-hoc, sandbox is incompatible, and stapling doesn't work on a
bare Mach-O (staple targets .app/dmg/pkg only) — onedir .app is the
supported route ([pyinstaller docs](https://pyinstaller.org/en/stable/usage.html),
[pyinstaller#5112](https://github.com/pyinstaller/pyinstaller/issues/5112)).

**Sidecars in Tauri.** A bundled Python binary (`bundle.externalBin`) must
be signed like any Mach-O. Tauri's bundler does attempt to sign sidecars
automatically when `APPLE_SIGNING_IDENTITY` is set — but there's an open
bug where an `externalBin` entry can invalidate the main binary's signature
and fail notarization
([tauri#11992](https://github.com/tauri-apps/tauri/issues/11992),
[discussion #12803](https://github.com/tauri-apps/tauri/discussions/12803)).
Community practice: pre-sign the sidecar (with the Python entitlements
above) before `tauri build`, and verify against the Tauri version in use.
A PyInstaller sidecar inside Tauri still needs the PyInstaller entitlements —
Tauri does not remove that complexity, it only wraps the outer pipeline.

**Tray / menu-bar-only.** Tray is a stable core v2 API (`tray-icon` cargo
feature; JS `@tauri-apps/api/tray` + Rust `tauri::tray`): menus, click
events, icon swap ([tauri.app/learn/system-tray](https://tauri.app/learn/system-tray/)).
Menu-bar-only is one line: `app.set_activation_policy(ActivationPolicy::Accessory)`
in setup, toggleable at runtime for a "show dock icon" preference
([discussion #6038](https://github.com/tauri-apps/tauri/discussions/6038),
[#10774](https://github.com/tauri-apps/tauri/discussions/10774)).
This matches what pystray/rumps gives the PyInstaller path, with better
dock-policy control than pystray offers.

**Bundle size.** A Tauri shell that just loads a localhost URL rides
WKWebView (system-provided): minimal apps land ~3 MB, real apps single-digit
to low-double-digit MB ([tauri size guide](https://v1.tauri.app/v1/guides/building/app-size/),
[discussion #6918](https://github.com/orgs/tauri-apps/discussions/6918)).
The dominant weight in either architecture stays the bundled Python runtime
(tens of MB); Tauri adds a small shell on top rather than an Electron-class
~100 MB one.

## Facts later cards depend on

- Tauri bundler = codesign + hardened runtime (default on) + entitlements +
  DMG + notarytool + staple, driven by env vars. PyInstaller path = all of
  that by hand.
- PyInstaller onefile is not notarization-viable; onedir .app only.
- Python-under-hardened-runtime entitlements:
  `allow-unsigned-executable-memory`, `disable-library-validation` —
  required in both architectures if the Python binary ships.
- Tauri signs sidecars automatically, but tauri#11992 (sidecar breaking
  main-binary signature) means: pre-sign the sidecar and test notarization
  early on the pinned Tauri version.
- Menu-bar-only in Tauri: tray API + `ActivationPolicy::Accessory`, both
  stable, runtime-toggleable.
- Tauri macOS shell overhead ~3–10 MB; Python runtime dominates either way.

## Confidence / gaps

- High: Tauri signing/notarization automation, entitlements pair,
  onefile pitfalls, Accessory policy (official docs + primary issues).
- Medium: exact current status of tauri#11992 — open at last check
  (needs-triage); re-verify against the Tauri patch release actually pinned.
- Low/unmeasured: exact shell size for our app (universal binaries roughly
  double Rust binary size; measure a hello-world build ourselves).
- Not covered: Windows/Linux distribution costs; auto-update signing
  (Tauri updater has its own key) — separate card if needed.
