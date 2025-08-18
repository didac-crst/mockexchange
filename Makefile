.PHONY: help install dev test lint format clean start stop logs start-valkey start-engine start-oracle start-periscope stop-valkey stop-engine stop-oracle stop-periscope logs-valkey logs-engine logs-oracle logs-periscope restart restart-valkey restart-engine restart-oracle restart-periscope restart-no-cache restart-valkey-no-cache restart-engine-no-cache restart-oracle-no-cache restart-periscope-no-cache examples

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ''
	@echo 'Note: Individual package start/stop scripts have been removed in favor of this unified Makefile.'

install: ## Install all dependencies
	poetry install
	cd packages/engine && poetry install
	cd packages/periscope && poetry install
	cd packages/oracle && poetry install

dev: ## Install development dependencies
	poetry install --with dev
	pre-commit install

test: ## Run unit tests for all packages (fast, no external dependencies)
	cd packages/engine && poetry run pytest tests/unit/
	cd packages/periscope && poetry run pytest
	cd packages/oracle && poetry run pytest

test-engine: ## Run engine tests
	cd packages/engine && poetry run pytest

test-oracle: ## Run oracle tests
	cd packages/oracle && poetry run pytest

test-periscope: ## Run periscope tests
	cd packages/periscope && poetry run pytest

test-unit: ## Run unit tests only (same as 'test')
	cd packages/engine && poetry run pytest tests/unit/
	cd packages/oracle && poetry run pytest
	cd packages/periscope && poetry run pytest

test-integration: ## Run integration tests only (requires running services)
	cd packages/engine && poetry run pytest tests/integration/

test-integration-fresh: restart-no-cache test-integration ## Run integration tests with fresh Docker builds (no cache)

test-integration-engine: ## Run engine integration tests only (requires running services)
	cd packages/engine && poetry run pytest tests/integration/

test-integration-engine-fresh: restart-engine-no-cache test-integration-engine ## Run engine integration tests with fresh engine build (no cache)

lint: ## Run linting for all packages
	poetry run ruff check .
	poetry run mypy packages/engine/src
	poetry run black --check .

format: ## Format code
	poetry run black .
	poetry run ruff check --fix .

clean: ## Clean up build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

start: ## Start all services with Docker Compose
	docker-compose up -d

start-valkey: ## Start only the valkey service
	docker-compose up -d valkey

start-engine: ## Start only the engine service
	docker-compose up -d engine

start-oracle: ## Start only the oracle service
	docker-compose up -d oracle

start-periscope: ## Start only the periscope service
	docker-compose up -d periscope

stop: ## Stop all services
	docker-compose down

stop-valkey: ## Stop only the valkey service
	docker-compose stop valkey

stop-engine: ## Stop only the engine service
	docker-compose stop engine

stop-oracle: ## Stop only the oracle service
	docker-compose stop oracle

stop-periscope: ## Stop only the periscope service
	docker-compose stop periscope

logs: ## Show logs from all services
	docker-compose logs -f

logs-valkey: ## Show valkey logs
	docker-compose logs -f valkey

logs-engine: ## Show engine logs
	docker-compose logs -f engine

logs-oracle: ## Show oracle logs
	docker-compose logs -f oracle

logs-periscope: ## Show periscope logs
	docker-compose logs -f periscope

restart: stop start ## Restart all services

restart-valkey: stop-valkey start-valkey ## Restart only the valkey service

restart-engine: stop-engine start-engine ## Restart only the engine service

restart-oracle: stop-oracle start-oracle ## Restart only the oracle service

restart-periscope: stop-periscope start-periscope ## Restart only the periscope service

restart-no-cache: ## Restart all services with fresh Docker builds (no cache)
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

restart-valkey-no-cache: ## Restart valkey service with fresh Docker build (no cache)
	docker-compose stop valkey
	docker-compose build --no-cache valkey
	docker-compose up -d valkey

restart-engine-no-cache: ## Restart engine service with fresh Docker build (no cache)
	docker-compose stop engine
	docker-compose build --no-cache engine
	docker-compose up -d engine

restart-oracle-no-cache: ## Restart oracle service with fresh Docker build (no cache)
	docker-compose stop oracle
	docker-compose build --no-cache oracle
	docker-compose up -d oracle

restart-periscope-no-cache: ## Restart periscope service with fresh Docker build (no cache)
	docker-compose stop periscope
	docker-compose build --no-cache periscope
	docker-compose up -d periscope

status: ## Show service status
	docker-compose ps

# Examples and Tools
examples: ## Show available examples
	@echo "Available examples:"
	@echo "  order-generator  - Random order generator for load testing"
	@echo ""
	@echo "Order Generator Commands:"
	@echo "  make order-generator           # Fresh start with reset"
	@echo "  make order-generator-restart   # Continue without reset"
	@echo "  make order-generator-restart-reset # Continue with reset"
	@echo "  make order-generator-logs      # View logs"
	@echo "  make order-generator-stop      # Stop generator"
	@echo "  make order-generator-status    # Check status"
	@echo ""
	@echo "Manual usage:"
	@echo "  cd examples/order-generator"
	@echo "  ./manage.sh start --reset"

order-generator: ## Start the order generator example (fresh start with reset)
	@echo "Starting order generator (fresh start with reset)..."
	@cd examples/order-generator && ./manage.sh start --reset

order-generator-restart: ## Restart the order generator (continue without reset)
	@echo "Restarting order generator (continue without reset)..."
	@cd examples/order-generator && ./manage.sh restart

order-generator-restart-reset: ## Restart the order generator with reset
	@echo "Restarting order generator with reset..."
	@cd examples/order-generator && ./manage.sh restart --reset

order-generator-logs: ## Show order generator logs
	@cd examples/order-generator && ./manage.sh logs

order-generator-stop: ## Stop the order generator
	@cd examples/order-generator && ./manage.sh stop

order-generator-status: ## Show order generator status
	@cd examples/order-generator && ./manage.sh status

# Version Info
version ?= $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
sha := $(shell git rev-parse --short HEAD)

version: ## Show current version and available tags
	@echo "Current version: $(version)"
	@echo "Git SHA: $(sha)"
	@echo ""
	@echo "Recent tags:"
	@git tag --sort=-version:refname | head -10
	@echo ""
	@echo "To create a release:"
	@echo "  git tag -a vX.Y.Z -m 'Release vX.Y.Z'"
	@echo "  git push origin vX.Y.Z"
	@echo ""
	@echo "To create a release branch:"
	@echo "  make release-branch                  # Interactive menu"
	@echo "  ./scripts/create-release-branch.sh [patch|minor|major]"
	@echo "  ./scripts/create-release-branch.sh patch --dry-run  # Preview"

release-branch: ## Create a new release branch (interactive)
	@echo "Creating release branch..."
	@echo "Choose bump type:"
	@echo "  1) patch (0.1.0 → 0.1.1)"
	@echo "  2) minor (0.1.0 → 0.2.0)"
	@echo "  3) major (0.1.0 → 1.0.0)"
	@read -p "Enter choice (1-3): " choice; \
	case $$choice in \
		1) ./scripts/create-release-branch.sh patch ;; \
		2) ./scripts/create-release-branch.sh minor ;; \
		3) ./scripts/create-release-branch.sh major ;; \
		*) echo "Invalid choice"; exit 1 ;; \
	esac
