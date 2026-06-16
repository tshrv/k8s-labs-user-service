# nagp-user-service

Production-ready FastAPI microservice for user management. Built with async SQLAlchemy + PostgreSQL, Alembic migrations, structured logging, and full integration test coverage via testcontainers.

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.115+ (async) |
| Database | PostgreSQL 16 via asyncpg |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic |
| Config | pydantic-settings (12-factor) |
| Logging | structlog (JSON in prod, colored in dev) |
| Package manager | uv |
| Testing | pytest + testcontainers (real Postgres) |
| Containerization | Docker (multi-stage Alpine) |

## Project Structure

```
nagp-user-service/
├── main.py                        # ASGI entry point (uvicorn main:app)
├── app/
│   ├── main.py                    # Application factory: create_app()
│   ├── config.py                  # Settings via pydantic-settings
│   ├── dependencies.py            # Typed FastAPI DI aliases
│   ├── exceptions.py              # Domain exception classes
│   ├── api/v1/
│   │   ├── router.py              # Aggregates all v1 routers
│   │   └── endpoints/
│   │       ├── health.py          # GET /api/v1/health, /health/db
│   │       └── users.py           # User CRUD endpoints
│   ├── core/
│   │   ├── logging.py             # structlog configuration
│   │   ├── middleware.py          # RequestID + Timing middleware
│   │   └── exception_handlers.py  # Global FastAPI exception handlers
│   ├── db/
│   │   ├── base.py                # DeclarativeBase + Alembic naming conventions
│   │   ├── session.py             # Async engine + session factory
│   │   └── models/user.py         # SQLAlchemy User ORM model
│   └── schemas/user.py            # Pydantic v2 request/response schemas
├── migrations/                    # Alembic migration scripts
│   └── versions/
├── tests/
│   ├── conftest.py                # testcontainers fixtures + migration lifecycle
│   ├── test_health.py
│   └── users/test_users_crud.py
├── Dockerfile                     # Multi-stage: uv Alpine builder → python Alpine runtime
├── docker-compose.yml             # App + PostgreSQL
└── .env.example                   # Environment variable template
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker (for running locally with docker-compose or for tests)

### Local Development

```bash
# Install all dependencies (runtime + dev)
uv sync

# Copy and edit environment config
cp .env.example .env

# Start PostgreSQL (or point DATABASE_URL at an existing instance)
docker compose up -d postgres

# Run database migrations
uv run alembic upgrade head

# Start the dev server with hot reload
uv run uvicorn main:app --reload
```

The API is now available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Full Stack with Docker

```bash
docker compose up --build
```

This starts both the app (`localhost:8000`) and a PostgreSQL instance. The app container mounts the local directory for hot-reload in development.

> **Note:** Migrations are not run automatically on container start. Run them manually:
> ```bash
> docker compose exec app uv run alembic upgrade head
> ```

## API Reference

All endpoints are prefixed with `/api/v1`.

### Health

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Liveness probe — no DB dependency |
| GET | `/api/v1/health/db` | Readiness probe — verifies DB connectivity |

### Users

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/users` | List users (paginated) |
| POST | `/api/v1/users` | Create a user |
| GET | `/api/v1/users/{id}` | Get user by ID |
| PATCH | `/api/v1/users/{id}` | Partially update a user |
| DELETE | `/api/v1/users/{id}` | Delete a user |

**Pagination query params:** `page` (default: 1), `size` (default: 20, max: 100)

**Example — create user:**
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "username": "alice", "password": "mysecretpass"}'
```

## Configuration

All settings are read from environment variables (or a `.env` file). See [.env.example](.env.example) for the full list.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL connection string |
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `SECRET_KEY` | *(change me)* | Used for future token signing |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins (JSON list) |
| `DATABASE_ECHO` | `false` | Log all SQL statements (dev only) |

> **Production note:** Swagger UI (`/docs`) and OpenAPI schema (`/openapi.json`) are automatically disabled when `ENVIRONMENT=production`.

## Database Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Roll back the most recent migration
uv run alembic downgrade -1

# Roll back to a clean slate
uv run alembic downgrade base

# Generate a new migration from ORM model changes
uv run alembic revision --autogenerate -m "describe_your_change"
```

> Alembic reads `DATABASE_URL` from the environment, falling back to the value in `alembic.ini`.

## Testing

Tests are **integration tests** — they run against a real PostgreSQL instance spun up automatically via [testcontainers](https://testcontainers-python.readthedocs.io/). Docker must be running.

```bash
# Run all tests
uv run pytest

# With coverage report
uv run pytest --cov=app --cov-report=term-missing

# Run a specific test file
uv run pytest tests/users/test_users_crud.py -v
```

**Test lifecycle (per session):**
1. testcontainers pulls and starts `postgres:16-alpine`
2. `alembic downgrade base` → `alembic upgrade head` (ensures a clean, fully-migrated schema)
3. Tests run — each test gets a fresh session that rolls back after the test
4. `alembic downgrade base`, container stops and is removed

## Code Quality

```bash
# Lint and auto-fix
uv run ruff check app tests --fix

# Type checking
uv run mypy app
```

## Key Design Decisions

**Application factory** — `create_app()` in `app/main.py` returns a configured `FastAPI` instance. This enables clean test setup (dependency overrides, settings reset) and defers all initialization to call time.

**Async-first** — Every DB operation uses `async/await` with `asyncpg`. The `get_db_session` dependency commits on success and rolls back on exception; endpoints use `db.flush()` (not `db.commit()`) to get the generated PK before the response is sent.

**Schema / ORM separation** — Pydantic schemas live in `app/schemas/`, SQLAlchemy models in `app/db/models/`. Endpoints receive schemas, interact with ORM models, then return schemas. ORM objects are never serialized directly.

**ULID primary keys** — 26-character, URL-safe, lexicographically sortable by creation time. Avoids B-tree index fragmentation caused by random UUIDs.

**Structured logging** — `structlog` with `contextvars` integration. The `RequestIDMiddleware` binds a `request_id` to the async context so every log line emitted during a request automatically includes it — no explicit passing needed.

**Alembic naming conventions** — `Base.metadata` is initialized with explicit naming conventions for indexes, constraints, and foreign keys. This prevents autogenerated names that differ between environments and break `alembic downgrade`.
