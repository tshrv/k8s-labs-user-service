# k8s-labs-user-service

A two-tier (API + database) application deployed on Kubernetes (GKE). The API tier is a FastAPI microservice that fetches records from a PostgreSQL database tier over the cluster network. This README is the assignment deliverable: the sections below cover the requirement understanding, assumptions, solution overview, and justification for the Kubernetes/Docker resources used.

## Deliverable Links

| Item | Link |
|---|---|
| Source repository | https://github.com/tshrv/k8s-labs-user-service |
| Docker Hub image | https://hub.docker.com/r/tshrv/k8s-labs-user-service (`tshrv/k8s-labs-user-service`) |
| Live API — list users from DB | http://136.68.44.58/api/v1/users |

> The cluster may be torn down after the demo recording to avoid cloud cost, so the live URL is not guaranteed to remain reachable.

---

# Assignment Documentation

## Requirement Understanding

Design, containerize, and deploy a multi-tier application on Kubernetes that simulates a real-world setup where a **service/API tier** fetches data from a **database tier** over an exposed API. Concretely:

- **API tier** — externally reachable, stateless, runs multiple replicas, supports rolling updates, self-heals, and scales horizontally on CPU (HPA). Its DB configuration must come from outside the image (ConfigMap), and the DB password must never appear in plaintext in any manifest (Secret).
- **Database tier** — reachable **only inside** the cluster, runs a single replica, persists its data across pod restarts/redeployments, and auto-recovers after a pod is deleted. Must hold one table seeded with 5–10 records.
- **Cross-cutting** — tiers communicate by Kubernetes Service DNS (never pod IPs); the API is exposed via Ingress; images are built and pushed to Docker Hub; and FinOps practices (resource requests/limits, right-sizing, autoscaling) are applied.

## Assumptions

- **Target platform is GKE.** The Ingress (`kubernetes.io/ingress.class: gce`) and the container-native load-balancing annotation (`cloud.google.com/neg`) are GKE-specific; the rest of the manifests are portable.
- **Single-node-friendly sizing.** Resource requests/limits assume small shared nodes (e.g. `e2-small`, 2 vCPU / 2 GiB), so all pods are sized to co-exist on a minimal, low-cost node pool.
- **`ReadWriteOnce` storage is sufficient** because the DB tier is intentionally a single writer (1 replica). This drives the `Recreate` strategy choice for Postgres.
- **Demo-grade secrets.** Secret values are base64-*encoded* (not encrypted) to satisfy the "no plaintext password in YAML" rule. A real deployment would source these from an external secret manager; this is documented in `k8s/secret.yaml`.
- **Seed data is loaded once** via an init-script ConfigMap on first DB startup (empty volume). The `users` table is seeded with 8 records.
- **The required "4 pods" for the API tier is expressed as the HPA ceiling** — the deployment idles at 2 replicas and scales up to 4 under load, rather than pinning 4 replicas around the clock.

## Solution Overview

```
                 Internet
                    │
                    ▼
        ┌───────────────────────┐
        │  Ingress (GKE L7 LB)  │   k8s/ingress.yaml — external entry point
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Service: user-service│   ClusterIP + NEG, port 80 → 8000
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Deployment: API tier │   2→4 replicas (HPA), RollingUpdate
        │  FastAPI :8000        │   ConfigMap + Secret via envFrom
        └───────────┬───────────┘
                    │  DNS: "postgres:5432"  (never pod IPs)
                    ▼
        ┌───────────────────────┐
        │  Service: postgres    │   ClusterIP — internal only
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Deployment: DB tier  │   1 replica, Recreate strategy
        │  postgres:16-alpine   │   seeded via init-script ConfigMap
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  PVC (10Gi, RWO)      │   data survives pod deletion
        └───────────────────────┘
```

**Container build (Docker).** A multi-stage Dockerfile uses the `uv` Alpine image to install locked dependencies into a virtualenv, then copies only that venv and the app into a slim `python:3.12-alpine` runtime. The result is a small, reproducible image (frozen lockfile, no build toolchain in the final layer) that listens on `:8000`. GitHub Actions (`.github/workflows/docker-image.yml`) builds on every push to `main` and pushes three tags to Docker Hub: `latest`, the commit SHA, and a UTC timestamp — the immutable tags make rollouts/rollbacks observable.

**Kubernetes manifests (`k8s/`).** All objects live in a dedicated `user-service` namespace:

| Manifest | Object | Purpose |
|---|---|---|
| `namespace.yaml` | Namespace | Isolates all resources |
| `configmap.yaml` | ConfigMap | Non-secret DB host/port/name + app config |
| `secret.yaml` | Secret | DB user/password + full `DATABASE_URL` |
| `app-deployment.yaml` | Deployment | API tier, 2 replicas, RollingUpdate, probes, resources |
| `app-service.yaml` | Service (ClusterIP) | Fronts API pods, NEG-enabled for Ingress |
| `ingress.yaml` | Ingress | External HTTP entry point |
| `hpa.yaml` | HorizontalPodAutoscaler | Scales API 2→4 on 70% CPU |
| `db-deployment.yaml` | Deployment | Postgres, 1 replica, Recreate strategy |
| `db-service.yaml` | Service (ClusterIP) | Internal-only DB endpoint |
| `db-pvc.yaml` | PersistentVolumeClaim | 10Gi RWO durable storage |
| `db-init-configmap.yaml` | ConfigMap | Schema + 8 seed rows on first start |

**Behaviours demonstrated:** external access via Ingress; **self-healing** (deleting an API or DB pod, the Deployment recreates it); **persistence** (deleting the DB pod, the PVC re-attaches and records survive); **rolling updates** (`kubectl set image` with `maxUnavailable: 0`); and **HPA** scaling under load (a Locust load test lives in `locust/`).

## Justification for the Resources Utilized

| Resource / choice | Why |
|---|---|
| **Namespace** | Groups and isolates the assignment's objects; makes teardown and RBAC scoping trivial. |
| **Two `Deployment`s (not a StatefulSet for DB)** | A single-replica Postgres backed by one PVC meets the persistence + auto-recovery requirement without StatefulSet complexity; the Deployment's controller already recreates the pod and re-attaches the PVC. |
| **API `RollingUpdate` (`maxSurge:1`, `maxUnavailable:0`)** | Zero-downtime deploys — a new pod must become Ready before an old one is removed, so the service never drops below its ready replica count. |
| **DB `Recreate` strategy** | The PVC is `ReadWriteOnce`; a second Postgres pod couldn't mount it during a rolling update, so `Recreate` makes the single-writer constraint explicit instead of letting a rollout wedge. |
| **ClusterIP for both Services** | API is exposed externally **only** through the Ingress; the DB Service stays ClusterIP so it is unreachable from outside the cluster, as required. |
| **Service DNS for tier-to-tier traffic** | The API connects to `postgres:5432` by Service name — pod IPs are ephemeral and would break on every reschedule. |
| **Ingress (GKE L7 LB)** | Single, stable external entry point for the API; cheaper and more idiomatic than a per-service cloud LoadBalancer. |
| **ConfigMap** | Externalizes non-secret DB connection details and app settings from the image — the same image runs in any environment by swapping config. |
| **Secret** | Keeps the DB password and connection string out of plaintext manifests; injected into both tiers via `secretKeyRef`/`secretRef`. |
| **PVC (10Gi, RWO, `standard`)** | Decouples DB data from the pod lifecycle so records survive pod deletion/redeploy; `standard` (HDD-class) is the cheapest class that satisfies durability for this workload. |
| **Liveness vs. readiness probes** | Liveness checks the process only (no DB), so a transient DB blip makes pods *unready* rather than triggering a cluster-wide restart loop; readiness checks DB connectivity so pods receive traffic only when they can fully serve. |
| **Requests/limits (API 50m/128Mi → 250m/256Mi; DB 100m/256Mi → 512Mi)** | Requests enable dense, cheap bin-packing on small nodes; limits cap any one pod's burst so a noisy replica can't starve its neighbours — the core FinOps control. |
| **HPA (min 2, max 4, 70% CPU)** | Idles at 2 pods during low traffic and only bursts to 4 when CPU justifies it, instead of paying for 4 replicas 24/7 — directly the cost-optimization requirement. |
| **Multi-stage Alpine Docker image** | Smaller images = faster pulls, lower registry/egress cost, and a reduced attack surface (no build tools in the runtime layer). |

**FinOps opportunities identified & implemented:** (1) HPA scale-to-minimum during idle (`hpa.yaml`); (2) per-pod CPU/memory limits to allow safe co-tenancy on small nodes (`app-deployment.yaml`); (3) `Recreate` + right-sized DB and slim Alpine images to fit a minimal, low-cost node pool (`db-deployment.yaml`).

---

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
k8s-labs-user-service/
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
