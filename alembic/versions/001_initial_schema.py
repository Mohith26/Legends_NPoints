"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reddit_id", sa.String(20), nullable=False),
        sa.Column("subreddit", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("top_comments", postgresql.JSONB(), nullable=True),
        sa.Column("upvotes", sa.Integer(), server_default="0"),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(100), nullable=True),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reddit_id"),
    )
    op.create_index("ix_raw_posts_reddit_id", "raw_posts", ["reddit_id"])
    op.create_index("ix_raw_posts_subreddit", "raw_posts", ["subreddit"])

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("methodology", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("topic_index", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=False),
        sa.Column("gpt_label", sa.String(200), nullable=True),
        sa.Column("gpt_summary", sa.Text(), nullable=True),
        sa.Column("post_count", sa.Integer(), server_default="0"),
        sa.Column("avg_upvotes", sa.Float(), server_default="0.0"),
        sa.Column("representative_docs", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_run_id", "topic_index", name="uq_run_topic_index"),
    )
    op.create_index("ix_topics_pipeline_run_id", "topics", ["pipeline_run_id"])

    op.create_table(
        "post_topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_post_id", sa.Integer(), sa.ForeignKey("raw_posts.id"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id"), nullable=False),
        sa.Column("pipeline_run_id", sa.Integer(), sa.ForeignKey("pipeline_runs.id"), nullable=False),
        sa.Column("probability", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_post_topics_raw_post_id", "post_topics", ["raw_post_id"])
    op.create_index("ix_post_topics_topic_id", "post_topics", ["topic_id"])
    op.create_index("ix_post_topics_pipeline_run_id", "post_topics", ["pipeline_run_id"])


def downgrade() -> None:
    op.drop_table("post_topics")
    op.drop_table("topics")
    op.drop_table("pipeline_runs")
    op.drop_table("raw_posts")
