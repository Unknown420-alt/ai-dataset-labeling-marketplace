# Changelog

## Day 11 - Review-I (MVP)

- Problem statement finalized and committed.
- Design docs added: architecture, ER, and class/module diagrams.
- Repo initialized with boilerplate (gitignore, LICENSE, env example).
- FastAPI backend scaffolded with health endpoint.
- Auth added: signup and login issuing real JWTs, bcrypt password hashing.
- Databases and label tasks created with owner scoping.
- Alembic migrations added for the full 7-table schema.
- Integration tests cover signup -> login -> dataset -> task flows.
- CI runs pytest on push/PR to main.

## Week 1

- Repo + branch protection set up.
- Tech stack decided: FastAPI, SQLAlchemy, SQLite/PostgreSQL.
- README and environment template created.