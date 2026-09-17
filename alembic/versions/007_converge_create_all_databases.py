"""Converge databases built by the old ``Base.metadata.create_all`` path

Revision ID: 007
Revises: 006
Create Date: 2026-09-16

Before this revision the pipeline created tables with ``create_all`` while the
web container ran ``alembic upgrade head``, so an existing database may have
been shaped by either. This migration inspects the live schema and only alters
what differs from the shape 001-006 produce:

* ``json`` columns that 001 creates as ``jsonb`` are converted in place
* the columns added by 002 and 004-006 and the tables added by 003 are
  created if missing (``create_all`` never adds columns to existing tables)
* ``raw_posts.reddit_id`` gets the 001 shape: unique constraint
  ``raw_posts_reddit_id_key`` plus non-unique index ``ix_raw_posts_reddit_id``
  (``create_all`` made a single unique index instead)

On a database that came through 001-006 every step is a no-op.

To bring a ``create_all`` database (one with no ``alembic_version`` table) to
head, stamp it and upgrade; see alembic/README.md::

    alembic stamp 006
    alembic upgrade head
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columns that 001 creates as JSONB but create_all created as JSON.
JSONB_COLUMNS = {
    "raw_posts": ["top_comments"],
    "pipeline_runs": ["config", "methodology"],
    "topics": ["keywords", "representative_docs"],
}

# Columns added by 002 and 004-006 that create_all never added to a table
# that already existed.
ADDED_COLUMNS = {
    "topics": [
        sa.Column("personas", sa.JSON(), nullable=True),
        sa.Column("failed_solutions", sa.JSON(), nullable=True),
        sa.Column("pain_points", sa.JSON(), nullable=True),
        sa.Column("build_legends_angle", sa.Text(), nullable=True),
    ],
    "label_stories": [
        sa.Column("micro_personas", sa.JSON(), nullable=True),
        sa.Column("source_post_ids", sa.JSON(), nullable=True),
        sa.Column("visceral_quotes", sa.JSON(), nullable=True),
    ],
}


def _ensure_labels_tables(inspector) -> None:
    """Create the 003 tables if they are missing (same definitions as 003)."""
    if not inspector.has_table("parent_labels"):
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

    if not inspector.has_table("label_stories"):
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

    if not inspector.has_table("post_labels"):
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


def _ensure_added_columns(inspector) -> None:
    for table, columns in ADDED_COLUMNS.items():
        existing = {c["name"] for c in inspector.get_columns(table)}
        for column in columns:
            if column.name not in existing:
                op.add_column(table, column)


def _convert_json_to_jsonb(inspector) -> None:
    for table, columns in JSONB_COLUMNS.items():
        types = {c["name"]: c["type"] for c in inspector.get_columns(table)}
        for column in columns:
            if isinstance(types[column], postgresql.JSONB):
                continue
            op.alter_column(
                table,
                column,
                type_=postgresql.JSONB(),
                existing_type=sa.JSON(),
                postgresql_using=f"{column}::jsonb",
            )


def _fix_reddit_id_uniqueness(inspector) -> None:
    uniques = {u["name"] for u in inspector.get_unique_constraints("raw_posts")}
    indexes = {i["name"]: i for i in inspector.get_indexes("raw_posts")}

    if "raw_posts_reddit_id_key" not in uniques:
        op.create_unique_constraint("raw_posts_reddit_id_key", "raw_posts", ["reddit_id"])

    index = indexes.get("ix_raw_posts_reddit_id")
    if index is not None and index["unique"]:
        op.drop_index("ix_raw_posts_reddit_id", table_name="raw_posts")
        index = None
    if index is None:
        op.create_index("ix_raw_posts_reddit_id", "raw_posts", ["reddit_id"])


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Re-inspect after each phase so later phases see what earlier ones created.
    _ensure_labels_tables(sa.inspect(bind))
    _ensure_added_columns(sa.inspect(bind))
    _convert_json_to_jsonb(sa.inspect(bind))
    _fix_reddit_id_uniqueness(sa.inspect(bind))


def downgrade() -> None:
    # The converged schema is exactly what 001-006 produce on a fresh
    # database, so there is nothing to undo.
    pass
