# Changelog

## Review-II (2026-09-21/22) — Top-notch upgrade

- **CRUD gap closed**: Added PATCH (rename) and DELETE endpoints for datasets (owner-scoped, 403 non-owner, 404 unknown, 409 if label tasks exist). Frontend inline edit/save/cancel added.
- **UI/UX redesign**: New shared design system (`components/ui/` — Button, Input, Select, Card, Badge, Avatar, EmptyState, LoadingSpinner, Table). Warm/earthy palette (sand/clay/moss/sky), responsive desktop-table + mobile-card pattern, fadeIn animations.
- **8 demo datasets**: Fixture CSVs (sentiment, spam, support-tickets, topics, product-reviews, headlines, FAQ-intent, urgency) with seed logic in `seed_cloud.py` (idempotent by name+owner).
- **Training demo**: TF-IDF + MultinomialNB classifier (`POST /datasets/{id}/train`, `POST /datasets/{id}/predict`). In-memory model cache with 5-min TTL, min 10 labeled rows required, scikit-learn 1.9.0.
- **Test coverage**: 27 tests total (auth, datasets CRUD+PATCH+DELETE, full labeler flow, training train+predict, security helpers).
- **Live URLs**: Frontend `https://ai-dataset-labeling-marketplace.vercel.app/`, Backend `https://web-production-487e1.up.railway.app/`.
- README rewritten with real URLs, new features, demo credentials, env vars (`DIRECT_URL`/`FRONTEND_URL`/`VITE_API_URL`), and seed steps.
- CHANGELOG.md created (this file).

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