# Changelog

All notable changes to TodoScope are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Internal checkpoints use a 4-segment scheme (e.g. `v1.0.0.1`) and are not
listed here — only public releases.

## [1.0.0] — 2026-05-03

First official release. TodoScope ships as a Mac app, standalone binaries
(macOS/Linux/Windows), Docker image, and Python package — all built locally
with zero cloud CI minutes.

### Core
- Web UI for browsing TODOs across all your repos (Flask + SSE streaming)
- Inline TODO scan: `# TODO`, `# FIXME`, `# BUG`, `# NOTE` across many comment styles
- `TODO.md` parsing with kanban board generation (sections → columns, items → cards)
- Honors `.gitignore` patterns
- Local repos config via `local_repos.yaml` (public/webhook metadata)
- Git blame enrichment with author badges on kanban cards
- Webhook refresh with HMAC-SHA256 verification + rate limiting
- Configurable editor links (vscode.dev, VS Code, Cursor, JetBrains, custom)

### MCP / AI integration
- `/api/mpco/manifest` and `/api/mpco/openapi.json` for AI agent discovery
- `list_repositories` and scan endpoints for programmatic access
- Public repo views (per-repo public flag, auth bypass for read-only routes)

### Distribution
- **macOS .app** with 🔭 menu bar icon (pystray) — Open Browser, Show Log,
  Hide/Show Dock Icon, Quit. Single-instance detection (clicking the .app
  while running just opens the browser).
- **DMG** with branded background art and drag-to-Applications layout
  (`create-dmg`).
- **Standalone binary** (`todoscope`) — macOS ARM64 native, Linux x86_64
  via Docker (`cdrx/pyinstaller-linux`), Windows .exe via Docker + Wine
  (`cdrx/pyinstaller-windows`).
- **Docker image** at `ghcr.io/startr/todoscope` — multi-arch, mounts
  cloned repos and access keys from the host.
- **PyPI package** (`todoscope`) for `pip install` / `uv tool install`.
- **Docker CLI wrapper** (`scripts/todoscope`) — 11 commands including
  `dev` mode with smart repo discovery + source mounting for hot reload.
- **CapRover one-click deploy** via `caprover-one-click.yml`.

### Networking
- `--tunnel` flag (cloudflared quick tunnel)
- `--tailscale` flag (Tailscale Funnel)
- `--share` (auto-detect best available)
- `--no-browser` headless mode for tmux/SSH/phone access

### Security
- Access key authentication (`access_keys.csv` with session + Bearer token)
- HTML escaping for multi-line TODO content
- Public/private repo flags (per-repo controls)

### Developer experience
- `~/.todoscope/` data directory (auto-migrates from `scanner/repositories/`)
- pyproject.toml with `todoscope` console script entry point
- `make release_finish` chains into `make release_all` for 3-segment tags —
  one command builds everything and uploads to GitHub Releases.
- `make internal_tag` for lightweight 4-segment checkpoints (no binaries)
- `make release_preflight` (Poka-yoke): fails before any irreversible action
  if working tree is dirty, develop is out of sync, or required tooling is
  missing (gh, Docker, create-dmg).
- 45 tests across CLI, error handling, and the bash CLI wrapper.

### Brand
- Renamed from `repo_scanner` → `Startr/TodoScope`
- 🔭 telescope as the brand mark across favicon, app icon, menu bar, DMG art
- Real Apple Color Emoji rendered via canvas-to-receiver pattern (browser
  renders the emoji, posts the PNG back to a tiny Python server, no
  Playwright/Pillow-emoji limits)

[1.0.0]: https://github.com/Startr/TodoScope/releases/tag/v1.0.0
