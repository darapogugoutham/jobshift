from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, Response, UploadFile
from fastapi.responses import Response as RawResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analysis.service import request_analysis
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import DomainError
from app.core.models import (
    AnalysisRequest,
    AnonymousSession,
    ImportPreview,
    ReferenceArtifact,
    TaskRecord,
)
from app.exports.service import make_json_export, make_pdf_export
from app.ingestion.parser import parse_upload, suggest_mappings, validate_mapped_rows
from app.ingestion.schemas import ImportConfirmation, ImportMappingUpdate
from app.sessions.service import create_session, now_utc, require_revision, resolve_session
from app.tasks.schemas import TaskCollection, TaskInput, TaskList, TaskMutation, TaskRead
from app.tasks.service import (
    create_task,
    delete_task,
    list_tasks,
    replace_tasks,
    total_hours,
    update_task,
)

router = APIRouter(prefix="/api/v1")


def owner_from_request(request: Request, db: Session, for_update: bool = False) -> AnonymousSession:
    return resolve_session(db, request.cookies.get(get_settings().session_cookie_name), for_update)


def revision(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.strip().strip('"'))
    except ValueError:
        raise DomainError(
            "invalid_revision", "If-Match must contain an integer input revision.", 400
        )


def session_result(owner: AnonymousSession):
    return {
        "session_id": str(owner.id),
        "created_at": owner.created_at,
        "expires_at": owner.expires_at,
        "input_revision": owner.input_revision,
    }


def task_list_response(db: Session, owner: AnonymousSession):
    tasks = list_tasks(db, owner)
    return TaskList(
        tasks=[TaskRead.model_validate(t, from_attributes=True) for t in tasks],
        input_revision=owner.input_revision,
        total_hours=total_hours(tasks),
    )


def set_cookie(response: Response, credential: str):
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        credential,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


@router.post("/sessions", status_code=201)
def new_session(response: Response, db: Session = Depends(get_db)):
    owner, credential = create_session(db)
    set_cookie(response, credential)
    return session_result(owner)


@router.get("/sessions/current")
def current_session(request: Request, db: Session = Depends(get_db)):
    return session_result(owner_from_request(request, db))


@router.delete("/sessions/current", status_code=204)
def delete_current_session(request: Request, response: Response, db: Session = Depends(get_db)):
    owner = owner_from_request(request, db)
    db.delete(owner)
    db.commit()
    response.delete_cookie(get_settings().session_cookie_name, path="/")
    return response


@router.get("/tasks", response_model=TaskList)
def get_tasks(request: Request, db: Session = Depends(get_db)):
    return task_list_response(db, owner_from_request(request, db))


@router.post("/tasks", response_model=TaskMutation, status_code=201)
def post_task(
    data: TaskInput,
    request: Request,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    owner = owner_from_request(request, db, for_update=True)
    require_revision(owner, revision(if_match))
    item = create_task(db, owner, data)
    tasks = list_tasks(db, owner)
    return {
        "task": TaskRead.model_validate(item, from_attributes=True),
        "input_revision": owner.input_revision,
        "total_hours": total_hours(tasks),
    }


@router.put("/tasks/{task_id}", response_model=TaskMutation)
def put_task(
    task_id: UUID,
    data: TaskInput,
    request: Request,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    owner = owner_from_request(request, db, for_update=True)
    require_revision(owner, revision(if_match))
    item = update_task(db, owner, task_id, data)
    return {
        "task": TaskRead.model_validate(item, from_attributes=True),
        "input_revision": owner.input_revision,
        "total_hours": total_hours(list_tasks(db, owner)),
    }


@router.delete("/tasks/{task_id}", status_code=204)
def remove_task(
    task_id: UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    owner = owner_from_request(request, db, for_update=True)
    require_revision(owner, revision(if_match))
    delete_task(db, owner, task_id)
    return response


@router.put("/tasks", response_model=TaskList)
def put_tasks(
    data: TaskCollection,
    request: Request,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    owner = owner_from_request(request, db, for_update=True)
    require_revision(owner, revision(if_match))
    replace_tasks(db, owner, data.tasks)
    return task_list_response(db, owner)


@router.post("/imports", status_code=201)
async def upload_import(
    request: Request, db: Session = Depends(get_db), file: UploadFile = File(...)
):
    owner = owner_from_request(request, db)
    try:
        content = await file.read(get_settings().max_upload_bytes + 1)
        parsed = parse_upload(file.filename or "upload", content)
    finally:
        await file.close()
    preview = ImportPreview(
        session_id=owner.id,
        expires_at=now_utc() + timedelta(minutes=get_settings().import_preview_ttl_minutes),
        filename=(file.filename or "upload")[:255],
        sheet_names=parsed["sheet_names"],
        selected_sheet=parsed["sheet_names"][0] if len(parsed["sheet_names"]) == 1 else None,
        headers=[],
        rows=[],
        sheets_data=parsed["sheets"],
        mapping={},
        row_errors=[],
        notices=[],
        status="pending",
    )
    if preview.selected_sheet:
        sheet = parsed["sheets"][preview.selected_sheet]
        preview.headers = sheet["headers"]
        preview.rows = sheet["rows"]
        preview.mapping = sheet.get("mapping", {})
        preview.notices = sheet.get("notices", [])
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return import_view(preview)


def get_import(db: Session, owner: AnonymousSession, import_id: UUID) -> ImportPreview:
    preview = db.scalar(
        select(ImportPreview).where(
            ImportPreview.id == import_id, ImportPreview.session_id == owner.id
        )
    )
    if preview is None:
        raise DomainError("import_not_found", "Import preview not found.", 404)
    if preview.expires_at <= now_utc():
        raise DomainError(
            "import_expired", "This import preview expired. Upload the file again.", 410
        )
    return preview


def import_view(p: ImportPreview):
    return {
        "id": str(p.id),
        "filename": p.filename,
        "sheet_names": p.sheet_names,
        "selected_sheet": p.selected_sheet,
        "headers": p.headers,
        "preview_rows": p.rows[:5],
        "mapping": p.mapping,
        "notices": p.notices,
        "row_errors": p.row_errors,
        "status": p.status,
        "requires_sheet_selection": len(p.sheet_names) > 1 and not p.selected_sheet,
    }


@router.get("/imports/{import_id}")
def retrieve_import(import_id: UUID, request: Request, db: Session = Depends(get_db)):
    return import_view(get_import(db, owner_from_request(request, db), import_id))


@router.put("/imports/{import_id}/mapping")
def update_import_mapping(
    import_id: UUID, data: ImportMappingUpdate, request: Request, db: Session = Depends(get_db)
):
    owner = owner_from_request(request, db)
    preview = get_import(db, owner, import_id)
    if preview.status == "confirmed":
        raise DomainError("import_already_confirmed", "This import has already been applied.", 409)
    sheet_name = data.sheet_name or preview.selected_sheet
    if sheet_name not in preview.sheets_data:
        raise DomainError("sheet_required", "Choose a worksheet from the uploaded workbook.", 422)
    sheet = preview.sheets_data[sheet_name]
    mapping = data.mapping if data.mapping is not None else suggest_mappings(sheet["headers"])[0]
    if len(set(mapping.values())) != len(mapping):
        raise DomainError("mapping_conflict", "A column can map to only one task field.", 422)
    preview.selected_sheet = sheet_name
    preview.headers = sheet["headers"]
    preview.rows = sheet["rows"]
    preview.mapping = mapping
    preview.notices = sheet["notices"]
    if "task_description" not in mapping or "hours_per_week" not in mapping:
        preview.notices.append("Map task description and weekly hours before confirming.")
    preview.status = "reviewing"
    db.commit()
    return import_view(preview)


@router.post("/imports/{import_id}/confirm")
def confirm_import(
    import_id: UUID,
    data: ImportConfirmation,
    request: Request,
    db: Session = Depends(get_db),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    owner = owner_from_request(request, db, for_update=True)
    require_revision(owner, revision(if_match))
    preview = get_import(db, owner, import_id)
    if preview.status == "confirmed":
        raise DomainError("import_already_confirmed", "This import has already been applied.", 409)
    mode = data.mode
    if not preview.selected_sheet:
        raise DomainError("sheet_required", "Choose a worksheet before confirming.", 422)
    accepted, errors = validate_mapped_rows(preview.headers, preview.rows, preview.mapping)
    preview.row_errors = errors
    if not accepted:
        db.commit()
        raise DomainError(
            "no_valid_rows", "No valid task rows can be imported.", 422, {"row_errors": errors}
        )
    from app.tasks.schemas import TaskCollection

    existing = list_tasks(db, owner)
    old = (
        [TaskInput.model_validate(t, from_attributes=True) for t in existing]
        if mode == "append"
        else []
    )
    incoming = [TaskInput.model_validate(item) for item in accepted]
    try:
        TaskCollection(tasks=old + incoming)
    except Exception as exc:
        raise DomainError(
            "task_validation",
            "The import would exceed task or weekly-hour limits.",
            422,
            {"errors": exc.errors()},
        ) from exc
    if mode == "replace":
        db.execute(delete(TaskRecord).where(TaskRecord.session_id == owner.id))
    db.add_all([TaskRecord(session_id=owner.id, **item.model_dump()) for item in incoming])
    owner.input_revision += 1
    preview.status = "confirmed"
    db.commit()
    result = task_list_response(db, owner)
    return {
        "message": "Tasks imported. Free-text descriptions may still contain identifying details.",
        "mode": mode,
        "row_errors": errors,
        "tasks": result.tasks,
        "input_revision": result.input_revision,
        "total_hours": result.total_hours,
    }


@router.delete("/imports/{import_id}", status_code=204)
def discard_import(
    import_id: UUID, request: Request, response: Response, db: Session = Depends(get_db)
):
    owner = owner_from_request(request, db)
    preview = get_import(db, owner, import_id)
    db.delete(preview)
    db.commit()
    return response


@router.post("/analyses", status_code=501)
def start_analysis(request: Request, db: Session = Depends(get_db)):
    return request_analysis(
        db, owner_from_request(request, db, for_update=True), request.app.state.engine_registry
    )


@router.get("/analyses/{analysis_id}")
def analysis_status(analysis_id: UUID, request: Request, db: Session = Depends(get_db)):
    owner = owner_from_request(request, db)
    item = db.scalar(
        select(AnalysisRequest).where(
            AnalysisRequest.id == analysis_id, AnalysisRequest.session_id == owner.id
        )
    )
    if item is None:
        raise DomainError("analysis_not_found", "Analysis request not found.", 404)
    return {
        "id": str(item.id),
        "status": item.status,
        "input_revision": item.input_revision,
        "missing_capabilities": item.missing_capabilities,
        "created_at": item.created_at,
        "completed_at": item.completed_at,
    }


@router.post("/scenarios", status_code=501)
def request_scenario(request: Request, db: Session = Depends(get_db)):
    owner_from_request(request, db)
    raise DomainError(
        "scenario_unavailable",
        "Scenario intelligence has not been implemented.",
        501,
        {"missing_capabilities": ["scenario_intelligence"]},
    )


@router.post("/plans", status_code=501)
def request_plan(request: Request, db: Session = Depends(get_db)):
    owner_from_request(request, db)
    raise DomainError(
        "plan_unavailable",
        "Plan generation has not been implemented.",
        501,
        {"missing_capabilities": ["plan_generation", "skill_recommendations"]},
    )


@router.get("/exports/json")
def json_export(request: Request, db: Session = Depends(get_db)):
    owner = owner_from_request(request, db)
    return make_json_export(db, owner)


@router.get("/exports/pdf")
def pdf_export(request: Request, db: Session = Depends(get_db)):
    owner = owner_from_request(request, db)
    content = make_pdf_export(db, owner)
    return RawResponse(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=jobshift-task-inventory.pdf"},
    )


@router.get("/reference/artifacts")
def reference_artifacts(request: Request, db: Session = Depends(get_db)):
    owner_from_request(request, db)
    items = db.scalars(
        select(ReferenceArtifact).order_by(ReferenceArtifact.source, ReferenceArtifact.release)
    )
    return {
        "artifacts": [
            {
                "source": x.source,
                "release": x.release,
                "artifact_name": x.artifact_name,
                "source_url": x.source_url,
                "checksum": x.checksum,
                "license": x.license,
                "import_status": x.import_status,
            }
            for x in items
        ]
    }
