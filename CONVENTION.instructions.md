---
applyTo: "*"
---
# Startr Development Workflow

## Core Principles

Every development task follows the **Plan-Document-Execute-Verify** cycle:

00. **DRY** - Don't Repeat Yourself Code
01. **KISS** - Keep It Simple, Stupid
10. **Plan** - Add to TODO before doing work
20. **Document** - Update docs and README as needed
30. **Execute** - Implement changes following standards
40. **Verify** - Test, commit, and check off completed items

## Standard Operating Procedure

### Before Starting Any Work

**ALWAYS add to TODO.md first:**

Always group related tasks under a clear category and main task in `TODO.md` using this template:

```markdown
## [Category] TODOs
- [ ] **[Task Name]**: Brief description
  - [ ] Subtask 1
  - [ ] Subtask 2
  - [ ] Test/verify step
  - [ ] Documentation update
```

Using this structure ensures that all work is tracked, dependencies are clear, and the scope is well-defined before any code changes begin. Additionally, it renders the task visible to the whole team for feedback and approval.

**NEVER start work without:**
- Adding the task to TODO.md
- Getting approval for significant changes
- Understanding the complete scope

### Planning Requirements

For each task, define:
- **Scope** - What exactly needs to be done
- **Dependencies** - What must be completed first
- **Testing** - How to verify it works
- **Documentation** - What docs need updates



## Python Environment

**Always use `pipenv` for development** — it keeps dependencies isolated and reproducible.

- `pipenv run <command>` for one-off commands (e.g., `pipenv run pytest`)
- `pipenv shell` to activate the venv for a session
- `pipenv install <pkg>` for production deps; `pipenv install --dev <pkg>` for dev-only
- Tests: `pipenv run pytest tests/` or `make test` (which wraps pipenv)
- Never install project deps into the global Python — use pipenv or uv

**Exception**: once code is packaged as a standalone binary (PyInstaller) or installed
via `pip install todoscope`, pipenv is no longer needed — the binary/package manages
its own dependencies.

## Makefile Standards

### Canonical Template Location

The authoritative templates live in **WEB-Startr.sh**:
- [`templates/Makefile.base`](https://github.com/Startr/WEB-Startr.sh/blob/master/templates/Makefile.base) — required core for every Startr project
- [`templates/Makefile.docker`](https://github.com/Startr/WEB-Startr.sh/blob/master/templates/Makefile.docker) — extension for containerised projects

This project conforms to both. When in doubt, the templates are the source of truth.

### Required Variable Block

Every Startr project Makefile must declare these variables using **exactly these names**, derived exactly this way. Place them at the top, before all targets:

```makefile
-include .env

PROJECTPATH := $(shell git rev-parse --show-toplevel)
PROJECT := $(shell echo $$(basename $(PROJECTPATH)) | tr '[:upper:]' '[:lower:]')
FULL_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
BRANCH := $(shell echo $(FULL_BRANCH) | sed 's/.*\///' | tr '[:upper:]' '[:lower:]')
TAG := $(shell git describe --always --tag)
REMOTE_URL := $(shell git config --get remote.origin.url 2>/dev/null || echo "unknown/unknown")
OWNER := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/]([^/]+)/[^/]+(.git)?$$|\1|')
PROJECT_NAME := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/][^/]+/([^/]+)(.git)?$$|\1|' | sed 's/\.git$$//')
CONTAINER := $(PROJECT)-$(BRANCH)
```

Project-specific additions go **after** this block.

### Required Targets

Every project must implement these targets:

| Target | Behaviour |
|---|---|
| `help` | Default target; dynamic listing via `@LC_ALL=C $(MAKE) -pRrq` |
| `show_vars` | Prints all standard variable values |
| `setup` | Creates `.env` with project defaults if missing |
| `it_run` | Run the project |
| `it_build` | Build the project |
| `it_build_n_run` | Build then run |
| `install_hooks` | Copies `scripts/hooks/*` into `.git/hooks/` |
| `uninstall_hooks` | Removes project hooks from `.git/hooks/` |
| `things_clean` | `git clean --exclude=!.env -Xdf` |
| `deploy` | CapRover deploy with login guard and submodule tar support |
| `require_gitflow_next` | Guards that git-flow-next is installed |
| `patch_release` / `minor_release` / `major_release` | git-flow release start |
| `hotfix` / `release_finish` / `hotfix_finish` | git-flow hotfix/finish |
| `release` | Calls `scripts/release.sh` — interactive orchestrator |

### Docker Extension Pattern

Containerised projects add these variables **after** the standard block:

```makefile
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)
IMAGE_NAME      ?= $(shell echo $(OWNER)/$(PROJECT_NAME) | tr '[:upper:]' '[:lower:]')
GHCR_IMAGE_NAME ?= ghcr.io/$(shell echo $(OWNER)/$(PROJECT_NAME) | tr '[:upper:]' '[:lower:]')
IMAGE_TAG       := $(if $(TAG),$(TAG),latest)
PORT_MAPPING    ?= 5000:5000
EXTRA_VOLUMES   ?=
```

`IMAGE_NAME` must be lowercased — Docker rejects uppercase registry paths.

`EXTRA_VOLUMES` lets any developer mount additional local paths without a custom target:
```bash
# In .env:
EXTRA_VOLUMES=-v /path/to/myrepos:/mnt/repos

# Or on the CLI:
make it_run EXTRA_VOLUMES="-v /path/to/myrepos:/mnt/repos"
```

`it_run_local` is a thin wrapper that passes `PROJECTS_DIR` through this same mechanism — no duplicate `docker run` block needed.

### scripts/ Directory Convention

Every project must have:
- `scripts/release.sh` — canonical interactive Git Flow orchestrator (copy from WEB-Startr.sh)
- `scripts/hooks/post-checkout` — hook installed via `make install_hooks`

Run `make install_hooks` after cloning to activate.

### Rules

- `.env` loading must use `-include` (silent, non-fatal) — never `ifneq/include/export`
- Never rename the standard variables — tooling and other projects depend on these names
- `CONTAINER` (not `CONTAINER_NAME`) is the running container name throughout
- `TAG` from `git describe --always --tag` degrades to a commit hash when no tags exist — this is correct behaviour

## See the [DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) for more details.