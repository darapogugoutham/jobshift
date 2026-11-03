## Change summary

<!-- What behavior changes, and why? -->

## TDD evidence

- [ ] I wrote or updated a test before changing production code.
- [ ] **Red:** I ran the new test first and confirmed it failed for the expected reason.
- [ ] **Green:** I made the smallest change to pass it and the relevant existing tests.
- [ ] **Refactor:** I reran affected tests after refactoring.

Failing test and command (red):

Passing test and command (green):

## Verification

- [ ] Frontend tests (`cd web && npm test`)
- [ ] Frontend build/type check (`cd web && npm run build`)
- [ ] Backend tests (`cd api && uv run pytest -q`)
- [ ] Backend lint/format checks
- [ ] PostgreSQL integration tests (real PostgreSQL with pgvector)
- [ ] Any unavailable checks and reason are described below.

Additional results or manual checks:
