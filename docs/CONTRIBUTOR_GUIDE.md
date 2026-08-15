# Contributor Guide

How to set up, test, and land changes in TodoScope.

## Getting Started

### Prerequisites

- Python 3.12 (the Pipfile pins 3.12; the package itself requires >=3.11)
- Git
- pipenv (`pip install pipenv`)

### Setup

```bash
git clone https://github.com/Startr/TodoScope.git GIT-TodoScope
cd GIT-TodoScope
cd scanner && pipenv install --dev && cd ..
make test            # verify the suite passes
make install_hooks   # optional: installs scripts/hooks (post-checkout)
```

### Run the app

```bash
make dev_run
```

Starts the Flask dev server (reloader on) at `http://localhost:5000`. With no
`scanner/access_keys.csv` present, auth is disabled — open access for local dev.

To run the CLI instead (what the packaged `todoscope` command executes):

```bash
PIPENV_PIPFILE=scanner/Pipfile pipenv run python -m scanner.cli --no-browser
```

## Repo Layout

All Python lives in the `scanner/` package. The root `app.py` is a thin shim
that re-exports `scanner.app` for Flask and WSGI hosts.

```text
app.py                  # shim: `from scanner.app import app`
pyproject.toml          # packaging; version from scanner.__version__;
                        # entry point: todoscope = scanner.cli:main
Makefile                # test, dev_run, docker (it_*), binaries, tauri_*, release
scanner/
  app.py                # Flask app: routes, auth, scan engine, SSE, tool API
  cli.py                # `todoscope` CLI: serve, --tray, tunnels
  error_handling.py     # error classes + decorators (safe_operation, ...)
  kanban.py             # TODO.md -> kanban parsing; source of truth for the board convention
  fragments.py          # server-rendered board fragments for live updates
  live.py               # per-repo filesystem watchdog feeding SSE
  templates/            # Jinja templates; partials/ holds live-board fragments
  static/
  tests/                # pytest suite
  Pipfile               # runtime + dev deps (pipenv)
  scan_state/           # per-repo incremental scan cache (JSON)
  repositories/         # cloned repos during local dev
tools/run_tests.sh      # test runner invoked by `make test`
scripts/                # build/release scripts, `todoscope` Docker wrapper, git hooks
src-tauri/              # Tauri v2 desktop shell
docs/
```

## Before Starting Work

Add your task to [TODO.md](../TODO.md) first. The board format is documented
in [TODO_CONVENTION.md](TODO_CONVENTION.md): sections map to kanban columns,
bold checkbox items are cards, indented checkboxes are the card's checklist.
Do not invent variations; `scanner/kanban.py` is the parser and the authority.

The wider Plan-Document-Execute-Verify cycle is in
[CONVENTION.instructions.md](../CONVENTION.instructions.md).

## Code Style

Match the surrounding code. In practice:

- PEP-8-ish: 4-space indent, `snake_case`, `CapWords` classes.
- Terse comments and one-line docstrings. Say what, skip the essay. Example
  from the codebase: `"""Return set of valid keys from access_keys.csv. Empty set = auth disabled."""`
- Import order: stdlib, third-party, local — separated by blank lines.
- Type hints where they clarify, not everywhere.

### Error handling

Use the decorators from `scanner/error_handling.py`. `safe_operation` is a
decorator factory — call it:

```python
from scanner.error_handling import safe_operation

@safe_operation(default_return=None)
def risky_operation():
    ...
```

JSON tool-API action endpoints in `scanner/app.py` (`scan_repository`,
`list_repositories`, `pull_repository`) wrap responses with the `mpco_response`
decorator (defined in `scanner/app.py`, not `error_handling.py`). The manifest,
spec, and streaming endpoints return their responses directly — a NDJSON stream
can't be wrapped by a jsonify-style decorator.

### Naming: the tool API is not MCP

The `/api/mpco/*` surface is a plugin-style manifest + OpenAPI REST API. It is
**not** the Model Context Protocol. Never call it MCP in code, comments, docs,
or UI copy — say "tool API" or "manifest + OpenAPI". The route paths keep the
`mpco` name.

## Testing

```bash
make test            # full suite
make test-error      # error handling tests only
make test-unit       # everything else
make test-coverage   # with coverage report
make test-verbose    # -v
```

`make test` runs `tools/run_tests.sh`, which cds to the repo root, sets
`PIPENV_PIPFILE=scanner/Pipfile`, and runs pytest via pipenv. To run one file:

```bash
PIPENV_PIPFILE=scanner/Pipfile pipenv run pytest scanner/tests/test_health.py
```

### Adding tests

Put `test_*.py` files under `scanner/tests/`. The runner picks them up
automatically.

Import convention: tests run from the repo root and import the app as
`scanner.app`. Import it *inside* the fixture or test, after any
monkeypatching, so module-level state (like `ACCESS_KEYS_FILE`) can be
redirected first:

```python
import pytest

@pytest.fixture
def client():
    from scanner.app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_health_ok(client):
    resp = client.get('/health')
    assert resp.status_code == 200
```

See `scanner/tests/test_login_remember.py` for the monkeypatch-then-import
pattern.

## Branches and Pull Requests

- `develop` is the working branch. Branch from it, PR back into it.
- `master` is the release branch. Only release merges land there.

```bash
git checkout develop
git pull
git checkout -b feature/your-feature-name
```

Before opening a PR:

1. `make test` passes.
2. TODO.md updated — completed items marked `- [x]`, new tasks added.
3. Docs updated where your change touches them: `docs/API_REFERENCE.md` for
   API changes, `docs/ARCHITECTURE.md` for structural ones, `README.md` for
   user-facing features.

PR description: what it does, what changed, how it was tested, which TODO.md
items it completes. Include screenshots for UI changes. At least one
maintainer review before merge.

## Commit Messages

Conventional Commits, as in the existing history:

```text
feat(cli): add session lock file and update settings for version check
fix(release): repair v1.0.0 release pipeline
docs: update README + TODO.md for v1.0 release readiness
test: add unit tests for error handling
chore: update dependencies
```

Format: `type(scope): description`, optional body, `Closes #123` where an
issue exists.

## Dependencies

Deps live in `scanner/Pipfile`:

```bash
cd scanner
pipenv install package_name          # runtime
pipenv install --dev package_name    # dev-only
pipenv lock
```

Commit both `Pipfile` and `Pipfile.lock`.

## Issue Reporting

Bugs: steps to reproduce, expected vs actual, Python version and OS, stack
traces. Features: what and why, proposed approach, whether you'll build it.

## Resources

- [Development Workflow](DEVELOPMENT_WORKFLOW.md)
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [TODO.md Convention](TODO_CONVENTION.md)
- [Project README](../README.md)
