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

The `todo-scope` Claude Code skill bootstraps and aligns a repo's TODO.md to TodoScope conventions. It ships in this repo at `.claude/skills/todo-scope/SKILL.md`.

- [ ] **Publish the todo-scope skill**: ship with the repo, package, document install #skill #packaging
  - [x] Vendor `SKILL.md` into `.claude/skills/todo-scope/` — auto-loads for Claude Code users working in this repo
  - [x] Generalize personal paths and fix the repo URL in the published copy
  - [x] Document manual install in README: curl into `~/.claude/skills/todo-scope/`
  - [ ] Package as a Claude Code plugin for one-command install
- [ ] **Promote the skill**: in-app nudges and outreach #brand #ux
  - [x] README section: convention explainer + install snippet under AI & Agent Integration (heading renamed 2026-08-15)
  - [x] Landing page: mention the skill in the "Connect your AI agent" section (2026-08-15)
  - [x] `/connect` page: skill install step alongside MCP setup (step 4, with copy button — 2026-08-15)
  - [ ] Scanner nudge: when a board is mostly bare single-line cards, suggest running the skill
  - [ ] Cross-post via sage.is and startr.style channels

### Features #feature

- [ ] **Explore scan results**: search, README context, metrics, exports #ux #reporting
  - [ ] Add README summary to scan results: show the top of each repo's README in the web interface #frontend
  - [ ] Search: implement a search feature for TODO comments #search
  - [ ] Metrics dashboard: visualize TODO metrics across projects
  - [ ] Report downloads: offer CSV, JSON, PDF export of scan results

### Tech Debt #tech-debt

- [x] **Refactor `stream_results.html` JS**: superseded — the hand-built DOM builders are deleted; the server renders partials and the client morphs them (see Phase 2 live board). #frontend #dry

## Backlog

- [ ] **MCPO: settle the MCP story** (rename shipped) #ai #mcp #decision
  - [x] The intended name is MCPO (old repo `Startr/WEB-MCPO-Repo_scanner`, "MCPo API" in Completed and README); routes shipped letter-swapped as `/api/mpco/*` in the founding commit `eb67dac` (2025-05-22) — census in [board-dossiers](docs/board-dossiers.md)
  - [x] Rename routes to `/api/mcpo/*` — done 2026-08-15 as a clean break (decided: no redirects, old paths dead); code + templates by hand, six docs via opencode delegate-edit (78s, diff verified), screenshots retaken, suite green
  - [ ] Decide the fork: real MCP server endpoint (JSON-RPC `tools/list` + `tools/call`) or retire the MCP term project-wide — deferred 2026-08-15; UI copy says "tool API" either way
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

### Release Pipeline — Repo Rename #release #brand

- [x] **Rename GitHub repo**: `Startr/WEB-MCPO-Repo_scanner` → `Startr/TodoScope` #brand
- [x] **Update Docker image**: `ghcr.io/startr/todoscope` #docker #brand
- [x] **Update all internal references**: pyproject.toml, scripts, templates, docs, README, CapRover #brand
- [x] **Convention**: clone to `GIT-TodoScope/` locally for dev clarity #brand
- [x] **Verified**: 45 tests passing, all links updated

### Release Pipeline — Docker CLI Wrapper + Dev Mode #release #docker #homebrew

- [x] **Create `scripts/todoscope`**: bash CLI wrapper (11 commands, dev mode, tunnels) #cli #docker
- [x] **Dev mode**: smart repo discovery, source mounting, hot reload #developer-experience
- [x] **Tunnel commands**: `todoscope tunnel` + `todoscope tailscale` #networking
- [ ] **Verify end-to-end**: `scripts/todoscope start` → open → dev → tunnel (needs Docker image built) #testing

### Release Pipeline — PyInstaller Binary Build (macOS + Linux + Windows) #release #binary #packaging

- [x] **Create `todoscope.spec`**: PyInstaller spec file (two targets: CLI onefile + .app windowed) #packaging
- [x] **Add dev deps to Pipfile**: pyinstaller, build, twine #packaging
- [x] **Makefile targets**: binary, binary_dir, app, dmg, pypi_build, pypi_publish, clean_dist #build
- [x] **Verified**: `make binary` → `dist/todoscope` (11MB ARM64) → `./dist/todoscope --version` → `1.0.0`
- [ ] **Cross-platform binaries — build & verify** #linux #windows #testing
  - [ ] Linux binary: PyInstaller on ubuntu (x86_64) — works in tmux/SSH #linux
  - [ ] Windows binary: PyInstaller on windows (.exe) #windows
  - [ ] Verify macOS: `make binary` → `./dist/todoscope --port 5001` → browser opens, SSE works
  - [ ] Verify Linux (headless): `./todoscope --no-browser --port 5001` → access via tunnel or LAN
  - [ ] Verify Windows: `todoscope.exe` → browser opens, SSE works

### Release Pipeline — Mac .app + DMG + Menu Bar #release #macos #app

- [x] **Build .app**: `make app` → TodoScope.app wrapper around PyInstaller binary #macos
- [x] **Create DMG**: `make dmg` → styled DMG via `create-dmg` with background + Applications link #macos
- [x] **App icon**: real 🔭 Apple Color Emoji via canvas+receiver (`scripts/generate_emoji_icon.sh`) #design
- [x] **Menu bar icon**: 🔭 on transparent background via canvas+receiver (`scripts/generate_menu_icon.sh`) #design
- [x] **pystray menu bar app**: 🔭 in menu bar with Open Browser, Show Log, Quit #macos
- [x] **Dock icon toggle**: Hide/Show Dock Icon menu item via NSApp.setActivationPolicy ctypes #macos
- [x] **Duplicate instance prevention**: detects running server, opens browser instead #reliability
- [x] **Data persistence**: local_repos.yaml, access_keys.csv, repositories all in `~/.todoscope/` #data
- [x] **Verified**: .app launches → Dock icon bounces → 🔭 in menu bar → browser opens → all menu items work

### Release Pipeline — Makefile Targets + Local Cross-Platform Builds #release #build

- [x] **Makefile targets**: binary, binary_dir, app, dmg, pypi_build, pypi_publish, clean_dist #build
- [x] **Icon wired**: `--icon assets/todoscope.icns` in app target #design
- [x] **Styled DMG**: `create-dmg` with background, icon positions, Applications drop link #design
- [x] **Cross-platform builds** (Docker, zero cloud CI): #build
  - [x] `binary_linux`: `cdrx/pyinstaller-linux` Docker container
  - [x] `binary_windows`: `cdrx/pyinstaller-windows` Docker + Wine
  - [x] `docker_push`: push to `ghcr.io/startr/todoscope`
- [x] **`scripts/release_all.sh`**: one command builds ALL artifacts + uploads via `gh` CLI #automation
- [x] **`make release_all` target**: calls release_all.sh #build
- [ ] **Code signing**: Developer ID credentials — consumed by the Tauri shell's bundler, per [the verdict](docs/efforts/app-shell-v2/decisions/the-verdict.md) #macos #security
  - [ ] [MANUALLY] D-U-N-S check for Startr LLC via Apple's lookup (developer.apple.com/enroll/duns-lookup) — use the exact legal name + address from formation docs; request free number if absent (~5 business days). Public D&B directory shows no listing as of 2026-08-01.
  - [ ] [MANUALLY] Pick/confirm the team Apple ID for enrollment; enroll Startr LLC in Apple Developer Program (US$99/yr, org enrollment needs the D-U-N-S)
  - [ ] [MANUALLY] Create Developer ID Application certificate in the developer portal
  - [ ] Superseded by the Tauri verdict: the manual codesign/notarytool Makefile pipeline will not be built — Tauri's bundler automates signing, notarization, stapling, and sidecar signing
  - [x] Meanwhile: unsigned Tauri .app ships via cask with a dequarantine postflight (decided 2026-08-15, [shell build choices](docs/efforts/app-shell-v2/decisions/shell-build-choices.md)) — the postflight is deleted once releases are signed. PyPI leg blocked: the name `todoscope` is taken by an unrelated package.
- [ ] **Verify full release**: `make release_all` → all artifacts built + uploaded

### Release Pipeline — Homebrew Tap #release #homebrew #deployment

- [ ] **Homebrew tap**: formula, cask, ecosystem updates #homebrew
  - [ ] Add `Formula/todoscope.rb` to homebrew-apps: Docker CLI formula — depends_on docker, git, cloudflared (optional), tailscale (optional); installs scripts/todoscope to bin
  - [x] Add `Casks/todoscope.rb` to `Sage-is/homebrew-apps`: Tauri .app via DMG with dequarantine postflight; version/sha256 maintained by the tap-update step in `scripts/release_all.sh`
  - [ ] Update `nuke-sage`: add todoscope to KNOWN_PROJECTS
  - [ ] Verify: `brew install --build-from-source Formula/todoscope.rb` works

### Release Pipeline — Automated Release Flow #release #automation

- [ ] **One-command release**: `make patch_release` + `make release_finish` triggers everything #automation #ci
  - [ ] Auto-bump version in `scanner/__init__.py` to match tag
  - [ ] Run tests before finishing
  - [ ] Tag push → CI builds all artifacts automatically
  - [ ] Post-release summary: GitHub Release link, PyPI link, brew install command
  - [ ] Verify: `make patch_release` → `make release_finish` → all CI green, all channels updated
- [ ] **Version single-source-of-truth**: `scanner/__init__.py` drives everything #packaging
  - [ ] `pyproject.toml` reads version dynamically
  - [ ] PyInstaller embeds it in the binary
  - [ ] `scripts/todoscope` VERSION synced by release script
  - [ ] Homebrew formula URL/SHA256 updated by CI

### Release Pipeline — Future Enhancements #release #future

- [ ] **Tray & Dock polish**: platform icon behavior across macOS, Linux, Windows #macos #cross-platform #design
  - [ ] Dock icon click → Open Browser: respond to `applicationShouldHandleReopen:` via PyObjC NSApplication delegate so clicking the running Dock icon opens the browser #ux
  - [ ] Menu bar icon dark/light mode: research macOS template images for auto-inverting icon on light menu bar
  - [ ] Linux/Windows tray icon colors: research platform-appropriate pystray styling on Linux (GNOME/KDE) and Windows
- [ ] **Tauri shell (v2.0)**: built 2026-08-15 — `src-tauri/` shell, `make tauri_dev`/`tauri_build`/`tauri_dmg`, cask route; settled points in [shell build choices](docs/efforts/app-shell-v2/decisions/shell-build-choices.md) #macos #app #tauri
  - [x] Sidecar on PyInstaller `--onedir` (`make sidecar_dir`), bundled whole via `bundle.macOS.files` — no externalBin, real pid, tauri#11992 sidestepped
  - [x] Rust surface thin: spawn sidecar, SIGTERM kill on quit, sticky OS-assigned port + `--exact-port` handshake, `/health` readiness poll — one main.rs
  - [x] Window opens on `http://127.0.0.1:PORT` programmatically after readiness — web UI ships unchanged, same-origin, no CORS
  - [x] Menu bar (App/Edit/View) with Cmd+= / Cmd+− / Cmd+0 zoom, factor persisted; remember-me login (30-day session); tray "Share on Network" toggle — auth-gated, rebinds `0.0.0.0`, LAN URL dialog
  - [x] pywebview path retired — researched and declined, [reality check](docs/efforts/app-shell-v2/decisions/pywebview-reality-check.md)
  - [ ] Signing era: wire APPLE_* env vars into `tauri build`, re-test tauri#11992 on the pinned version, drop the cask's dequarantine postflight
  - [ ] `kill -9` of the shell orphans the sidecar — consider a parent-pid poll in cli.py
- [ ] **Branding & Poka-Yoke audit**: ensure all user-facing text, errors, and flows are clear and mistake-proof for v1 #brand #ux
  - [x] Copy + error-message leg shipped 2026-08-15 via the brand voice audit (see Completed)
  - [ ] Mistake-proofing pass over flows: poka-yoke devices for destructive and confusing paths

## Bugs

- [ ] **`make binary` output is clobbered by the sidecar build**: `release_all.sh` runs `make binary` (onefile → `dist/todoscope`) then `make tauri_dmg` → `sidecar_dir` → `make binary_dir`, whose onedir output replaces `dist/todoscope` with a *directory*. The upload step tests `[[ -f ... ]]`, so the macOS binary is silently skipped from the release. Caught by hand during the v1.1.0 release; the binary was rebuilt and uploaded separately. Fix: stage the onefile before the DMG build, or give the two targets separate output paths. #release #packaging
- [ ] **`cli.py` overrides `TODOSCOPE_DATA_DIR` instead of honouring it**: [cli.py:144](scanner/cli.py#L144) assigns `~/.todoscope` unconditionally, so an operator or test cannot point the CLI at another data dir. Fix: `os.environ.get("TODOSCOPE_DATA_DIR") or os.path.expanduser("~/.todoscope")`. #cli
- [ ] **TODO.md's own convention table becomes kanban cards**: the blockquote table at the head of this file (and the copies in README/TODO_CONVENTION) parses into cards like "In Progress | ## In Progress | # FIXME:". Blockquoted table rows should not produce cards. #kanban #parser

## Completed

- [x] **v1.1.0 released**: tagged on master, GitHub release with macOS binary + Linux binary + DMG, clean GHCR image, cask published to `Sage-is/homebrew-apps` — `brew install --cask sage-is/apps/todoscope`. Cask verified by rehearsing the real install (download → sha match → quarantine flag → postflight strip → launch → `/health` reports 1.1.0, `/api/mcpo/manifest` 200) — 2026-08-16 #release
- [x] **SECURITY: access keys leaked in the public Docker image**: no `.dockerignore` existed, so `COPY . /app/` swept the gitignored `scanner/access_keys.csv` into `ghcr.io/startr/todoscope`. Tags `v1.0.0`, `v1.1.0`, `latest` all carried a live key. Remediated 2026-08-16: key rotated, `.dockerignore` added (build context 3.85 GB → 35 MB), clean images pushed over `v1.1.0` and `latest`. **Still open: delete the leaked GHCR versions (needs `delete:packages` scope) and untrack `scanner/local_repos.yaml`.** #security #docker
- [x] **Fix inline TODO comments rendering as markdown headings**: `#` doubles as `<h1>`, so `# TODO: x` painted as a giant heading; `inline_todo_to_card` now strips comment syntax. 10 tests — 2026-08-16 #kanban
- [x] **Fix "Last Scanned" always reading never**: scan state is keyed by directory basename, the lookup used the display name — any repo registered under a different name showed `never`. Regression test added — 2026-08-16 #ux
- [x] **Fix `local_path` leak**: scan-stream `init` now includes the filesystem path for authed viewers only (no-keys instances unaffected); locked by 2 tests in `test_public_repo_privacy.py` — 2026-08-15 #security #privacy
- [x] **Incremental-scan benchmark**: `test_incremental_scan_perf.py`, 400-file fixture timed with timeit — full 6.21s, incremental 0.58s (10.7x), cached 0.09s (65.8x); 2x floor asserted in CI — 2026-08-15 #performance #testing
- [x] **Documentation refresh**: all four docs rewritten against current code and fresh-eyes verified; 6 verifier findings fixed, incl. `pipenv run todoscope` now working from a fresh clone (editable install in scanner/Pipfile) — 2026-08-15, full records in [completed-todos](docs/completed-todos.md) #documentation
- [x] **Brand & Landing — Scope D (Brand Consistency)**: 24-finding voice audit applied; false MCP claim relabeled "tool API"; error messages moved to founder voice — 2026-08-15 #brand #copy
- [x] **Brand & Landing — Scope C (MCP / Sage.is Integration)**: `/connect` page, dashboard tool-API strip with live status dot, `docs/connect-sage.md` with screenshots — 2026-08-15 #ai #mcp #integration
- [x] **Brand & Landing — Scope B (Dashboard)**: header + pitch, unified smart repo input with live hint, empty state, table filter, Last Scanned + force-rescan — 2026-08-15 #ux #dashboard
- [x] **Brand & Landing — Scope A (Logged-Out Landing)**: hero, features strip, screenshot, agent section, OG meta — 2026-08-15 #brand #landing
- [x] **Multi-host repo support**: GitHub / GitLab / Codeberg / Bitbucket / sourcehut + pure-local; five verification lanes pass; no-origin stream bug fixed — 2026-08-15 #core #frontend
- [x] **Incremental scans + live board (Phase 2)**: git-diff incremental with scan_state (six-scenario verify), server-rendered fragments, `/events` SSE, watchdog, checkbox write-back — 2026-08-15 #performance #core
- [x] **Release Pipeline — Package Foundation**: pyproject.toml, scanner/cli.py entry point, frozen-app + data-dir support in app.py, `__version__` single source; verified via `pip install -e .` #release #packaging
- [x] **Subdirectory Migration**: Python files, tests, and Pipfiles under scanner/; imports and Makefile updated, exercised end-to-end 2026-08-15 #development #structure
- [x] **Speed up scan**: cached KANBAN board loads instantly on page load while full scan runs in background #performance #ux
- [x] **Fix existing repositories not working**
- [x] **Robust error handling**: custom exceptions, retries, and recovery strategies #core #error-handling
- [x] **Broaden TODO pattern recognition**: FIXME, BUG, NOTE in various comment formats #core #parser
- [x] **DRY Makefile targets** #development #testing
- [x] **Enable streaming of API results** #api #performance
- [x] **TODO.md and TODO.txt file detection** #feature #core
- [x] **Web interface for displaying TODO files** #ux #frontend
- [x] **MCPo API for TODO files** #api #integration
- [x] **GitHub webhook integration** for automated repository scanning #integration #automation
- [x] **TODO file processing**: diverse filenames, root and subdirectory scanning, content display #feature #core
- [x] **Testing infrastructure**: unit and integration tests #core #testing
- [x] **Makefile targets and test runner** #development #testing
- [x] **Honor .gitignore patterns** during repository scans #core
- [x] **Stream scan results** in the web UI #ux #frontend
- [x] **HTML escaping** for multi-line display #security #rendering
- [x] **Fix server hanging** after completing scans #critical #backend
- [x] **Skip `scanner/repositories/`** when scanning this project as a local repo #core #backend
- [x] **User authentication**: access_keys.csv with session and Bearer token auth #security #auth
- [x] **Footer update**: cross-links to sage.is and startr.style #brand #footer
- [x] **Rename "Todoscope" to "TodoScope"** consistently #brand #consistency
- [x] **Favicon**: telescope emoji #brand #visual
- [x] **Page titles**: descriptive, brand-consistent `<title>` tags #brand #seo
- [x] **Noindex on login page** #seo #privacy
- [x] **Meta description**: one-line pitch as default meta description #brand #seo
- [x] **YAML config migration**: `local_repos.yaml` with public/webhook metadata #core #config
- [x] **Line-number tracking** in `parse_todo_md()` for all cards and children #core #kanban
- [x] **Kanban resource links**: board guide, `/resources` page, footer link #feature #kanban
- [x] **Configurable editor link targets**: vscode.dev, VS Code, Cursor, JetBrains, custom URI templates #feature #editor
- [x] **Public repo views**: per-repo public flag, auth bypass for read-only routes #feature #sharing
- [x] **Webhook refresh**: HMAC-SHA256 verification, rate limiting, pull + kanban rebuild #feature #automation
- [x] **Git author visualization**: blame enrichment, author badges on kanban cards #feature #kanban
