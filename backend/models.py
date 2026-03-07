from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class RawPost(Base):
    __tablename__ = "raw_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reddit_id = Column(String(20), unique=True, nullable=False, index=True)
    subreddit = Column(String(100), nullable=False, index=True)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    top_comments = Column(JSON, nullable=True)
    upvotes = Column(Integer, default=0)
    url = Column(Text, nullable=True)
    author = Column(String(100), nullable=True)
    created_utc = Column(DateTime(timezone=True), nullable=True)
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    post_topics = relationship("PostTopic", back_populates="post")
    post_labels = relationship("PostLabel", back_populates="post")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSON, nullable=True)
    methodology = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    topics = relationship("Topic", back_populates="pipeline_run")
    labels = relationship("ParentLabel", back_populates="pipeline_run")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    topic_index = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    keywords = Column(JSON, nullable=False)
    gpt_label = Column(String(200), nullable=True)
    gpt_summary = Column(Text, nullable=True)
    post_count = Column(Integer, default=0)
    avg_upvotes = Column(Float, default=0.0)
    representative_docs = Column(JSON, nullable=True)
    personas = Column(JSON, nullable=True)
    failed_solutions = Column(JSON, nullable=True)
    pain_points = Column(JSON, nullable=True)
    build_legends_angle = Column(Text, nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="topics")
    post_topics = relationship("PostTopic", back_populates="topic")

    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "topic_index", name="uq_run_topic_index"),
    )


class PostTopic(Base):
    __tablename__ = "post_topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_post_id = Column(Integer, ForeignKey("raw_posts.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    probability = Column(Float, nullable=True)

    post = relationship("RawPost", back_populates="post_topics")
    topic = relationship("Topic", back_populates="post_topics")


class ParentLabel(Base):
    __tablename__ = "parent_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    post_count = Column(Integer, default=0)
    discovery_method = Column(String(20), nullable=False, default="regex")  # regex | gpt
    example_phrases = Column(JSON, nullable=True)
    marketing_insights = Column(JSON, nullable=True)

    pipeline_run = relationship("PipelineRun", back_populates="labels")
    stories = relationship("LabelStory", back_populates="label", cascade="all, delete-orphan")
    post_labels = relationship("PostLabel", back_populates="label", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "slug", name="uq_run_label_slug"),
    )


class LabelStory(Base):
    __tablename__ = "label_stories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label_id = Column(Integer, ForeignKey("parent_labels.id"), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    summary = Column(Text, nullable=True)
    post_count = Column(Integer, default=0)
    pain_points = Column(JSON, nullable=True)
    failed_solutions = Column(JSON, nullable=True)
    build_legends_angle = Column(Text, nullable=True)
    representative_quotes = Column(JSON, nullable=True)
    micro_personas = Column(JSON, nullable=True)
    source_post_ids = Column(JSON, nullable=True)

    label = relationship("ParentLabel", back_populates="stories")


class PostLabel(Base):
    __tablename__ = "post_labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_post_id = Column(Integer, ForeignKey("raw_posts.id"), nullable=False, index=True)
    label_id = Column(Integer, ForeignKey("parent_labels.id"), nullable=False, index=True)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    matched_phrase = Column(Text, nullable=True)

    post = relationship("RawPost", back_populates="post_labels")
    label = relationship("ParentLabel", back_populates="post_labels")
