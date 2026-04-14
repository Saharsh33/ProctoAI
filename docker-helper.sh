#!/bin/bash

# ProctoAI Docker Helper Script
# Usage: ./docker-helper.sh [command] [args...]

set -e

PROJECT_NAME="proctoai"
COMPOSE_FILE="docker-compose.yml"
COMPOSE_DEV_FILE="docker-compose.dev.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_info "Creating .env from .env.example..."
        cp .env.example .env
        print_success ".env created. Please update it with your values."
    fi
}

# Build images
build() {
    print_header "Building Docker Images"
    if [ "$1" == "dev" ]; then
        print_info "Building development images..."
        docker-compose -f $COMPOSE_DEV_FILE build
    else
        print_info "Building production images..."
        docker-compose -f $COMPOSE_FILE build
    fi
    print_success "Build complete!"
}

# Start containers
up() {
    print_header "Starting Containers"
    check_env
    if [ "$1" == "dev" ]; then
        print_info "Starting development environment..."
        docker-compose -f $COMPOSE_DEV_FILE up
    else
        print_info "Starting production environment..."
        docker-compose -f $COMPOSE_FILE up -d
        print_success "Containers started in background"
        print_info "View logs with: ./docker-helper.sh logs"
    fi
}

# Stop containers
down() {
    print_header "Stopping Containers"
    if [ "$1" == "dev" ]; then
        docker-compose -f $COMPOSE_DEV_FILE down
    else
        docker-compose -f $COMPOSE_FILE down
    fi
    print_success "Containers stopped"
}

# View logs
logs() {
    if [ -z "$1" ]; then
        docker-compose -f $COMPOSE_FILE logs -f
    else
        docker-compose -f $COMPOSE_FILE logs -f "$1"
    fi
}

# Run migrations
migrate() {
    print_header "Running Database Migrations"
    print_info "Running: python -m alembic upgrade head"
    docker-compose exec backend python -m alembic upgrade head
    print_success "Migrations complete!"
}

# Create new migration
migration() {
    if [ -z "$1" ]; then
        print_error "Migration name required!"
        echo "Usage: ./docker-helper.sh migration 'Migration name'"
        exit 1
    fi
    print_header "Creating New Migration"
    print_info "Creating migration: $1"
    docker-compose exec backend python -m alembic revision --autogenerate -m "$1"
    print_success "Migration created!"
}

# Run tests
test() {
    print_header "Running Tests"
    if [ -z "$1" ]; then
        docker-compose exec backend pytest
    else
        docker-compose exec backend pytest "$1"
    fi
}

# Run tests with coverage
test_coverage() {
    print_header "Running Tests with Coverage"
    docker-compose exec backend pytest --cov=app --cov-report=html tests/
    print_success "Coverage report generated in htmlcov/index.html"
}

# Access database CLI
db() {
    print_header "PostgreSQL CLI"
    docker-compose exec postgres psql -U postgres -d quizapp
}

# Access backend shell
shell() {
    print_header "Python Shell"
    docker-compose exec backend python
}

# Restart services
restart() {
    print_header "Restarting Services"
    down
    up
    print_success "Services restarted!"
}

# Clean up volumes
clean() {
    print_header "Cleaning Up Docker Resources"
    if [ "$1" == "all" ]; then
        print_error "Removing all containers, volumes, and images!"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --rmi all
            print_success "All resources cleaned!"
        fi
    else
        print_info "Removing stopped containers and dangling images..."
        docker container prune -f
        docker image prune -f
        print_success "Cleanup complete!"
    fi
}

# Status check
status() {
    print_header "Container Status"
    docker-compose ps
}

# Health check
health() {
    print_header "Health Check"
    print_info "Checking backend health..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Backend is healthy"
    else
        print_error "Backend health check failed"
    fi
}

# Print usage
usage() {
    cat << EOF
${BLUE}ProctoAI Docker Helper${NC}

${YELLOW}Usage:${NC}
    ./docker-helper.sh [command] [args...]

${YELLOW}Commands:${NC}
    build [dev|prod]     Build Docker images
    up [dev|prod]        Start containers (dev: foreground, prod: background)
    down [dev|prod]      Stop containers
    logs [service]       View container logs
    migrate              Run Alembic migrations
    migration <name>     Create new migration
    test [path]          Run tests
    test-coverage        Run tests with coverage report
    db                   Access PostgreSQL CLI
    shell                Access Python shell
    restart [dev|prod]   Restart containers
    clean [all]          Clean up Docker resources
    status               Show container status
    health               Check service health
    help                 Show this help message

${YELLOW}Examples:${NC}
    ./docker-helper.sh build dev         # Build dev images
    ./docker-helper.sh up prod           # Start production environment
    ./docker-helper.sh migrate           # Run database migrations
    ./docker-helper.sh migration "Add user table"
    ./docker-helper.sh logs backend      # View backend logs
    ./docker-helper.sh clean all         # Remove everything

${YELLOW}Default Environment:${NC}
    Backend: http://localhost:8000
    Postgres: localhost:5432
    MinIO: http://localhost:9001
    API Docs: http://localhost:8000/docs
EOF
}

# Main script logic
case "$1" in
    build)
        build "$2"
        ;;
    up)
        up "$2"
        ;;
    down)
        down "$2"
        ;;
    logs)
        logs "$2"
        ;;
    migrate)
        migrate
        ;;
    migration)
        migration "$2"
        ;;
    test)
        test "$2"
        ;;
    test-coverage)
        test_coverage
        ;;
    db)
        db
        ;;
    shell)
        shell
        ;;
    restart)
        restart "$2"
        ;;
    clean)
        clean "$2"
        ;;
    status)
        status
        ;;
    health)
        health
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        if [ -z "$1" ]; then
            usage
        else
            print_error "Unknown command: $1"
            echo "Run './docker-helper.sh help' for usage information"
            exit 1
        fi
        ;;
esac
