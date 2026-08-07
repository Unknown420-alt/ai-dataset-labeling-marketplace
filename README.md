# AI Dataset Labeling Marketplace

A marketplace where dataset owners publish raw data and labelers get paid to
label it. An AI assistant suggests labels and gets corrected by humans, so the
final dataset is high quality and useful for training.

This is the backend for the R2021 Sem 5 capstone project. Built with FastAPI,
SQLAlchemy (async), and SQLite for local dev (PostgreSQL in production).

## What's here right now

- **Auth** - signup / login / refresh, issues real JWTs, bcrypt-hashed passwords
- **Datasets** - create, list, get (only your own)
- **Label tasks** - create and list labeling work against a dataset
- **Migrations** - Alembic manages the schema (5 tables)
- **Tests** - health check + a full signup -> login -> dataset -> task flow

## Tech stack

| Layer   | Choice                                    |
|---------|-------------------------------------------|
| API     | FastAPI + Uvicorn                         |
| DB      | SQLAlchemy 2.0 async, SQLite (dev) / PostgreSQL (prod) |
| Migrate | Alembic                                   |
| Auth    | JWT (python-jose) + bcrypt                |
| Tests   | pytest + pytest-asyncio + httpx TestClient|
| CI      | GitHub Actions (lint + pytest)            |

## Project structure

```
.
├── alembic/              # migration scripts + env.py
├── app/
│   ├── api/v1/           # routers: health, auth, users, datasets, tasks
│   ├── core/             # config, database engine
│   ├── models/           # SQLAlchemy models (5 tables)
│   ├── schemas/          # pydantic request/response models
│   └── services/         # security (JWT, bcrypt), business logic
├── tests/                # pytest suite
├── docs/diagrams/        # architecture, ER, module diagrams
├── .env.example          # copy to .env and fill in
└── requirements.txt
```

## Run it locally

1. **Python** - needs 3.12+.

2. **Install deps**

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment** - copy the example and set your secret:

   ```bash
   cp .env.example .env
   # edit .env -> pick a real SECRET_KEY, keep DATABASE_URL=sqlite+aiosqlite:///./marketplace.db for dev
   ```

4. **Create the database**

   ```bash
   python -m alembic -c alembic.ini upgrade head
   ```

   This builds the blank `marketplace.db` with all 5 tables.

5. **Run the server**

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open http://127.0.0.1:8000/docs - you can try the endpoints from the Swagger UI.

### Quick smoke test (2 core flows)

```bash
# signup -> get a token from the response
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","full_name":"You","password":"secret123","role":"owner"}'

# create a dataset with that token
curl -X POST http://127.0.0.1:8000/api/v1/datasets/ \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"cats","description":"cat photos","file_type":"csv"}'

# then list your datasets / create a label task against it
```

## Tests

```bash
python -m pytest
```

The integration test boots the app in-process, signs up a real user, logs in,
creates a dataset, creates a label task, and checks auth failures (401 / 404).

## CI

`.github/workflows/ci.yml` installs deps and runs pytest on every push and PR to
`main`.

## Docs & diagrams

See `docs/diagrams/` for the architecture, ER, and module diagrams. The problem
statement lives in `Problem_Statement.md`.

## TODO (next sprints)

- Frontend (React) - actually using the API, not just docs
- File upload for datasets (local disk, then S3-style)
- Label submission flow for labelers + payment/billing
- AI suggestion pass over unlabeled items
- Containerize with Docker, deploy PostgreSQL