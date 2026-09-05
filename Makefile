.PHONY: help build up down restart logs test lint migrate seed health clean

COMPOSE = cd infrastructure && docker compose
STACK = infrastructure

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ────────────────────────────────────────────────

build: ## Build all Docker images
	$(COMPOSE) build

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

restart-web: ## Restart web + scheduler
	$(COMPOSE) restart web scheduler

logs: ## Tail all logs
	$(COMPOSE) logs -f

logs-web: ## Tail web logs
	$(COMPOSE) logs -f web

# ─── Development ───────────────────────────────────────────

setup: ## Full setup (certs + start + seed)
	cd $(STACK) && ./scripts/setup.sh

seed: ## Seed Wazuh configuration
	$(COMPOSE) exec web python seed_wazuh_config.py

migrate: ## Run Django migrations
	$(COMPOSE) exec web python manage.py migrate

createsuperuser: ## Create Django superuser
	$(COMPOSE) exec web python manage.py createsuperuser

shell: ## Open Django shell
	$(COMPOSE) exec web python manage.py shell

dbshell: ## Open database shell
	$(COMPOSE) exec db psql -U ariba_soc -d ariba_soc

# ─── Testing ───────────────────────────────────────────────

test: ## Run all tests
	$(COMPOSE) exec web python manage.py test

test-verbose: ## Run tests with verbose output
	$(COMPOSE) exec web python manage.py test --verbosity=2

# ─── Code Quality ──────────────────────────────────────────

lint: ## Run linting (flake8 + black check)
	cd ariba_soc && flake8 . --max-line-length=120 --ignore=E501,W503
	cd ariba_soc && black --check .

format: ## Auto-format code
	cd ariba_soc && black .
	cd ariba_soc && isort .

# ─── Health & Monitoring ───────────────────────────────────

health: ## Run health check
	$(STACK)/scripts/health-check.sh

status: ## Show container status
	$(COMPOSE) ps

# ─── Backup & Restore ──────────────────────────────────────

backup: ## Backup database and configs
	$(STACK)/scripts/backup.sh

restore: ## Restore from backup (usage: make restore TIMESTAMP=20260101_000000)
	$(STACK)/scripts/restore.sh $(TIMESTAMP)

# ─── Cleanup ───────────────────────────────────────────────

clean: ## Remove stopped containers and unused images
	docker container prune -f
	docker image prune -f

clean-all: ## Remove everything (containers, volumes, networks)
	$(COMPOSE) down -v --rmi all
	docker system prune -af

# ─── Production ────────────────────────────────────────────

prod-up: ## Start production stack
	$(COMPOSE) -f docker-compose.prod.yml up -d

prod-down: ## Stop production stack
	$(COMPOSE) -f docker-compose.prod.yml down

deploy: ## Deploy to remote server (usage: make deploy SERVER=user@ip)
	$(STACK)/scripts/deploy-remote.sh $(SERVER)
