"""Add visceral_quotes column to label_stories

Revision ID: 006
Revises: 005
Create Date: 2026-03-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("label_stories", sa.Column("visceral_quotes", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("label_stories", "visceral_quotes")
