SHELL := /bin/bash

# Docker-related variables
IMAGE_NAME := repo-scanner
CONTAINER_NAME := repo-scanner-app
HOST_PORT := 5000
CONTAINER_PORT := 5000

# Helper functions
define ensure-executable
	@if [ ! -x $(1) ]; then \
		echo "Making $(1) executable..."; \
		chmod +x $(1); \
	fi
endef

.PHONY: all sync-todos docker-build docker-run docker-stop docker-logs docker-clean docker-prune run-dev test test-error test-unit test-coverage test-verbose

all: docker-build # Default target

sync-todos:
	@echo "Syncing TODO.md to README.md using script..."
	$(call ensure-executable,tools/sync_readme_todos.sh)
	@tools/sync_readme_todos.sh

# --- Test Targets ---
# Main test target that accepts arguments via TEST_ARGS variable
test:
	@echo "Running tests with args: $(TEST_ARGS)"
	$(call ensure-executable,tools/run_tests.sh)
	@tools/run_tests.sh $(TEST_ARGS)

# Convenience targets for common test scenarios
test-error:
	@$(MAKE) test TEST_ARGS="--error"

test-unit:
	@$(MAKE) test TEST_ARGS="--unit"

test-coverage:
	@$(MAKE) test TEST_ARGS="--all --coverage"

test-verbose:
	@$(MAKE) test TEST_ARGS="--all --verbose"

# --- Docker Targets ---
docker-build:
	@echo "Building Docker image '$(IMAGE_NAME)'..."
	@docker build -t $(IMAGE_NAME) .

docker-run: DOCKER_ARGS ?=
docker-run:
	@echo "Running Docker container '$(CONTAINER_NAME)' from image '$(IMAGE_NAME)'..."
	@# Stop and remove if already running to avoid conflicts
	@docker stop $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker rm $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker run -d -p $(HOST_PORT):$(CONTAINER_PORT) --name $(CONTAINER_NAME) $(DOCKER_ARGS) $(IMAGE_NAME)
	@echo "Container '$(CONTAINER_NAME)' started on port $(HOST_PORT)."

docker-stop:
	@echo "Stopping Docker container '$(CONTAINER_NAME)'..."
	@docker stop $(CONTAINER_NAME)

docker-logs:
	@echo "Showing logs for Docker container '$(CONTAINER_NAME)'..."
	@docker logs -f $(CONTAINER_NAME)

docker-clean: docker-stop
	@echo "Removing Docker container '$(CONTAINER_NAME)'..."
	@docker rm $(CONTAINER_NAME)

docker-prune: docker-clean
	@echo "Removing Docker image '$(IMAGE_NAME)'..."
	@docker rmi $(IMAGE_NAME) || echo "Image '$(IMAGE_NAME)' not found or could not be removed (perhaps it has dependent children?)"

# --- Development Targets ---
run-dev: DEV_ARGS ?=
run-dev:
	@echo "Starting Flask development server..."
	@FLASK_APP=app.py FLASK_ENV=development flask run --host=0.0.0.0 --port=$(HOST_PORT) --debug $(DEV_ARGS)

run-tunnel:
	@echo "Starting Flask with Cloudflare tunnel..."
	$(call ensure-executable,tools/run_with_cloudflared.sh)
	@tools/run_with_cloudflared.sh

# Note on two-way sync (from previous version, kept for context if needed):
# True two-way synchronization is complex to implement reliably in a Makefile...
# (The rest of the comment about two-way sync can be kept or removed as preferred)
