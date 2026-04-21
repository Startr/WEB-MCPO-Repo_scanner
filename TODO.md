# TODO — TodoScope

> **Convention** — Sections below map to kanban columns. Inline source-code
> tags use the same vocabulary so items stay cross-referenced between this
> file and the codebase. `KANBAN.canvas` auto-generates from this file and
> inline tags — do not hand-edit it.
>
> | Column      | Markdown section  | Inline tag  |
> |-------------|-------------------|-------------|
> | Backlog     | `## Backlog`      |             |
> | TODO        | `## TODO`         | `# TODO:`   |
> | In Progress | `## In Progress`  | `# FIXME:`  |
> | Bugs        | `## Bugs`         | `# BUG:`    |
> | Done        | `- [x]` items / `## Done` | —   |

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

- [ ] **Add a dashboard header**: restate the one-line pitch, orient the user #ux #brand
- [ ] **Unify repo entry**: one input that accepts a git URL *or* a local path, with smart detection #ux #simplify
- [ ] **Empty state for Repositories**: onboarding card with quick-start actions #ux #onboarding
- [ ] **Surface MCP endpoints on the dashboard**: copy-to-clipboard for manifest URL and sample cURL #ai #mcp #ux
- [ ] **Add search/filter to the Repositories table** #ux #search
- [ ] **Add a visible "last scanned" timestamp + manual refresh control** per repo row #ux
- [ ] **Move the GitHub contribute banner to the footer** #ux #hierarchy
- [ ] **Clarify the "shallow clone" checkbox**: tooltip or inline help #ux #copy

### Brand & Landing Page — Scope C (MCP / Sage.is Integration) #ai #mcp #integration

- [ ] **Create a dedicated `/connect` or `/mcp` page** with step-by-step instructions #mcp #docs
- [ ] **Add a "Copy MCP manifest URL" button** on the dashboard #mcp #ux
- [ ] **Write a short guide** — `docs/connect-sage.md` — with screenshots #docs #mcp
- [ ] **Add an MCP health indicator** to the dashboard #observability #mcp

### Brand & Landing Page — Scope D (Brand Consistency) #brand #copy

- [ ] **Audit all user-facing copy** against the brand interview voice #copy #brand
- [ ] **Error messages**: review for tone — honest founder voice, not generic Flask errors #copy #ux

### Brand & Landing Page — Scope E (First-Run & Onboarding) #onboarding

- [ ] **First-run wizard**: after setting the first access key, walk through registering a repo and connecting an AI agent #onboarding #ux
- [ ] **Include a demo/sample repo option** on first visit #onboarding #demo
- [ ] **Add a "Try it live" section** to the logged-out landing #onboarding #landing

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

- [ ] **Add README summary to scan results**: Show the top of each repo's README in the web interface #ux #frontend
- [ ] **Search**: Implement a search feature for TODO comments #search #ux
- [ ] **Metrics dashboard**: Visualize TODO metrics across projects #reporting #ux
- [ ] **Report downloads**: Offer CSV, JSON, PDF export of scan results #reporting #feature

### Tech Debt #tech-debt

- [ ] **Refactor `stream_results.html` JS**: `createTodoElement()` and `createTodoMarkdownElement()` build DOM by hand with duplicated Startr.style strings. Extract shared styles into named constants or use server-rendered partials. #frontend #dry

## Backlog

- [ ] **Inline TODO completion tracking**: Snapshot-and-diff approach to detect when inline TODOs are removed between scans and show them as completed in the Done column. Uses `.todoscope-snapshot.json` and `.todoscope-done.json`. Git-history-independent — works on shallow clones. #feature #kanban
- [ ] **TODO editor + checkbox write-back**: Interactive checkboxes on kanban cards that write back to TODO.md. Includes atomic mutations, optimistic concurrency, advisory file locking, add-TODO form, and merge conflict detection. #feature #editor #kanban
- [ ] **Publish CapRover one-click app source**: Add `caprover-one-click.yml` to the Sage-is one-click repo #deployment #caprover
- [ ] **Priority inference from TODO comments** #core #parser
- [ ] **Plugin system** to extend scanner functionality #architecture #extensibility
- [ ] **Task manager integration** (Jira, Asana, Trello) #integration #external

### Release Pipeline — Repo Rename #release #brand

- [x] **Rename GitHub repo**: `Startr/WEB-MCPO-Repo_scanner` → `Startr/TodoScope` #brand
- [x] **Update Docker image**: `ghcr.io/startr/todoscope` #docker #brand
- [x] **Update all internal references**: pyproject.toml, scripts, templates, docs, README, CapRover #brand
- [x] **Convention**: clone to `GIT-TodoScope/` locally for dev clarity #brand
- [x] **Verified**: 45 tests passing, all links updated

### Release Pipeline — Docker CLI Wrapper + Dev Mode #release #docker #homebrew

- [x] **Create `scripts/todoscope`**: bash CLI wrapper (based on ai-ui pattern) #cli #docker
  - [ ] Commands: start, stop, update, dev, logs, open, status, version, tunnel, tailscale, nuke
  - [ ] Auto-find free port if default (5000) is taken
  - [ ] Reuse: ensure_docker, sage_project_dir, find_repo_nearby, is_ephemeral_path
  - [ ] Image: `ghcr.io/sage-is/todoscope:latest`, container: `todoscope`
  - [ ] Config dir: `~/.sage-is/` (Sage project registry)
- [ ] **Dev mode**: smart local development workflow #developer-experience
  - [ ] Resolution: --dir → $TODOSCOPE_DEV_DIR → find_repo_nearby → saved path → clone fresh
  - [ ] Mount source into container: scanner/ + app.py
  - [ ] FLASK_ENV=development, FLASK_DEBUG=1
  - [ ] --where flag: print saved source location
  - [ ] Ephemeral path warning
- [ ] **Tunnel commands**: `todoscope tunnel` + `todoscope tailscale` #networking
- [ ] **Verify**: `scripts/todoscope start` → `scripts/todoscope open` → works; `scripts/todoscope dev` → hot reload works

### Release Pipeline — PyInstaller Binary Build (macOS + Linux + Windows) #release #binary #packaging

- [x] **Create `todoscope.spec`**: PyInstaller spec file (two targets: CLI onefile + .app windowed) #packaging
- [x] **Add dev deps to Pipfile**: pyinstaller, build, twine #packaging
- [x] **Makefile targets**: binary, binary_dir, app, dmg, pypi_build, pypi_publish, clean_dist #build
- [x] **Verified**: `make binary` → `dist/todoscope` (11MB ARM64) → `./dist/todoscope --version` → `1.0.0`
- [ ] **Linux binary**: PyInstaller on ubuntu (x86_64) — works in tmux/SSH #linux
- [ ] **Windows binary**: PyInstaller on windows (.exe) #windows
- [ ] **Verify macOS**: `make binary` → `./dist/todoscope --port 5001` → browser opens, SSE works
- [ ] **Verify Linux (headless)**: `./todoscope --no-browser --port 5001` → access via tunnel or LAN
- [ ] **Verify Windows**: `todoscope.exe` → browser opens, SSE works

### Release Pipeline — Mac .app + DMG (v1.0 browser launcher) #release #macos #app

- [ ] **Build .app**: PyInstaller `--windowed` → TodoScope.app in Dock, opens Safari #macos
- [ ] **Create DMG**: `hdiutil` packaging for distribution #macos
- [ ] **Create `assets/todoscope.icns`**: telescope emoji rendered at icon sizes #design
- [ ] **Verify**: mount DMG → open TodoScope.app → Dock icon, Safari opens, SSE scan works

### Release Pipeline — Makefile Targets (local dev, fast, free) #release #build

- [ ] **Add targets**: binary, binary_dir, app, dmg, pypi_build, pypi_publish, clean_dist #build
- [ ] **Verify**: `make binary` and `make dmg` produce correct artifacts locally

### Release Pipeline — GitHub Actions CI/CD (tags only, hybrid) #release #ci

- [ ] **Create `.github/workflows/release.yml`**: triggered ONLY on v* tag push #ci
  - [ ] Job: docker (ubuntu, multi-arch GHCR push) ~5 billed min
  - [ ] Job: macos (single runner: CLI binary + .app + DMG) ~50 billed min (10x)
  - [ ] Job: linux (ubuntu, CLI binary x86_64, works in tmux/SSH) ~3 billed min
  - [ ] Job: windows (CLI .exe x86_64) ~6 billed min (2x)
  - [ ] Job: pypi (build + publish) ~2 billed min
  - [ ] Job: release (download all → GitHub Release)
  - [ ] Job: update-brew (SHA256 → homebrew-apps auto-commit)
  - [ ] Budget: ~65 billed min/release (~3% of free tier)
- [ ] **Code signing placeholder**: gated on APPLE_DEVELOPER_ID secret #macos #security
- [ ] **Verify**: `make release_finish` → tag push → all CI jobs green

### Release Pipeline — Homebrew Tap #release #homebrew #deployment

- [ ] **Add `Formula/todoscope.rb` to homebrew-apps**: Docker CLI formula #homebrew
  - [ ] depends_on: docker, git, cloudflared (optional), tailscale (optional)
  - [ ] Installs scripts/todoscope to bin
- [ ] **Add `Casks/todoscope.rb` to homebrew-apps**: .app via DMG #homebrew
- [ ] **Update `nuke-sage`**: add todoscope to KNOWN_PROJECTS #homebrew
- [ ] **Verify**: `brew install --build-from-source Formula/todoscope.rb` works

### Release Pipeline — Automated Release Flow #release #automation

- [ ] **One-command release**: `make patch_release` + `make release_finish` triggers everything #automation #ci
  - [ ] Auto-bump version in `scanner/__init__.py` to match tag
  - [ ] Run tests before finishing
  - [ ] Tag push → CI builds all artifacts automatically
  - [ ] Post-release summary: GitHub Release link, PyPI link, brew install command
- [ ] **Version single-source-of-truth**: `scanner/__init__.py` drives everything #packaging
  - [ ] `pyproject.toml` reads version dynamically
  - [ ] PyInstaller embeds it in the binary
  - [ ] `scripts/todoscope` VERSION synced by release script
  - [ ] Homebrew formula URL/SHA256 updated by CI
- [ ] **Verify**: `make patch_release` → `make release_finish` → all CI green, all channels updated

### Release Pipeline — Future: Native Mac UI (v1.1+) #release #macos #future

- [ ] **v1.1 — pystray menu bar icon**: Open Browser / Quit; deps: pystray, Pillow #macos
- [ ] **v1.2 — pywebview embedded WKWebView**: native window + status bar; deps: pywebview #macos
  - [ ] Validate SSE streaming through WKWebView before committing
  - [ ] Validate threading model: Flask thread + pystray detached + pywebview main thread

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
