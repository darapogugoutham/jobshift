"""Create anonymous sessions, task inventory, imports, analysis requests, and reference metadata."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("credential_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_sessions_credential_hash", "sessions", ["credential_hash"], unique=True)
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_description", sa.Text(), nullable=False),
        sa.Column("hours_per_week", sa.Float(), nullable=False),
        sa.Column("frequency", sa.String(20)),
        sa.Column("tools_used", postgresql.JSONB()),
        sa.Column("skills_used", postgresql.JSONB()),
        sa.Column("involves_people", sa.Boolean()),
        sa.Column("physical_presence_required", sa.Boolean()),
        sa.Column("decision_authority", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_tasks_session_id", "tasks", ["session_id"])
    op.create_table(
        "import_previews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sheet_names", postgresql.JSONB(), nullable=False),
        sa.Column("selected_sheet", sa.String(255)),
        sa.Column("headers", postgresql.JSONB(), nullable=False),
        sa.Column("sheets_data", postgresql.JSONB(), nullable=False),
        sa.Column("rows", postgresql.JSONB(), nullable=False),
        sa.Column("mapping", postgresql.JSONB(), nullable=False),
        sa.Column("row_errors", postgresql.JSONB(), nullable=False),
        sa.Column("notices", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
    )
    op.create_index("ix_import_previews_session_id", "import_previews", ["session_id"])
    op.create_index("ix_import_previews_expires_at", "import_previews", ["expires_at"])
    op.create_table(
        "analysis_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("missing_capabilities", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_analysis_requests_session_id", "analysis_requests", ["session_id"])
    op.create_table(
        "reference_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("release", sa.String(120), nullable=False),
        sa.Column("artifact_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("checksum", sa.String(128)),
        sa.Column("license", sa.String(255)),
        sa.Column("import_status", sa.String(30), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade():
    op.drop_table("reference_artifacts")
    op.drop_index("ix_analysis_requests_session_id", table_name="analysis_requests")
    op.drop_table("analysis_requests")
    op.drop_index("ix_import_previews_expires_at", table_name="import_previews")
    op.drop_index("ix_import_previews_session_id", table_name="import_previews")
    op.drop_table("import_previews")
    op.drop_index("ix_tasks_session_id", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_credential_hash", table_name="sessions")
    op.drop_table("sessions")
