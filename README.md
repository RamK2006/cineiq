# CINEIQ 🎬

**Next-Generation AI-Powered Movie Recommendation Platform**


## Overview

CINEIQ is a production-grade movie recommendation platform featuring advanced AI-driven personalized movie suggestions, real-time analytics, and a cinematic user interface.

1. **FastAPI Backend** — Advanced ML inference, personalized recommendations, robust data processing pipelines
2. **Next.js 15 Frontend** — Immersive, cinematic design system with Server-Side Rendering (SSR) for optimal performance

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Next.js 15     │────▶│   FastAPI API    │
│  Frontend       │◀────│   (Backend)      │
└─────────────────┘     └──────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌──────────┐ ┌──────┐ ┌────────┐
              │PostgreSQL│ │Redis │ │Qdrant  │
              │   16     │ │  7   │ │ VecDB  │
              └──────────┘ └──────┘ └────────┘
                               │
                          ┌────────┐
                          │ MinIO  │
                          │Storage │
                          └────────┘
```

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Run with Docker (Recommended)
The entire stack can be launched via Docker Compose:

```bash
cp .env.example .env
# Fill in API keys in .env
make dev
# or alternatively
docker-compose up --build
```

### Run Locally (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
# Set up necessary env variables
uvicorn app.main:app --reload   # Start API server
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Deployment

### Vercel monorepo deployment

CINEIQ uses a single Vercel project configured from the repository root.
The root `vercel.json` is the source of truth for both applications:

- `frontend/package.json` is built with the Next.js runtime.
- `backend/vercel_entry.py` is deployed with the Python runtime.
- Requests to `/api/*` are routed to the FastAPI backend.
- All remaining requests are served by the Next.js frontend.

When importing the repository into Vercel:

1. Keep the project root directory set to the repository root.
2. Do not set `frontend/` as the Vercel Root Directory.
3. Configure the environment variables from `.env.example`.
4. Set `NEXT_PUBLIC_API_URL` only when the frontend should use an external backend. If it is not set, production uses the same-origin `/api/v1` endpoint and local development uses `http://localhost:8001`.

Only the root `vercel.json` should exist. Adding another Vercel configuration inside `frontend/` can cause Vercel to select a different deployment strategy.

## Technology Stack

- **Backend:** FastAPI, SQLAlchemy (async), AI/ML Pipelines
- **Frontend:** Next.js 15, React, Tailwind CSS / Vanilla CSS (Cinematic Design)
- **Database:** PostgreSQL 16
- **Caching & Brokers:** Redis 7
- **Vector Search:** Qdrant
- **Object Storage:** MinIO
- **Containerization:** Docker & Docker Compose
