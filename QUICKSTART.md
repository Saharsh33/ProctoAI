# Quick Start Guide - Docker Setup

## TL;DR - Get Running in 5 Minutes

### Step 1: Initial Setup
```bash
cd /home/jainam/Documents/projects/ProctoAI
cp .env.example .env
```

### Step 2: Start Everything
```bash
# Production (background)
docker-compose up -d

# OR Development (foreground with auto-reload)
docker-compose -f docker-compose.dev.yml up
```

### Step 3: Run Migrations
```bash
docker-compose exec backend python -m alembic upgrade head
```

### Step 4: Access Services
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **MinIO**: http://localhost:9001 (minioadmin/minioadmin)

## Using the Helper Script

For easier management, use the included helper script:

```bash
# Make it executable (one time)
chmod +x ./docker-helper.sh

# View all available commands
./docker-helper.sh help

# Common commands
./docker-helper.sh build dev          # Build dev images
./docker-helper.sh up dev             # Start with auto-reload
./docker-helper.sh logs backend       # View backend logs
./docker-helper.sh migrate            # Run migrations
./docker-helper.sh test               # Run tests
./docker-helper.sh clean              # Clean up
```

## Common Tasks

### View Logs
```bash
# All services
docker-compose logs -f

# Just backend
docker-compose logs -f backend
```

### Run Migrations
```bash
docker-compose exec backend python -m alembic upgrade head
```

### Create New Migration
```bash
docker-compose exec backend python -m alembic revision --autogenerate -m "Add new table"
```

### Run Tests
```bash
docker-compose exec backend pytest
```

### Access Database
```bash
docker-compose exec postgres psql -U postgres -d quizapp
```

### Stop Everything
```bash
docker-compose down
```

### Stop and Remove Volumes (WARNING: Deletes data!)
```bash
docker-compose down -v
```

## Troubleshooting

### Backend won't start?
```bash
# Check logs
docker-compose logs backend

# Make sure database is ready
docker-compose logs postgres
```

### Port already in use?
Edit `.env` and change the port:
```
BACKEND_PORT=8001
POSTGRES_PORT=5433
```

### Need to reset database?
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec backend python -m alembic upgrade head
```

## Environment Variables

Key variables to customize in `.env`:

```bash
# Security (IMPORTANT!)
SECRET_KEY=change-this-to-random-string

# Database
POSTGRES_PASSWORD=secure-password
POSTGRES_DB=quizapp

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Frontend
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Debug
DEBUG=false  # Set to true for development
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────┐  ┌──────────────────┐ │
│  │  FastAPI    │  │   PostgreSQL 16  │ │
│  │  :8000      │  │   :5432          │ │
│  └─────────────┘  └──────────────────┘ │
│         │                               │
│  ┌──────────────┐                       │
│  │    MinIO     │                       │
│  │  :9000/9001  │                       │
│  └──────────────┘                       │
│                                         │
│  Volume: postgres_data                  │
│  Volume: reports_volume                 │
│  Volume: minio_data                     │
│                                         │
└─────────────────────────────────────────┘
```

## Next Steps

1. **Read full documentation**: See `DOCKER.md`
2. **Configure for production**: Update `.env` with real values
3. **Setup monitoring**: Add prometheus/grafana
4. **Setup CI/CD**: Use docker-compose in pipelines
5. **Deploy**: Use Kubernetes or container orchestration

## Need Help?

- View detailed docs: `cat DOCKER.md`
- Check helper script: `./docker-helper.sh help`
- View docker-compose file: `cat docker-compose.yml`
- Check logs: `docker-compose logs [service]`
