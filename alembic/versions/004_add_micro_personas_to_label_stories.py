"""Add micro_personas column to label_stories

Revision ID: 004
Revises: 003
Create Date: 2026-03-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("label_stories", sa.Column("micro_personas", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("label_stories", "micro_personas")
