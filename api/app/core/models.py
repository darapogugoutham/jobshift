from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AnonymousSession(Base):
    __tablename__ = "sessions"
    id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    credential_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    input_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks = relationship("TaskRecord", cascade="all, delete-orphan", passive_deletes=True)
    imports = relationship("ImportPreview", cascade="all, delete-orphan", passive_deletes=True)
    analyses = relationship("AnalysisRequest", cascade="all, delete-orphan", passive_deletes=True)


class TaskRecord(Base):
    __tablename__ = "tasks"
    id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    task_description: Mapped[str] = mapped_column(Text)
    hours_per_week: Mapped[float] = mapped_column(Float)
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tools_used: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    skills_used: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    involves_people: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    physical_presence_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    decision_authority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ImportPreview(Base):
    __tablename__ = "import_previews"
    id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    sheet_names: Mapped[list[str]] = mapped_column(JSONB)
    selected_sheet: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headers: Mapped[list[str]] = mapped_column(JSONB)
    sheets_data: Mapped[dict] = mapped_column(JSONB)
    rows: Mapped[list[list[str]]] = mapped_column(JSONB)
    mapping: Mapped[dict] = mapped_column(JSONB, default=dict)
    row_errors: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    notices: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(24), default="pending")


class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"
    id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[object] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), index=True
    )
    input_revision: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[list[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    missing_capabilities: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReferenceArtifact(Base):
    __tablename__ = "reference_artifacts"
    id: Mapped[object] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(120))
    release: Mapped[str] = mapped_column(String(120))
    artifact_name: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    import_status: Mapped[str] = mapped_column(String(30), default="not_imported")
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
