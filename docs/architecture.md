# JobShift architecture and integration boundaries

## Request path

React in `web/` sends same-origin requests through Vite's `/api` proxy to FastAPI. FastAPI validates the anonymous HttpOnly cookie, fixed session expiry, request origin for mutations, payload, and input revision before database changes. SQLAlchemy persists sessions, normalized tasks, import previews, analysis-request status, and reference artifact metadata in PostgreSQL. Alembic enables pgvector and creates the schema before the API starts.

```text
Browser (React) -> Vite proxy -> FastAPI -> session authorization -> PostgreSQL
                                               |-> upload parser -> temporary mapping preview
                                               |-> analysis request -> unavailable providers -> 501
                                               |-> JSON/PDF inventory exports
```

## Privacy and lifecycle

Session IDs are identifiers, not credentials. A random bearer secret is set in an HttpOnly cookie, and the server stores only its SHA-256 hash. Expiry is assigned at creation and is not extended by ordinary use. Every authorized request checks expiry. Deleting a session cascades to its owned rows. The scheduled cleanup process deletes expired sessions every 15 minutes and temporary previews after 30 minutes. Database backup/log retention is controlled separately by the operator.

The file parser accepts bounded CSV/XLSX content, rejects spreadsheet formula cells, and stores only normalized preview rows and mapping state. It does not run macros or formulas. Mapping confirmation and task mutation are committed together. Append/replace is explicit, and the task collection uses an optimistic revision check.

## Analysis boundary

The provider contracts live in `api/app/engines/interfaces.py`; output data models and validation constraints live in `api/app/engines/contracts.py`. `EngineRegistry` currently registers unavailable placeholders. `api/app/analysis/service.py` stores the request's task revision and produces a terminal `not_implemented` result/501. It must not be marked successful until matching, evidence interpretation, scoring, scenarios, recommendations, and planning are implemented and return validated outputs.

When adding providers, implement the relevant Protocol, validate outputs against the contracts, then register it in `api/app/engines/placeholders.py` (the registry can later be renamed). Update capability reporting only for genuinely functional providers. Keep routes, UI, and database request-status transitions stable by extending the analysis service rather than invoking providers in HTTP handlers.

## Database and API lifecycle

`infra/docker-compose.yml` has separate database, one-shot migration, API, cleanup, and web services. The migration job waits for the PostgreSQL/pgvector health check and completes before the API starts. Do not migrate inside individual API workers. `GET /health/live` is process liveness; `/health/ready` checks PostgreSQL, the required schema, and pgvector. `/api/v1/capabilities` reports infrastructure and algorithm readiness separately.

## Known boundaries

- No reference datasets, occupational crosswalks, embeddings, or evidence sources are loaded.
- No AI/LLM provider is called.
- Exports include task inventory and explicit unavailable analysis fields only.
- Synthetic example tasks are client-side presentation inputs; they are not stored until the user explicitly saves them.
- Backups and operational logs may have independent retention. Application expiry is not a universal deletion guarantee.
