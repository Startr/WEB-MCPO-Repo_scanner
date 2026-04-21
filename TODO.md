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
- [ ] **Add TodoScope to `Sage-is/homebrew-apps` tap**: Write a Formula that pulls the Docker image and wires up a launchd service #deployment #homebrew
- [ ] **Priority inference from TODO comments** #core #parser
- [ ] **Plugin system** to extend scanner functionality #architecture #extensibility
- [ ] **Task manager integration** (Jira, Asana, Trello) #integration #external

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
