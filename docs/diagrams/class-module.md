# Class / Module Diagram v1

```mermaid
classDiagram
    class FastAPI_App {
        +title: str
        +version: str
        +include_router(api_v1)
        +CORSMiddleware
    }

    class APIRouter {
        <<namespace>>
    }

    class AuthRoutes {
        +signup(payload, db) AuthResponse
        +login(payload, db) AuthResponse
        +me(current) UserPublic
        +refresh(current) AuthResponse
    }

    class UserRoutes {
        +register(payload, db) UserPublic
        +login(email, password, db) token
    }

    class DatasetRoutes {
        +create(payload, current, db) DatasetPublic
        +list(current, db) list
        +get(id, current, db) DatasetPublic
    }

    class TaskRoutes {
        +create(payload, current, db) LabelTaskPublic
        +list(current, db) list
    }

    class SecurityService {
        +hash_password(pw) str
        +verify_password(pw, hashed) bool
        +make_token(claims) str
        +verify_token(token) dict
        +get_current_user(token, db) User
        +oauth2_scheme
    }

    class Database {
        +engine: AsyncEngine
        +AsyncSessionLocal
        +Base
        +get_db() AsyncSession
    }

    class Config {
        +secret_key
        +algorithm
        +database_url
    }

    class User
    class Dataset
    class LabelTask
    class DataItem
    class LabelSubmission

    FastAPI_App --> APIRouter : mounts
    APIRouter --> AuthRoutes
    APIRouter --> UserRoutes
    APIRouter --> DatasetRoutes
    APIRouter --> TaskRoutes

    AuthRoutes --> SecurityService
    UserRoutes --> SecurityService
    DatasetRoutes --> SecurityService : get_current_user
    TaskRoutes --> SecurityService : get_current_user

    SecurityService --> Database : get_db / AsyncSession
    SecurityService --> Config
    Database --> Config : database_url

    User --> Database : Base
    Dataset --> Database : Base
    LabelTask --> Database : Base
    DataItem --> Database : Base
    LabelSubmission --> Database : Base
```

## Notes

- Routers live in `app/api/v1/`, models in `app/models/`, and `SecurityService`
  covers JWT + bcrypt so routes stay thin.
- `get_current_user` is a shared FastAPI dependency: it decodes the token and
  returns the logged-in user, which is what keeps dataset/task routes scoped.
- Pydantic schemas (`app/schemas/`) sit between routes and models for
  request validation / response serialization.