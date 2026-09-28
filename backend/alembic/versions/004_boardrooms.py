"""Add boardrooms table (universal AI Boardroom workspaces).

Revision ID: 004_boardrooms
Revises: 003_mvp_plan_approval
"""
from alembic import op
import sqlalchemy as sa

revision = "004_boardrooms"
down_revision = "003_mvp_plan_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "boardrooms",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("analysis", sa.JSON(), nullable=True),
        sa.Column("board", sa.JSON(), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("messages", sa.JSON(), nullable=True),
        sa.Column("decisions", sa.JSON(), nullable=True),
        sa.Column("tasks", sa.JSON(), nullable=True),
        sa.Column("outputs", sa.JSON(), nullable=True),
        sa.Column("history", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_boardrooms_user_id", "boardrooms", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_boardrooms_user_id", table_name="boardrooms")
    op.drop_table("boardrooms")
