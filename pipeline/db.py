from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base, LabelStory, ParentLabel, PipelineRun, PostLabel, PostTopic, RawPost, Topic


def get_engine(database_url: str):
    return create_engine(database_url)


def get_session(database_url: str) -> Session:
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def ensure_tables(database_url: str):
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)


def upsert_raw_post(session: Session, post_data: dict) -> int | None:
    """Insert a post, skip if reddit_id already exists. Returns post id or None."""
    existing = session.query(RawPost).filter_by(reddit_id=post_data["reddit_id"]).first()
    if existing:
        return existing.id

    post = RawPost(**post_data)
    session.add(post)
    session.flush()
    return post.id


def create_pipeline_run(session: Session, config_dict: dict | None = None) -> PipelineRun:
    run = PipelineRun(
        status="running",
        config=config_dict,
    )
    session.add(run)
    session.commit()
    return run


def update_pipeline_run(
    session: Session,
    run_id: int,
    status: str | None = None,
    methodology: dict | None = None,
    error_message: str | None = None,
):
    run = session.query(PipelineRun).get(run_id)
    if status:
        run.status = status
    if methodology:
        run.methodology = methodology
    if error_message:
        run.error_message = error_message
    if status in ("completed", "failed"):
        run.completed_at = datetime.now(timezone.utc)
    session.commit()


def store_topic(session: Session, topic_data: dict) -> Topic:
    topic = Topic(**topic_data)
    session.add(topic)
    session.flush()
    return topic


def store_post_topic(session: Session, post_topic_data: dict):
    pt = PostTopic(**post_topic_data)
    session.add(pt)


def get_all_posts(session: Session) -> list[RawPost]:
    return session.query(RawPost).all()


def store_label(session: Session, label_data: dict) -> ParentLabel:
    label = ParentLabel(**label_data)
    session.add(label)
    session.flush()
    return label


def store_label_story(session: Session, story_data: dict) -> LabelStory:
    story = LabelStory(**story_data)
    session.add(story)
    session.flush()
    return story


def store_post_label(session: Session, post_label_data: dict):
    pl = PostLabel(**post_label_data)
    session.add(pl)
