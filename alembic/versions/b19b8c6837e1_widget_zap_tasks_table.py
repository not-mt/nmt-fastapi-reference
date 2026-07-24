"""widget_zap_tasks_table

Create widget_zap_tasks table and add last_task_uuid and
last_task_status to widgets.

Revision ID: b19b8c6837e1
Revises: cb1902fe9e48
Create Date: 2026-06-20 09:41:19.295646

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b19b8c6837e1"
down_revision: Union[str, None] = "cb1902fe9e48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "widgets",
        sa.Column("last_task_uuid", sa.String(36), nullable=True, default=None),
    )
    op.add_column(
        "widgets",
        sa.Column("last_task_status", sa.String(16), nullable=True, default=None),
    )
    op.create_table(
        "widget_zap_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("widget_id", sa.Integer(), nullable=False),
        sa.Column("task_uuid", sa.String(36), nullable=False),
        sa.Column("state", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runtime", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["widget_id"],
            ["widgets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_widget_zap_tasks_widget_id_created_at",
        "widget_zap_tasks",
        ["widget_id", "created_at"],
    )
    op.create_index(
        "ix_widget_zap_tasks_task_uuid",
        "widget_zap_tasks",
        ["task_uuid"],
    )


def downgrade() -> None:
    op.drop_index("ix_widget_zap_tasks_task_uuid", table_name="widget_zap_tasks")
    op.drop_index(
        "ix_widget_zap_tasks_widget_id_created_at", table_name="widget_zap_tasks"
    )
    op.drop_table("widget_zap_tasks")
    op.drop_column("widgets", "last_task_status")
    op.drop_column("widgets", "last_task_uuid")
