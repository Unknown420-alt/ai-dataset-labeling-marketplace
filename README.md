# AI Dataset Labeling Marketplace

_A place where dataset owners get their raw data labeled by a distributed crowd of labelers, with an AI assistant in the loop._

## Live Demo

Not yet — the product goes live on a public URL by Day 41 (see Review-II). Coming soon: frontend on Vercel, backend + database on Render/Railway.

## Overview

Dataset owners publish raw data (CSV today) and create labeling tasks against it. Labelers claim those tasks and label each row; the AI assistant suggests a label per item which the human can confirm or correct. Every label is stored per labeler, so the owner ends up with a clean, human-reviewed dataset ready for training.

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
| Hosting (Day 41) | Vercel/Netlify (frontend), Render/Railway (backend) |

## Features

**Auth module**
- Signup / login / refresh with real JWTs, bcrypt-hashed passwords
- Two roles: dataset **owner** and **labeler**

**Datasets module**
- Create and list datasets (owners only see their own)
- Declared `file_type`, items count, and status tracked

**Label tasks module**
- Owners create labeling tasks against a dataset with a `label_schema` JSON
- Task lifecycle: draft → open → in progress → completed
- CSV item upload per task (validated, capped at 5 MB)

**Labeling module**
- Labelers claim open tasks
- List items with any AI suggestion shown
- Submit labels (`source: human`) that update the item's `final_label`

**API convention**
- Every response follows one envelope: `{ "success", "data", "message" }`
- Correct HTTP status codes: 200/201 success, 400/401/404 client errors

## Screenshots

To be added once the frontend is hosted (Day 41).

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

## Environment Variables

| Variable | Description | Required |
| -------- | ----------- | -------- |
| `SECRET_KEY` | JWT signing secret — pick a long random string | Yes |
| `DATABASE_URL` | SQLAlchemy async DB URL (Postgres or SQLite) | Yes |
| `ALGORITHM` | JWT algorithm, keep `HS256` | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes | Yes |
| `ENVIRONMENT` | `development` / `production` | Yes |

## API Documentation

Swagger UI is served at http://127.0.0.1:8000/docs (production URL once hosted on Day 41).

## Running Tests

```bash
python -m pytest
```

Covers auth, datasets/tasks, the full labeler flow (claim → items → submit), and security helpers. A `black --check` lint gate runs in CI.

## Deployment

Deployment begins in Week 6:
- Backend + PostgreSQL → Render or Railway
- Frontend → Vercel or Netlify
- GitHub Actions triggers on every push/PR to `main`: install deps → lint → run tests; deploy step added from Week 6 onward.

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
│   └── src/components/    # auth, owner, and labeler screens
├── tests/                 # pytest suite
├── data/                  # sample CSV for quick demos
├── .env.example
├── Problem_Statement.md
├── requirements.txt
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

Team member — full name and contact to be added to the report. Project guide: [guide name].