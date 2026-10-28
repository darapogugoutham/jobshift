from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import DomainError

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live():
    return {"status": "alive"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        exists = db.execute(
            text(
                "SELECT to_regclass('public.sessions') IS NOT NULL AND to_regclass('public.tasks') IS NOT NULL AND to_regclass('public.alembic_version') IS NOT NULL AND EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')"
            )
        ).scalar_one()
    except Exception as exc:
        raise DomainError("not_ready", "Database or required schema is unavailable.", 503) from exc
    if not exists:
        raise DomainError("not_ready", "Database schema or pgvector extension is not ready.", 503)
    return {
        "status": "ready",
        "database": "ready",
        "schema": "ready",
        "analysis": "not_implemented",
    }


@router.get("/api/v1/capabilities")
def capabilities(request: Request, db: Session = Depends(get_db)):
    database = False
    try:
        database = bool(
            db.execute(text("SELECT to_regclass('public.sessions') IS NOT NULL")).scalar_one()
        )
    except Exception:
        database = False
    infrastructure = "available" if database else "unavailable"
    return {
        "application_foundation": "ready",
        "task_storage": infrastructure,
        "upload_processing": infrastructure,
        "exports": infrastructure,
        "analysis_ready": False,
        "capabilities": request.app.state.engine_registry.capability_status(),
        "missing_capabilities": request.app.state.engine_registry.missing_capabilities(),
        "reference_data": {"status": "not_imported"},
    }
