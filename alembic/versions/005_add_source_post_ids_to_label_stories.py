"""Add source_post_ids column to label_stories

Revision ID: 005
Revises: 004
Create Date: 2026-03-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("label_stories", sa.Column("source_post_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("label_stories", "source_post_ids")
