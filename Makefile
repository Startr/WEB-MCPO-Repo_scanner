SHELL := /bin/bash

# Docker-related variables
IMAGE_NAME := repo-scanner
CONTAINER_NAME := repo-scanner-app
HOST_PORT := 5000
CONTAINER_PORT := 5000

.PHONY: all sync-todos docker-build docker-run docker-stop docker-logs docker-clean docker-prune run-dev

all: docker-build # Default target

sync-todos:
	@echo "Syncing TODO.md to README.md using script..."
	@if [ ! -x tools/sync_readme_todos.sh ]; then \
		echo "Making tools/sync_readme_todos.sh executable..."; \
		chmod +x tools/sync_readme_todos.sh; \
	fi
	@tools/sync_readme_todos.sh

# --- Docker Targets ---
docker-build:
	@echo "Building Docker image '$(IMAGE_NAME)'..."
	@docker build -t $(IMAGE_NAME) .

docker-run:
	@echo "Running Docker container '$(CONTAINER_NAME)' from image '$(IMAGE_NAME)'..."
	@# Stop and remove if already running to avoid conflicts
	@docker stop $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker rm $(CONTAINER_NAME) >/dev/null 2>&1 || true
	@docker run -d -p $(HOST_PORT):$(CONTAINER_PORT) --name $(CONTAINER_NAME) $(IMAGE_NAME)
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
run-dev:
	@echo "Starting Flask development server..."
	@FLASK_APP=app.py FLASK_ENV=development flask run --host=0.0.0.0 --port=$(HOST_PORT) --debug

# Note on two-way sync (from previous version, kept for context if needed):
# True two-way synchronization is complex to implement reliably in a Makefile...
# (The rest of the comment about two-way sync can be kept or removed as preferred)
