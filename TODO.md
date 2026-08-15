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

## In Progress

### Brand & Landing Page — Scope A (Logged-Out Landing) #brand #landing

The current login page is a cold password prompt with zero context. Turn it into a proper landing page.
The one-line pitch is: *"See every TODO across all your repos. The awareness layer for teams — and the AI agents on them — who need to know what's actually unfinished."*

- [ ] **Promote login.html into a real landing page**: hero, pitch, features, sign-in #brand #landing #critical
  - [x] Add brand hero: headline, subhead, and a short "what it is" paragraph
  - [x] Add a 3-bullet "what makes it different" strip (the inversion, MCP-native, open-source)
  - [x] Embed screenshot above the fold
  - [x] Move the sign-in form into a secondary section below the hero
  - [ ] Add "New to TodoScope?" copy with link to README / GitHub
  - [ ] Add social proof / cross-links to sage.is and startr.style
  - [ ] Add OG meta tags (`og:title`, `og:description`, `og:image`)
- [ ] **Surface the MCP / AI agent story on the landing page** #brand #ai #mcp
  - [ ] Add a "Connect your AI agent" section
  - [ ] Link directly to `/api/mpco/manifest` and `/api/mpco/openapi.json`
  - [ ] Include a one-paragraph framing: "AI agents are part of your team"

### Release Pipeline — Package Foundation #release #packaging

- [x] **Create `pyproject.toml`**: package metadata, entry point, setuptools build #packaging
- [x] **Create `scanner/cli.py`**: CLI entry point #cli #packaging
- [x] **Update `scanner/app.py`**: frozen app + data dir + auto-migrate support #packaging #core
- [x] **`__version__` already in `scanner/__init__.py`** at 1.0.0 #packaging
- [x] **Verified**: `pip install -e .` → `todoscope` command starts server, auto-migrates repos to `~/.todoscope/`

### Multi-host repo support #core #frontend

- [x] **Support GitLab / Gitea / Codeberg / Bitbucket / sourcehut + clean pure-local repos** #core #frontend
  - [x] Add `parse_git_origin()` + `build_web_*_url()` helpers in `scanner/app.py`
  - [x] Replace `_code_dev_url` and extend SSE `init` payload with `web_file_url_template`
  - [x] Update `stream_results.html` to consume SSE template instead of github-only regex
  - [x] Rename `code_dev_url` → `web_view_url`; update labels and `index.html` placeholder
  - [ ] Verify: GitHub, GitLab.com, codeberg.org, bitbucket.org, registered local repo

### Incremental scans #performance #core

- [x] **Re-scan only files changed since last run (git-diff incremental)** #performance #core
  - [x] Add `scan_state_path` / `load_scan_state` / `save_scan_state` helpers in `scanner/app.py`
  - [x] Add `git_changed_paths(repo_path, last_sha)` returning (changed, deleted) sets
  - [x] Add `rescan_files(repo_path, rel_paths, exclusions)` — shared helper for both git-diff and future watch path
  - [x] Wire incremental vs full-scan choice into `stream_data`; persist state at end
  - [x] Invalidate on: exclusions hash change, force-push (last SHA unreachable), corrupt cache
  - [ ] Verify: first scan, no-op re-scan, single-file edit, branch switch, force-push, exclusions change
- [ ] **Phase 2: live board — server watches, browser morphs** #performance #core
  - [x] `scanner/fragments.py` + Jinja partials: server renders board/list HTML; one truth on the wire (markdown-it-py, GFM task lists, blame badges server-side)
  - [x] Client: deleted `createTodoElement` / `createTodoMarkdownElement` / `renderKanban` DOM builders; idiomorph morphs fragments in place (scroll and state survive)
  - [x] `scanner/live.py`: watchdog observer per registered local repo — lazy start/stop with subscribers, 400ms debounce, ignores its own `KANBAN.canvas` writes
  - [x] `/events/<repo>` persistent SSE channel with heartbeats; GitHub webhook publishes to it; cloned repos poll git at 60s while subscribed
  - [x] No-change law: unchanged repo → cached fragments served, zero scanning; dirty repo → `rescan_files` incremental only
  - [x] Deleted the client 3s fetch-poll and `location.reload()` doorbell; removed marked.js (markdown renders server-side)
  - [x] Page load never pulls local repos (working copy is the truth); clones pull behind the cached paint
  - [x] Checkbox write-back: `POST /api/todo_toggle` flips `- [ ]` ↔ `- [x]` atomically — line-content hash guard (stale view → 409), authed + local repos only, watchdog round-trip morphs the confirmation into every tab
  - [x] Verify: edit TODO.md in an editor → board morphs in ~1s without reload; second browser tab stays in sync
  - [ ] PyInstaller spec: add hiddenimports for `watchdog`, `markdown_it`, `mdit_py_plugins` so binary builds keep live mode #packaging

### Subdirectory Migration #development #structure

- [ ] **Migrate Python files and dependencies to subdirectory structure**
  - [x] Create scanner subdirectory
  - [x] Implement `__init__.py`
  - [x] Move `error_handling.py` to scanner subdirectory
  - [x] Update imports in `app.py`
  - [x] Move remaining Python files (test files) to `scanner/tests`
  - [x] Move Pipfile and Pipfile.lock to scanner subdirectory
  - [ ] Test and update the Makefile accordingly

## TODO

### Brand & Landing Page — Scope B (Dashboard) #ux #dashboard

- [ ] **Dashboard orientation**: header, pitch, visual hierarchy #ux #brand
  - [ ] Add a dashboard header: restate the one-line pitch, orient the user
  - [ ] Move the GitHub contribute banner to the footer #hierarchy
- [ ] **Repo entry UX**: one smart input, onboarding empty state, inline help #ux #simplify #onboarding
  - [ ] Unify repo entry: one input that accepts a git URL *or* a local path, with smart detection
  - [ ] Empty state for Repositories: onboarding card with quick-start actions
  - [ ] Clarify the "shallow clone" checkbox: tooltip or inline help #copy
- [ ] **Repositories table tooling**: search, freshness, refresh #ux #search
  - [ ] Add search/filter to the Repositories table
  - [ ] Add a visible "last scanned" timestamp + manual refresh control per repo row

### Brand & Landing Page — Scope C (MCP / Sage.is Integration) #ai #mcp #integration

- [ ] **MCP integration surface**: dedicated page, dashboard shortcuts, guide, health #mcp #ux #docs
  - [ ] Create a dedicated `/connect` or `/mcp` page with step-by-step instructions
  - [ ] Surface MCP endpoints on the dashboard: copy-to-clipboard manifest URL and sample cURL #ai
  - [ ] Write a short guide — `docs/connect-sage.md` — with screenshots
  - [ ] Add an MCP health indicator to the dashboard #observability

### Brand & Landing Page — Scope D (Brand Consistency) #brand #copy

- [ ] **Brand voice audit**: all user-facing copy and errors #copy #brand
  - [ ] Audit all user-facing copy against the brand interview voice
  - [ ] Error messages: review for tone — honest founder voice, not generic Flask errors #ux

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
  - [x] README section: convention explainer + install snippet under AI & MCP Integration
  - [ ] Landing page: mention the skill in the "Connect your AI agent" section
  - [ ] `/connect` page: skill install step alongside MCP setup
  - [ ] Scanner nudge: when a board is mostly bare single-line cards, suggest running the skill
  - [ ] Cross-post via sage.is and startr.style channels

### Documentation #documentation

- [ ] **Create comprehensive API documentation**: Standalone API reference guide #documentation #api
  - [ ] Document all endpoints with request/response examples
  - [ ] Add error code reference
  - [ ] Include authentication documentation
  - [ ] Test API documentation completeness
- [ ] **Add architecture documentation**: System design and component overview #documentation #architecture
  - [ ] Create component diagram
  - [ ] Document data flow
  - [ ] Document deployment options
  - [ ] Verify architecture docs match current implementation
- [ ] **Create contributor guide**: Detailed guide for new contributors #documentation #community
  - [ ] Define code style guide
  - [ ] Document testing requirements
  - [ ] Define pull request process
  - [ ] Test contributor onboarding process
- [ ] **Create development workflow documentation** #documentation #development
  - [ ] Document setup process
  - [ ] Document feature development cycle
  - [ ] Document testing procedures

### Features #feature

- [ ] **Explore scan results**: search, README context, metrics, exports #ux #reporting
  - [ ] Add README summary to scan results: show the top of each repo's README in the web interface #frontend
  - [ ] Search: implement a search feature for TODO comments #search
  - [ ] Metrics dashboard: visualize TODO metrics across projects
  - [ ] Report downloads: offer CSV, JSON, PDF export of scan results

### Tech Debt #tech-debt

- [x] **Refactor `stream_results.html` JS**: superseded — the hand-built DOM builders are deleted; the server renders partials and the client morphs them (see Phase 2 live board). #frontend #dry

## Backlog

- [ ] **Inline TODO completion tracking**: Snapshot-and-diff approach to detect when inline TODOs are removed between scans and show them as completed in the Done column. Uses `.todoscope-snapshot.json` and `.todoscope-done.json`. Git-history-independent — works on shallow clones. #feature #kanban
- [ ] **TODO editor — remaining scope**: add-TODO form, edit card text, and drag-between-columns write-back. Checkbox toggling shipped (see Phase 2 live board). #feature #editor #kanban
- [ ] **Publish CapRover one-click app source**: Add `caprover-one-click.yml` to the Sage-is one-click repo #deployment #caprover
- [ ] **Scanner extensibility**: smarter parsing, plugins, external integrations #architecture #integration
  - [ ] Priority inference from TODO comments #core #parser
  - [ ] Plugin system to extend scanner functionality #extensibility
  - [ ] Task manager integration (Jira, Asana, Trello) #external
- [ ] **Ralph-loop agent mode**: run an agent loop against TODO.md as the state file — each iteration picks the next unfinished item, works it, checks it off, commits. Fresh context per pass via `claude -p` in a bash loop (true Ralph) or `/loop` with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` lowered to force frequent compaction (approximation). TODO.md is already the ideal Ralph state file. #ai #agent #automation

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

## Bugs

*No known bugs. Use `# BUG:` inline tags to flag defects in source.*

## Completed

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
