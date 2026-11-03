# Contributing to JobShift

## Test-driven development is the default

For every behavior change or bug fix, use the red-green-refactor cycle:

1. **Red:** write the smallest test that describes the expected behavior. Run it and confirm that it fails for the expected reason. Do not start the implementation before this check.
2. **Green:** make the smallest production-code change that passes the new test and the relevant existing tests.
3. **Refactor:** improve the code while keeping the tests green. Rerun the affected tests after each refactor.

For a bug fix, first reproduce the bug in a regression test. For API behavior, prefer service/route tests and real PostgreSQL integration tests for database semantics. Do not use SQLite as a substitute for PostgreSQL. For frontend behavior, test observable UI or API-client behavior rather than implementation details. For migrations, exercise the migration against PostgreSQL in CI.

Tests are part of the change, not follow-up work. A behavior change without a corresponding test should be treated as incomplete. If a behavior cannot reasonably be tested automatically, explain why in the pull request and include the manual verification steps.

## Commands

Run frontend tests in watch mode while developing:

```sh
cd web
npm run test:watch
```

Run the frontend suite and production type/build checks before opening a pull request:

```sh
cd web
npm test
npm run build
```

Run backend tests and static checks:

```sh
cd api
uv run pytest -q
uv run ruff check app alembic tests
uv run ruff format --check app alembic tests
```

The PostgreSQL integration tests require a disposable PostgreSQL database with pgvector. Set `TEST_DATABASE_URL` before running `pytest`; the integration fixture creates and drops its test schema. GitHub Actions supplies a real PostgreSQL/pgvector service and runs the integration tests on every push and pull request.

## Existing code and TDD history

The current test suites are a baseline for this project. Their presence does not establish that earlier implementation work followed TDD. New and changed behavior must follow the red-green-refactor sequence above, with evidence recorded in the pull request checklist.
