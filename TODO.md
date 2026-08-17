# TODO — TodoScope

> **Convention** — Sections below map to kanban columns. Inline source-code
> tags use the same vocabulary so items stay cross-referenced between this
> file and the codebase. `KANBAN.canvas` auto-generates from this file and
> inline tags — do not hand-edit it.
>
> | Column      | Markdown section          | Inline tag |
> |-------------|---------------------------|------------|
> | Backlog     | `## Backlog`              |            |
> | TODO        | `## TODO`                 | `# TODO:`  |
> | In Progress | `## In Progress`          | `# FIXME:` |
> | Bugs        | `## Bugs`                 | `# BUG:`   |
> | Done        | `- [x]` items / `## Done` | —          |
>
> Shipped work is archived in [docs/completed-todos.md](docs/completed-todos.md).
> Narration cut from open cards lives in [docs/board-dossiers.md](docs/board-dossiers.md).

<!-- All content below this line has been revised — tools/sync_readme_todos.py syncs it into README.md via `make sync_todos` -->

## In Progress

*Nothing in flight. Claim a card by moving it here from TODO.*

## TODO

### Brand & Landing Page — Scope E (First-Run & Onboarding) #onboarding

- [ ] **First-run onboarding**: wizard, demo repo, try-it-live #onboarding #ux
  - [ ] First-run wizard: after setting the first access key, walk through registering a repo and connecting an AI agent
  - [ ] Include a demo/sample repo option on first visit #demo
  - [ ] Add a "Try it live" section to the logged-out landing #landing

### todo-scope Skill — Publish & Promote #ai #skill #brand

The `todo-scope` Claude Code skill bootstraps and aligns a repo's TODO.md to TodoScope conventions. It ships in this repo at `.claude/skills/todo-scope/SKILL.md`. Vendoring, path generalisation, README install docs, and the landing-page and `/connect` mentions all shipped — see the archive.

- [ ] **Publish the todo-scope skill**: package for one-command install #skill #packaging
  - [ ] Package as a Claude Code plugin
- [ ] **Promote the skill**: in-app nudges and outreach #brand #ux
  - [ ] Scanner nudge: when a board is mostly bare single-line cards, suggest running the skill
  - [ ] Cross-post via sage.is and startr.style channels

### Features #feature

- [ ] **Explore scan results**: search, README context, metrics, exports #ux #reporting
  - [ ] Add README summary to scan results: show the top of each repo's README in the web interface #frontend
  - [ ] Search: implement a search feature for TODO comments #search
  - [ ] Metrics dashboard: visualize TODO metrics across projects
  - [ ] Report downloads: offer CSV, JSON, PDF export of scan results

## Backlog

- [ ] **MCPO: settle the MCP story** — rename shipped 2026-08-15, one decision left #ai #mcp #decision
  - [ ] Real MCP server endpoint (JSON-RPC `tools/list` + `tools/call`), or retire the MCP term project-wide. UI copy says "tool API" either way. Rename history and route census in [board-dossiers](docs/board-dossiers.md)
- [ ] **Untrack `scanner/local_repos.yaml`**: it is committed, publishing local filesystem paths and a `webhook_secret` field that is `null` today but one commit from being live. `git rm --cached` + gitignore; the file stays on disk and the app recreates it. #security
- [ ] **Share-on-Network firewall test**: verify the desktop app's tray share toggle across the macOS application firewall — accept the incoming-connections prompt, reach the LAN URL from a second device, sign in with an access key. Local curl-to-own-LAN-IP is filtered on the dev Mac, so this needs a real second device. #macos #app #network
- [ ] **Inline TODO completion tracking**: Snapshot-and-diff approach to detect when inline TODOs are removed between scans and show them as completed in the Done column. Uses `.todoscope-snapshot.json` and `.todoscope-done.json`. Git-history-independent — works on shallow clones. #feature #kanban
- [ ] **TODO editor — remaining scope**: add-TODO form, edit card text, and drag-between-columns write-back. Checkbox toggling shipped (see Phase 2 live board). #feature #editor #kanban
- [ ] **Publish CapRover one-click app source**: Add `caprover-one-click.yml` to the Sage-is one-click repo #deployment #caprover
- [ ] **Scanner extensibility**: smarter parsing, plugins, external integrations #architecture #integration
  - [ ] Priority inference from TODO comments #core #parser
  - [ ] Plugin system to extend scanner functionality #extensibility
  - [ ] Task manager integration (Jira, Asana, Trello) #external
- [ ] **Ralph-loop agent mode**: agent loop with TODO.md as the state file #ai #agent #automation
  - [ ] Each pass: pick the next unfinished item, work it, check it off, commit
  - [ ] Fresh context per pass: `claude -p` in a bash loop (true Ralph), or `/loop` with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` lowered (approximation)

### Release Pipeline — Remaining legs #release

- [ ] **Verify end-to-end**: `scripts/todoscope start` → open → dev → tunnel #testing
- [ ] **Cross-platform binaries — build & verify** #linux #windows #testing
  - [ ] Linux binary: PyInstaller on ubuntu (x86_64) — works in tmux/SSH #linux
  - [ ] Windows binary: PyInstaller on windows (.exe) — Wine under Apple Silicon emulation fails, so this needs a real Windows host #windows
  - [ ] Verify macOS: `make binary` → `./dist/todoscope --port 5001` → browser opens, SSE works
  - [ ] Verify Linux (headless): `./todoscope --no-browser --port 5001` → access via tunnel or LAN
  - [ ] Verify Windows: `todoscope.exe` → browser opens, SSE works
- [ ] **Code signing**: Developer ID credentials — consumed by the Tauri shell's bundler, per [the verdict](docs/efforts/app-shell-v2/decisions/the-verdict.md) #macos #security
  - [ ] [MANUALLY] D-U-N-S check for Startr LLC via Apple's lookup (developer.apple.com/enroll/duns-lookup) — use the exact legal name + address from formation docs; request free number if absent (~5 business days). Public D&B directory shows no listing as of 2026-08-01.
  - [ ] [MANUALLY] Pick/confirm the team Apple ID for enrollment; enroll Startr LLC in Apple Developer Program (US$99/yr, org enrollment needs the D-U-N-S)
  - [ ] [MANUALLY] Create Developer ID Application certificate in the developer portal
  - [ ] Wire `APPLE_*` env vars into `tauri build`, re-test tauri#11992 on the pinned version, drop the cask's dequarantine postflight. The manual codesign/notarytool pipeline will not be built — Tauri's bundler handles signing, notarization, stapling, and sidecar signing.
- [ ] **Homebrew — formula leg** (cask shipped in v1.1.0) #homebrew #deployment
  - [ ] Add `Formula/todoscope.rb` to homebrew-apps: Docker CLI formula — depends_on docker, git, cloudflared (optional), tailscale (optional); installs `scripts/todoscope` to bin
  - [ ] Update `nuke-sage`: add todoscope to KNOWN_PROJECTS
  - [ ] Verify: `brew install --build-from-source Formula/todoscope.rb` works
  - [ ] Verify the cask installs through brew itself — blocked locally, `/opt/homebrew` is not writable by this account and needs the admin account #macos
- [ ] **PyPI leg**: blocked — the name `todoscope` is taken by an unrelated package. Decide on a scoped name or drop PyPI. #packaging #decision
- [ ] **One-command release**: `make patch_release` + `make release_finish` triggers everything #automation #ci
  - [ ] Auto-bump version in `scanner/__init__.py` to match the tag — done by hand for v1.1.0
  - [ ] Run tests before finishing
  - [ ] Tag push → CI builds all artifacts automatically
  - [ ] Post-release summary: GitHub Release link, brew install command
- [ ] **Version single-source-of-truth**: `scanner/__init__.py` drives everything #packaging
  - [x] `pyproject.toml` reads version dynamically
  - [ ] PyInstaller embeds it in the binary
  - [ ] `scripts/todoscope` VERSION synced by the release script — hand-synced for v1.1.0
  - [ ] Cask version/sha256 updated by the release script (its tap step assumes `Casks/todoscope.rb` exists; it now does)

### Release Pipeline — Future Enhancements #release #future

- [ ] **Tray & Dock polish**: platform icon behavior across macOS, Linux, Windows #macos #cross-platform #design
  - [ ] Dock icon click → Open Browser: respond to `applicationShouldHandleReopen:` via PyObjC NSApplication delegate so clicking the running Dock icon opens the browser #ux
  - [ ] Menu bar icon dark/light mode: research macOS template images for auto-inverting icon on light menu bar
  - [ ] Linux/Windows tray icon colors: research platform-appropriate pystray styling on Linux (GNOME/KDE) and Windows
- [ ] **Tauri shell — remaining**: shipped 2026-08-15, settled points in [shell build choices](docs/efforts/app-shell-v2/decisions/shell-build-choices.md) #macos #app #tauri
  - [ ] `kill -9` of the shell orphans the sidecar — consider a parent-pid poll in cli.py
- [ ] **Branding & Poka-Yoke audit**: mistake-proofing pass over flows — poka-yoke devices for destructive and confusing paths. Copy and error-message leg shipped via the brand voice audit. #brand #ux

## Bugs

- [ ] **`make binary` output is clobbered by the sidecar build**: the release silently ships no macOS binary #release #packaging
  - [ ] `release_all.sh` runs `make binary` (onefile → `dist/todoscope`), then `make tauri_dmg` → `sidecar_dir` → `make binary_dir`, whose onedir output replaces `dist/todoscope` with a *directory*
  - [ ] The upload step tests `[[ -f ... ]]`, so the binary is skipped without a warning — caught by hand during v1.1.0 and uploaded separately
  - [ ] Fix: stage the onefile before the DMG build, or give the two targets separate output paths
- [ ] **`cli.py` overrides `TODOSCOPE_DATA_DIR` instead of honouring it**: [cli.py:144](scanner/cli.py#L144) assigns `~/.todoscope` unconditionally, so an operator or test cannot point the CLI at another data dir. Fix: `os.environ.get("TODOSCOPE_DATA_DIR") or os.path.expanduser("~/.todoscope")`. #cli
- [ ] **TODO.md's own convention table becomes kanban cards**: the blockquote table at the head of this file (and the copies in README/TODO_CONVENTION) parses into cards like "In Progress | ## In Progress | # FIXME:". Blockquoted table rows should not produce cards. #kanban #parser

## Completed

> Full history archived in [docs/completed-todos.md](docs/completed-todos.md).

- [x] **v1.1.0 released**: tagged on master, GitHub release with macOS binary + Linux binary + DMG, clean GHCR image, cask published to `Sage-is/homebrew-apps` — `brew install --cask sage-is/apps/todoscope`. Cask verified by rehearsing the real install (download → sha match → quarantine flag → postflight strip → launch → `/health` reports 1.1.0, `/api/mcpo/manifest` 200) — 2026-08-16 #release
- [x] **SECURITY: access keys leaked in the public Docker image**: no `.dockerignore` existed, so `COPY . /app/` swept the gitignored `scanner/access_keys.csv` into `ghcr.io/startr/todoscope`. Tags `v1.0.0`, `v1.1.0`, `latest` all carried a live key. Remediated 2026-08-16: key rotated, `.dockerignore` added (build context 3.85 GB → 35 MB), clean images pushed over `v1.1.0` and `latest`, and every leaked version deleted — including two *untagged* digests that still served the key after the tagged ones were gone. Registry now holds one clean version. #security #docker
- [x] **Fix inline TODO comments rendering as markdown headings**: `#` doubles as `<h1>`, so `# TODO: x` painted as a giant heading; `inline_todo_to_card` now strips comment syntax. 10 tests — 2026-08-16 #kanban
- [x] **Fix "Last Scanned" always reading never**: scan state is keyed by directory basename, the lookup used the display name — any repo registered under a different name showed `never`. Regression test added — 2026-08-16 #ux
- [x] **Fix `local_path` leak**: scan-stream `init` now includes the filesystem path for authed viewers only (no-keys instances unaffected); locked by 2 tests in `test_public_repo_privacy.py` — 2026-08-15 #security #privacy
- [x] **Multi-host repo support**: GitHub / GitLab / Codeberg / Bitbucket / sourcehut + pure-local; five verification lanes pass; no-origin stream bug fixed — 2026-08-15 #core #frontend
- [x] **Incremental scans + live board (Phase 2)**: git-diff incremental with scan_state (six-scenario verify), server-rendered fragments, `/events` SSE, watchdog, checkbox write-back — 2026-08-15 #performance #core
