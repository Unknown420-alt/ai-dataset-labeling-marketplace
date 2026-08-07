# Architecture Diagram v1

```mermaid
flowchart LR
    subgraph Client
        UI[React frontend<br/>/docs Swagger UI]
    end

    subgraph Backend["FastAPI backend (app/)"]
        API[API v1 routers<br/>health / auth / users / datasets / tasks]
        SVC[Services<br/>security / JWT / bcrypt]
        MOD[Models<br/>User Dataset LabelTask DataItem<br/>LabelSubmission TaskClaim AISuggestion]
    end

    subgraph Data["Data layer"]
        DB[(SQLite dev<br/>PostgreSQL prod)]
        MIG[Alembic migrations]
    end

    EXT[External services<br/>OpenAI suggestion<br/>later weeks]

    UI -->|HTTP / JSON| API
    API --> SVC
    SVC --> MOD
    MOD --> DB
    MIG --> DB
    API -.->|AI suggestions<br/>(planned)| EXT

    subgraph Hosting["Hosting (planned)"]
        FE_HOST[Vercel - frontend]
        BE_HOST[Render - backend API]
        DB_HOST[Railway / Aiven - PostgreSQL]
    end
```

## Notes

- Client talks to the API over plain HTTP + JSON. CORS is open to localhost dev
  origins (5173 / 3000) for the future React app.
- The API layer is split per domain (auth, datasets, tasks) under `app/api/v1/`.
- Auth uses a stateless JWT (HS256). The token carries the user id (`sub`) and
  role; protected routes resolve the current user via a FastAPI dependency.
- All DB access is async SQLAlchemy. Alembic owns schema changes.
- The AI suggestion service is intentionally stubbed until later sprints.
- Hosting boundary: frontend on Vercel, backend API on Render, managed
  PostgreSQL on Railway/Aiven - wiring this up is Day 41 work.
