# TODO List for Repo Scanner

<!-- All content below this line has been revised for clarity, conciseness, vigorous language, tagging, and DRY principles. Uncompleted items from the original '''Completed''' section have been moved to '''Medium Priority'''. -->

## Brand & Landing Page (CEO Review — scoped by surface)

These items align the product surface with the voice we locked in via [docs/brand-interview.md](docs/brand-interview.md).
The one-line pitch is: *"See every TODO across all your repos. The awareness layer for teams — and the AI agents on them — who need to know what's actually unfinished."*

### Scope A — Logged-Out Landing (login page) #brand #landing

The current login page is a cold password prompt with zero context. Turn it into a proper landing page.

- [ ] **Promote login.html into a real landing page**: hero, pitch, features, sign-in #brand #landing #critical
  - [x] Add brand hero: headline, subhead (use the one-line pitch verbatim), and a short "what it is" paragraph
  - [x] Add a 3-bullet "what makes it different" strip (the inversion, MCP-native, open-source)
  - [x] Embed the existing `Sage_repo-TODOs.gif` or a fresh screenshot above the fold
  - [x] Move the sign-in form into a right-hand card or section below the hero — secondary action, not primary
  - [ ] Add "New to TodoScope?" copy with a link to the README / GitHub for evaluators who aren't signing in
  - [ ] Add social proof / cross-links to [sage.is](https://sage.is) and [startr.style](https://startr.style)
  - [ ] Add OG meta tags (`og:title`, `og:description`, `og:image`) so shared links render properly
- [ ] **Surface the MCP / AI agent story on the landing page** #brand #ai #mcp
  - [ ] Add a "Connect your AI agent" section showing how to point Sage / Claude / any MCP client at the instance
  - [ ] Link directly to `/api/mpco/manifest` and `/api/mpco/openapi.json` from the landing page
  - [ ] Include a one-paragraph framing: "AI agents are part of your team"

### Scope B — Logged-In Dashboard (index page) #ux #dashboard

The dashboard is functional but has no brand presence and no empty state.

- [ ] **Add a dashboard header**: restate the one-line pitch in short form, orient the user #ux #brand
- [ ] **Unify repo entry**: one input that accepts a git URL *or* a local path, with smart detection #ux #simplify
- [ ] **Empty state for Repositories**: when no repos are registered, show a friendly onboarding card with 2-3 suggested quick-start actions (scan a demo repo, register a local path, copy MCP endpoint) #ux #onboarding
- [ ] **Surface MCP endpoints on the dashboard**: a small "Connect to an AI agent" card with copy-to-clipboard buttons for the manifest URL and a sample cURL #ai #mcp #ux
- [ ] **Add search/filter to the Repositories table** (relevant as soon as the list grows past ~10) #ux #search
- [ ] **Add a visible "last scanned" timestamp + manual refresh control** per repo row #ux
- [ ] **Move the GitHub contribute banner to the footer** — it's competing with the primary action #ux #hierarchy
- [ ] **Clarify the "shallow clone" checkbox**: tooltip or inline help explaining when to use it #ux #copy

### Scope C — MCP / Sage.is Integration Surface #ai #mcp #integration

This is our killer differentiator and it's currently invisible in the UI.

- [ ] **Create a dedicated `/connect` or `/mcp` page** with step-by-step instructions to wire TodoScope into Sage, Claude Desktop, and generic MCP clients #mcp #docs
- [ ] **Add a "Copy MCP manifest URL" button** visible on the logged-in dashboard #mcp #ux
- [ ] **Write a short guide** — `docs/connect-sage.md` — with screenshots showing an end-to-end Sage → TodoScope query #docs #mcp
- [ ] **Add an MCP health indicator** to the dashboard: green dot when the manifest endpoint is responding, red when not #observability #mcp

### Scope D — Brand Consistency & Copy #brand #copy

Small touches that make the product feel like it belongs to the Startr / Sage family.

- [ ] **Audit all user-facing copy** against the brand interview voice: honest founder tone, clarity-first, never buzzwordy #copy #brand
- [x] **Footer update**: added cross-links to sage.is and startr.style; "Part of the Startr ecosystem" framing #brand #footer
- [x] **Rename "Todoscope" → "TodoScope"** consistently across templates, README, caprover manifest, and page titles #brand #consistency
- [x] **Favicon**: replaced the clipboard emoji with a telescope (🔭) — consistent with the "scope" metaphor in the name #brand #visual
- [x] **Page titles**: descriptive, brand-consistent `<title>` tags applied to base / index / login #brand #seo
- [x] **Noindex on login page**: added `<meta name="robots" content="noindex, nofollow">` so self-hosted instances don't get indexed #seo #privacy
- [x] **Meta description**: added the one-line pitch as the default meta description in base.html #brand #seo
- [ ] **Error messages**: review for tone — should match the honest founder voice, not generic flask errors #copy #ux

### Scope E — First-Run & Onboarding Experience #onboarding

A new user's first 60 seconds decides whether they come back.

- [ ] **First-run wizard**: after setting the first access key, walk the user through registering a repo and connecting an AI agent #onboarding #ux
- [ ] **Include a demo/sample repo option** on first visit so the user can see streaming results before registering anything of their own #onboarding #demo
- [ ] **Add a "Try it live" section** to the logged-out landing that runs a preview scan against a public demo repo #onboarding #landing

## Documentation & Planning TODOs
- [ ] **Create comprehensive API documentation**: Standalone API reference guide #documentation #api
  - [ ] Document all endpoints with request/response examples
  - [ ] Add error code reference
  - [ ] Include authentication plans
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
- [ ] **Enhance code documentation**: Add comprehensive docstrings #documentation #code
  - [ ] Add docstrings to TodoItem class
  - [ ] Document API endpoints with proper docstrings
  - [ ] Add inline comments for complex logic
  - [ ] Verify documentation generation works
- [ ] **Create development workflow documentation**: Detailed workflow guide #documentation #development
  - [ ] Document setup process
  - [ ] Document feature development cycle
  - [ ] Document testing procedures
  - [ ] Test workflow documentation with new developer

## High Priority
- [x] Fix the MAJOR issue with existing repositories not working. #core #bug
- [x] Implement a robust error handling mechanism for the scanner. #core #error-handling
- [x] Broaden TODO pattern recognition (e.g., FIXME, BUG, NOTE). #core #parser
- [x] DRY Makefile targets. (Allow passing args to targets?) #development #testing
- [x] Enable streaming of API results for improved responsiveness. #api #performance
- [ ] Migrate Python files and dependencies to subdirectory structure. #development #structure
    - [x] Create scanner subdirectory. #development #structure
    - [x] Implement __init__.py for the subdirectory. #development #structure
    - [x] Move error_handling.py to scanner subdirectory. #development #structure
    - [x] Update imports in app.py. #development #structure
    - [x] Move remaining Python files (test files) to scanner/tests. #development #structure
    - [x] Move Pipfile and Pipfile.lock to scanner subdirectory. #development #structure
    - [ ] Test and update the Makefile accordingly. #development #testing



## Medium Priority
- [ ] Add detection of TODO.md and TODO.txt files. #feature #core (no capitalization needed)
- [ ] Implement a user-friendly web interface for displaying TODO files. #ux #frontend
- [ ] Include the option to look at the TODO files with our MCPo Api. #api #integration
- [ ] Add summary from repo readme files to the web interface. (optioanlly the top 20lines) #ux #frontend
- [ ] Implement a search feature for TODO comments. #search #ux
- [ ] Develop a dashboard to visualize TODO metrics across projects. #reporting #ux
- [ ] Offer report downloads in multiple formats (CSV, JSON, PDF). #reporting #feature
- [ ] Integrate with GitHub webhooks for automated repository scanning. #integration #automation
- [ ] Enhance TODO file processing: #feature #core
    - [ ] Recognize diverse TODO filenames (e.g., TODO.md, todo.txt). #detection
    - [ ] Scan TODO files located in the project root directory. #discovery
    - [ ] Extend scanning to TODO files within subdirectories. #discovery
    - [ ] Display content from identified TODO files. #rendering #ux

## Tech Debt
- [ ] **Refactor `stream_results.html` JS**: `createTodoElement()` and `createTodoMarkdownElement()` build DOM by hand with duplicated Startr.style strings. Replace with server-rendered Jinja2 partials + SSE that push HTML fragments, or at minimum extract shared styles into named constants. #frontend #dry

## Low Priority
- [ ] Publish CapRover one-click app source: add `caprover-one-click.yml` to the Sage-is one-click repo and register it as a custom source in CapRover. #deployment #caprover
- [ ] Add TodoScope to the `Sage-is/homebrew-apps` tap: write a Formula that pulls the Docker image and wires up a launchd service. #deployment #homebrew
- [ ] Introduce user authentication for secure access. #security #auth
- [ ] Implement priority inference from TODO comments. #core #parser
- [ ] Design a plugin system to extend scanner functionality. #architecture #extensibility
- [ ] Facilitate integration with task managers (Jira, Asana, Trello). #integration #external
- [ ] Create a command-line interface (CLI) for versatile use. #cli #accessibility
- [ ] Improve visibility of scrollable local repositories list on the main page. #ux #frontend

## Completed
- [x] Implement comprehensive error handling with custom exceptions, retries, and recovery strategies. #core #error-handling
- [x] Create testing infrastructure with unit and integration tests. #core #testing
- [x] Add Makefile targets and test runner for easy test execution. #development #testing
- [x] Honor .gitignore patterns during repository scans. #core
- [x] Stream scan results efficiently in the web UI. #ux #frontend
- [x] Ensure proper HTML escaping for multi-line display. #security #rendering
- [x] Broaden TODO pattern recognition to include FIXME, BUG, and NOTE in various comment formats. #core #parser
- [x] Fix server hanging issue: server no longer becomes unresponsive after completing scans. #critical #backend
- [x] Skip `scanner/repositories/` when scanning this project as a local repo — prevents recursing into managed cloned repos. #core #backend
