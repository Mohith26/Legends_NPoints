"""Add Build Legends analysis columns to topics

Revision ID: 002
Revises: 001
Create Date: 2026-02-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("personas", sa.JSON(), nullable=True))
    op.add_column("topics", sa.Column("failed_solutions", sa.JSON(), nullable=True))
    op.add_column("topics", sa.Column("pain_points", sa.JSON(), nullable=True))
    op.add_column("topics", sa.Column("build_legends_angle", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("topics", "build_legends_angle")
    op.drop_column("topics", "pain_points")
    op.drop_column("topics", "failed_solutions")
    op.drop_column("topics", "personas")
