# Docker Setup Summary

This document summarizes all the Docker files created for the ProctoAI backend.

## Files Created

### 1. **Dockerfiles**

#### `fastapi-backend/Dockerfile` (Production - Optimized)
- Light-weight base image: `python:3.13-slim`
- Includes all production dependencies
- Creates `/app/reports` directory for PDF storage
- Exposes port 8000
- Includes health check
- Ready for production deployment

#### `fastapi-backend/Dockerfile.dev` (Development)
- Same base as production
- Includes test dependencies
- Enables auto-reload with `--reload` flag
- Better for development workflow

#### `fastapi-backend/Dockerfile.prod` (Multi-stage Production)
- Advanced multi-stage build for optimized image size
- Builder stage: compiles dependencies
- Final stage: minimal runtime image
- Non-root user for security
- Entrypoint script for initialization

### 2. **Docker Compose Files**

#### `docker-compose.yml` (Production)
Services:
- **PostgreSQL 16 Alpine**: Database (port 5432)
- **FastAPI Backend**: Main app (port 8000)
- **MinIO**: Object storage (ports 9000, 9001)

Features:
- Health checks for all services
- Persistent volumes for data
- Custom network (proctoai_network)
- Background mode by default

#### `docker-compose.dev.yml` (Development)
Same services as production but:
- Runs in foreground for easy debugging
- Volume mounts for live code editing
- MinIO included for local testing

### 3. **Configuration Files**

#### `.env.example`
Template for environment variables:
- Database credentials
- JWT secrets
- MinIO configuration
- CORS settings
- PDF storage path

#### `.dockerignore`
Excludes unnecessary files from Docker context:
- Git files
- Python cache
- IDE settings
- Test files
- Database files

### 4. **Scripts**

#### `fastapi-backend/docker-entrypoint.sh`
Initialization script that:
- Waits for PostgreSQL to be ready
- Runs database migrations automatically
- Ensures MinIO bucket exists
- Starts Uvicorn server

#### `docker-helper.sh`
Bash helper script with commands:
- `build [dev|prod]`: Build images
- `up [dev|prod]`: Start containers
- `down [dev|prod]`: Stop containers
- `migrate`: Run migrations
- `test`: Run tests
- `clean`: Clean up resources
- And more...

### 5. **Documentation**

#### `DOCKER.md` (Comprehensive Guide)
- Prerequisites
- Quick start instructions
- Accessing services
- Database management
- Development workflows
- Troubleshooting
- Production deployment
- Security notes

#### `QUICKSTART.md` (Getting Started)
- TL;DR 5-minute setup
- Using helper scripts
- Common tasks
- Quick troubleshooting
- Architecture diagram

#### `Makefile`
Easy command shortcuts:
- `make help`: Show all commands
- `make up-prod`: Start production
- `make up-dev`: Start development
- `make migrate`: Run migrations
- `make test`: Run tests
- And more...

### 6. **CI/CD**

#### `.github/workflows/docker.yml`
GitHub Actions workflow:
- Builds Docker image on push
- Runs tests in Docker
- Lints code with flake8, black, isort
- Caches layers for faster builds

## Quick Start

### 1. Setup
```bash
cd /home/jainam/Documents/projects/ProctoAI
cp .env.example .env
```

### 2. Choose Your Method

**Using docker-compose directly:**
```bash
# Production
docker-compose up -d

# Development with auto-reload
docker-compose -f docker-compose.dev.yml up
```

**Using helper script:**
```bash
chmod +x docker-helper.sh
./docker-helper.sh up dev
```

**Using Makefile:**
```bash
make up-prod    # or make up-dev
```

### 3. Run Migrations
```bash
# Any method works:
docker-compose exec backend python -m alembic upgrade head
./docker-helper.sh migrate
make migrate
```

### 4. Access Services
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- MinIO: http://localhost:9001

## Project Structure
```
ProctoAI/
├── fastapi-backend/
│   ├── Dockerfile              # Production
│   ├── Dockerfile.dev          # Development
│   ├── Dockerfile.prod         # Multi-stage production
│   ├── docker-entrypoint.sh    # Initialization script
│   ├── requirements.txt
│   ├── requirements-test.txt
│   ├── app/
│   │   ├── main.py
│   │   └── ...
│   └── ...
├── docker-compose.yml          # Production compose
├── docker-compose.dev.yml      # Development compose
├── .dockerignore
├── .env.example
├── docker-helper.sh            # Helper script
├── Makefile                    # Make commands
├── DOCKER.md                   # Full documentation
├── QUICKSTART.md               # Quick reference
└── .github/
    └── workflows/
        └── docker.yml          # CI/CD
```

## Environment Variables

Key variables to configure in `.env`:

```bash
# Production Security
SECRET_KEY=generate-strong-random-key
POSTGRES_PASSWORD=strong-password
MINIO_SECRET_KEY=strong-password

# Development
DEBUG=true/false
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Ports (if you need to change)
BACKEND_PORT=8000
POSTGRES_PORT=5432
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
```

## Common Commands

### Development Workflow
```bash
# Start with auto-reload
make up-dev

# View logs (in another terminal)
make logs

# Run migrations
make migrate

# Run tests
make test

# Access Python shell
make shell

# Stop when done
make down-dev
```

### Production Setup
```bash
# Build images
make build-prod

# Start services
make up-prod

# Monitor
make health
make status

# Cleanup
make clean-all
```

## Volumes

Three persistent volumes are created:

1. **postgres_data** - PostgreSQL database files
2. **minio_data** - MinIO object storage
3. **reports_volume** - Generated PDF reports

Data persists across container restarts unless you run `docker-compose down -v`

## Networks

All services communicate through a Docker bridge network:
- Production: `proctoai_network`
- Development: `proctoai_network_dev`

Services use container names for DNS resolution:
- `postgres` - PostgreSQL container
- `backend` - FastAPI container
- `minio` - MinIO container

## Performance Considerations

1. **Multi-stage builds**: Reduces final image size
2. **Alpine base**: Lightweight Linux distribution
3. **Layer caching**: Speeds up rebuilds
4. **Health checks**: Ensures service availability
5. **Non-root user**: Improved security (prod only)

## Security Best Practices

1. Change `SECRET_KEY` to a strong random string
2. Use strong database passwords
3. Update MinIO credentials
4. Restrict `CORS_ORIGINS` to your domain
5. Set `DEBUG=false` in production
6. Don't commit `.env` with real credentials
7. Use HTTPS in production (via reverse proxy)
8. Regularly update base images

## Troubleshooting

### Ports in use?
Edit `.env` and change port numbers

### Database won't connect?
```bash
# Check if postgres is healthy
docker-compose ps
make health

# Check logs
make logs postgres
```

### Need to reset everything?
```bash
make clean-all
make up-prod
make migrate
```

### Having issues?
1. Check `DOCKER.md` for detailed troubleshooting
2. View logs: `make logs [service]`
3. Check database: `make db`
4. Reset: `make reset-db`

## Next Steps

1. ✅ Docker setup complete
2. Run tests: `make test`
3. Deploy: Use provided docker-compose files
4. Monitor: Setup logging and monitoring
5. Scale: Use Kubernetes or container orchestration

## Support

For more information:
- Docker docs: https://docs.docker.com/
- FastAPI docs: https://fastapi.tiangolo.com/
- PostgreSQL docs: https://www.postgresql.org/docs/
- MinIO docs: https://min.io/docs/

See `DOCKER.md` and `QUICKSTART.md` for detailed guides.
