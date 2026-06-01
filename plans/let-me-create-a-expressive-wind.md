# Pizzeria Web App — Implementation Plan

## Context

Greenfield project: build a static-ish marketing site for a pizzeria (homepage with description, pizza menu, contacts) plus a private admin area where the owner can CRUD pizzas. Data lives in PostgreSQL; the public menu reflects edits in near real-time.

Constraints from the user:
- **Monorepo** with separate `frontend/` and `backend/` folders, each containing `src/`.
- **Frontend**: Node-based — Next.js (React + TypeScript).
- **Backend**: Python + FastAPI, applying **DDD** (domain / application / infrastructure / api).
- **TDD**: every backend use case and every frontend component starts from a failing test.
- **Polyglot devcontainer** (Node 20 + Python 3.12 + Postgres service) scaffolded via the `devcontainer-init` skill.
- Pizzeria location reference: https://maps.app.goo.gl/DB4NzLKxTB1yXaxaA (used for hardcoded contacts).

## Progress So Far

✅ Steps 1–3 complete:
- Repository scaffolded with frontend/, backend/, .github/workflows/, .devcontainer/
- GitHub Actions CI workflows configured (backend-tests, frontend-tests)
- Devcontainer setup (Node 20, Python 3.12, Postgres service)
- Claude VSCode extension and GitHub CLI added to devcontainer

🔄 Next: Step 04 — Backend Bootstrap

## High-Level Architecture

```
mulino/
├── .devcontainer/              # Node 20 + Python 3.12 + Postgres, with Claude extension + GitHub CLI
│   ├── devcontainer.json
│   ├── docker-compose.yml
│   └── Dockerfile
├── .github/workflows/
│   ├── backend.yml            # backend-tests job
│   └── frontend.yml           # frontend-tests job
├── frontend/
│   └── src/
│       ├── app/               # Next.js App Router
│       │   ├── page.tsx       # homepage: hero, pizza list, contacts
│       │   └── admin/         # gated admin area
│       ├── components/
│       ├── lib/api.ts         # typed client for FastAPI
│       └── __tests__/
├── backend/
│   └── src/
│       └── pizzeria/
│           ├── domain/        # Pizza entity, Money/Allergen value objects
│           ├── application/   # use cases
│           ├── infrastructure/# SQLAlchemy models, repos
│           └── api/           # FastAPI routers
│       └── tests/             # unit + integration
├── README.md, .gitignore, .editorconfig, CLAUDE.md
└── .env.example, .env.local.example
```

## Step 04 — Backend Bootstrap

**Objective:** Initialize the Python backend with uv, add core dependencies, and scaffold the DDD package structure.

**Working directory:** `backend/`

**Actions:**
```bash
uv init --package --name pizzeria
uv add fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg alembic \
        pydantic pydantic-settings "passlib[bcrypt]" "python-jose[cryptography]"
uv add --dev pytest pytest-asyncio httpx ruff
```

**Configure pyproject.toml:**
- `tool.ruff`: line-length=100, lint.select=[E,F,I,UP,B]
- `tool.pytest.ini_options`: asyncio_mode=auto, testpaths=[tests]

**Create DDD package skeleton:**
```
backend/src/pizzeria/
├── __init__.py
├── domain/
│   └── __init__.py
├── application/
│   └── __init__.py
├── infrastructure/
│   └── __init__.py
└── api/
    └── __init__.py
tests/
├── unit/
└── integration/
```

**Acceptance:**
- `uv run python -c "import pizzeria"` succeeds
- `uv run pytest -q` → "no tests ran" (clean exit)
- `uv run ruff check .` → clean

## Remaining Steps (05–16)

After Step 04, follow these in order:

- **05** — Domain TDD (Pizza, Money, Allergen aggregate)
- **06** — Application TDD (use cases: ListPizzas, CreatePizza, UpdatePizza, DeletePizza)
- **07** — Infrastructure TDD (SQLAlchemy repository)
- **08** — Auth TDD (password hashing, JWT, AuthenticateOwner)
- **09** — API TDD (FastAPI routers with dependency injection)
- **10** — Migrations & Seed (Alembic initial migration + owner seed script)
- **11** — Frontend Bootstrap (Next.js scaffolding + Vitest)
- **12** — API Client (lib/api.ts typed client + MSW tests)
- **13** — Homepage (server components + pizza list + contacts)
- **14** — Admin Login (form + authentication flow)
- **15** — Admin CRUD (pizza table + create/edit/delete)
- **16** — Verification (manual e2e, PR flow, production build)

## Critical Files (Backend)

To be created in Steps 04–10:
- `backend/pyproject.toml` (with uv config)
- `backend/src/pizzeria/{domain,application,infrastructure,api}/__init__.py`
- `backend/src/pizzeria/domain/pizza.py`, `money.py`, `allergen.py`
- `backend/src/pizzeria/application/use_cases/*.py` (list, create, update, delete)
- `backend/src/pizzeria/infrastructure/db.py`, `repositories/pizza_repository.py`, `security.py`
- `backend/src/pizzeria/api/main.py`, `routers/pizzas.py`, `routers/auth.py`, `deps.py`, `schemas.py`
- `backend/alembic/` (env.py + versions/)
- `backend/tests/unit/` and `backend/tests/integration/`

## Domain Model (Pizza Aggregate)

Fields: `id: UUID`, `name: str` (unique ≤80), `description: str`, `ingredients: list[str]` (≥1), `allergens: set[Allergen]` (EU 14 enum), `price: Money` (amount > 0), `available: bool`.

EU 14 allergens: `gluten crustaceans eggs fish peanuts soy milk nuts celery mustard sesame sulphites lupin molluscs`.

Invariants enforced in `domain/` layer only.

## Verification (End-to-End)

1. Backend can be imported and tests run
2. All backend use cases have passing tests
3. FastAPI server starts and serves `/api/pizzas`
4. Frontend fetches from FastAPI and displays menu
5. Admin login works and CRUD operations persist to database
6. GitHub Actions CI blocks PRs until both backend-tests and frontend-tests pass
