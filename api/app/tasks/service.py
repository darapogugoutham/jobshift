from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.models import AnonymousSession, TaskRecord
from app.tasks.schemas import TaskCollection, TaskInput


def task_data(item: TaskInput) -> dict:
    return item.model_dump()


def list_tasks(db: Session, owner: AnonymousSession) -> list[TaskRecord]:
    return list(
        db.scalars(
            select(TaskRecord)
            .where(TaskRecord.session_id == owner.id)
            .order_by(TaskRecord.created_at, TaskRecord.id)
        )
    )


def total_hours(tasks: list[TaskRecord]) -> float:
    return round(sum(task.hours_per_week for task in tasks), 4)


def ensure_total(tasks: list[TaskInput]) -> None:
    TaskCollection(tasks=tasks)


def mutate_revision(owner: AnonymousSession) -> None:
    owner.input_revision += 1


def create_task(db: Session, owner: AnonymousSession, item: TaskInput) -> TaskRecord:
    current = list_tasks(db, owner)
    if len(current) >= 60:
        raise DomainError("task_limit", "A session can contain at most 60 tasks.", 422)
    ensure_total([TaskInput.model_validate(t, from_attributes=True) for t in current] + [item])
    record = TaskRecord(session_id=owner.id, **task_data(item))
    db.add(record)
    mutate_revision(owner)
    db.commit()
    db.refresh(record)
    return record


def replace_tasks(db: Session, owner: AnonymousSession, items: list[TaskInput]) -> list[TaskRecord]:
    ensure_total(items)
    db.execute(delete(TaskRecord).where(TaskRecord.session_id == owner.id))
    records = [TaskRecord(session_id=owner.id, **task_data(item)) for item in items]
    db.add_all(records)
    mutate_revision(owner)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


def update_task(db: Session, owner: AnonymousSession, task_id: UUID, item: TaskInput) -> TaskRecord:
    records = list_tasks(db, owner)
    current = next((task for task in records if task.id == task_id), None)
    if current is None:
        raise DomainError("task_not_found", "Task not found in this session.", 404)
    if item.id != task_id:
        raise DomainError("task_id_mismatch", "The task ID cannot change during an update.", 422)
    inputs = [
        TaskInput.model_validate(t, from_attributes=True) if t.id != task_id else item
        for t in records
    ]
    ensure_total(inputs)
    for key, value in task_data(item).items():
        setattr(current, key, value)
    mutate_revision(owner)
    db.commit()
    db.refresh(current)
    return current


def delete_task(db: Session, owner: AnonymousSession, task_id: UUID) -> None:
    result = db.execute(
        delete(TaskRecord).where(TaskRecord.session_id == owner.id, TaskRecord.id == task_id)
    )
    if result.rowcount == 0:
        raise DomainError("task_not_found", "Task not found in this session.", 404)
    mutate_revision(owner)
    db.commit()
