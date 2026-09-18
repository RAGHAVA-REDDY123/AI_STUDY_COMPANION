# Production Deployment & Infrastructure Guide

This guide details how to deploy the **AI Study Companion** (`AI_STUDY_COMPANION`) to production environments with multi-tenant security, pgvector persistence, Server-Sent Events (SSE) streaming support, and automated CI/CD.

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Environment Variables Matrix](#2-environment-variables-matrix)
3. [Deployment Option A: Render (Zero-DevOps Blueprint)](#3-deployment-option-a-render-zero-devops-blueprint)
4. [Deployment Option B: Self-Hosted Docker Compose (VPS / AWS EC2)](#4-deployment-option-b-self-hosted-docker-compose-vps--aws-ec2)
5. [Deployment Option C: Split Deployment (Vercel + Railway/Neon)](#5-deployment-option-c-split-deployment-vercel--railwayneon)
6. [CI/CD Pipeline with GitHub Actions](#6-cicd-pipeline-with-github-actions)
7. [Production Monitoring, Backups & Maintenance](#7-production-monitoring-backups--maintenance)

---

## 1. Architecture Overview

```
                                 [ Internet / Users ]
                                          │
                                          ▼
                             [ Public Ingress (Port 80/443) ]
                             (Nginx Reverse Proxy / SSL Termination)
                                  │                     │
                    ┌─────────────┘                     └─────────────┐
                    ▼                                                 ▼
          [ Next.js 14 Web App ]                            [ FastAPI Backend API ]
             (Port 3000 Node)                                   (Port 8000 ASGI)
                    │                                                 │
                    │                                                 ├───► [ Redis 7 ] (Cache & Queue)
                    │                                                 │
                    │                                                 ├───► [ Celery Worker ] (Background Tasks)
                    │                                                 │
                    └─────────────────────────────────────────────────┴───► [ PostgreSQL 16 + pgvector ]
```

---

## 2. Environment Variables Matrix

Create a `.env` file based on `.env.example`:

| Variable | Scope | Required | Description | Example / Default |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Backend/Worker | **Yes** | Async PostgreSQL connection string with pgvector | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `REDIS_URL` | Backend/Worker | **Yes** | Redis connection URI | `redis://localhost:6379/0` |
| `SECRET_KEY` | Backend/Worker | **Yes** | Cryptographic key for signing JWT tokens | `openssl rand -hex 32` |
| `GEMINI_API_KEY` | Backend/Worker | **Yes** | Google Gemini API key | `AIzaSy...` |
| `GEMINI_MODEL` | Backend/Worker | No | Google Gemini foundation model | `gemini-2.5-flash` |
| `EMBEDDING_MODEL`| Backend/Worker | No | HuggingFace embedding model | `BAAI/bge-small-en-v1.5` |
| `EMBEDDING_DIMENSION` | Backend | No | Vector dimension for pgvector HNSW index | `384` |
| `ENVIRONMENT` | Backend | No | Environment identifier | `production` |
| `NEXT_PUBLIC_API_URL` | Frontend | **Yes** | Client-facing public API URL | `https://api.yourdomain.com/api/v1` |

---

## 3. Deployment Option A: Render (Zero-DevOps Blueprint)

The repository includes a root [`render.yaml`](../render.yaml) Infrastructure-as-Code blueprint.

### Steps to Deploy:
1. Push your repository to GitHub: `https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION`.
2. Navigate to [dashboard.render.com](https://dashboard.render.com) and click **New +** ➔ **Blueprint**.
3. Connect your `AI_STUDY_COMPANION` repository.
4. Render will automatically discover `render.yaml` and provision:
   - **PostgreSQL Database** (`ai-study-companion-db`) with vector extension.
   - **Redis Instance** (`ai-study-companion-redis`) for Celery and caching.
   - **FastAPI Web Service** (`ai-study-companion-backend`) on Python 3.11.
   - **Next.js Web Service** (`ai-study-companion-frontend`) on Node 20.
5. In the Render Dashboard, fill in your `GEMINI_API_KEY`.
6. Click **Apply Blueprint**. The build and deployment will initialize automatically.

---

## 4. Deployment Option B: Self-Hosted Docker Compose (VPS / AWS EC2)

For production deployments on Ubuntu 22.04 / 24.04 (AWS EC2, DigitalOcean, Hetzner, Linode):

### 1. Provision Server & Install Docker:
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose plugin
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone Repository & Setup Environment:
```bash
git clone https://github.com/RAGHAVA-REDDY123/AI_STUDY_COMPANION.git
cd AI_STUDY_COMPANION

# Create production environment file
cp .env.example .env
nano .env  # Enter your real GEMINI_API_KEY, secure passwords, and domain
```

### 3. Build & Launch Containers:
```bash
# Launch full-stack production containers in detached mode
docker compose -f docker-compose.prod.yml up -d --build

# Verify all containers are healthy
docker compose -f docker-compose.prod.yml ps
```

### 4. Setup SSL with Let's Encrypt (Certbot):
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## 5. Deployment Option C: Split Deployment (Vercel + Railway/Neon)

If you prefer hosting the frontend on Vercel and backend/database on Railway or Neon:

### Frontend on Vercel:
1. Import repository on [vercel.com](https://vercel.com).
2. Set Root Directory to `frontend`.
3. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://your-backend.railway.app/api/v1`
4. Deploy!

### Backend on Railway / Neon:
1. Create a PostgreSQL database on Neon or Railway (enable `CREATE EXTENSION IF NOT EXISTS vector;`).
2. Deploy backend using `backend/Dockerfile`.
3. Set environment variables (`DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `SECRET_KEY`).

---

## 6. CI/CD Pipeline with GitHub Actions

The repository includes pre-configured GitHub Actions workflows:

### `.github/workflows/ci.yml` (Continuous Integration)
- Automatically triggers on every **Push** and **Pull Request** to `main`.
- **Backend Job**: Launches isolated PostgreSQL (with pgvector) and Redis service containers, installs dependencies, runs flake8 linting, and executes the `pytest` test suite.
- **Frontend Job**: Verifies strict TypeScript compilation (`npx tsc --noEmit`) and validates the Next.js production build.
- **Docker Validation Job**: Tests that both `backend/Dockerfile` and `frontend/Dockerfile` build cleanly.

### `.github/workflows/cd.yml` (Continuous Delivery)
- Automatically triggers on push to `main`.
- Builds optimized multi-stage Docker images.
- Publishes tagged images to **GitHub Container Registry** (`ghcr.io/raghava-reddy123/ai-study-companion-*`).
- Automatically triggers deployment webhook (if `RENDER_DEPLOY_HOOK_URL` secret is configured).

---

## 7. Production Monitoring, Backups & Maintenance

### Database Backups:
```bash
# Automated daily pg_dump
docker exec -t study_companion_postgres pg_dump -U postgres ai_study_companion > backup_$(date +%Y%m%d).sql
```

### AI Usage & Cost Observability:
Platform usage, token consumption, and costs are tracked in real-time in the `ai_usage_logs` PostgreSQL table. You can inspect these directly from the Admin Dashboard at:
```
http://yourdomain.com/admin
```
Or query directly:
```sql
SELECT feature, model_name, COUNT(*), SUM(total_tokens) AS total_tokens, SUM(estimated_cost_usd) AS cost_usd
FROM ai_usage_logs
GROUP BY feature, model_name;
```
