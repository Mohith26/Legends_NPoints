from datetime import datetime, timezone
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import LabelStory, ParentLabel, PipelineRun, PostLabel, PostTopic, RawPost, Topic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


class SchemaNotAtHead(RuntimeError):
    """The database is not at the latest Alembic revision."""


def get_engine(database_url: str):
    return create_engine(database_url)


def get_session(database_url: str) -> Session:
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def get_alembic_script() -> ScriptDirectory:
    """Return the alembic/versions script directory, regardless of the working directory."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    return ScriptDirectory.from_config(config)


def get_alembic_head() -> str:
    """Return the head revision of the alembic/versions script directory."""
    return get_alembic_script().get_current_head()


def get_database_revision(database_url: str) -> str | None:
    """Return the revision recorded in alembic_version, or None if there is none."""
    engine = get_engine(database_url)
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def require_schema_at_head(database_url: str) -> str:
    """Raise SchemaNotAtHead unless the database is at the Alembic head.

    Alembic is the only thing that creates or alters the schema; the pipeline
    never runs migrations itself because it runs from a laptop against the
    production database. Returns the head revision on success.
    """
    script = get_alembic_script()
    head = script.get_current_head()
    current = get_database_revision(database_url)
    if current == head:
        return head

    if current is None:
        detail = (
            "the database has no alembic_version table. If it was built by the old "
            "create_all path, run `alembic stamp 006` and then `alembic upgrade head` "
            "(see alembic/README.md); otherwise run `alembic upgrade head`."
        )
    elif current not in {revision.revision for revision in script.walk_revisions()}:
        detail = (
            f"the database is at revision {current}, which this checkout does not have; "
            "the checkout is behind the database. Pull the latest migrations, then retry."
        )
    else:
        detail = (
            f"the database is at revision {current}. "
            "Run `alembic upgrade head` against this database, then retry."
        )
    raise SchemaNotAtHead(f"Database schema is not at Alembic head {head}: {detail}")


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
