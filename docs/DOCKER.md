# 🐳 Docker Support for Orkit Crew

Complete Docker support for running Orkit Crew in development and production environments.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Development Mode](#development-mode)
- [Production Mode](#production-mode)
- [Environment Variables](#environment-variables)
- [Volume Mounts](#volume-mounts)
- [Troubleshooting](#troubleshooting)

---

## Overview

Orkit Crew provides a multi-stage Docker build optimized for both development and production use. The Docker setup includes:

- **Multi-stage build** for smaller production images
- **Non-root user** for security
- **Health checks** built-in
- **Volume mounts** for persistent data
- **Development hot-reload** support

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 20.10+ 
- [Docker Compose](https://docs.docker.com/compose/install/) 2.0+

Verify installation:

```bash
docker --version
docker compose version
```

---

## Quick Start

### Run from Docker Hub

```bash
# Show help
docker run huaquanghan/orkit-crew orkit --help

# Run planning command
docker run -e PLANNO_URL=http://host.docker.internal:8787 \
  -e PLANNO_API_KEY=your-key \
  huaquanghan/orkit-crew orkit plan "Create a Python API"

# Interactive mode
docker run -it --rm \
  -e PLANNO_URL=http://host.docker.internal:8787 \
  -e PLANNO_API_KEY=your-key \
  huaquanghan/orkit-crew orkit chat
```

### Build and Run Locally

```bash
# Clone repository
git clone https://github.com/huaquanghan/orkit-crew.git
cd orkit-crew

# Build image
docker build -t orkit-crew .

# Run container
docker run -it --rm orkit-crew orkit --help
```

---

## Development Mode

### Using Docker Compose

```bash
# Start all services (app + infrastructure)
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down
```

### Development with Hot Reload

Create `docker-compose.dev.yml`:

```yaml
version: "3.8"

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    container_name: orkit-app-dev
    volumes:
      - ./src:/app/src:ro  # Mount source code for development
      - ./sessions:/app/sessions
      - ./workspace:/app/workspace
      - ./.env:/app/.env:ro
    environment:
      - APP_ENV=development
      - LOG_LEVEL=DEBUG
    stdin_open: true
    tty: true
    command: ["orkit", "chat"]
```

Run:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Local Development with External Services

If you have Redis and Qdrant running locally:

```bash
# Start only infrastructure services
docker-compose up -d redis qdrant

# Run app locally (outside Docker)
source .venv/bin/activate
orkit --help
```

---

## Production Mode

### Production Docker Compose

```yaml
version: "3.8"

services:
  app:
    image: huaquanghan/orkit-crew:latest
    container_name: orkit-app
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - PLANNO_URL=${PLANNO_URL}
      - PLANNO_API_KEY=${PLANNO_API_KEY}
      - DEFAULT_MODEL=${DEFAULT_MODEL:-gpt-5.4}
      - APP_ENV=production
      - LOG_LEVEL=INFO
    volumes:
      - orkit-sessions:/app/sessions
      - orkit-workspace:/app/workspace
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

volumes:
  orkit-sessions:
  orkit-workspace:
```

### Production Deployment Steps

```bash
# 1. Pull latest image
docker pull huaquanghan/orkit-crew:latest

# 2. Create production compose file
cp docker-compose.yml docker-compose.prod.yml

# 3. Set environment variables
export PLANNO_URL=https://your-planno-instance.com
export PLANNO_API_KEY=your-production-key

# 4. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f
```

### Security Best Practices

1. **Use non-root user**: The image runs as `orkit` user (UID 1000)
2. **Read-only mounts**: Mount `.env` as read-only
3. **Secrets management**: Use Docker secrets or external vaults
4. **Network isolation**: Run in isolated Docker networks

```bash
# Create isolated network
docker network create orkit-network

# Run with custom network
docker run --network orkit-network huaquanghan/orkit-crew orkit --help
```

---

## Environment Variables

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLANNO_URL` | Planno Gateway URL | `http://host.docker.internal:8787` |
| `PLANNO_API_KEY` | API key for Planno | - |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_MODEL` | Default LLM model | `gpt-5.4` |
| `APP_ENV` | Environment mode | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `REDIS_URL` | Redis connection URL | - |
| `QDRANT_URL` | Qdrant connection URL | - |

### Passing Environment Variables

```bash
# Via command line
docker run -e PLANNO_API_KEY=secret -e LOG_LEVEL=DEBUG orkit-crew

# Via env file
docker run --env-file .env orkit-crew

# Via Docker Compose (automatically loads .env)
docker-compose up -d
```

---

## Volume Mounts

### Available Volumes

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./sessions` | `/app/sessions` | Session data persistence |
| `./workspace` | `/app/workspace` | Working files and outputs |
| `./.env` | `/app/.env` | Environment configuration |

### Volume Examples

```bash
# Persist sessions and workspace
docker run -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/workspace:/app/workspace \
  huaquanghan/orkit-crew orkit plan "Create API"

# Use named volumes
docker run -v orkit-data:/app/sessions \
  -v orkit-work:/app/workspace \
  huaquanghan/orkit-crew orkit --help
```

### Docker Compose Volumes

```yaml
services:
  app:
    volumes:
      # Bind mounts for development
      - ./sessions:/app/sessions
      - ./workspace:/app/workspace
      - ./.env:/app/.env:ro
      
      # Named volumes for production
      - orkit-sessions:/app/sessions
      - orkit-workspace:/app/workspace

volumes:
  orkit-sessions:
  orkit-workspace:
```

---

## Troubleshooting

### Common Issues

#### Container won't start

```bash
# Check logs
docker-compose logs app

# Check environment variables
docker-compose config

# Verify image exists
docker images | grep orkit
```

#### Connection to Planno Gateway refused

```bash
# For local Planno on host machine, use:
PLANNO_URL=http://host.docker.internal:8787

# For Linux, you may need:
PLANNO_URL=http://172.17.0.1:8787

# Test connectivity
docker run --rm orkit-crew curl http://host.docker.internal:8787/health
```

#### Permission denied errors

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./sessions ./workspace

# Or run with current user
docker run --user $(id -u):$(id -g) orkit-crew
```

#### Image build fails

```bash
# Clean build cache
docker build --no-cache -t orkit-crew .

# Check build logs
docker build -t orkit-crew . 2>&1 | tee build.log
```

### Health Check

```bash
# Check container health
docker ps

# View health check logs
docker inspect --format='{{.State.Health}}' orkit-app

# Manual health check
docker exec orkit-app curl http://localhost:8000/health
```

### Debugging

```bash
# Shell into container
docker exec -it orkit-app /bin/bash

# Check environment
docker exec orkit-app env

# View running processes
docker exec orkit-app ps aux
```

### Getting Help

- [GitHub Issues](https://github.com/huaquanghan/orkit-crew/issues)
- [Integration Guide](INTEGRATION.md) for deployment options
