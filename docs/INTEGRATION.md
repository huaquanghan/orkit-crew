# 🔌 Integration Guide

Complete guide for integrating Orkit Crew with CI/CD pipelines and deploying to various cloud platforms.

## Table of Contents

- [CI/CD Integration](#cicd-integration)
  - [GitHub Actions](#github-actions)
- [Deployment Platforms](#deployment-platforms)
  - [Railway](#railway)
  - [Render](#render)
  - [Fly.io](#flyio)
  - [AWS ECS](#aws-ecs)
  - [Digital Ocean App Platform](#digital-ocean-app-platform)
- [Docker Registry](#docker-registry)
  - [Docker Hub](#docker-hub)
  - [GitHub Container Registry (GHCR)](#github-container-registry-ghcr)

---

## CI/CD Integration

### GitHub Actions

The repository includes a GitHub Actions workflow for automated Docker builds and pushes.

#### Workflow Features

- Build Docker image on push to `main` branch
- Push to GitHub Container Registry (GHCR)
- Tag with semantic version and `latest`
- Multi-platform builds (amd64, arm64)

#### Workflow File

`.github/workflows/docker.yml`:

```yaml
name: Docker Build and Push

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
    - name: Checkout repository
      uses: actions/checkout@v4

    - name: Set up QEMU
      uses: docker/setup-qemu-action@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=semver,pattern={{version}}
          type=semver,pattern={{major}}.{{minor}}
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        platforms: linux/amd64,linux/arm64
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

#### Setup Instructions

1. **Enable GitHub Container Registry**:
   - Go to Repository Settings → Packages
   - Ensure "Inherit access from source repository" is selected

2. **Add Repository Secrets** (if needed):
   - Go to Settings → Secrets and variables → Actions
   - Add any required environment variables

3. **Trigger Build**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

---

## Deployment Platforms

### Railway

[Railway](https://railway.app) provides easy deployment from GitHub with automatic scaling.

#### Deployment Steps

1. **Create Railway Account**:
   - Sign up at [railway.app](https://railway.app)
   - Connect your GitHub account

2. **Create New Project**:
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login
   railway login
   
   # Create project
   railway init
   ```

3. **Configure Environment Variables**:
   ```bash
   railway variables set PLANNO_URL=https://your-planno-instance.com
   railway variables set PLANNO_API_KEY=your-api-key
   railway variables set APP_ENV=production
   ```

4. **Deploy**:
   ```bash
   railway up
   ```

#### railway.json Configuration

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "orkit --help",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### Render

[Render](https://render.com) offers simple deployment with free tier options.

#### Deployment Steps

1. **Create Render Account**:
   - Sign up at [render.com](https://render.com)

2. **Create Web Service**:
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select "Docker" environment

3. **Configure Service**:
   - **Name**: `orkit-crew`
   - **Runtime**: `Docker`
   - **Plan**: `Free` or paid tier
   - **Docker Command**: `orkit --help` (or your custom command)

4. **Environment Variables**:
   ```
   PLANNO_URL=https://your-planno-instance.com
   PLANNO_API_KEY=your-api-key
   APP_ENV=production
   LOG_LEVEL=INFO
   ```

5. **Deploy**:
   - Click "Create Web Service"
   - Render will automatically build and deploy

#### render.yaml (Infrastructure as Code)

```yaml
services:
  - type: web
    name: orkit-crew
    runtime: docker
    repo: https://github.com/huaquanghan/orkit-crew
    plan: free
    envVars:
      - key: PLANNO_URL
        sync: false
      - key: PLANNO_API_KEY
        sync: false
      - key: APP_ENV
        value: production
      - key: LOG_LEVEL
        value: INFO
```

---

### Fly.io

[Fly.io](https://fly.io) provides edge-deployed containers with excellent performance.

#### Deployment Steps

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Create App**:
   ```bash
   fly apps create orkit-crew
   ```

4. **Create fly.toml**:
   ```toml
   app = 'orkit-crew'
   primary_region = 'sin'

   [build]
     dockerfile = "Dockerfile"

   [env]
     APP_ENV = "production"
     LOG_LEVEL = "INFO"

   [[services]]
     internal_port = 8000
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0

     [[services.ports]]
       port = 8000
       handlers = ["http"]
   ```

5. **Set Secrets**:
   ```bash
   fly secrets set PLANNO_URL=https://your-planno-instance.com
   fly secrets set PLANNO_API_KEY=your-api-key
   ```

6. **Deploy**:
   ```bash
   fly deploy
   ```

#### Fly.io Commands

```bash
# View logs
fly logs

# SSH into machine
fly ssh console

# Scale up
fly scale count 2

# View status
fly status
```

---

### AWS ECS

[AWS ECS](https://aws.amazon.com/ecs/) (Elastic Container Service) provides scalable container orchestration.

#### Deployment Steps

1. **Prerequisites**:
   - AWS CLI configured
   - ECS CLI installed

2. **Create ECR Repository**:
   ```bash
   aws ecr create-repository --repository-name orkit-crew
   ```

3. **Push Image to ECR**:
   ```bash
   # Login to ECR
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   
   # Tag and push
   docker tag orkit-crew:latest <account-id>.dkr.ecr.<region>.amazonaws.com/orkit-crew:latest
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/orkit-crew:latest
   ```

4. **Create ECS Cluster**:
   ```bash
   aws ecs create-cluster --cluster-name orkit-cluster
   ```

5. **Create Task Definition** (`task-definition.json`):
   ```json
   {
     "family": "orkit-crew",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
     "containerDefinitions": [
       {
         "name": "orkit-crew",
         "image": "<account-id>.dkr.ecr.<region>.amazonaws.com/orkit-crew:latest",
         "essential": true,
         "environment": [
           {"name": "APP_ENV", "value": "production"},
           {"name": "LOG_LEVEL", "value": "INFO"}
         ],
         "secrets": [
           {"name": "PLANNO_URL", "valueFrom": "arn:aws:secretsmanager:<region>:<account-id>:secret:planno-url"},
           {"name": "PLANNO_API_KEY", "valueFrom": "arn:aws:secretsmanager:<region>:<account-id>:secret:planno-api-key"}
         ],
         "portMappings": [
           {
             "containerPort": 8000,
             "protocol": "tcp"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/orkit-crew",
             "awslogs-region": "<region>",
             "awslogs-stream-prefix": "ecs"
           }
         }
       }
     ]
   }
   ```

6. **Register Task Definition**:
   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

7. **Create Service**:
   ```bash
   aws ecs create-service \
     --cluster orkit-cluster \
     --service-name orkit-service \
     --task-definition orkit-crew:1 \
     --desired-count 1 \
     --launch-type FARGATE \
     --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxx],securityGroups=[sg-xxxx],assignPublicIp=ENABLED}"
   ```

---

### Digital Ocean App Platform

[Digital Ocean App Platform](https://www.digitalocean.com/products/app-platform) provides simple container deployment.

#### Deployment Steps

1. **Create App Spec** (`.do/app.yaml`):
   ```yaml
   name: orkit-crew
   region: singapore
   services:
   - name: orkit-crew
     image:
       registry_type: DOCR
       repository: orkit-crew
       tag: latest
     http_port: 8000
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: APP_ENV
       value: production
     - key: LOG_LEVEL
       value: INFO
     - key: PLANNO_URL
       value: https://your-planno-instance.com
       type: SECRET
     - key: PLANNO_API_KEY
       value: your-api-key
       type: SECRET
   ```

2. **Create Container Registry**:
   ```bash
   doctl registry create orkit-registry
   ```

3. **Push Image**:
   ```bash
   # Login
   doctl registry login
   
   # Tag and push
   docker tag orkit-crew:latest registry.digitalocean.com/orkit-registry/orkit-crew:latest
   docker push registry.digitalocean.com/orkit-registry/orkit-crew:latest
   ```

4. **Deploy App**:
   ```bash
   doctl apps create --spec .do/app.yaml
   ```

#### Using doctl CLI

```bash
# List apps
doctl apps list

# View logs
doctl apps logs <app-id>

# Update app
doctl apps update <app-id> --spec .do/app.yaml
```

---

## Docker Registry

### Docker Hub

#### Push to Docker Hub

1. **Login**:
   ```bash
   docker login
   ```

2. **Tag Image**:
   ```bash
   docker tag orkit-crew:latest huaquanghan/orkit-crew:latest
   docker tag orkit-crew:latest huaquanghan/orkit-crew:v1.0.0
   ```

3. **Push**:
   ```bash
   docker push huaquanghan/orkit-crew:latest
   docker push huaquanghan/orkit-crew:v1.0.0
   ```

#### Automated Builds

1. Go to [Docker Hub](https://hub.docker.com)
2. Create repository
3. Link GitHub account
4. Configure automated builds for tags

---

### GitHub Container Registry (GHCR)

#### Push to GHCR

1. **Login**:
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```

2. **Tag Image**:
   ```bash
   docker tag orkit-crew:latest ghcr.io/huaquanghan/orkit-crew:latest
   docker tag orkit-crew:latest ghcr.io/huaquanghan/orkit-crew:v1.0.0
   ```

3. **Push**:
   ```bash
   docker push ghcr.io/huaquanghan/orkit-crew:latest
   docker push ghcr.io/huaquanghan/orkit-crew:v1.0.0
   ```

#### Package Visibility

1. Go to Repository → Packages
2. Click on the package
3. Set visibility to "Public" or "Private"
4. Configure access permissions

#### Pull from GHCR

```bash
# Public image
docker pull ghcr.io/huaquanghan/orkit-crew:latest

# Private image (requires authentication)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
docker pull ghcr.io/huaquanghan/orkit-crew:latest
```

---

## Summary

| Platform | Best For | Difficulty | Cost |
|----------|----------|------------|------|
| Railway | Quick deployment, auto-scaling | Easy | Free tier available |
| Render | Simple hosting, free tier | Easy | Free tier available |
| Fly.io | Edge deployment, performance | Medium | Pay per usage |
| AWS ECS | Enterprise, complex workloads | Hard | Pay per usage |
| Digital Ocean | Simple, predictable pricing | Medium | Fixed pricing |

Choose the platform that best fits your needs and infrastructure requirements.
