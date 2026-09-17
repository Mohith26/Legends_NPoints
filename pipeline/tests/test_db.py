import pytest
from sqlalchemy import create_engine, text

from pipeline.db import SchemaNotAtHead, get_alembic_head, require_schema_at_head


@pytest.fixture
def sqlite_url(tmp_path):
    return f"sqlite:///{tmp_path / 'schema.db'}"


def stamp(database_url: str, revision: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        conn.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": revision})


def test_head_is_latest_migration():
    assert get_alembic_head() == "007"


def test_head_lookup_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    head = get_alembic_head()
    monkeypatch.chdir(tmp_path)
    assert get_alembic_head() == head


def test_unstamped_database_is_rejected_with_upgrade_instructions(sqlite_url):
    with pytest.raises(SchemaNotAtHead) as excinfo:
        require_schema_at_head(sqlite_url)
    message = str(excinfo.value)
    assert "no alembic_version table" in message
    assert "alembic stamp 006" in message
    assert "alembic upgrade head" in message


def test_database_behind_head_is_rejected(sqlite_url):
    stamp(sqlite_url, "006")

    with pytest.raises(SchemaNotAtHead) as excinfo:
        require_schema_at_head(sqlite_url)
    message = str(excinfo.value)
    assert "revision 006" in message
    assert "alembic upgrade head" in message


def test_database_ahead_of_checkout_is_rejected_without_upgrade_advice(sqlite_url):
    stamp(sqlite_url, "999")

    with pytest.raises(SchemaNotAtHead) as excinfo:
        require_schema_at_head(sqlite_url)
    message = str(excinfo.value)
    assert "revision 999" in message
    assert "checkout is behind the database" in message
    assert "alembic upgrade head" not in message


def test_database_at_head_is_accepted(sqlite_url):
    stamp(sqlite_url, get_alembic_head())

    assert require_schema_at_head(sqlite_url) == get_alembic_head()
