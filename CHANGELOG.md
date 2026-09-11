# Changelog

## Review-II (Phase 5-6: Grading + Docs)

- README rewritten with live-URL placeholders (Vercel frontend, Render backend), badge section (CI, Render health, coverage).
- Demo credentials documented: `owner@demo.com` / `labeler@demo.com` (password: `ReviewPass123`), seeded by `scripts/seed_cloud.py`.
- `VITE_API_URL` contract added: must include `/api/v1` suffix (see `frontend/src/api.js`).
- Environment variables table split into backend and frontend sections.
- Deployment table with platform and URL placeholders added.
- Folder structure updated to reflect `scripts/`, `render.yaml`, `Procfile`.
- CHANGELOG.md created (this file).
- `.gitignore` updated: `backend.log`, `test_marketplace.db`, `.omo/` added.
- Junk file `backend.log` deleted.
- Verified: `pytest -q` 13 passed, `alembic heads` single head (6cea99c70951).

## Day 11 - Review-I (MVP)

- Problem statement finalized and committed.
- Design docs added: architecture, ER, and class/module diagrams.
- Repo initialized with boilerplate (gitignore, LICENSE, env example).
- FastAPI backend scaffolded with health endpoint.
- Auth added: signup and login issuing real JWTs, bcrypt password hashing.
- Datasets and label tasks created with owner scoping.
- Alembic migrations added for the full 7-table schema.
- Response envelope standardized: every endpoint returns { success, data, message }.
- Labeler flow added: claim a task, upload CSV items, submit labels.
- React frontend added (Vite + Tailwind + Axios): auth, dashboard, labeling screens.
- Docker Compose added for local PostgreSQL development.
- Integration tests cover auth, dataset/task flows, and the full labeler flow.
- CI runs black lint + pytest on every push/PR to main, and builds the frontend.

## Week 1

- Repo + branch protection set up.
- Tech stack decided: FastAPI, SQLAlchemy, SQLite/PostgreSQL.
- README and environment template created.