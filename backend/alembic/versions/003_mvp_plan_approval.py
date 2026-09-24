"""Create Plan, Deliverable, Approval models for MVP phase.

Revision ID: 003_mvp_plan_approval
Revises: 002_priority2_operating_memory
Create Date: 2026-06-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_mvp_plan_approval'
down_revision = '002'
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return sa.inspect(bind).has_table(name)


def _column_exists(bind, table: str, column: str) -> bool:
    if not _table_exists(bind, table):
        return False
    return column in [c["name"] for c in sa.inspect(bind).get_columns(table)]


def upgrade() -> None:
    bind = op.get_bind()

    # NOTE: migration 001 runs Base.metadata.create_all() against the current models,
    # which already includes these tables/columns. Guard against "already exists" so
    # this migration is safe to run both on a fresh DB and on one where 001 created everything.
    tables_already_exist = _table_exists(bind, "plans")

    if tables_already_exist:
        return

    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('milestones', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('owner_agent', sa.String(), nullable=True),
        sa.Column('plan_type', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('generated_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_plans_project_id', 'project_id')
    )

    # Create deliverables table (architecture v2 version)
    op.create_table(
        'deliverables',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=True),
        sa.Column('objective_id', sa.String(), nullable=True),
        sa.Column('plan_id', sa.String(), nullable=True),
        sa.Column('deliverable_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('content_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('storage_backend', sa.String(), nullable=False, server_default='inline'),
        sa.Column('storage_path', sa.String(), nullable=True),
        sa.Column('mime_type', sa.String(), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('checksum_sha256', sa.String(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_deliverable_id', sa.String(), nullable=True),
        sa.Column('created_by_agent', sa.String(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by_user_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['objective_id'], ['objectives.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_deliverable_id'], ['deliverables.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_deliverables_project_id', 'project_id'),
        sa.Index('ix_deliverables_task_id', 'task_id')
    )

    # Create approvals table
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('requested_by', sa.String(), nullable=True),
        sa.Column('requested_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('approver_id', sa.String(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decision_reason', sa.Text(), nullable=True),
        sa.Column('history', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_approvals_project_id', 'project_id')
    )

    # Add columns to tasks table
    op.add_column('tasks', sa.Column('plan_id', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('stage', sa.String(), nullable=False, server_default='todo'))
    op.add_column('tasks', sa.Column('review_required', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('tasks', sa.Column('reviewer_id', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('approval_status', sa.String(), nullable=False, server_default='unapproved'))
    op.add_column('tasks', sa.Column('approval_history', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column('tasks', sa.Column('estimated_hours', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('time_spent_hours', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('tasks', sa.Column('due_date', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('review_requested_at', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('blocked_reason', sa.Text(), nullable=True))
    op.add_column('tasks', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('tasks', sa.Column('attempt_logs', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column('tasks', sa.Column('external_url', sa.String(), nullable=True))

    # Create foreign key for plan_id in tasks
    op.create_foreign_key('fk_tasks_plan_id', 'tasks', 'plans', ['plan_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_tasks_plan_id', 'tasks', ['plan_id'])

    # Add deliverables relationship to projects
    # (This is just metadata, no schema change needed)


def downgrade() -> None:
    # Drop foreign key and index
    op.drop_index('ix_tasks_plan_id', table_name='tasks')
    op.drop_constraint('fk_tasks_plan_id', 'tasks', type_='foreignkey')

    # Drop columns from tasks
    op.drop_column('tasks', 'external_url')
    op.drop_column('tasks', 'attempt_logs')
    op.drop_column('tasks', 'retry_count')
    op.drop_column('tasks', 'blocked_reason')
    op.drop_column('tasks', 'review_requested_at')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'time_spent_hours')
    op.drop_column('tasks', 'estimated_hours')
    op.drop_column('tasks', 'approval_history')
    op.drop_column('tasks', 'approval_status')
    op.drop_column('tasks', 'reviewer_id')
    op.drop_column('tasks', 'review_required')
    op.drop_column('tasks', 'stage')
    op.drop_column('tasks', 'plan_id')

    # Drop tables
    op.drop_table('approvals')
    op.drop_table('deliverables')
    op.drop_table('plans')
