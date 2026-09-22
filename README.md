# AI Dataset Labeling Marketplace

_A place where dataset owners get their raw data labeled by a distributed crowd of labelers, with an AI assistant in the loop._

[![CI](https://github.com/AI-DS-Labeling-Labeler/Labeling-Labeler/actions/workflows/ci.yml/badge.svg)](https://github.com/AI-DS-Labeling-Labeler/Labeling-Labeler/actions)
[![Railway Health](https://img.shields.io/badge/Railway-health--check-brightgreen?logo=railway)](https://web-production-487e1.up.railway.app/health)
[![Coverage](https://img.shields.io/badge/coverage-27%2F27%20tests-blue)](#running-tests)

## Live Demo

| Component | URL |
| --------- | --- |
| Frontend  | https://ai-dataset-labeling-marketplace.vercel.app/ |
| Backend   | https://web-production-487e1.up.railway.app/ |
| API docs  | https://web-production-487e1.up.railway.app/docs |

> **Health check:** `GET /health` should return `{"success":true,"data":{"status":"ok"},"message":"healthy"}`.

## Overview

Dataset owners publish raw data (CSV today) and create labeling tasks against it. Labelers claim those tasks and label each row; the AI assistant suggests a label per item which the human can confirm or correct. Every label is stored per labeler, so the owner ends up with a clean, human-reviewed dataset ready for training.

## Demo Credentials

Seeded automatically on first deploy via `scripts/seed_cloud.py`:

| Role    | Email              | Password      |
| ------- | ------------------ | ------------- |
| Owner   | owner@demo.com     | ReviewPass123 |
| Labeler | labeler@demo.com   | ReviewPass123 |

> These are idempotent. The seed script skips them if they already exist.

## Architecture Diagram

See [`docs/diagrams/architecture.md`](docs/diagrams/architecture.md) — the client layer (React SPA), API layer (FastAPI), and database (PostgreSQL) are drawn there, along with the hosting boundary.

## Tech Stack

Matches Section 4 of the project specification (Python track).

| Layer            | Choice                                            |
| ---------------- | ------------------------------------------------- |
| Frontend         | React.js (JavaScript) + Tailwind CSS + Axios    |
| Backend          | FastAPI (Python 3.12) on Uvicorn                  |
| Auth             | JWT (python-jose / FastAPI users) + bcrypt        |
| ORM / Data       | SQLAlchemy 2.0 (async)                            |
| Database         | PostgreSQL 15 (SQLite for local dev only)         |
| Migrations       | Alembic                                           |
| Build tool       | pip + requirements.txt (backend), npm (frontend)  |
| Testing          | Pytest (unit tests mandatory)                     |
| API docs         | Auto-generated Swagger UI at `/docs`              |
| CI/CD            | GitHub Actions (lint + tests)                     |
| Hosting (Day 41) | Vercel (frontend), Railway (backend)    |

## Features

**Auth module**
- Signup / login / refresh with real JWTs, bcrypt-hashed passwords
- Two roles: dataset **owner** and **labeler**

**Datasets module**
- Create, list, rename (PATCH), and delete datasets (owners only see their own)
- Declared `file_type`, items count, and status tracked
- Delete guarded by 409 if label tasks still reference the dataset

**Label tasks module**
- Owners create labeling tasks against a dataset with a `label_schema` JSON
- Task lifecycle: draft → open → in progress → completed
- CSV item upload per task (validated, capped at 5 MB)

**Labeling module**
- Labelers claim open tasks
- List items with any AI suggestion shown
- Submit labels (`source: human`) that update the item's `final_label`

**Training demo (TF-IDF + Naive Bayes)**
- Train a text classifier on labeled dataset items (`POST /datasets/{id}/train`)
- Predict labels for new text (`POST /datasets/{id}/predict`)
- In-memory model cache with 5-minute TTL, minimum 10 labeled rows required

**API convention**
- Every response follows one envelope: `{ "success", "data", "message" }`
- Correct HTTP status codes: 200/201 success, 400/401/404 client errors

## Screenshots

_Live at_ https://ai-dataset-labeling-marketplace.vercel.app/ _— login with demo credentials below._

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15 (or Docker, or just use the SQLite fallback for a quick start)

### 1. Clone & install backend

```bash
git clone <your-repo-url>
cd <repo>
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

Then pick your database in `.env` (see the table below).

### 3. Create the database

**Option A — PostgreSQL (recommended, matches the project DB):**

```bash
docker compose up -d           # starts PostgreSQL on 5432
python -m alembic upgrade head
```

**Option B — SQLite (zero setup, for quick local runs):**

Set `DATABASE_URL=sqlite+aiosqlite:///./marketplace.db` in `.env`, then:

```bash
python -m alembic upgrade head
```

### 4. Run the backend

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs for the Swagger UI.

### 5. Run the frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173 — the Vite dev server proxies `/api` to the backend.

### 6. Seed demo users (optional, local)

```bash
python scripts/seed_cloud.py
```

Creates `owner@demo.com` / `labeler@demo.com` with password `ReviewPass123`.

## Environment Variables

### Backend (`.env` or Render env vars)

| Variable | Description | Required |
| -------- | ----------- | -------- |
| `SECRET_KEY` | JWT signing secret — pick a long random string | Yes |
| `DATABASE_URL` | SQLAlchemy async DB URL (Postgres or SQLite) | Yes |
| `DIRECT_URL` | Direct connection URL (for Alembic migrations) | Render only |
| `ALGORITHM` | JWT algorithm, keep `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | Yes |
| `ENVIRONMENT` | `development` / `production` | Yes |
| `FRONTEND_URL` | Full Vercel URL for CORS (e.g. `https://your-app.vercel.app`) | Production |

### Frontend (Vercel env vars)

| Variable | Description | Required |
| -------- | ----------- | -------- |
| `VITE_API_URL` | Backend API base URL — **must include `/api/v1` suffix** | Yes (prod) |

**VITE_API_URL contract:**

The frontend reads `import.meta.env.VITE_API_URL || '/api/v1'` (see `frontend/src/api.js`).

- **Production:** set to `https://web-production-487e1.up.railway.app/api/v1` (trailing `/api/v1` is mandatory)
- **Local dev:** leave unset; the Vite dev server proxies `/api` to the backend automatically
- **Why `/api/v1`:** all backend routes are mounted under the `/api/v1` prefix (`app/api/v1/`). Without this suffix the frontend would 404 on every request.

Example Vercel configuration:
```
VITE_API_URL=https://web-production-487e1.up.railway.app/api/v1
```

## API Documentation

Swagger UI is served at:
- **Local:** http://127.0.0.1:8000/docs
- **Production:** `https://web-production-487e1.up.railway.app/docs`

## Running Tests

```bash
python -m pytest
```

Current coverage: **27 tests** across auth, datasets/tasks (CRUD + PATCH + DELETE), the full labeler flow (claim → items → submit), training (train + predict), and security helpers. A `black --check` lint gate runs in CI.

## Deployment

| Component | Platform | URL |
| --------- | -------- | --- |
| Frontend  | Vercel   | https://ai-dataset-labeling-marketplace.vercel.app/ |
| Backend   | Railway  | https://web-production-487e1.up.railway.app/ |
| Database  | Supabase (PostgreSQL) | Configured via `DATABASE_URL` / `DIRECT_URL` |

**CI pipeline** (`.github/workflows/ci.yml`): lint (black) → test (pytest) on every push/PR to `main`.

**Railway pre-deploy:** `alembic upgrade head` → `seed_cloud.py` (idempotent).

## Folder Structure

```
.
├── .github/workflows/     # CI pipeline (black + pytest)
├── alembic/               # migrations + env.py
├── app/
│   ├── api/v1/            # routers: health, auth, datasets, tasks, labeling
│   ├── core/              # config, async database engine
│   ├── models/            # SQLAlchemy models (7 tables)
│   ├── schemas/           # Pydantic request/response models
│   └── services/          # security, responses, upload helpers
├── docs/diagrams/         # architecture, ER, module diagrams
├── frontend/              # React + Tailwind + Axios SPA
│   └── src/               # components (auth, owner, labeler), api.js, App.jsx
├── scripts/               # seed_cloud.py (demo data)
├── tests/                 # pytest suite (13 tests)
├── data/                  # sample CSV for quick demos
├── .env.example
├── Problem_Statement.md
├── requirements.txt
├── render.yaml            # Render service definition
├── Procfile               # Railway/Heroku fallback
└── docker-compose.yml     # PostgreSQL 15 for local dev
```

## Future Enhancements

- Automatic AI labeling pass over unlabeled items using the current `ai_suggestion` columns
- Payment / billing for labelers and dataset owners
- In-app review/QA of conflicting labeler submissions
- JSON dataset upload and S3-style storage

## License

This project is for academic use under the R2021 Sem 5 capstone program.

## Author / Contact

S Girivasan — stugirivasan10143@gmail.com
Project Guide: [Name]
