# CINEIQ 🎬

![CI](https://github.com/RamK2006/cineiq/actions/workflows/ci.yml/badge.svg)
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

## Technology Stack

- **Backend:** FastAPI, SQLAlchemy (async), AI/ML Pipelines
- **Frontend:** Next.js 15, React, Tailwind CSS / Vanilla CSS (Cinematic Design)
- **Database:** PostgreSQL 16
- **Caching & Brokers:** Redis 7
- **Vector Search:** Qdrant
- **Object Storage:** MinIO
- **Containerization:** Docker & Docker Compose
