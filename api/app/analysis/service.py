from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.models import AnalysisRequest, AnonymousSession
from app.engines.placeholders import EngineRegistry
from app.tasks.service import list_tasks


def request_analysis(
    db: Session, owner: AnonymousSession, registry: EngineRegistry | None = None
) -> AnalysisRequest:
    registry = registry or EngineRegistry()
    missing = registry.missing_capabilities()
    tasks = list_tasks(db, owner)
    if not tasks:
        raise DomainError(
            "tasks_required", "Save at least one task before requesting analysis.", 422
        )
    record = AnalysisRequest(
        session_id=owner.id,
        input_revision=owner.input_revision,
        snapshot=[
            {
                "id": str(t.id),
                "task_description": t.task_description,
                "hours_per_week": t.hours_per_week,
            }
            for t in tasks
        ],
        status="not_implemented",
        missing_capabilities=missing,
        completed_at=datetime.now(UTC),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    raise DomainError(
        "analysis_not_implemented",
        "Your tasks are saved. The analysis engine has not been connected yet.",
        501,
        {
            "analysis_request_id": str(record.id),
            "input_revision": record.input_revision,
            "status": record.status,
            "missing_capabilities": missing,
        },
    )
