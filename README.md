# CINEIQ 🎬

**AI-Powered Movie Recommendation Platform**

[![ECSoC 2026](https://img.shields.io/badge/ECSoC-2026-blue?style=flat-square)](https://github.com/RamK2006/cineiq)
[![License](https://img.shields.io/github/license/RamK2006/cineiq?style=flat-square)](https://github.com/RamK2006/cineiq/blob/main/LICENSE)
[![Good First Issues](https://img.shields.io/github/issues/RamK2006/cineiq/good%20first%20issue?style=flat-square&label=good%20first%20issues)](https://github.com/RamK2006/cineiq/issues?q=is%3Aopen+label%3A%22good+first+issue%22)

## Overview

CINEIQ is a movie recommendation platform featuring AI-driven personalized suggestions, a cinematic user interface, and real-time analytics. Built with a modern full-stack architecture using FastAPI and Next.js 15.

## Current Status

> 🚧 **Active Development** — CINEIQ is under active development as part of [ECSoC 2026](https://github.com/RamK2006/cineiq). Core features are functional, and many exciting capabilities are on the roadmap.

### Implemented ✅
- Next.js 15 frontend with cinematic UI
- FastAPI backend with health endpoints
- TMDB movie data integration
- Movie detail pages with backdrop images
- Navigation with active route highlighting
- Responsive layout for desktop and mobile
- Docker Compose stack for local development

### Planned 🚧
- Semantic search with Qdrant vector database
- Collaborative filtering recommendation engine (SVD)
- Real-time watch party with WebSocket sync
- User authentication and profiles
- Movie rating and review system
- Watchlist, history, and interaction tracking
- Voice search with Web Speech API
- Emotional arc generation using Gemini
- Dark/light theme toggle

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

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Core UI, TMDB integration, Docker setup | ✅ Complete |
| 2 | Auth, profiles, theme toggle, share button | 🚧 In Progress |
| 3 | Semantic search, recommendations, ratings | 📋 Planned |
| 4 | Watch party, voice search, emotional arcs | 📋 Planned |

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 20+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Run with Docker (Recommended)

```bash
cp .env.example .env
# Fill in API keys in .env
make dev
# or
docker-compose up --build
```

### Run Locally (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL 16 |
| Caching | Redis 7 |
| Vector Search | Qdrant |
| Object Storage | MinIO |
| Containerization | Docker & Docker Compose |

## Contributing

We welcome contributions, especially during ECSoC 2026!

### How to Contribute

1. **Find an issue** — Look for issues labeled `good first issue` for beginner-friendly tasks
2. **Claim it** — Comment on the issue to let others know you're working on it
3. **Fork & branch** — Fork the repo and create a branch: `fix/issue-number-description` or `feat/issue-number-description`
4. **Make changes** — Write clean, well-documented code
5. **Test** — Ensure `npm run build` and `npm run lint` pass (frontend) or relevant tests pass (backend)
6. **Submit a PR** — Reference the issue number in your PR description (e.g., "Fixes #38")

### Branch Naming

- Bug fixes: `fix/issue-number-short-description`
- Features: `feat/issue-number-short-description`
- Documentation: `docs/issue-number-short-description`

### PR Checklist

- [ ] PR references the issue it fixes
- [ ] Code builds without errors
- [ ] No unnecessary files committed
- [ ] Clear description of changes

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
