# Review-II Viva Preparation

> AI Dataset Labeling Marketplace — Capstone cheat-sheet with faculty Q&A and a runnable demo script.

---

## 1. Database Design

### Tables & relationships

| # | Table | Purpose | Key columns |
|---|-------|---------|-------------|
| 1 | `users` | Auth + roles | `id`, `email` (unique), `hashed_password`, `role` (owner/labeler/admin), `is_active` |
| 2 | `datasets` | Uploaded CSVs | `id`, `owner_id` FK→users, `name`, `storage_url`, `file_type`, `total_items`, `status` |
| 3 | `label_tasks` | Labeling jobs | `id`, `dataset_id` FK→datasets, `title`, `instructions`, `label_schema` (JSON), `num_labelers`, `status` |
| 4 | `data_items` | One row per CSV row | `id`, `task_id` FK→label_tasks, `row_index`, `content_json` (JSON), `ai_suggestion`, `final_label` |
| 5 | `label_submissions` | One submission per labeler per item | `id`, `item_id` FK→data_items, `labeler_id` FK→users, `label_value` (JSON), `source` |
| 6 | `task_claims` | Who claimed what task | `id`, `task_id` FK→label_tasks, `labeler_id` FK→users, `assigned_count`, `status` |
| 7 | `ai_suggestions` | Audit log of model predictions | `id`, `item_id` FK→data_items, `model_name`, `confidence_score`, `prediction_json` |

**ER chain:** `users 1→N datasets 1→N label_tasks 1→N data_items 1→N label_submissions`  
`users 1→N task_claims N→1 label_tasks`  
`data_items 1→N ai_suggestions`

**File refs:** `app/models/user.py`, `app/models/dataset.py`, `app/models/task.py`, `app/models/data_item.py`, `app/models/submission.py`, `app/models/task_claim.py`, `app/models/ai_suggestion.py`

---

## 2. Async Engine & Connection Pool

```python
# app/core/database.py
engine = create_async_engine(settings.database_url, **_engine_kwargs(...))
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)
```

- **asyncpg** driver (`postgresql+asyncpg://`) for non-blocking Postgres I/O.
- `pool_size=10, max_overflow=20, pool_pre_ping=True` — keeps connections alive, rejects stale ones.
- SSL via `_unverified_ssl_context()` when the URL contains `ssl=require` (Aiven).
- `get_db()` is an `async def` generator used as a FastAPI `Depends()`.

**File ref:** `app/core/database.py` lines 1–37

---

## 3. CRUD — PATCH & DELETE with 409 Guard

**PATCH (rename dataset):**
```python
# app/api/v1/datasets.py
@router.patch("/{dataset_id}")
async def rename_dataset(dataset_id: int, body: DatasetUpdate, db=Depends(get_db), user=Depends(get_current_user)):
    ds = await _get_owned(db, dataset_id, user.id)
    if body.name is not None:
        ds.name = body.name
    await db.commit()
    return ok(DatasetPublic.model_validate(ds).model_dump(), "renamed")
```

**DELETE with referential guard:**
```python
@router.delete("/{dataset_id}")
async def delete_dataset(...):
    ds = await _get_owned(db, dataset_id, user.id)
    # ── guard ──
    result = await db.execute(select(func.count()).where(LabelTask.dataset_id == ds.id))
    if result.scalar() > 0:
        raise HTTPException(409, "Cannot delete: dataset has label tasks")
    await db.delete(ds)
    await db.commit()
    return ok(None, "deleted")
```

The 409 prevents orphaned label tasks — a referential integrity check in application code before `db.delete()`.

**File refs:** `app/api/v1/datasets.py` (rename + delete endpoints), `app/schemas/dataset.py` (DatasetUpdate)

---

## 4. JWT Authentication Flow

1. **Signup** — `POST /auth/signup` → bcrypt hash → insert user → return JWT.
2. **Login** — `POST /auth/login` → `authenticate()` checks email+password → `make_token({"sub": user_id})`.
3. **Per-request** — `Depends(get_current_user)` extracts `Bearer` token → `verify_token()` decodes JWT → looks up user by `sub` claim.
4. **Expiry** — `access_token_expire_minutes=60` (default, configurable).
5. **Production guard** — `app/core/config.py` line 31: if `ENVIRONMENT=production` and `SECRET_KEY` is still the dev default, `sys.exit(1)`.

```python
# app/services/security.py
def make_token(data: dict, ...) -> str:
    to_encode.update({"exp": expire, "iat": now})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
```

**File refs:** `app/services/security.py`, `app/api/v1/auth.py`, `app/core/config.py`

---

## 5. Claim Race Handling (409)

```python
# app/api/v1/labeling.py — POST /labeling/claim
existing = await db.execute(
    select(TaskClaim).where(
        TaskClaim.task_id == body.task_id,
        TaskClaim.labeler_id == user.id,
    )
)
if existing.scalar_one_or_none():
    raise HTTPException(409, "You already claimed this task")

# Check task capacity
task = await db.get(LabelTask, body.task_id)
count_result = await db.execute(
    select(func.count()).where(TaskClaim.task_id == task.id)
)
if count_result.scalar() >= task.num_labelers:
    raise HTTPException(409, "Task already has maximum labelers")
```

Two-level guard: (1) prevent the same labeler from claiming twice; (2) prevent exceeding `num_labelers` capacity. In production you'd use `SELECT … FOR UPDATE`, but for this scale the application-level check is sufficient.

**File ref:** `app/api/v1/labeling.py` claim endpoint

---

## 6. Envelope Response Pattern

Every response — success or error — flows through one shape:

```json
{ "success": true|false, "data": ..., "message": "..." }
```

```python
# app/services/responses.py
def ok(data=None, message="OK"):   return {"success": True, "data": data, "message": message}
def fail(message, data=None):       return {"success": False, "data": data, "message": message}
```

Global exception handlers in `app/main.py` (lines 18–35) also return this shape for `HTTPException` and `RequestValidationError`, so the frontend always sees one contract.

Pydantic schema: `app/schemas/api.py` — `ApiEnvelope`.

**File refs:** `app/services/responses.py`, `app/main.py`, `app/schemas/api.py`

---

## 7. Alembic Migrations

**Migration 1** — `3df614ab9576_create_initial_tables.py`  
Creates the five core tables: `users`, `datasets`, `label_tasks`, `data_items`, `label_submissions`.

**Migration 2** — `6cea99c70951_add_task_claims_and_ai_suggestions_.py`  
Adds `task_claims` and `ai_suggestions` tables (evolved schema without touching earlier tables).

Both are idempotent and run via `alembic upgrade head` at deploy time (Procfile / render.yaml `preDeployCommand`).

**File refs:** `alembic/versions/3df614ab9576_create_initial_tables.py`, `alembic/versions/6cea99c70951_add_task_claims_and_ai_suggestions_.py`

---

## 8. Training Demo — TF-IDF + Naive Bayes

```python
# app/services/training.py
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
    ("clf", MultinomialNB()),
])
scores = cross_val_score(pipeline, texts, labels, cv=n_folds, scoring="accuracy")
```

- **Minimum:** 10 labeled rows (`MIN_LABELED_ROWS`).
- **Cap:** 2000 rows (`MAX_TRAINING_ROWS`) to keep demo fast.
- **Accuracy:** k-fold cross-validation (k = min(5, n_samples)), returned to frontend.
- **Cache:** `_model_cache[dataset_id] = (pipeline, timestamp)` with 300 s TTL. Expired entries raise `KeyError` → retrain prompt.
- **Predict:** `POST /datasets/{id}/predict` → `predict_with_model()` → returns `{label, confidence}`.

**File ref:** `app/services/training.py`, API endpoints in `app/api/v1/datasets.py`

---

## 9. Deployment Architecture

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend (React + Vite) | Vercel | `ai-dataset-labeling-marketplace.vercel.app` |
| Backend (FastAPI + Uvicorn) | Railway | `web-production-487e1.up.railway.app` |
| Database | Supabase (PostgreSQL) | via `DATABASE_URL` env var |

- **Railway Procfile:** `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **Vercel** reads `VITE_API_URL` for the backend base (must end in `/api/v1`).
- **CORS:** `app/main.py` allows `localhost:5173` (dev) + the `FRONTEND_URL` env var.
- **CI:** GitHub Actions → `black --check` → `pytest` on every push to `main`.

**File refs:** `Procfile`, `render.yaml`, `frontend/src/api.js`, `app/main.py` (CORS)

---

## 10. Known Limitation (be honest in viva)

> The in-memory model cache (`_model_cache`) is per-process. On Railway with a single container this is fine, but if scaled to multiple workers the cache won't be shared. A production system would use Redis or a managed model store. This is documented as a known limitation.

**File ref:** `app/services/training.py` line 13

---

## 11. Demo Script (exact clicks)

### Phase 1 — Owner creates dataset + task

1. Open `https://ai-dataset-labeling-marketplace.vercel.app/`
2. **Login** as `owner@demo.com` / `ReviewPass123`
3. Navigate to **Datasets** → click **Create Dataset**
   - Name: `Review2 Demo`, File type: `csv`
4. Open the new dataset → click **Upload CSV** → pick `data/sample.csv` (or any 15+ row CSV with a `text` and `label` column)
5. Navigate to **Tasks** → click **Create Task**
   - Title: `Sentiment Labels`, Instructions: `Label each item positive/negative`
   - Set `label_schema` to `{"label": ["positive", "negative"]}`
   - Link to the dataset you just created
6. The task appears with status **open**

### Phase 2 — Labeler claims and labels

7. **Logout** → **Login** as `labeler@demo.com` / `ReviewPass123`
8. Navigate to **Labeling** → see the open task → click **Claim**
9. Items load — each shows the CSV row content + (optional) AI suggestion
10. For each item, select a label from the schema → click **Submit**
11. After submitting all items, the task moves to **completed**

### Phase 3 — Train the model

12. **Logout** → **Login** as `owner@demo.com`
13. Navigate to **Datasets** → open the dataset → click **Train Model**
14. Response shows: `accuracy: 0.XX`, `labeled_count: N`
15. Click **Predict** → type sample text → see predicted label + confidence

---

## 12. Quick-Fire Faculty Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Why async SQLAlchemy instead of sync? | FastAPI is async; sync DB calls block the event loop. `create_async_engine` + `asyncpg` keeps the server non-blocking under concurrent requests. (`app/core/database.py`) |
| 2 | What does `pool_pre_ping=True` do? | Sends a lightweight `SELECT 1` before reusing a pooled connection. If the connection was dropped by Postgres/Aiven, it's replaced instead of failing. (`app/core/database.py` line 22) |
| 3 | How does bcrypt handle long passwords? | We truncate to 72 bytes before hashing — a bcrypt limit. The truncation is explicit in `hash_password()` and `verify_password()`. (`app/services/security.py` lines 20, 27) |
| 4 | Why is `is_active` an Integer (0/1) not Boolean? | SQLite compatibility during local dev — SQLite doesn't have a native BOOLEAN. Integer works across both Postgres and SQLite. (`app/models/user.py` line 20) |
| 5 | What prevents a dataset delete when tasks exist? | A `SELECT COUNT(*)` on `label_tasks` before `db.delete()`. Returns HTTP 409 with a clear message. (`app/api/v1/datasets.py` delete endpoint) |
| 6 | How does the claim race condition work? | Two checks: (1) duplicate claim per labeler → 409, (2) `count >= num_labelers` → 409. Application-level, not row-level locking. Adequate for current scale. (`app/api/v1/labeling.py`) |
| 7 | Why `expire_on_commit=False` on the session? | After `db.commit()`, SQLAlchemy defaults to expiring all attributes. With async sessions, accessing expired attributes triggers lazy loads that can't run outside the session context. This flag prevents that. (`app/core/database.py` line 27) |
| 8 | What is the envelope pattern and why? | Every response is `{success, data, message}`. Simplifies frontend error handling — one shape to parse for both success and failure. (`app/services/responses.py`) |
| 9 | How does the production SECRET_KEY guard work? | If `ENVIRONMENT=production` and the key is still `dev-secret-key-change-me`, the process calls `sys.exit(1)` at import time. Prevents running with a guessable signing key. (`app/core/config.py` lines 31-37) |
| 10 | Why TF-IDF + Naive Bayes for training? | Fast, interpretable, no GPU needed. Good baseline for text classification demos. `TfidfVectorizer` with unigrams+bigrams captures enough signal. (`app/services/training.py`) |
| 11 | What is `_model_cache` TTL and why? | 300 seconds (5 min). Prevents stale models from being used after the data may have changed. Expired entries raise `KeyError`, prompting retrain. (`app/services/training.py` line 14) |
| 12 | Why `MAX_TRAINING_ROWS = 2000`? | Keeps the demo fast — TF-IDF + NB trains in <1s on 2k rows. Larger datasets would slow the demo without meaningful accuracy gains for a proof-of-concept. (`app/services/training.py` line 17) |
| 13 | How does CORS work here? | `app/main.py` reads `FRONTEND_URL` env var + hardcoded localhost origins. Vercel's URL is added at deploy time; local dev uses `localhost:5173`. (`app/main.py` lines 38-50) |
| 14 | What does `alembic upgrade head` in the Procfile do? | Runs all pending migrations on deploy. Ensures the DB schema matches the code before Uvicorn starts. Idempotent — no-ops if already current. (`Procfile` line 1) |
| 15 | Why two migrations instead of one? | The second migration (`task_claims` + `ai_suggestions`) was added in a later iteration. Alembic chains them in order. Each migration is a self-contained, reversible unit. (`alembic/versions/`) |
| 16 | How does the frontend know the API URL? | `import.meta.env.VITE_API_URL || '/api/v1'` in `frontend/src/api.js`. Vercel sets it to the Railway URL; local dev relies on Vite's proxy. (`frontend/src/api.js`) |
| 17 | What are the test coverage numbers? | 27 tests across auth, datasets/tasks CRUD, the full labeler flow (claim→items→submit), training (train+predict), and security helpers. All green. (`tests/`) |
| 18 | Known limitation you'd fix first? | In-memory model cache doesn't survive restarts or scale across workers. Production fix: Redis-backed cache or a model registry like MLflow. (`app/services/training.py` line 13) |

---

*Generated from verified source files. Every file path and line number referenced above exists in the codebase.*
