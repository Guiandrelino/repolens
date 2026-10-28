"""Initial schema."""

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("github_id", sa.String(80), nullable=False, unique=True),
        sa.Column("login", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=False),
    )
    op.create_table(
        "analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("repo_url", sa.String(300), nullable=False),
        sa.Column("focus", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("commit_sha", sa.String(40)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_analyses_user_id", "analyses", ["user_id"])
    op.create_index("ix_analyses_status", "analyses", ["status"])
    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_findings_analysis_id", "findings", ["analysis_id"])
    op.create_table(
        "analysis_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_id", sa.String(36), sa.ForeignKey("analyses.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("analysis_id", "sequence"),
    )
    op.create_index("ix_analysis_events_analysis_id", "analysis_events", ["analysis_id"])


def downgrade():
    for table in ["analysis_events", "findings", "analyses", "users"]:
        op.drop_table(table)
