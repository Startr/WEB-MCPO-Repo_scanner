# =============================================================================
# TodoScope CI/CD Framework
# =============================================================================
# Provider-agnostic build and deployment system.
# Runs on: Linux, macOS, Windows (WSL)
# Requires: make, bash, git, container runtime (podman or docker)
#
# Quick start:
#   make it_build   — build container image
#   make it_run     — run the container
#   make dev_run    — start Flask dev server locally
#   make deploy     — deploy to CapRover
#   make help       — list all targets
# =============================================================================

# Load environment variables from .env if it exists
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

SHELL := /bin/bash

# Auto-detect container runtime (prefer podman, fall back to docker)
CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)

# Derive org/repo from git remote (e.g. git@github.com:Startr/WEB-MCPO-Repo_scanner.git → startr/web-mcpo-repo_scanner)
GIT_REPO_SLUG := $(shell git remote get-url origin 2>/dev/null | sed -E 's|\.git$$||; s|.*[:/]([^/]+/[^/]+)$$|\1|' | tr '[:upper:]' '[:lower:]')

IMAGE_NAME      ?= $(GIT_REPO_SLUG)
GHCR_IMAGE_NAME ?= ghcr.io/$(GIT_REPO_SLUG)
GIT_TAG         := $(shell git tag --sort=-v:refname | sed 's/^v//' | head -n 1)
IMAGE_TAG       := $(if $(GIT_TAG),$(GIT_TAG),latest)
GIT_BRANCH      := $(shell git rev-parse --abbrev-ref HEAD)
ifeq ($(GIT_BRANCH),HEAD)
    GIT_BRANCH  := $(shell git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD)
endif
SAFE_GIT_BRANCH := $(subst /,-,$(GIT_BRANCH))
SAFE_GIT_BRANCH := $(shell echo $(SAFE_GIT_BRANCH) | tr '[:upper:]' '[:lower:]')
CONTAINER_NAME  ?= $(shell echo $(GIT_REPO_SLUG) | tr '/' '-')

PORT_MAPPING ?= 5000:5000
SECRET_KEY   ?= $(shell python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "changeme")

# Guard macro: prints a helpful error if a required tool is missing
define require_tool
	@if [ -z "$($(1))" ]; then \
		echo "Error: $(2) not found in PATH."; \
		exit 1; \
	fi
endef

# Ensure a script is executable before running it
define ensure-executable
	@if [ ! -x $(1) ]; then chmod +x $(1); fi
endef

.PHONY: help \
        it_build it_build_no_cache it_build_n_run \
        it_run it_run_ghcr it_stop it_logs it_clean it_gone \
        dev_run run_tunnel \
        sync_todos \
        test test-error test-unit test-coverage test-verbose \
        deploy default-deploy \
        require_gitflow_next minor_release patch_release major_release \
        hotfix release_finish hotfix_finish \
        things_clean

help:
	@echo "======================================================="
	@echo "  $(IMAGE_NAME) — TodoScope by Startr.Cloud"
	@echo ""
	@echo "Usage examples:"
	@echo "  1) Build:      make it_build"
	@echo "  2) Run:        make it_run"
	@echo "  3) Dev:        make dev_run"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null \
		| awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' \
		| sort | grep -E -v -e '^[^[:alnum:]]' -e '^$$@$$'
	@echo ""

# --- Build Targets ---
it_build:
	@echo "Building $(IMAGE_NAME):$(IMAGE_TAG) with BuildKit..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --load \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
		-t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
		.
	@afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
	@echo ""

it_build_no_cache:
	@echo "Building $(IMAGE_NAME):$(IMAGE_TAG) without cache..."
	@export DOCKER_BUILDKIT=1 && \
	$(CONTAINER_RUNTIME) build --no-cache --load \
		-t $(IMAGE_NAME):$(IMAGE_TAG) \
		-t $(IMAGE_NAME):latest \
		-t $(IMAGE_NAME):$(IMAGE_TAG)-$(SAFE_GIT_BRANCH) \
		-t $(IMAGE_NAME):$(SAFE_GIT_BRANCH) \
		.
	@afplay /System/Library/Sounds/Glass.aiff 2>/dev/null || true
	@echo ""

it_build_n_run: it_build
	@$(MAKE) it_run

# --- Run Targets ---
# Path to your local projects folder — override in .env or on the CLI
PROJECTS_DIR ?= $(HOME)/Documents/Projects/GitHub
DOCKER_ARGS  ?=

it_run:
	@mkdir -p scanner/repositories
	@test -f scanner/access_keys.csv || touch scanner/access_keys.csv
	@$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@$(CONTAINER_RUNTIME) rm   $(CONTAINER_NAME) >/dev/null 2>&1 || true
	$(CONTAINER_RUNTIME) run -d \
		-p $(PORT_MAPPING) \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-v "$(PWD)/scanner/repositories:/app/scanner/repositories" \
		-v "$(PWD)/scanner/access_keys.csv:/app/scanner/access_keys.csv" \
		-e SECRET_KEY="$(SECRET_KEY)" \
		$(DOCKER_ARGS) \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Container '$(CONTAINER_NAME)' started on port $(PORT_MAPPING)."

it_run_ghcr:
	$(CONTAINER_RUNTIME) run -d \
		-p $(PORT_MAPPING) \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-v "$(PWD)/scanner/repositories:/app/scanner/repositories" \
		-v "$(PWD)/scanner/access_keys.csv:/app/scanner/access_keys.csv" \
		-e SECRET_KEY="$(SECRET_KEY)" \
		$(GHCR_IMAGE_NAME):$(IMAGE_TAG)

# Like it_run but also mounts PROJECTS_DIR so local repos are accessible
# without cloning. Register them inside the app from /mnt/projects/<name>.
# Override PROJECTS_DIR in .env or: make it_run_local PROJECTS_DIR=~/code
it_run_local:
	@mkdir -p scanner/repositories
	@test -f scanner/access_keys.csv || touch scanner/access_keys.csv
	@$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@$(CONTAINER_RUNTIME) rm   $(CONTAINER_NAME) >/dev/null 2>&1 || true
	$(CONTAINER_RUNTIME) run -d \
		-p $(PORT_MAPPING) \
		--name $(CONTAINER_NAME) \
		--restart unless-stopped \
		-v "$(PWD)/scanner/repositories:/app/scanner/repositories" \
		-v "$(PWD)/scanner/access_keys.csv:/app/scanner/access_keys.csv" \
		-v "$(PROJECTS_DIR):/mnt/projects" \
		-e SECRET_KEY="$(SECRET_KEY)" \
		$(DOCKER_ARGS) \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Container '$(CONTAINER_NAME)' started on port $(PORT_MAPPING)."
	@echo "Projects mounted at /mnt/projects (from $(PROJECTS_DIR))"

it_stop:
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME)

it_logs:
	$(CONTAINER_RUNTIME) logs -f $(CONTAINER_NAME)

it_clean:
	$(CONTAINER_RUNTIME) system prune -f
	$(CONTAINER_RUNTIME) builder prune --force
	@echo ""

it_gone:
	@echo "Forcefully stopping and removing $(CONTAINER_NAME)..."
	$(CONTAINER_RUNTIME) stop $(CONTAINER_NAME) || true
	$(CONTAINER_RUNTIME) rm -f $(CONTAINER_NAME) || true
	@echo "Container $(CONTAINER_NAME) has been removed."

# --- Development Targets ---
DEV_ARGS ?=

dev_run:
	@echo "Starting Flask development server..."
	@FLASK_APP=app.py FLASK_ENV=development \
	flask run --host=0.0.0.0 --port=5000 --debug $(DEV_ARGS)

run_tunnel:
	$(call ensure-executable,tools/run_with_cloudflared.sh)
	@tools/run_with_cloudflared.sh

# --- Test Targets ---
TEST_ARGS ?=

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

minor_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}')

patch_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}')

major_release: require_gitflow_next
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}')

hotfix: require_gitflow_next
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3"."$$4+1}')

release_finish: require_gitflow_next
	git flow release finish && git push origin develop && git push origin master && git push --tags && git checkout develop

hotfix_finish: require_gitflow_next
	git flow hotfix finish && git push origin develop && git push origin master && git push --tags && git checkout develop

things_clean:
	git clean --exclude=!.env -Xdf
