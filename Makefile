# =============================================================================
# repo_scanner — Startr.Cloud
# =============================================================================
# Conforms to: WEB-Startr.sh/templates/Makefile.base + Makefile.docker
#
# Quick start (no container needed):
#   make dev_run    — start Flask dev server directly (fastest for development)
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
        it_run it_run_ghcr it_run_local \
        it_stop it_logs it_clean it_gone \
        install_hooks uninstall_hooks \
        dev_run run_tunnel \
        sync_todos \
        test test-error test-unit test-coverage test-verbose \
        deploy default-deploy \
        require_gitflow_next patch_release minor_release major_release \
        hotfix release_finish hotfix_finish \
        release things_clean

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
dev_run:
	@echo "Starting Flask development server..."
	@FLASK_APP=app.py FLASK_ENV=development \
	flask run --host=0.0.0.0 --port=5000 --debug $(DEV_ARGS)

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
	$(call ensure-executable,tools/sync_readme_todos.sh)
	@tools/sync_readme_todos.sh

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
require_gitflow_next:
	@if ! git flow version 2>/dev/null | grep -q 'git-flow-next'; then \
		echo "Error: git-flow-next required. Install: brew install git-flow-next"; \
		exit 1; \
	fi

patch_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')

minor_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')

major_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')

hotfix: require_gitflow_next
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3"."$$4+1}')

release_finish: require_gitflow_next
	git flow release finish && git push origin develop && git push origin master && git push --tags && git checkout develop

hotfix_finish: require_gitflow_next
	git flow hotfix finish && git push origin develop && git push origin master && git push --tags && git checkout develop

release:
	@scripts/release.sh

things_clean:
	git clean --exclude=!.env -Xdf
