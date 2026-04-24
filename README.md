# 🔭 TodoScope

[![GitHub](https://img.shields.io/badge/View%20on-GitHub-brightgreen)](https://github.com/Startr/TodoScope)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-black?logo=flask)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-compatible-7C3AED)](https://modelcontextprotocol.io)
[![GitHub stars](https://img.shields.io/github/stars/Startr/TodoScope?style=social)](https://github.com/Startr/TodoScope/stargazers)
[![TODOs](https://img.shields.io/endpoint?url=https://todoscope.sage.is/api/badge/todos/WEB-Sage.is-repo_scanner)](http://localhost:5000/scan_stream/WEB-Sage.is-repo_scanner)
[![GitHub last commit](https://img.shields.io/github/last-commit/Startr/TodoScope)](https://github.com/Startr/TodoScope/commits)

Every codebase has a to-do list. Most of them are a mess. TodoScope is about the gap between what teams say they'll fix and what actually gets done — and what that gap reveals about how software really gets built.

**Give your AI assistant a live view of every TODO across all your repos.**

Connect [Sage.is](https://sage.is), [Claude.ai](https://claude.ai), or any MCP-compatible assistant and ask: *"What's still TODO in this project?"* TodoScope answers instantly. It also gives your team a clean web UI to browse, track, and stay on top of inline TODOs and TODO.md files — without leaving the codebase.

The code is open. The project evolves. Get involved.

![Sage_repo-TODOs.gif](Sage_repo-TODOs.gif)

## AI & MCP Integration

TodoScope implements the [Model Context Protocol](https://modelcontextprotocol.io), making it a first-class tool for AI assistants.

*   **Sage.is AI** and **Claude.ai** can call TodoScope directly — ask your assistant to list, summarize, or prioritize TODOs across any repo it has access to.
*   Any MCP-compatible client discovers TodoScope automatically via its manifest endpoint.
*   The OpenAPI spec is generated dynamically — the docs always match the live API.

| Endpoint | Purpose |
|---|---|
| `GET /api/mpco/manifest` | Service discovery for MCP clients |
| `GET /api/mpco/openapi.json` | Live OpenAPI 3.0 spec |
| `POST /api/mpco/scan_repository` | Scan a repo, return all TODOs as JSON |

## What It Does

TODOs pile up. They hide in comments, sit in TODO.md files, and get forgotten across repos. TodoScope finds them all:

*   **AI-ready API:** MCP-compliant — Sage.is, Claude.ai, and other assistants query it directly.
*   **Streaming scan:** See TODOs appear in real time as files are scanned.
*   **TODO.md support:** Detects and renders standalone TODO files alongside inline code comments.
*   **Live refresh:** Watches local repos for changes and updates the view without a full rescan.
*   **Local repo management:** Register local paths — paths stay on the server, never exposed to the browser.
*   **.gitignore aware:** Skips files and directories your project ignores.

## How It Works

1.  Provide a Git URL or register a local repo path.
2.  TodoScope clones (or reads) the repository.
3.  It scans all text files for TODO patterns and finds standalone TODO.md files.
4.  Results stream to the web UI and are available via the API.

## Installation

### Standalone binary (no Python required)

Download from [GitHub Releases](https://github.com/Startr/TodoScope/releases) and run:

```bash
./todoscope
```

Opens your browser to `http://localhost:5000`. Data stored in `~/.todoscope/`.

### macOS .app

Download `TodoScope.dmg` from [Releases](https://github.com/Startr/TodoScope/releases), drag to Applications.
Double-click → 🔭 appears in your menu bar → browser opens. Menu bar icon has Open Browser, Show Log, and Quit.

### pip / uv

```bash
pip install todoscope    # or: uv tool install todoscope
todoscope
```

### Local development

Requires Python 3.11+ and Git.

```bash
git clone https://github.com/Startr/TodoScope.git GIT-TodoScope
cd GIT-TodoScope
pip install pipenv
cd scanner && pipenv install
cd ..
make it_run_dev
```

Open `http://localhost:5000`. The security warning on the page walks you through setting your first access key.

### Docker

```bash
git clone https://github.com/Startr/TodoScope.git GIT-TodoScope
cd GIT-TodoScope
make it_build
make it_run SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

Cloned repositories and your `access_keys.csv` are mounted from the host, so they survive container restarts.

### CapRover

Deploy from the CapRover dashboard using the included `caprover-one-click.yml`, or add this repo as a custom one-click source. Set the `SECRET_KEY` variable during setup. After deployment, visit the app URL and set your first access key via the security panel.

### Cloudflare Quick Tunnel

To share a local instance publicly for demos:

```bash
make run_tunnel
```

### API Endpoints

The scanner provides a RESTful API. Key endpoints include:

*   **Scan Repository:**
    ```bash
    curl -X POST http://localhost:5000/api/mpco/scan_repository \
      -H "Content-Type: application/json" \
      -d '{"repo_url": "https://github.com/username/repository.git"}'
    ```
*   **List Local Repositories:**
    ```bash
    curl -X GET http://localhost:5000/api/mpco/list_repositories
    ```
*   **Pull Repository Updates:**
    ```bash
    curl -X POST http://localhost:5000/api/mpco/pull_repository \
      -H "Content-Type: application/json" \
      -d '{"repo_name": "repository_name_from_list"}'
    ```

#### Example API Output (Scan Repository)

```json
{
  "repo_url": "https://github.com/username/repository.git",
  "repo_name": "repository",
  "todo_count": 42,
  "todos": [
    {
      "file_path": "src/main.py",
      "line_num": 24,
      "todo_text": "# TODO: Fix this hack when we have time",
      "next_line": "def temporary_solution():"
    }
    // ... more TODOs
  ],
  "web_url": "http://localhost:5000/scan/https://github.com/username/repository.git"
}
```

## Project TODOs

This project, while dedicated to finding TODOs, has its own list of desired enhancements and features. Contributions are welcome!

<!-- BEGIN PROJECT TODOS -->
<!-- This section is automatically generated from TODO.md. Edits here will be overwritten. -->
## Brand & Landing Page (CEO Review — scoped by surface)

### Scope A — Logged-Out Landing (login page)

- [ ] **Promote login.html into a real landing page**: hero, pitch, features, sign-in
- [ ] **Surface the MCP / AI agent story on the landing page**

### Scope B — Logged-In Dashboard (index page)

- [ ] **Add a dashboard header**: restate the one-line pitch in short form, orient the user
- [ ] **Unify repo entry**: one input that accepts a git URL *or* a local path, with smart detection
- [ ] **Empty state for Repositories**: when no repos are registered, show a friendly onboarding card with 2-3 suggested quick-start actions (scan a demo repo, register a local path, copy MCP endpoint)
- [ ] **Surface MCP endpoints on the dashboard**: a small "Connect to an AI agent" card with copy-to-clipboard buttons for the manifest URL and a sample cURL
- [ ] **Add search/filter to the Repositories table** (relevant as soon as the list grows past ~10)
- [ ] **Add a visible "last scanned" timestamp + manual refresh control** per repo row
- [ ] **Move the GitHub contribute banner to the footer** — it's competing with the primary action
- [ ] **Clarify the "shallow clone" checkbox**: tooltip or inline help explaining when to use it

### Scope C — MCP / Sage.is Integration Surface

- [ ] **Create a dedicated `/connect` or `/mcp` page** with step-by-step instructions to wire TodoScope into Sage, Claude Desktop, and generic MCP clients
- [ ] **Add a "Copy MCP manifest URL" button** visible on the logged-in dashboard
- [ ] **Write a short guide** — `docs/connect-sage.md` — with screenshots showing an end-to-end Sage → TodoScope query
- [ ] **Add an MCP health indicator** to the dashboard: green dot when the manifest endpoint is responding, red when not

### Scope D — Brand Consistency & Copy

- [ ] **Audit all user-facing copy** against the brand interview voice: honest founder tone, clarity-first, never buzzwordy
- [x] **Footer update**: added cross-links to sage.is and startr.style; "Part of the Startr ecosystem" framing
- [x] **Rename "Todoscope" → "TodoScope"** consistently across templates, README, caprover manifest, and page titles
- [x] **Favicon**: replaced the clipboard emoji with a telescope (🔭) — consistent with the "scope" metaphor in the name
- [x] **Page titles**: descriptive, brand-consistent `<title>` tags applied to base / index / login
- [x] **Noindex on login page**: added `<meta name="robots" content="noindex, nofollow">` so self-hosted instances don't get indexed
- [x] **Meta description**: added the one-line pitch as the default meta description in base.html
- [ ] **Error messages**: review for tone — should match Startr voice, not generic flask errors

### Scope E — First-Run & Onboarding Experience

- [ ] **First-run wizard**: after setting the first access key, walk the user through registering a repo and connecting an AI agent
- [ ] **Include a demo/sample repo option** on first visit so the user can see streaming results before registering anything of their own
- [ ] **Add a "Try it live" section** to the logged-out landing that runs a preview scan against a public demo repo

## Documentation & Planning TODOs
- [ ] **Create comprehensive API documentation**: Standalone API reference guide
- [ ] **Add architecture documentation**: System design and component overview
- [ ] **Create contributor guide**: Detailed guide for new contributors
- [ ] **Enhance code documentation**: Add comprehensive docstrings
- [ ] **Create development workflow documentation**: Detailed workflow guide

## High Priority
- [x] Fix the MAJOR issue with existing repositories not working.
- [x] Implement a robust error handling mechanism for the scanner.
- [x] Broaden TODO pattern recognition (e.g., FIXME, BUG, NOTE).
- [x] DRY Makefile targets. (Allow passing args to targets?)
- [x] Enable streaming of API results for improved responsiveness.
- [ ] Migrate Python files and dependencies to subdirectory structure.

## Medium Priority
- [ ] Add detection of TODO.md and TODO.txt files. #feature #core (no capitalization needed)
- [ ] Implement a user-friendly web interface for displaying TODO files.
- [ ] Include the option to look at the TODO files with our MCPo Api.
- [ ] Add summary from repo readme files to the web interface. (optioanlly the top 20lines)
- [ ] Implement a search feature for TODO comments.
- [ ] Develop a dashboard to visualize TODO metrics across projects.
- [ ] Offer report downloads in multiple formats (CSV, JSON, PDF).
- [ ] Integrate with GitHub webhooks for automated repository scanning.
- [ ] Enhance TODO file processing:

## Tech Debt
- [ ] **Refactor `stream_results.html` JS**: `createTodoElement()` and `createTodoMarkdownElement()` build DOM by hand with duplicated Startr.style strings. Replace with server-rendered Jinja2 partials + SSE that push HTML fragments, or at minimum extract shared styles into named constants.

## Low Priority
- [ ] Publish CapRover one-click app source: add `caprover-one-click.yml` to the Startr one-click repo and register it as a custom source in CapRover.
- [ ] Add TodoScope to the `Startr/homebrew-apps` tap: write a Formula that pulls the Docker image and wires up a launchd service.
- [ ] Introduce user authentication for secure access.
- [ ] Implement priority inference from TODO comments.
- [ ] Design a plugin system to extend scanner functionality.
- [ ] Facilitate integration with task managers (Jira, Asana, Trello).
- [ ] Create a command-line interface (CLI) for versatile use.
- [ ] Improve visibility of scrollable local repositories list on the main page.

## Completed
- [x] Implement comprehensive error handling with custom exceptions, retries, and recovery strategies.
- [x] Create testing infrastructure with unit and integration tests.
- [x] Add Makefile targets and test runner for easy test execution.
- [x] Honor .gitignore patterns during repository scans.
- [x] Stream scan results efficiently in the web UI.
- [x] Ensure proper HTML escaping for multi-line display.
- [x] Broaden TODO pattern recognition to include FIXME, BUG, and NOTE in various comment formats.
- [x] Fix server hanging issue: server no longer becomes unresponsive after completing scans.
- [x] Skip `scanner/repositories/` when scanning this project as a local repo — prevents recursing into managed cloned repos.
<!-- END PROJECT TODOS -->

## Changelog

### v0.0.1 — First Release (2026-04-16)

- Access key authentication with CSV-backed key management and login/logout flow
- Live TODO count badge endpoint (`/api/badge/todos/:repo`)
- Streaming scan results in the web UI via SSE
- MCP-compatible API: manifest, OpenAPI spec, and `scan_repository` endpoint
- Broadened TODO pattern recognition: `FIXME`, `BUG`, `NOTE` alongside `TODO`
- `.gitignore`-aware scanning; skips `scanner/repositories/` in local scans
- TodoScope branding: naming, favicon, meta/OG tags, footer ecosystem links
- Landing page with hero copy, feature strip, and embedded demo GIF
- code.dev deep-link for every registered repository
- Robust error handling with custom exceptions, retries, and recovery strategies
- Unit and integration test suite with Makefile runner targets
- CapRover one-click deployment config (`caprover-one-click.yml`)

## License

Copyright © 2025 Startr LLC.

Released under the GNU Affero General Public License v3.0 (AGPL-3.0).

Use it. Share it. Make it better. But keep it open. The full license text is available in the `LICENSE` file.

## Contribution

Contributions are highly encouraged! If you have an idea for improvement or a bug fix, please:

1.  Fork the repository.
2.  Create a new branch for your feature or fix.
3.  Make your changes.
4.  Submit a pull request with a clear description of your changes.

Let's work together to make this tool even better and help keep our codebases clean and manageable!

