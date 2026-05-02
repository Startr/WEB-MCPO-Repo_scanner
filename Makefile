# =============================================================================
# repo_scanner — Startr.Cloud
# =============================================================================
# Conforms to: WEB-Startr.sh/templates/Makefile.base + Makefile.docker
#
# Quick start (no container needed):
#   make it_run_dev — start Flask dev server via Pipenv outside the container
#
# Container workflow:
#   make it_build   — build container image
#   make it_run     — run the container
#   make it_run_local — run with PROJECTS_DIR mounted at /mnt/projects
#   make deploy     — deploy to CapRover
#   make help       — list all targets
# =============================================================================

# --- Standard .env loading (Makefile.base) ---
-include .env

# --- Standard variable block (Makefile.base — do not alter names) ---
PROJECTPATH := $(shell git rev-parse --show-toplevel)
PROJECT := $(shell echo $$(basename $(PROJECTPATH)) | tr '[:upper:]' '[:lower:]')
FULL_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
BRANCH := $(shell echo $(FULL_BRANCH) | sed 's/.*\///' | tr '[:upper:]' '[:lower:]')
TAG := $(shell git describe --always --tag)
REMOTE_URL := $(shell git config --get remote.origin.url 2>/dev/null || echo "unknown/unknown")
OWNER := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/]([^/]+)/[^/]+(.git)?$$|\1|')
PROJECT_NAME := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/][^/]+/([^/]+)(.git)?$$|\1|' | sed 's/\.git$$//')
CONTAINER := $(PROJECT)-$(BRANCH)

# --- Docker extension variables (Makefile.docker) ---
SHELL := /bin/bash
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)
IMAGE_NAME      ?= $(shell echo $(OWNER)/$(PROJECT_NAME) | tr '[:upper:]' '[:lower:]')
GHCR_IMAGE_NAME ?= ghcr.io/$(shell echo $(OWNER)/$(PROJECT_NAME) | tr '[:upper:]' '[:lower:]')
IMAGE_TAG       := $(if $(TAG),$(TAG),latest)
PORT_MAPPING    ?= 5000:5000
SECRET_KEY      ?= $(shell python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changeme")

# Project-specific variables
PROJECTS_DIR    ?= $(HOME)/Documents/Projects/GitHub
EXTRA_VOLUMES   ?=
DOCKER_ARGS     ?=
DEV_ARGS        ?=
TEST_ARGS       ?=

# Ensure a script is executable before running it
define ensure-executable
	@if [ ! -x $(1) ]; then chmod +x $(1); fi
endef

.PHONY: help show_vars setup \
        it_build it_build_no_cache it_build_n_run \
	it_run it_run_ghcr it_run_local it_run_dev \
        it_stop it_logs it_clean it_gone \
        install_hooks uninstall_hooks \
        dev_run run_tunnel \
        sync_todos \
        test test-error test-unit test-coverage test-verbose \
        deploy default-deploy \
        require_gitflow_next release_preflight \
        first_release patch_release minor_release major_release internal_tag \
        hotfix release_finish hotfix_finish \
        release things_clean \
        binary binary_dir binary_linux binary_windows \
        app dmg pypi_build pypi_publish clean_dist \
        release_all docker_push

# --- Info Targets ---
help:
	@echo "================================================"
	@echo "       $(OWNER)/$(PROJECT_NAME) by Startr.Cloud"
	@echo "================================================"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null \
		| awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' \
		| sort | grep -E -v -e '^[^[:alnum:]]' -e '^$$@$$'
	@echo ""

show_vars:
	@echo "=== Standard Variables (Makefile.base) ==="
	@echo "PROJECTPATH=$(PROJECTPATH)"
	@echo "PROJECT=$(PROJECT)"
	@echo "OWNER=$(OWNER)"
	@echo "PROJECT_NAME=$(PROJECT_NAME)"
	@echo "FULL_BRANCH=$(FULL_BRANCH)"
	@echo "BRANCH=$(BRANCH)"
	@echo "TAG=$(TAG)"
	@echo "CONTAINER=$(CONTAINER)"
	@echo ""
	@echo "=== Docker Extension Variables (Makefile.docker) ==="
	@echo "CONTAINER_RUNTIME=$(CONTAINER_RUNTIME)"
	@echo "IMAGE_NAME=$(IMAGE_NAME)"
	@echo "GHCR_IMAGE_NAME=$(GHCR_IMAGE_NAME)"
	@echo "IMAGE_TAG=$(IMAGE_TAG)"
	@echo "PORT_MAPPING=$(PORT_MAPPING)"
	@echo "PROJECTS_DIR=$(PROJECTS_DIR)"
	@echo "EXTRA_VOLUMES=$(EXTRA_VOLUMES)"
	@echo ""

# --- Build Targets ---
it_build:
	@echo "Building $(IMAGE_NAME):$(IMAGE_TAG) with BuildKit..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --load \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(IMAGE_TAG)-$(BRANCH) \
		-t $(IMAGE_NAME):$(BRANCH) \
		.
	@afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
	@echo ""

it_build_no_cache:
	@echo "Building $(IMAGE_NAME):$(IMAGE_TAG) without cache..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --no-cache --load \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(IMAGE_TAG)-$(BRANCH) \
		-t $(IMAGE_NAME):$(BRANCH) \
		.
	@afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
	@echo ""

it_build_n_run: it_build
	@$(MAKE) it_run

# --- Run Targets ---
it_run:
	@mkdir -p scanner/repositories
	@test -f scanner/access_keys.csv || touch scanner/access_keys.csv
	@$(CONTAINER_RUNTIME) stop $(CONTAINER) >/dev/null 2>&1 || true
	@$(CONTAINER_RUNTIME) rm   $(CONTAINER) >/dev/null 2>&1 || true
	$(CONTAINER_RUNTIME) run -d \
		-p $(PORT_MAPPING) \
		--name $(CONTAINER) \
		--restart unless-stopped \
		-v "$(PWD)/scanner/repositories:/app/scanner/repositories" \
		-v "$(PWD)/scanner/access_keys.csv:/app/scanner/access_keys.csv" \
		-e SECRET_KEY="$(SECRET_KEY)" \
		$(EXTRA_VOLUMES) \
		$(DOCKER_ARGS) \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Container '$(CONTAINER)' started on port $(PORT_MAPPING)."
	@echo "Tip: set EXTRA_VOLUMES in .env to mount additional local repos"

it_run_ghcr:
	@mkdir -p scanner/repositories
	@test -f scanner/access_keys.csv || touch scanner/access_keys.csv
	@$(CONTAINER_RUNTIME) stop $(CONTAINER) >/dev/null 2>&1 || true
	@$(CONTAINER_RUNTIME) rm   $(CONTAINER) >/dev/null 2>&1 || true
	$(CONTAINER_RUNTIME) run -d \
		-p $(PORT_MAPPING) \
		--name $(CONTAINER) \
		--restart unless-stopped \
		-v "$(PWD)/scanner/repositories:/app/scanner/repositories" \
		-v "$(PWD)/scanner/access_keys.csv:/app/scanner/access_keys.csv" \
		-e SECRET_KEY="$(SECRET_KEY)" \
		$(EXTRA_VOLUMES) \
		$(GHCR_IMAGE_NAME):$(IMAGE_TAG)

# Mount PROJECTS_DIR at /mnt/projects — then register repos inside the app.
# Override PROJECTS_DIR in .env or: make it_run_local PROJECTS_DIR=~/code
it_run_local:
	@$(MAKE) it_run EXTRA_VOLUMES="-v $(PROJECTS_DIR):/mnt/projects $(EXTRA_VOLUMES)"
	@echo "Projects mounted at /mnt/projects (from $(PROJECTS_DIR))"

it_run_dev:
	@echo "Starting Flask development server via Pipenv outside the container..."
	@cd scanner && \
	FLASK_APP=../app.py FLASK_ENV=development \
	pipenv run flask run --host=0.0.0.0 --port=5000 --debug $(DEV_ARGS)

it_stop:
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER)

it_logs:
	$(CONTAINER_RUNTIME) logs -f $(CONTAINER)

it_clean:
	$(CONTAINER_RUNTIME) system prune -f
	$(CONTAINER_RUNTIME) builder prune --force
	@echo ""

it_gone:
	@echo "Forcefully stopping and removing $(CONTAINER)..."
	$(CONTAINER_RUNTIME) stop $(CONTAINER) || true
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER) || true
	@echo "Container $(CONTAINER) has been removed."

# --- Development Targets ---
dev_run: it_run_dev

run_tunnel:
	$(call ensure-executable,tools/run_with_cloudflared.sh)
	@tools/run_with_cloudflared.sh

# --- Setup Targets ---
setup:
	@echo "Setting up local development environment..."
	@if [ ! -f .env ]; then \
		printf 'PORT_MAPPING=5000:5000\n' > .env; \
		printf 'SECRET_KEY=changeme\n' >> .env; \
		printf 'PROJECTS_DIR=$(HOME)/Documents/Projects/GitHub\n' >> .env; \
		printf '# EXTRA_VOLUMES=-v /path/to/repos:/mnt/repos\n' >> .env; \
		echo ".env created — edit it to customize your environment."; \
	else \
		echo ".env already exists — skipping."; \
	fi

install_hooks:
	@if [ ! -d scripts/hooks ]; then echo "ERROR: scripts/hooks not found"; exit 1; fi
	@for hook in scripts/hooks/*; do \
		if [ -f "$$hook" ]; then \
			hook_name=$$(basename "$$hook"); \
			cp "$$hook" ".git/hooks/$$hook_name" && chmod +x ".git/hooks/$$hook_name"; \
			echo "Installed: $$hook_name"; \
		fi; \
	done

uninstall_hooks:
	@for hook in scripts/hooks/*; do \
		if [ -f "$$hook" ]; then \
			hook_name=$$(basename "$$hook"); \
			rm -f ".git/hooks/$$hook_name" && echo "Removed: $$hook_name"; \
		fi; \
	done

# --- Test Targets ---
test:
	@echo "Running tests with args: $(TEST_ARGS)"
	$(call ensure-executable,tools/run_tests.sh)
	@tools/run_tests.sh $(TEST_ARGS)

test-error:
	@$(MAKE) test TEST_ARGS="--error"

test-unit:
	@$(MAKE) test TEST_ARGS="--unit"

test-coverage:
	@$(MAKE) test TEST_ARGS="--all --coverage"

test-verbose:
	@$(MAKE) test TEST_ARGS="--all --verbose"

# --- Project-specific Targets ---
sync_todos:
	$(call ensure-executable,tools/sync_readme_todos.py)
	@tools/sync_readme_todos.py

kanban:
	@echo "Generating KANBAN.canvas..."
	@cd scanner && PYTHONPATH=$(PROJECTPATH) pipenv run python -m scanner.kanban $(PROJECTPATH)

# --- Binary Build Targets ---
binary:
	@echo "Building standalone binary with PyInstaller..."
	@cd scanner && pipenv run pyinstaller -y --onefile \
		--name todoscope \
		--add-data "../scanner/templates:scanner/templates" \
		--add-data "../scanner/static:scanner/static" \
		--add-data "../assets/todoscope.icns:assets" \
		--add-data "../assets/todoscope_menu_icon.png:assets" \
		--hidden-import=yaml \
		--hidden-import=pystray \
		--hidden-import=PIL \
		cli.py --distpath ../dist --workpath ../build
	@echo "Binary at: dist/todoscope"

binary_dir:
	@echo "Building standalone directory with PyInstaller..."
	@cd scanner && pipenv run pyinstaller -y --onedir \
		--name todoscope \
		--add-data "../scanner/templates:scanner/templates" \
		--add-data "../scanner/static:scanner/static" \
		--hidden-import=yaml \
		cli.py --distpath ../dist --workpath ../build
	@echo "App directory at: dist/todoscope/"

# --- Cross-Platform Binary Builds (Docker — run on your Mac) ---
# Uses cdrx/docker-pyinstaller images to build Linux/Windows binaries locally.
# No cloud CI needed — Docker handles the target OS environment.

binary_linux:
	@echo "Building Linux x86_64 binary via Docker..."
	docker run --rm -v "$(PWD):/src" cdrx/pyinstaller-linux \
		"pyinstaller --onefile --name todoscope \
		--add-data 'scanner/templates:scanner/templates' \
		--add-data 'scanner/static:scanner/static' \
		--hidden-import=yaml \
		scanner/cli.py"
	@mkdir -p dist/linux
	@mv dist/todoscope dist/linux/todoscope 2>/dev/null || true
	@echo "Linux binary at: dist/linux/todoscope"

binary_windows:
	@echo "Building Windows x86_64 .exe via Docker (Wine)..."
	docker run --rm -v "$(PWD):/src" cdrx/pyinstaller-windows \
		"pyinstaller --onefile --name todoscope \
		--add-data 'scanner/templates;scanner/templates' \
		--add-data 'scanner/static;scanner/static' \
		--hidden-import=yaml \
		scanner/cli.py"
	@mkdir -p dist/windows
	@mv dist/todoscope.exe dist/windows/todoscope.exe 2>/dev/null || true
	@echo "Windows binary at: dist/windows/todoscope.exe"

# --- macOS .app + DMG ---

app: binary
	@echo "Building macOS .app wrapper..."
	@# -- Clean previous .app build (not the binary!) --
	@rm -rf dist/TodoScope.app
	@mkdir -p dist/TodoScope.app/Contents/MacOS
	@mkdir -p dist/TodoScope.app/Contents/Resources
	@# -- Copy binary as the app executable (no wrapper — binary IS the .app process) --
	@cp dist/todoscope dist/TodoScope.app/Contents/MacOS/TodoScope
	@chmod +x dist/TodoScope.app/Contents/MacOS/TodoScope
	@# -- Copy icon --
	@cp assets/todoscope.icns dist/TodoScope.app/Contents/Resources/todoscope.icns
	@# -- Write Info.plist --
	@printf '<?xml version="1.0" encoding="UTF-8"?>\n\
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n\
<plist version="1.0">\n\
<dict>\n\
  <key>CFBundleName</key><string>TodoScope</string>\n\
  <key>CFBundleDisplayName</key><string>TodoScope</string>\n\
  <key>CFBundleIdentifier</key><string>com.startr.todoscope</string>\n\
  <key>CFBundleVersion</key><string>$(TAG)</string>\n\
  <key>CFBundleShortVersionString</key><string>$(TAG)</string>\n\
  <key>CFBundleIconFile</key><string>todoscope.icns</string>\n\
  <key>CFBundleExecutable</key><string>TodoScope</string>\n\
  <key>CFBundlePackageType</key><string>APPL</string>\n\
  <key>NSHighResolutionCapable</key><true/>\n\
</dict>\n\
</plist>\n' > dist/TodoScope.app/Contents/Info.plist
	@echo "App at: dist/TodoScope.app"

dmg: app
	@echo "Creating styled DMG with create-dmg..."
	@rm -f "dist/TodoScope-$$(git describe --always --tag).dmg"
	create-dmg \
		--volname "TodoScope" \
		--background "assets/dmg_background.png" \
		--window-pos 200 120 \
		--window-size 660 400 \
		--icon-size 80 \
		--icon "TodoScope.app" 165 190 \
		--app-drop-link 495 190 \
		--no-internet-enable \
		"dist/TodoScope-$$(git describe --always --tag).dmg" \
		"dist/TodoScope.app"
	@echo "DMG created: dist/TodoScope-$$(git describe --always --tag).dmg"

pypi_build:
	@cd scanner && pipenv run python -m build --outdir ../dist

pypi_publish: pypi_build
	@cd scanner && pipenv run twine upload ../dist/*.whl ../dist/*.tar.gz

clean_dist:
	rm -rf dist/ build/

# --- Docker Push to GHCR ---
docker_push: it_build
	@echo "Pushing Docker image to GHCR..."
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) $(GHCR_IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) $(GHCR_IMAGE_NAME):latest
	$(CONTAINER_RUNTIME) push $(GHCR_IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) push $(GHCR_IMAGE_NAME):latest
	@echo "Pushed: $(GHCR_IMAGE_NAME):$(IMAGE_TAG)"

# --- Full Release (all local, zero cloud CI) ---
# Builds every artifact and uploads to GitHub + PyPI + GHCR.
# Usage: make patch_release && make release_finish && make release_all
release_all:
	$(call ensure-executable,scripts/release_all.sh)
	@scripts/release_all.sh

# --- Deployment Targets ---
HAS_CAPROVER       := $(shell which caprover 2>/dev/null && echo 1)
HAS_CAPROVER_LOGIN := $(shell caprover ls 2>/dev/null | grep -q "Logged in" && echo 1)
HAS_SUBMODULE      := $(shell [ -f .gitmodules ] && echo 1)
DEPLOY_FLAGS       ?=

deploy:
	@if [ "$(HAS_CAPROVER)" = "" ]; then \
		echo "CapRover CLI not installed. Run: npm install -g caprover"; \
		exit 1; \
	elif [ "$(HAS_CAPROVER_LOGIN)" = "" ]; then \
		echo "Not logged in to CapRover. Run: caprover login"; \
		exit 1; \
	fi
	@if [ "$(HAS_SUBMODULE)" = "1" ]; then \
		git ls-files --recurse-submodules | tar -czf deploy.tar -T -; \
		npx caprover deploy -t ./deploy.tar $(DEPLOY_FLAGS); \
		rm ./deploy.tar; \
	else \
		npx caprover deploy $(DEPLOY_FLAGS); \
	fi

default-deploy:
	@$(MAKE) deploy DEPLOY_FLAGS="--default"

# --- Release Targets ---

# Auto-detect version from release/* or hotfix/* branch name
RELEASE_VERSION := $(shell git rev-parse --abbrev-ref HEAD | sed -n -e 's/^release\///p' -e 's/^hotfix\///p')

# Clear stale git-flow merge state left over from an interrupted finish
define clear_stale_gitflow_state
	if [ -f .git/gitflow/state/merge.json ] && [ ! -f .git/MERGE_HEAD ]; then \
		echo "Clearing stale git-flow merge state..."; \
		rm -f .git/gitflow/state/merge.json; \
	fi
endef

require_gitflow_next:
	@if ! git flow version 2>/dev/null | grep -q 'git-flow-next'; then \
		echo "Error: git-flow-next required. Install: brew install git-flow-next"; \
		exit 1; \
	fi

# Pre-flight checks before a public release. Fails BEFORE any irreversible
# action (tag creation, push) so a bad state can't produce a half-released tag.
release_preflight:
	@echo "→ Pre-flight checks..."
	@git diff-index --quiet HEAD || \
		(echo "ERROR: uncommitted changes — commit or stash first" && exit 1)
	@git fetch origin develop --quiet
	@[ "$$(git rev-parse develop)" = "$$(git rev-parse origin/develop)" ] || \
		(echo "ERROR: local develop differs from origin/develop — pull or push first" && exit 1)
	@command -v gh >/dev/null || (echo "ERROR: gh CLI not installed — run 'brew install gh'" && exit 1)
	@gh auth status >/dev/null 2>&1 || (echo "ERROR: gh not authenticated — run 'gh auth login'" && exit 1)
	@docker info >/dev/null 2>&1 || (echo "ERROR: Docker not running — start Docker Desktop" && exit 1)
	@command -v create-dmg >/dev/null || (echo "ERROR: create-dmg missing — run 'brew install create-dmg'" && exit 1)
	@echo "  ✓ All checks passed"

first_release: require_gitflow_next
	git flow release start 0.0.1
	@echo ""
	@echo "=== First release branch created (release/0.0.1) ==="
	@echo "Next steps:"
	@echo "  1. make release_finish     # Merge, tag, and push to origin"

patch_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')

minor_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')

major_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')

# hotfix uses git-flow-next's hotfix branch (off master). Auto-bumps PATCH from latest tag.
hotfix: require_gitflow_next
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')

# Lightweight internal tag — no binary release, no git-flow merge ceremony.
# Auto-increments the 4th segment. v1.0.0 → v1.0.0.1; v1.0.0.3 → v1.0.0.4
# Use for internal milestones, RCs, demo checkpoints — anything you want to
# mark in git history without triggering a public binary release.
internal_tag:
	@LAST=$$(git tag --sort=-v:refname | head -1 | sed 's/^v//'); \
	if [ -z "$$LAST" ]; then \
		echo "ERROR: no tags exist yet — create v0.0.1 or later first via 'make first_release'"; exit 1; \
	fi; \
	if echo "$$LAST" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$$'; then \
		NEXT="v$${LAST}.1"; \
	elif echo "$$LAST" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$$'; then \
		NEXT="v$$(echo "$$LAST" | awk -F. '{print $$1"."$$2"."$$3"."$$4+1}')"; \
	else \
		echo "ERROR: latest tag '$$LAST' has unexpected format"; exit 1; \
	fi; \
	echo "Tagging $$NEXT (internal — no binary release)"; \
	git tag -a "$$NEXT" -m "Internal tag $$NEXT"; \
	git push origin "$$NEXT"; \
	echo "Pushed $$NEXT to origin."

release_finish: require_gitflow_next release_preflight
	@$(clear_stale_gitflow_state)
	@git flow release finish --no-fetch || ( \
		echo "git-flow finish failed — completing release/$(RELEASE_VERSION) manually..."; \
		rm -f .git/gitflow/state/merge.json; \
		git checkout master && \
		git merge --no-ff --no-edit release/$(RELEASE_VERSION) && \
		(git tag -a "$(RELEASE_VERSION)" -m "Release $(RELEASE_VERSION)" 2>/dev/null || echo "  Tag $(RELEASE_VERSION) already exists") && \
		git checkout develop && \
		git merge --no-ff --no-edit master && \
		git branch -d release/$(RELEASE_VERSION) \
	)
	@git push origin develop && git push origin master && git push --tags
	@git checkout develop
	@echo ""
	@echo "=== Release $(RELEASE_VERSION) tagged and pushed ==="
	@# Chain into release_all only for 3-segment public tags.
	@# 4-segment tags (e.g. v1.0.0.1) skip binaries — use 'make internal_tag' for those.
	@if echo "$(RELEASE_VERSION)" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$$'; then \
		echo ""; \
		echo "=== Building binaries for v$(RELEASE_VERSION) ==="; \
		$(MAKE) release_all; \
	else \
		echo "Non-public version $(RELEASE_VERSION) — skipping binary release."; \
		echo "Use 'make internal_tag' for lightweight checkpoints."; \
	fi

hotfix_finish: require_gitflow_next
	@$(clear_stale_gitflow_state)
	@git flow hotfix finish --no-fetch || ( \
		echo "git-flow hotfix finish failed — completing manually..."; \
		rm -f .git/gitflow/state/merge.json; \
		HOTFIX_VER=$$(git rev-parse --abbrev-ref HEAD | sed 's/^hotfix\///'); \
		git checkout master && \
		git merge --no-ff --no-edit hotfix/$$HOTFIX_VER && \
		(git tag -a "$$HOTFIX_VER" -m "Hotfix $$HOTFIX_VER" 2>/dev/null || echo "  Tag $$HOTFIX_VER already exists") && \
		git checkout develop && \
		git merge --no-ff --no-edit master && \
		git branch -d hotfix/$$HOTFIX_VER \
	)
	@git push origin develop && git push origin master && git push --tags
	@git checkout develop

release:
	@scripts/release.sh

things_clean:
	git clean --exclude=!.env -Xdf
