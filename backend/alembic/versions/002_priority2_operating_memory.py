"""Priority 2 operating memory tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_operating_profiles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("business_model", sa.String(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("value_proposition", sa.Text(), nullable=True),
        sa.Column("market_positioning", sa.Text(), nullable=True),
        sa.Column("products_services", sa.JSON(), nullable=True),
        sa.Column("competitors", sa.JSON(), nullable=True),
        sa.Column("customer_segments", sa.JSON(), nullable=True),
        sa.Column("revenue_model", sa.Text(), nullable=True),
        sa.Column("pricing", sa.JSON(), nullable=True),
        sa.Column("team_structure", sa.JSON(), nullable=True),
        sa.Column("team_size", sa.String(), nullable=True),
        sa.Column("budget", sa.String(), nullable=True),
        sa.Column("geography", sa.String(), nullable=True),
        sa.Column("tech_stack", sa.Text(), nullable=True),
        sa.Column("marketing_strategy", sa.Text(), nullable=True),
        sa.Column("sales_strategy", sa.Text(), nullable=True),
        sa.Column("marketing_assets", sa.JSON(), nullable=True),
        sa.Column("technical_assets", sa.JSON(), nullable=True),
        sa.Column("current_goals", sa.JSON(), nullable=True),
        sa.Column("current_problems", sa.JSON(), nullable=True),
        sa.Column("product_roadmap", sa.JSON(), nullable=True),
        sa.Column("risks", sa.JSON(), nullable=True),
        sa.Column("brand_voice", sa.Text(), nullable=True),
        sa.Column("growth_stage", sa.String(), nullable=True),
        sa.Column("operating_mode", sa.String(), nullable=True),
        sa.Column("discovery_confidence", sa.Float(), nullable=True),
        sa.Column("synced_from_blueprint_version", sa.Integer(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("ix_company_operating_profiles_project_id", "company_operating_profiles", ["project_id"])

    op.create_table(
        "decision_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("decision_type", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_agent", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("related_task_id", sa.String(), nullable=True),
        sa.Column("related_session_id", sa.String(), nullable=True),
        sa.Column("related_deliverable_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_deliverable_id"], ["deliverables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_logs_project_id", "decision_logs", ["project_id"])
    op.create_index("ix_decision_logs_created_at", "decision_logs", ["created_at"])

    op.create_table(
        "memory_update_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("trigger", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("field_updates", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_memory_update_events_project_id", "memory_update_events", ["project_id"])
    op.create_index("ix_memory_update_events_created_at", "memory_update_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("memory_update_events")
    op.drop_table("decision_logs")
    op.drop_table("company_operating_profiles")
