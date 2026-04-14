.PHONY: help build up down logs migrate test clean health restart shell db

# Variables
COMPOSE := docker-compose
COMPOSE_DEV := docker-compose -f docker-compose.dev.yml
BACKEND := $(COMPOSE) exec backend
BACKEND_DEV := $(COMPOSE_DEV) exec backend

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m

help:
	@echo "$(BLUE)================================$(NC)"
	@echo "$(BLUE)ProctoAI Docker Commands$(NC)"
	@echo "$(BLUE)================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup:$(NC)"
	@echo "  make setup              - Setup .env from template"
	@echo "  make build-prod         - Build production images"
	@echo "  make build-dev          - Build development images"
	@echo ""
	@echo "$(YELLOW)Running:$(NC)"
	@echo "  make up-prod            - Start production environment"
	@echo "  make up-dev             - Start development environment (auto-reload)"
	@echo "  make down-prod          - Stop production environment"
	@echo "  make down-dev           - Stop development environment"
	@echo "  make restart-prod       - Restart production environment"
	@echo "  make restart-dev        - Restart development environment"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  make migrate            - Run database migrations"
	@echo "  make migration NAME=... - Create new migration"
	@echo "  make db                 - Access PostgreSQL CLI"
	@echo "  make reset-db           - Reset database (removes all data)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  make logs [SERVICE]     - View container logs"
	@echo "  make shell              - Access Python shell"
	@echo "  make test               - Run tests"
	@echo "  make test-cov           - Run tests with coverage"
	@echo ""
	@echo "$(YELLOW)Maintenance:$(NC)"
	@echo "  make health             - Check service health"
	@echo "  make status             - Show container status"
	@echo "  make clean              - Remove stopped containers"
	@echo "  make clean-all          - Remove all images, containers, volumes"
	@echo ""

# Setup
setup:
	@if [ ! -f ".env" ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓$(NC) .env file created from .env.example"; \
		echo "$(YELLOW)→ Please update .env with your configuration$(NC)"; \
	else \
		echo "$(YELLOW)→$(NC) .env file already exists"; \
	fi

# Build
build-prod:
	@echo "$(BLUE)Building production images...$(NC)"
	$(COMPOSE) build
	@echo "$(GREEN)✓ Build complete$(NC)"

build-dev:
	@echo "$(BLUE)Building development images...$(NC)"
	$(COMPOSE_DEV) build
	@echo "$(GREEN)✓ Build complete$(NC)"

# Running - Production
up-prod: setup
	@echo "$(BLUE)Starting production environment...$(NC)"
	$(COMPOSE) up -d
	@echo "$(GREEN)✓ Services started in background$(NC)"
	@echo "$(YELLOW)→ View logs with: make logs$(NC)"

down-prod:
	@echo "$(BLUE)Stopping production environment...$(NC)"
	$(COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart-prod: down-prod up-prod
	@echo "$(GREEN)✓ Services restarted$(NC)"

# Running - Development
up-dev: setup
	@echo "$(BLUE)Starting development environment (auto-reload enabled)...$(NC)"
	$(COMPOSE_DEV) up

down-dev:
	@echo "$(BLUE)Stopping development environment...$(NC)"
	$(COMPOSE_DEV) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

restart-dev: down-dev up-dev
	@echo "$(GREEN)✓ Services restarted$(NC)"

# Database
migrate:
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(BACKEND) python -m alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(NC)"

migration:
	@if [ -z "$(NAME)" ]; then \
		echo "$(RED)✗ Migration name required$(NC)"; \
		echo "Usage: make migration NAME=\"Your migration name\""; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration: $(NAME)$(NC)"
	$(BACKEND) python -m alembic revision --autogenerate -m "$(NAME)"
	@echo "$(GREEN)✓ Migration created$(NC)"

db:
	@echo "$(BLUE)Opening PostgreSQL CLI...$(NC)"
	$(COMPOSE) exec postgres psql -U postgres -d quizapp

reset-db:
	@echo "$(YELLOW)⚠ This will delete all data!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Resetting database...$(NC)"; \
		$(COMPOSE) down -v; \
		$(COMPOSE) up -d; \
		sleep 5; \
		$(BACKEND) python -m alembic upgrade head; \
		echo "$(GREEN)✓ Database reset complete$(NC)"; \
	else \
		echo "$(YELLOW)→ Reset cancelled$(NC)"; \
	fi

# Development
logs:
	@if [ -z "$(SERVICE)" ]; then \
		$(COMPOSE) logs -f; \
	else \
		$(COMPOSE) logs -f $(SERVICE); \
	fi

shell:
	@echo "$(BLUE)Opening Python shell...$(NC)"
	$(BACKEND) python

test:
	@echo "$(BLUE)Running tests...$(NC)"
	$(BACKEND) pytest $(TEST_PATH)
	@echo "$(GREEN)✓ Tests complete$(NC)"

test-cov:
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(BACKEND) pytest --cov=app --cov-report=html tests/
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

# Status
status:
	@echo "$(BLUE)Container Status:$(NC)"
	@$(COMPOSE) ps

health:
	@echo "$(BLUE)Checking service health...$(NC)"
	@if curl -sf http://localhost:8000/health > /dev/null; then \
		echo "$(GREEN)✓ Backend is healthy$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Backend health check failed$(NC)"; \
	fi
	@$(COMPOSE) ps

# Cleanup
clean:
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	docker container prune -f
	docker image prune -f
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all:
	@echo "$(YELLOW)⚠ This will remove all containers, images, and volumes!$(NC)"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Removing all Docker resources...$(NC)"; \
		$(COMPOSE) down -v --rmi all; \
		$(COMPOSE_DEV) down -v --rmi all 2>/dev/null || true; \
		docker container prune -af; \
		docker image prune -af; \
		docker volume prune -af; \
		echo "$(GREEN)✓ All Docker resources removed$(NC)"; \
	else \
		echo "$(YELLOW)→ Cleanup cancelled$(NC)"; \
	fi

# Shortcuts
.PHONY: logs
logs: logs
