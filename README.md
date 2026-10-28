# JobShift

JobShift is a Calm & Guided single-page app for capturing a worker's weekly tasks. The frontend saves a private task inventory to a FastAPI service backed by PostgreSQL. Anonymous sessions, upload review, task revisions, exports, expiry, and health reporting are implemented. Matching, exposure scoring, scenario calculations, skill recommendations, and learning plans are intentionally unavailable; the app creates no substitute scores or recommendations.

## Start the complete app

Requirements: Docker Desktop with Compose, Node.js 22+, and a browser. From the repository root:

```sh
cp .env.example .env
# Optionally replace the development database password in .env.
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

Open <http://localhost:5173>. The API is at <http://localhost:8000>; interactive API documentation is at <http://localhost:8000/docs>. Compose starts PostgreSQL with pgvector, waits for database health, runs Alembic once, then starts the API, cleanup loop, and Vite. Ports bind to localhost. Stop with Ctrl-C; `docker compose --env-file .env -f infra/docker-compose.yml down` stops containers. Add `-v` only if you also intend to delete the local database volume.

The Vite development server proxies `/api` and `/health` to the API container, so browser requests use the same origin and the HttpOnly cookie works in local development.

## Local development without Compose

Use Python 3.12, PostgreSQL with pgvector, uv, and Node.js 22. Set `DATABASE_URL` and `SECURE_COOKIES=false` for local HTTP. Then:

```sh
cd api
uv sync --locked --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

In another terminal:

```sh
cd web
npm ci
cp .env.example .env.local
npm run dev
```

Use `npm run dev` exactly (without a trailing period). The Vite proxy target defaults to `http://localhost:8000`. Do not put private credentials in `VITE_*` variables.

## Sessions, tasks, and imports

The browser creates an anonymous session automatically. Its unpredictable credential is held in an HttpOnly cookie; only a SHA-256 hash is stored in PostgreSQL. Refreshing the page recovers the session and saved tasks from the API; task data is not stored in localStorage. State-changing requests require an allowed Origin and every task/import/analysis/export operation checks the session credential and fixed expiry. Sessions expire no later than 24 hours after creation. The cleanup service removes expired sessions every 15 minutes; run it manually with `cd api && uv run python -m app.cleanup`.

Task entry and upload use the same normalized backend validation. Save sends the complete task list with its `If-Match` input revision; stale writes return 409. CSV and XLSX uploads are limited to 5 MB and 60 task rows. The API returns a temporary preview with worksheet/header and suggested mappings; users review the mapping and choose append or replace. CSV quoted fields and BOM are supported. XLSX formulas are rejected and never evaluated. Raw upload bytes are discarded after parsing; parsed previews expire after 30 minutes. Identifier-looking columns are omitted with a notice, but free text may still identify a person.

## Analysis and capabilities

`/api/v1/capabilities` distinguishes working storage/upload/export infrastructure from unavailable analysis engines. An analysis request saves an immutable task-revision reference, then returns HTTP 501 with status `not_implemented` and missing capabilities. Tasks remain saved. Scenario and plan requests also return explicit 501 responses. “Try an example” loads visibly synthetic inputs in the page only; they are not analyzed or saved unless the user explicitly chooses to save them.

The extension points are:

- Implement providers for `TaskMatcher`, `ExposureScorer`, `ScenarioEngine`, `SkillRecommender`, and `PlanGenerator` in `api/app/engines/interfaces.py`, using the contracts in `api/app/engines/contracts.py`.
- Register usable providers in `EngineRegistry` in `api/app/engines/placeholders.py`; `api/app/main.py` attaches the registry to the app. Each output must satisfy the Pydantic contracts and reference valid task/evidence IDs. Only then should that capability report available.
- Connect orchestration in `api/app/analysis/service.py`. Do not mark requests successful until all required providers return validated evidence-backed output.
- Add source/release/artifact metadata through `api/app/reference/repository.py` and the `reference_artifacts` model. No occupational evidence is preloaded or verified.

The frontend renders unavailable states from backend capabilities and never infers task matches or scores. JSON and PDF exports contain only saved task inventory, total hours, revision/time/version metadata, and an explicit `not_implemented` analysis status.

## Migrations, tests, and checks

```sh
cd api
uv sync --locked --group dev
uv run alembic upgrade head
uv run ruff check app alembic tests
uv run ruff format --check app alembic tests
uv run pytest -q
```

The PostgreSQL integration suite requires a real database with pgvector and does not use SQLite. Set `TEST_DATABASE_URL` to a dedicated disposable test database before pytest; those tests create/drop their tables. Without it, PostgreSQL integration tests are skipped. Frontend checks:

```sh
cd web
npm ci
npm test
npm run build
npm audit
```

GitHub Actions runs backend lint/format, the API suite against a PostgreSQL/pgvector service, npm audit, frontend tests, and the production TypeScript/Vite build. Alembic migrations are in `api/alembic/versions/`; apply them with `uv run alembic upgrade head` (or the Compose one-shot `migrate` service).

## Privacy and troubleshooting

There is no analytics, external AI-provider, or error-reporting transmission of task content. Task/session records are removed by expiry cleanup or immediate session deletion. Database backups and infrastructure logs may have separate retention; this application does not claim deletion from those systems. Cookie `Secure` defaults on; Compose explicitly disables it only for local HTTP. Production deployments must set secure cookies and explicit trusted origins.

- **API says database unavailable:** confirm the PostgreSQL health check passes and `DATABASE_URL` uses the Compose hostname `db` inside containers. For host-run API, use `localhost` instead.
- **Migration service fails:** inspect `docker compose ... logs migrate db`; ensure the database is healthy and the password matches `.env`, then rerun `docker compose ... up migrate`.
- **Browser cannot call API:** use `http://localhost:5173` and keep Vite's `/api` proxy enabled. Check the API health route at <http://localhost:8000/health/ready>.
- **Port already in use:** PostgreSQL is published on localhost port 5433 to avoid a common local PostgreSQL conflict. If another service already uses it, change only the left side of that port mapping in `infra/docker-compose.yml`; containers still connect to `db:5432`.

## Project layout

- `web/`: React/TypeScript page, typed API client, styles, and frontend tests.
- `api/app/`: FastAPI routes and focused service modules (`core`, `sessions`, `tasks`, `ingestion`, `reference`, `analysis`, `engines`, `exports`, `health`).
- `api/alembic/`: PostgreSQL schema migrations.
- `api/tests/`: unit/contract tests and opt-in real PostgreSQL integration tests.
- `infra/docker-compose.yml`: local PostgreSQL, one-shot migration, API, cleanup loop, and web services.
- `docs/architecture.md`: request/data flow and privacy boundaries.
