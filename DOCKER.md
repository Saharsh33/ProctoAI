# Docker Setup for ProctoAI Backend

This guide explains how to build and run the ProctoAI backend using Docker.

## Prerequisites

- Docker (version 20.10+)
- Docker Compose (version 1.29+)

## Quick Start

### 1. Clone the repository and navigate to the project root:

```bash
cd /path/to/ProctoAI
```

### 2. Create an `.env` file from `.env.example`:

```bash
cp .env.example .env
```

### 3. Update `.env` with your configuration (especially SECRET_KEY in production):

```bash
# Change these values in production
SECRET_KEY=your-very-secure-random-string
POSTGRES_PASSWORD=your-secure-db-password
MINIO_SECRET_KEY=your-secure-minio-password
```

### 4. Run the containers

#### Production Setup:
```bash
docker-compose up -d
```

#### Development Setup (with auto-reload):
```bash
docker-compose -f docker-compose.dev.yml up
```

## Accessing Services

After the containers are running:

- **FastAPI Backend API**: http://localhost:8000
- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **API Documentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (username: `minioadmin`, password: `minioadmin`)

## Database Management

### Run Alembic Migrations

Inside the running container:

```bash
# Apply all pending migrations
docker-compose exec backend python -m alembic upgrade head

# Check current migration
docker-compose exec backend python -m alembic current

# Create a new migration
docker-compose exec backend python -m alembic revision --autogenerate -m "Migration name"
```

### Access PostgreSQL CLI

```bash
docker-compose exec postgres psql -U postgres -d quizapp
```

## Development Workflows

### 1. Running Tests

```bash
docker-compose -f docker-compose.dev.yml exec backend pytest
```

### 2. Running Tests with Coverage

```bash
docker-compose -f docker-compose.dev.yml exec backend pytest --cov=app tests/
```

### 3. Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### 4. Interactive Python Shell

```bash
docker-compose exec backend python -i -c "from app.db.session import SessionLocal; db = SessionLocal()"
```

## Docker Images

### Production Image
- **Base Image**: `python:3.13-slim`
- **Size**: ~400-500MB
- **Contains**: Only production dependencies
- **Health Check**: HTTP endpoint at `/health`

### Development Image (Dockerfile.dev)
- **Base Image**: `python:3.13-slim`
- **Contains**: All dependencies + test dependencies
- **Features**: Auto-reload enabled

## Services Included

1. **PostgreSQL 16 Alpine**
   - Volume: `postgres_data`
   - Port: 5432 (configurable)
   - Health Check: pg_isready

2. **FastAPI Backend**
   - Volume: App code mounted for development
   - Reports volume: `/app/reports`
   - Port: 8000 (configurable)
   - Health Check: HTTP GET /health

3. **MinIO (Object Storage)**
   - Volume: `minio_data`
   - Console Port: 9001
   - API Port: 9000

## Volumes

- `postgres_data`: PostgreSQL database files
- `minio_data`: MinIO object storage data
- `reports_volume`: Generated PDF reports

## Environment Variables

See `.env.example` for all available configuration options:

### Critical for Production:
- `SECRET_KEY` - Change to a strong random string
- `POSTGRES_PASSWORD` - Strong database password
- `MINIO_SECRET_KEY` - Strong MinIO password
- `DEBUG` - Set to `false` in production
- `CORS_ORIGINS` - Restrict to your frontend domain

## Stopping and Cleaning Up

### Stop containers without removing volumes:
```bash
docker-compose down
```

### Remove containers AND volumes (careful!):
```bash
docker-compose down -v
```

### Remove containers, volumes, AND images:
```bash
docker-compose down -v --rmi all
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs backend

# Verify database is ready
docker-compose exec backend python -c "from app.db.session import SessionLocal; SessionLocal()"
```

### Database connection refused
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check DATABASE_URL in .env file
- Verify network connectivity: `docker network inspect proctoai_network`

### MinIO connection issues
- Check if MinIO is running: `docker-compose ps`
- Verify MINIO_URL matches container name: `http://minio:9000`

### Port already in use
Change ports in `.env`:
```bash
BACKEND_PORT=8001
POSTGRES_PORT=5433
MINIO_PORT=9002
MINIO_CONSOLE_PORT=9002
```

## Performance Tips

1. **Database Optimization**:
   - Create indexes for frequently queried columns
   - Use connection pooling (already configured)

2. **API Optimization**:
   - Enable gzip compression
   - Use caching headers
   - Implement rate limiting

3. **Storage Optimization**:
   - Clean up old reports regularly
   - Implement S3 lifecycle policies for MinIO

## Security Notes

1. **Never commit `.env` with real credentials**
2. **Use strong SECRET_KEY in production** (at least 32 random characters)
3. **Change default MinIO credentials**
4. **Use HTTPS in production** (configure via reverse proxy)
5. **Restrict CORS_ORIGINS to your domain**
6. **Use environment-specific configurations**

## Production Deployment

For production deployment:

1. Use a production-grade reverse proxy (nginx, Traefik)
2. Enable HTTPS/SSL certificates
3. Use external database and storage services
4. Implement monitoring and logging
5. Use secrets management (Kubernetes secrets, HashiCorp Vault)
6. Scale horizontally with multiple backend instances

Example Kubernetes manifests available on request.

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MinIO Documentation](https://min.io/docs/minio/container/index.html)
