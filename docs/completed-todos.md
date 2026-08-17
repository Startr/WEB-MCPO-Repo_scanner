# Completed TODOs — full records

Shipped cards moved off the board's In Progress column, verbatim, with their
evidence notes. The board keeps one-liners in `## Completed`; the detail lives
here.

## 2026-08-15 register pass

### Documentation #documentation

- [x] **Create comprehensive API documentation**: Standalone API reference guide — rewritten 2026-08-15 against current code (was June-2025 vintage: claimed no auth, invented a /stream route and error codes that never existed, called the response envelope MCP) #documentation #api
  - [x] Document all endpoints with request/response examples (web routes table, SSE event types, JSON APIs, tool API)
  - [x] Add error code reference (400/401/403/404/409/429/500 mapped to real routes)
  - [x] Include authentication documentation (session + ?key + Bearer, public routes, public-repo prefixes)
  - [x] Test API documentation completeness — fresh-eyes verifier passed; its two nits (repo_fingerprint key shape, task-line bullet forms) fixed
- [x] **Add architecture documentation**: System design and component overview — rewritten 2026-08-15 (dropped the speculative microservices/PostgreSQL future section, GitPython claim, planned-CLI claim) #documentation #architecture
  - [x] Create component diagram (mermaid: Flask, scan core, fragments, live watcher, kanban, CLI, Tauri shell)
  - [x] Document data flow (SSE scan with incremental decision; live board watchdog → fragments → /events → idiomorph)
  - [x] Document deployment options (pipenv, pip, Docker/GHCR, PyInstaller, .app/DMG, Tauri)
  - [x] Verify architecture docs match current implementation — verifier caught the false "paths never leave the server" security note (contradicted the local_path bug) and a missing .obsidian in the skip list; both fixed
- [x] **Create contributor guide**: rewritten 2026-08-15 (removed make run/make lint ghosts, wrong mpco_response import, unrepresentative style examples, unbuilt DB-migration section) #documentation #community
  - [x] Define code style guide (matches the actual codebase register)
  - [x] Document testing requirements (make test mechanics, deferred scanner.app import pattern)
  - [x] Define pull request process (develop working / master release, verified from history)
  - [x] Test contributor onboarding process — verifier passed; its decorator-scope nit fixed
- [x] **Create development workflow documentation** — rewritten 2026-08-15 #documentation #development
  - [x] Document setup process (verifier caught that `pipenv run todoscope` only worked via a global editable install; fixed for real: scanner/Pipfile now installs the project editable, entry point verified in the venv)
  - [x] Document feature development cycle (board conventions, Tauri attach loop via TODOSCOPE_DEV_PORT)
  - [x] Document testing procedures (verifier also caught the auth-file location under the CLI — ~/.todoscope/access_keys.csv, not scanner/; reworded)

### Brand & Landing Page — Scope D (Brand Consistency) #brand #copy

- [x] **Brand voice audit**: all user-facing copy and errors #copy #brand
  - [x] Audit all user-facing copy against the brand interview voice — 24 findings via 4-auditor + 2-judge workflow, all double-accepted and applied 2026-08-15; biggest: the "MCP" claim was false (plugin manifest + OpenAPI, not the Model Context Protocol) — relabeled to "tool API" across landing, dashboard, /connect, README badge and body; also fixed the webhook "secret below" that was never displayed, the "read-only scan" line that was false for authed local views, and the backwards "never sent to the browser" path promise
  - [x] Error messages: review for tone — honest founder voice, not generic Flask errors: 401 body, bad-key login, empty repo input, scan-failure SSE (now "Scan stopped: …" without the client's doubled "Error:" prefix), manifest/OpenAPI product naming ("TODO Scanner" → "TodoScope"), cli --share hint and --help tagline #ux

### Brand & Landing Page — Scope C (MCP / Sage.is Integration) #ai #mcp #integration

- [x] **MCP integration surface**: dedicated page, dashboard shortcuts, guide, health #mcp #ux #docs
  - [x] Create a dedicated `/connect` page: four steps (key, manifest, curl proof, skill), endpoints table, live MCP status chip — authed route, verified via test client 2026-08-15
  - [x] Surface MCP endpoints on the dashboard: "AI agents" strip with copy-to-clipboard manifest URL and sample cURL #ai
  - [x] Write a short guide — `docs/connect-sage.md` — with headless-Chrome screenshots (`docs/images/`)
  - [x] Add an MCP health indicator to the dashboard: manifest probe drives a status dot on both `/` and `/connect` (found + fixed: startr.style `--bgc` custom property beats `style.backgroundColor`, so the JS sets the property) #observability

### Brand & Landing Page — Scope B (Dashboard) #ux #dashboard

- [x] **Dashboard orientation**: header, pitch, visual hierarchy #ux #brand
  - [x] Add a dashboard header: restate the one-line pitch, orient the user
  - [x] Move the GitHub contribute banner to the footer #hierarchy
- [x] **Repo entry UX**: one smart input, onboarding empty state, inline help #ux #simplify #onboarding
  - [x] Unify repo entry: one input that accepts a git URL *or* a local path, with smart detection (decided 2026-08-15: detect + live hint chip; `_classify_repo_input` server-side mirrors the client hint, `/add_local` route kept for API/tests)
  - [x] Empty state for Repositories: onboarding card with quick-start actions (prefills the input with TodoScope's own repo)
  - [x] Clarify the "shallow clone" checkbox: tooltip explains speed vs thin git history #copy
- [x] **Repositories table tooling**: search, freshness, refresh #ux #search
  - [x] Add search/filter to the Repositories table (client-side, hides webhook sub-rows too)
  - [x] Add a visible "last scanned" timestamp + manual refresh control per repo row (`scanned_at` from scan state; ⟳ link passes `refresh=1` → full rescan bypassing the incremental cache — verified via SSE status assertions 2026-08-15)

### Brand & Landing Page — Scope A (Logged-Out Landing) #brand #landing

The current login page is a cold password prompt with zero context. Turn it into a proper landing page.
The one-line pitch is: *"See every TODO across all your repos. The awareness layer for teams — and the AI agents on them — who need to know what's actually unfinished."*

- [x] **Promote login.html into a real landing page**: hero, pitch, features, sign-in #brand #landing #critical
  - [x] Add brand hero: headline, subhead, and a short "what it is" paragraph
  - [x] Add a 3-bullet "what makes it different" strip (the inversion, MCP-native, open-source) — the "MCP-native" bullet was later corrected to "open source" by the 2026-08-15 brand audit
  - [x] Embed screenshot above the fold
  - [x] Move the sign-in form into a secondary section below the hero
  - [x] Add "New to TodoScope?" copy with link to README / GitHub
  - [x] Add social proof / cross-links to sage.is and startr.style
  - [x] Add OG meta tags (`og:title`, `og:description`, `og:image`)
- [x] **Surface the MCP / AI agent story on the landing page** #brand #ai #mcp
  - [x] Add a "Connect your AI agent" section — "Your AI teammates can see what's unfinished" with 3-step onboarding + endpoints table + curl example
  - [x] Link directly to `/api/mpco/manifest` and `/api/mpco/openapi.json`
  - [x] Include a one-paragraph framing: "AI agents are part of your team"

### Multi-host repo support #core #frontend

- [x] **Support GitLab / Gitea / Codeberg / Bitbucket / sourcehut + clean pure-local repos** #core #frontend
  - [x] Add `parse_git_origin()` + `build_web_*_url()` helpers in `scanner/app.py`
  - [x] Replace `_code_dev_url` and extend SSE `init` payload with `web_file_url_template`
  - [x] Update `stream_results.html` to consume SSE template instead of github-only regex
  - [x] Rename `code_dev_url` → `web_view_url`; update labels and `index.html` placeholder
  - [x] Verify: GitHub, GitLab.com, codeberg.org, bitbucket.org, registered local repo — all five pass (2026-08-15): live-host URL checks confirmed each template's grammar and line anchor (GitHub routes via vscode.dev by design; GitLab `/-/blob/#L`, Forgejo `src/branch/#L`, Bitbucket `src/#lines-`); pure-local lane surfaced and fixed a real bug — `get_repo_origin_url` now treats a missing origin remote as a normal state (returns `''`) instead of a ~3s retry-then-error that killed the stream and hid the repo from the listing

### Incremental scans #performance #core

- [x] **Re-scan only files changed since last run (git-diff incremental)** #performance #core
  - [x] Add `scan_state_path` / `load_scan_state` / `save_scan_state` helpers in `scanner/app.py`
  - [x] Add `git_changed_paths(repo_path, last_sha)` returning (changed, deleted) sets
  - [x] Add `rescan_files(repo_path, rel_paths, exclusions)` — shared helper for both git-diff and future watch path
  - [x] Wire incremental vs full-scan choice into `stream_data`; persist state at end
  - [x] Invalidate on: exclusions hash change, force-push (last SHA unreachable), corrupt cache
  - [x] Verify: first scan, no-op re-scan, single-file edit, branch switch, force-push, exclusions change — all six pass (2026-08-15, six isolated E2E fixtures; two hardening fixes landed: incremental path now uses the canvas-filtered change set, and `find_todos` skips `KANBAN.canvas` by name instead of trusting `file --mime`)
- [x] **Phase 2: live board — server watches, browser morphs** #performance #core
  - [x] `scanner/fragments.py` + Jinja partials: server renders board/list HTML; one truth on the wire (markdown-it-py, GFM task lists, blame badges server-side)
  - [x] Client: deleted `createTodoElement` / `createTodoMarkdownElement` / `renderKanban` DOM builders; idiomorph morphs fragments in place (scroll and state survive)
  - [x] `scanner/live.py`: watchdog observer per registered local repo — lazy start/stop with subscribers, 400ms debounce, ignores its own `KANBAN.canvas` writes
  - [x] `/events/<repo>` persistent SSE channel with heartbeats; GitHub webhook publishes to it; cloned repos poll git at 60s while subscribed
  - [x] No-change law: unchanged repo → cached fragments served, zero scanning; dirty repo → `rescan_files` incremental only
  - [x] Deleted the client 3s fetch-poll and `location.reload()` doorbell; removed marked.js (markdown renders server-side)
  - [x] Page load never pulls local repos (working copy is the truth); clones pull behind the cached paint
  - [x] Checkbox write-back: `POST /api/todo_toggle` flips `- [ ]` ↔ `- [x]` atomically — line-content hash guard (stale view → 409), authed + local repos only, watchdog round-trip morphs the confirmation into every tab
  - [x] Verify: edit TODO.md in an editor → board morphs in ~1s without reload; second browser tab stays in sync
  - [x] PyInstaller spec: add hiddenimports for `watchdog`, `markdown_it`, `mdit_py_plugins` so binary builds keep live mode #packaging

## Historical completions (archived from the board 2026-08-16)

Moved out of TODO.md's `## Completed` column to keep the board readable. Every
item is verbatim; nothing was reworded or dropped.

### v1.1.0 release cycle — 2026-08-15 / 2026-08-16

- [x] **v1.1.0 released**: tagged on master, GitHub release with macOS binary + Linux binary + DMG, clean GHCR image, cask published to `Sage-is/homebrew-apps` — `brew install --cask sage-is/apps/todoscope`. Cask verified by rehearsing the real install (download → sha match → quarantine flag → postflight strip → launch → `/health` reports 1.1.0, `/api/mcpo/manifest` 200) — 2026-08-16 #release
- [x] **SECURITY: access keys leaked in the public Docker image**: no `.dockerignore` existed, so `COPY . /app/` swept the gitignored `scanner/access_keys.csv` into `ghcr.io/startr/todoscope`. Tags `v1.0.0`, `v1.1.0`, `latest` all carried a live key. Remediated 2026-08-16: key rotated, `.dockerignore` added (build context 3.85 GB → 35 MB), clean images pushed over `v1.1.0` and `latest`, and every leaked version deleted — including two *untagged* digests that still served the key by digest after the tagged ones were gone. Registry now holds one clean version. #security #docker
- [x] **Fix inline TODO comments rendering as markdown headings**: `#` doubles as `<h1>`, so `# TODO: x` painted as a giant heading; `inline_todo_to_card` now strips comment syntax. 10 tests — 2026-08-16 #kanban
- [x] **Fix "Last Scanned" always reading never**: scan state is keyed by directory basename, the lookup used the display name — any repo registered under a different name showed `never`. Regression test added — 2026-08-16 #ux
- [x] **Fix `local_path` leak**: scan-stream `init` now includes the filesystem path for authed viewers only (no-keys instances unaffected); locked by 2 tests in `test_public_repo_privacy.py` — 2026-08-15 #security #privacy
- [x] **Incremental-scan benchmark**: `test_incremental_scan_perf.py`, 400-file fixture timed with timeit — full 6.21s, incremental 0.58s (10.7x), cached 0.09s (65.8x); 2x floor asserted in CI — 2026-08-15 #performance #testing
- [x] **Documentation refresh**: all four docs rewritten against current code and fresh-eyes verified; 6 verifier findings fixed, incl. `pipenv run todoscope` now working from a fresh clone (editable install in scanner/Pipfile) — 2026-08-15 #documentation
- [x] **Brand & Landing — Scope D (Brand Consistency)**: 24-finding voice audit applied; false MCP claim relabeled "tool API"; error messages moved to founder voice — 2026-08-15 #brand #copy
- [x] **Brand & Landing — Scope C (MCP / Sage.is Integration)**: `/connect` page, dashboard tool-API strip with live status dot, `docs/connect-sage.md` with screenshots — 2026-08-15 #ai #mcp #integration
- [x] **Brand & Landing — Scope B (Dashboard)**: header + pitch, unified smart repo input with live hint, empty state, table filter, Last Scanned + force-rescan — 2026-08-15 #ux #dashboard
- [x] **Brand & Landing — Scope A (Logged-Out Landing)**: hero, features strip, screenshot, agent section, OG meta — 2026-08-15 #brand #landing
- [x] **Multi-host repo support**: GitHub / GitLab / Codeberg / Bitbucket / sourcehut + pure-local; five verification lanes pass; no-origin stream bug fixed — 2026-08-15 #core #frontend
- [x] **Incremental scans + live board (Phase 2)**: git-diff incremental with scan_state (six-scenario verify), server-rendered fragments, `/events` SSE, watchdog, checkbox write-back — 2026-08-15 #performance #core

### Release Pipeline — Repo Rename #release #brand

- [x] **Rename GitHub repo**: `Startr/WEB-MCPO-Repo_scanner` → `Startr/TodoScope` #brand
- [x] **Update Docker image**: `ghcr.io/startr/todoscope` #docker #brand
- [x] **Update all internal references**: pyproject.toml, scripts, templates, docs, README, CapRover #brand
- [x] **Convention**: clone to `GIT-TodoScope/` locally for dev clarity #brand
- [x] **Verified**: 45 tests passing, all links updated

### Release Pipeline — Mac .app + DMG + Menu Bar #release #macos #app

Superseded by the Tauri shell for distribution, but the pystray menu-bar path
still ships as the CLI's Finder-launch mode.

- [x] **Build .app**: `make app` → TodoScope.app wrapper around PyInstaller binary #macos
- [x] **Create DMG**: `make dmg` → styled DMG via `create-dmg` with background + Applications link #macos
- [x] **App icon**: real 🔭 Apple Color Emoji via canvas+receiver (`scripts/generate_emoji_icon.sh`) #design
- [x] **Menu bar icon**: 🔭 on transparent background via canvas+receiver (`scripts/generate_menu_icon.sh`) #design
- [x] **pystray menu bar app**: 🔭 in menu bar with Open Browser, Show Log, Quit #macos
- [x] **Dock icon toggle**: Hide/Show Dock Icon menu item via NSApp.setActivationPolicy ctypes #macos
- [x] **Duplicate instance prevention**: detects running server, opens browser instead #reliability
- [x] **Data persistence**: local_repos.yaml, access_keys.csv, repositories all in `~/.todoscope/` #data
- [x] **Verified**: .app launches → Dock icon bounces → 🔭 in menu bar → browser opens → all menu items work

### Release Pipeline — build plumbing (completed legs)

- [x] **Create `scripts/todoscope`**: bash CLI wrapper (11 commands, dev mode, tunnels) #cli #docker
- [x] **Dev mode**: smart repo discovery, source mounting, hot reload #developer-experience
- [x] **Tunnel commands**: `todoscope tunnel` + `todoscope tailscale` #networking
- [x] **Create `todoscope.spec`**: PyInstaller spec file (two targets: CLI onefile + .app windowed) #packaging
- [x] **Add dev deps to Pipfile**: pyinstaller, build, twine #packaging
- [x] **Makefile targets**: binary, binary_dir, app, dmg, pypi_build, pypi_publish, clean_dist #build
- [x] **Verified**: `make binary` → `dist/todoscope` (11MB ARM64) → `./dist/todoscope --version` → `1.0.0`
- [x] **Icon wired**: `--icon assets/todoscope.icns` in app target #design
- [x] **Styled DMG**: `create-dmg` with background, icon positions, Applications drop link #design
- [x] **Cross-platform builds** (Docker, zero cloud CI): `binary_linux` via `cdrx/pyinstaller-linux`; `binary_windows` via `cdrx/pyinstaller-windows` + Wine; `docker_push` to `ghcr.io/startr/todoscope` #build
- [x] **`scripts/release_all.sh`**: one command builds ALL artifacts + uploads via `gh` CLI #automation
- [x] **`make release_all` target**: calls release_all.sh #build
- [x] Add `Casks/todoscope.rb` to `Sage-is/homebrew-apps`: Tauri .app via DMG with dequarantine postflight; version/sha256 maintained by the tap-update step in `scripts/release_all.sh`

### Tauri shell (v2.0) — completed legs

- [x] Sidecar on PyInstaller `--onedir` (`make sidecar_dir`), bundled whole via `bundle.macOS.files` — no externalBin, real pid, tauri#11992 sidestepped
- [x] Rust surface thin: spawn sidecar, SIGTERM kill on quit, sticky OS-assigned port + `--exact-port` handshake, `/health` readiness poll — one main.rs
- [x] Window opens on `http://127.0.0.1:PORT` programmatically after readiness — web UI ships unchanged, same-origin, no CORS
- [x] Menu bar (App/Edit/View) with Cmd+= / Cmd+− / Cmd+0 zoom, factor persisted; remember-me login (30-day session); tray "Share on Network" toggle — auth-gated, rebinds `0.0.0.0`, LAN URL dialog
- [x] pywebview path retired — researched and declined, [reality check](efforts/app-shell-v2/decisions/pywebview-reality-check.md)

### Core product history

- [x] **Release Pipeline — Package Foundation**: pyproject.toml, scanner/cli.py entry point, frozen-app + data-dir support in app.py, `__version__` single source; verified via `pip install -e .` #release #packaging
- [x] **Subdirectory Migration**: Python files, tests, and Pipfiles under scanner/; imports and Makefile updated, exercised end-to-end 2026-08-15 #development #structure
- [x] **Refactor `stream_results.html` JS**: superseded — the hand-built DOM builders are deleted; the server renders partials and the client morphs them (see Phase 2 live board). #frontend #dry
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
