import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.models import AnalysisRequest, AnonymousSession, TaskRecord
from app.main import app


@pytest.fixture(scope="session")
def pg_engine():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a real PostgreSQL database for integration tests")
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(pg_engine):
    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    with factory() as db:
        db.execute(delete(AnonymousSession))
        db.commit()

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def created_session(client):
    response = client.post("/api/v1/sessions")
    assert response.status_code == 201
    assert response.headers.get("set-cookie", "").lower().find("httponly") >= 0
    return response.json()


def test_postgres_session_recovery_task_persistence_revision_exports_and_delete(
    client, created_session, pg_engine
):
    task = {
        "id": "b31a7cee-9c40-427c-918d-fb4b540fb5fd",
        "task_description": "Prepare monthly service reports",
        "hours_per_week": 4,
        "frequency": "monthly",
        "tools_used": ["Sheets"],
        "skills_used": None,
        "involves_people": None,
        "physical_presence_required": False,
        "decision_authority": 2,
        "notes": None,
    }
    saved = client.put("/api/v1/tasks", headers={"If-Match": "0"}, json={"tasks": [task]})
    assert saved.status_code == 200 and saved.json()["input_revision"] == 1
    refreshed = client.get("/api/v1/sessions/current")
    assert (
        refreshed.status_code == 200
        and refreshed.json()["session_id"] == created_session["session_id"]
    )
    listing = client.get("/api/v1/tasks")
    assert listing.json()["tasks"][0]["involves_people"] is None
    stale = client.put("/api/v1/tasks", headers={"If-Match": "0"}, json={"tasks": [task]})
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "revision_conflict"
    result = client.post("/api/v1/analyses", json={})
    assert result.status_code == 501
    error = result.json()["error"]
    assert error["code"] == "analysis_not_implemented"
    status = client.get("/api/v1/analyses/" + error["details"]["analysis_request_id"])
    assert status.json()["status"] == "not_implemented" and status.json()["input_revision"] == 1
    exported = client.get("/api/v1/exports/json")
    assert exported.status_code == 200
    assert exported.json()["analysis"] == {"status": "not_implemented", "result": None}
    pdf = client.get("/api/v1/exports/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    other = TestClient(app)
    other.post("/api/v1/sessions")
    assert other.get("/api/v1/tasks").json()["tasks"] == []
    deleted = client.delete("/api/v1/sessions/current")
    assert deleted.status_code == 204
    assert client.get("/api/v1/tasks").status_code == 401
    with Session(pg_engine) as db:
        assert db.scalar(select_count(TaskRecord)) == 0
        assert db.scalar(select_count(AnalysisRequest)) == 0


def select_count(model):
    from sqlalchemy import func, select

    return select(func.count()).select_from(model)


def test_postgres_upload_mapping_confirmation_and_cross_session_authorization(client):
    csv_bytes = b'task_description,hours_per_week,frequency,involves_people\n"Talk with clients, and follow up",3,weekly,no\n'
    preview = client.post("/api/v1/imports", files={"file": ("tasks.csv", csv_bytes, "text/csv")})
    assert preview.status_code == 201
    state = preview.json()
    assert state["headers"][0] == "task_description"
    mapped = client.put(
        f"/api/v1/imports/{state['id']}/mapping",
        json={"sheet_name": "CSV", "mapping": state["mapping"]},
    )
    assert mapped.status_code == 200
    confirmed = client.post(
        f"/api/v1/imports/{state['id']}/confirm", headers={"If-Match": "0"}, json={"mode": "append"}
    )
    assert confirmed.status_code == 200 and confirmed.json()["total_hours"] == 3
    assert confirmed.json()["tasks"][0]["involves_people"] is False
    outsider = TestClient(app)
    outsider.post("/api/v1/sessions")
    assert outsider.get(f"/api/v1/imports/{state['id']}").status_code == 404


def test_expiry_and_idempotent_cleanup(pg_engine, client, created_session, monkeypatch):
    session_id = created_session["session_id"]
    with Session(pg_engine) as db:
        db.execute(
            text("UPDATE sessions SET expires_at=:past WHERE id=:id"),
            {"past": datetime.now(UTC) - timedelta(hours=1), "id": session_id},
        )
        db.commit()
    expired = client.get("/api/v1/sessions/current")
    assert expired.status_code == 401 and expired.json()["error"]["code"] == "session_expired"
    from app import cleanup

    factory = sessionmaker(bind=pg_engine, expire_on_commit=False)
    monkeypatch.setattr(cleanup, "SessionLocal", factory)
    assert cleanup.cleanup_expired()["expired_sessions_deleted"] == 1
    assert cleanup.cleanup_expired()["expired_sessions_deleted"] == 0


def test_health_readiness_and_capability_status(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json()["analysis"] == "not_implemented"
    caps = client.get("/api/v1/capabilities").json()
    assert caps["task_storage"] == "available" and caps["analysis_ready"] is False
    assert all(value == "unavailable" for value in caps["capabilities"].values())
