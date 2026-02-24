"""Add parent_labels, label_stories, post_labels tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parent_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("post_count", sa.Integer(), server_default="0"),
        sa.Column("discovery_method", sa.String(20), nullable=False, server_default="regex"),
        sa.Column("example_phrases", sa.JSON(), nullable=True),
        sa.Column("marketing_insights", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
        sa.UniqueConstraint("pipeline_run_id", "slug", name="uq_run_label_slug"),
    )
    op.create_index("ix_parent_labels_pipeline_run_id", "parent_labels", ["pipeline_run_id"])

    op.create_table(
        "label_stories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("post_count", sa.Integer(), server_default="0"),
        sa.Column("pain_points", sa.JSON(), nullable=True),
        sa.Column("failed_solutions", sa.JSON(), nullable=True),
        sa.Column("build_legends_angle", sa.Text(), nullable=True),
        sa.Column("representative_quotes", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["label_id"], ["parent_labels.id"]),
    )
    op.create_index("ix_label_stories_label_id", "label_stories", ["label_id"])

    op.create_table(
        "post_labels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_post_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=False),
        sa.Column("matched_phrase", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["raw_post_id"], ["raw_posts.id"]),
        sa.ForeignKeyConstraint(["label_id"], ["parent_labels.id"]),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_runs.id"]),
    )
    op.create_index("ix_post_labels_raw_post_id", "post_labels", ["raw_post_id"])
    op.create_index("ix_post_labels_label_id", "post_labels", ["label_id"])
    op.create_index("ix_post_labels_pipeline_run_id", "post_labels", ["pipeline_run_id"])


def downgrade() -> None:
    op.drop_table("post_labels")
    op.drop_table("label_stories")
    op.drop_table("parent_labels")
