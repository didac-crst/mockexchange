.PHONY: help install dev test lint format clean start stop logs start-valkey start-engine start-oracle start-periscope stop-valkey stop-engine stop-oracle stop-periscope logs-valkey logs-engine logs-oracle logs-periscope examples

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

test: ## Run tests for all packages
	cd packages/engine && poetry run pytest
	cd packages/periscope && poetry run pytest
	cd packages/oracle && poetry run pytest

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
