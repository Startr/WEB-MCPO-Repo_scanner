# Development Workflow

## Setup

Clone, then pick one (or both) of two installs:

```bash
git clone https://github.com/Startr/TodoScope.git
cd TodoScope
```

**Pipenv — dev work and tests.** The Pipfile lives in `scanner/`, Python 3.12:

```bash
cd scanner
pipenv install --dev
```

**Editable install — gives you the `todoscope` command** (`scanner.cli:main`,
Python >= 3.11):

```bash
pip install -e .    # from repo root
```

Optional:

```bash
make setup           # write a starter .env (PORT_MAPPING, SECRET_KEY, PROJECTS_DIR)
make install_hooks   # copy scripts/hooks/ into .git/hooks/
```

## Run the Server in Dev

From `scanner/` (so pipenv finds the Pipfile):

```bash
pipenv run todoscope --port 5001 --no-browser
```

Flags ([`scanner/cli.py`](../scanner/cli.py)):

| Flag | Effect |
| ---- | ------ |
| `--port N` | Default 5000. Probes upward if taken. If a server already answers, opens it instead of starting a second instance. |
| `--host` | Default 127.0.0.1 |
| `--no-browser` | Headless — don't open a browser |
| `--exact-port` | Bind exactly `--port`, fail if taken. Used by the desktop shell handshake. |
| `--share` / `--tunnel` / `--tailscale` | Expose via tailscale funnel or cloudflared |
| `--tray` | Menu bar mode |

**Data dir**: the CLI sets `TODOSCOPE_DATA_DIR=~/.todoscope` — repositories,
`scan_state/` cache, `.secret_key` all live there. When unset (Docker,
`make it_run_dev`), the app falls back to `scanner/`-relative paths.

**Auth in dev**: no keys means auth is disabled — every route is open. Under
the `todoscope` CLI the auth file is `~/.todoscope/access_keys.csv` (the CLI
sets `TODOSCOPE_DATA_DIR`); `scanner/access_keys.csv` applies only when
`TODOSCOPE_DATA_DIR` is unset (`make it_run_dev`, Docker). The file needs the
`key,label` header line plus a data row. `/health` reports the auth state.

Alternative — Flask dev server with reloader and debugger:

```bash
make it_run_dev      # flask run --debug on 0.0.0.0:5000, data under scanner/
```

## Test Loop

```bash
make test
```

Runs [`tools/run_tests.sh`](../tools/run_tests.sh): pipenv with
`PIPENV_PIPFILE=scanner/Pipfile`, pytest over `scanner/tests/`.

Variants: `make test-unit`, `make test-error`, `make test-coverage`,
`make test-verbose`. Single file, direct:

```bash
PIPENV_PIPFILE=scanner/Pipfile pipenv run pytest scanner/tests/test_health.py -v
```

Test files: `test_cli.py`, `test_todoscope_cli.py`, `test_error_handling.py`,
`test_health.py`, `test_login_remember.py`, `test_pattern_recognition.py`.

## Feature Cycle

Follow **Plan-Document-Execute-Verify** from
[CONVENTION.instructions.md](../CONVENTION.instructions.md):

### 1. Plan — add a card to TODO.md first

Board conventions: [TODO_CONVENTION.md](TODO_CONVENTION.md). Section headers
map to kanban columns (In Progress / TODO / Backlog / Bugs / Done); hashtags go
on the card header; steps go in a sub-checklist:

```markdown
### Feature name #tag1 #tag2
- [ ] **Feature name**: one-line claim
  - [ ] Core change
  - [ ] Tests
  - [ ] Docs
```

### 2. Document

Docstrings for new functions, [API_REFERENCE.md](API_REFERENCE.md) for new
endpoints, README for user-facing changes, this file if the process changes.

### 3. Execute

Follow the code standards below and existing patterns in
[`scanner/app.py`](../scanner/app.py).

### 4. Verify

`make test`, exercise the endpoint or UI by hand, check off the card in TODO.md.

## Code Standards

- Type hints where possible, PEP 8, terse docstrings.
- Wrap failure-prone operations in `@safe_operation` from
  [`scanner/error_handling.py`](../scanner/error_handling.py); use its custom
  exceptions and error IDs.
- Tool-API endpoints (`/api/mpco/*`) use the `@mpco_response` decorator in
  `scanner/app.py`. That surface is a plugin-style manifest + OpenAPI REST API
  — it is **not** the Model Context Protocol. Say "tool API", never "MCP";
  only the route paths keep the mpco name.
- Live-board HTML renders server-side: fragments in
  [`scanner/fragments.py`](../scanner/fragments.py) +
  `scanner/templates/partials/`, pushed over `/events/<repo>` SSE by the
  watcher in [`scanner/live.py`](../scanner/live.py). Keep initial render and
  SSE payloads on the same fragment code.

## File Organization

```text
TodoScope/
├── app.py                # thin shim → scanner.app (Docker/Flask entry)
├── pyproject.toml        # packaging; console script todoscope = scanner.cli:main
├── Makefile
├── scanner/              # the Python package
│   ├── app.py            # Flask app: scanning, auth, tool API, SSE
│   ├── cli.py            # todoscope CLI (serve / tray)
│   ├── tray.py           # menu bar mode
│   ├── error_handling.py
│   ├── kanban.py         # TODO.md → kanban mapping
│   ├── fragments.py      # server-rendered board fragments
│   ├── live.py           # per-repo file watcher → SSE
│   ├── templates/        # HTML (partials/ holds the fragments)
│   ├── static/
│   ├── tests/
│   ├── scan_state/       # per-repo incremental scan cache (JSON)
│   └── Pipfile           # deps, Python 3.12
├── src-tauri/            # Tauri v2 desktop shell
├── scripts/              # release_all.sh, hooks/, todoscope Docker wrapper
├── tools/                # run_tests.sh, sync_readme_todos.py
└── docs/
```

## Desktop Dev Loop (Tauri)

Full loop — builds the PyInstaller onedir sidecar, then runs the shell:

```bash
make tauri_dev       # installs cargo tauri-cli if missing; sidecar via make sidecar_dir
```

Fast loop for Python changes — attach the shell to a server you run yourself,
no sidecar rebuild:

```bash
# terminal 1, from scanner/
pipenv run todoscope --port 5000 --exact-port --no-browser

# terminal 2
TODOSCOPE_DEV_PORT=5000 make tauri_dev
```

With `TODOSCOPE_DEV_PORT` set the shell spawns nothing and attaches to that
port. Restart the Python server to pick up changes. Rebuild the sidecar only
when deps or bundled data files change: `make sidecar_dir`.

## Git Workflow

Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.

Branches (git-flow-next):

- `master` — released code
- `develop` — integration branch
- `release/x.y.z`, `hotfix/x.y.z` — cut with `make patch_release` /
  `make minor_release` / `make hotfix`

## Docker

```bash
make it_build        # build image
make it_run          # run on 5000:5000; mounts scanner/repositories + access_keys.csv
make it_run_local    # also mounts PROJECTS_DIR at /mnt/projects
make it_run_ghcr     # run the published ghcr.io/startr/todoscope image
```

## Releases

Overview only — the source of truth is
[`scripts/release_all.sh`](../scripts/release_all.sh) (header comments) and the
Makefile release targets.

```bash
make patch_release   # cut release/x.y.z
make release_finish  # merge, tag, push; public x.y.z tags chain into release_all
```

`make release_all` builds everything locally (macOS/Linux/Windows binaries,
Tauri .app + DMG, Docker → GHCR, PyPI) and uploads to GitHub Releases. Desktop
DMG alone: `make tauri_dmg`. Internal checkpoints without a binary release:
`make internal_tag`.

## Troubleshooting

1. **Dependencies not installing** — install pipenv (`pip install pipenv`);
   `scanner/Pipfile` wants Python 3.12.
2. **Port 5000 taken** — the CLI probes upward automatically unless
   `--exact-port`; check with `lsof -i :5000`.
3. **No output from the .app** — when launched from Finder, the app logs to
   `~/.todoscope/todoscope.log` (`tail -f` it).
4. **Stale scan results** — force a full rescan with the dashboard
   force-rescan control or `refresh=1`; the incremental cache is per-repo JSON
   in `scan_state/` (under `~/.todoscope` for the CLI, `scanner/` otherwise).
5. **Tests failing** — `pipenv install --dev` in `scanner/`, then isolate with
   `make test-unit` / `make test-error`.
