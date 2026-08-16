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
