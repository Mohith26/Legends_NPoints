import logging
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import OperationalError

from backend.database import get_db
from backend.main import app
from backend.models import LabelStory, ParentLabel, PipelineRun, Topic


def _completed_run(db_session):
    run = PipelineRun(status="completed", completed_at=datetime.now(timezone.utc))
    db_session.add(run)
    db_session.flush()
    return run


def _label(db_session, **story_fields):
    run = _completed_run(db_session)
    label = ParentLabel(pipeline_run_id=run.id, name="Sleep", slug="sleep", post_count=1)
    db_session.add(label)
    db_session.flush()
    story = LabelStory(label_id=label.id, title="Bedtime battles", post_count=1, **story_fields)
    db_session.add(story)
    db_session.commit()
    return label, story


def _topic(db_session, **fields):
    run = _completed_run(db_session)
    topic = Topic(
        pipeline_run_id=run.id, topic_index=0, rank=1, keywords=[],
        post_count=1, avg_upvotes=1.0, representative_docs=[], **fields,
    )
    db_session.add(topic)
    db_session.commit()
    return topic


# ── Pagination bounds ───────────────────────────────────────────────────────

@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": 10**17}, {"page_size": 0}, {"page_size": 1000},
])
def test_topic_posts_rejects_out_of_range_pagination(client, db_session, params):
    topic = _topic(db_session)
    response = client.get(f"/api/topics/{topic.id}/posts", params=params)
    assert response.status_code == 422


@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": 10**17}, {"page_size": 0}, {"page_size": 1000},
])
def test_label_posts_rejects_out_of_range_pagination(client, db_session, params):
    label, _ = _label(db_session)
    response = client.get(f"/api/labels/{label.id}/posts", params=params)
    assert response.status_code == 422


def test_posts_accept_in_range_pagination(client, db_session):
    topic = _topic(db_session)
    response = client.get(f"/api/topics/{topic.id}/posts", params={"page": 1, "page_size": 100})
    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_posts_reject_invalid_sort(client, db_session):
    topic = _topic(db_session)
    response = client.get(f"/api/topics/{topic.id}/posts", params={"sort": "newest"})
    assert response.status_code == 422


# ── Tolerant read schemas ───────────────────────────────────────────────────

def test_label_story_missing_why_failed_still_renders(client, db_session, caplog):
    label, story = _label(
        db_session,
        failed_solutions=[{"solution": "Melatonin"}],
    )
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    solutions = response.json()["stories"][0]["failed_solutions"]
    assert solutions == [{"solution": "Melatonin", "why_failed": ""}]
    assert any(
        f"label {label.id} story {story.id}" in r.getMessage() and "why_failed" in r.getMessage()
        for r in caplog.records
    )


def test_label_story_partial_micro_persona_still_renders(client, db_session, caplog):
    label, story = _label(
        db_session,
        micro_personas=[{"child_profile": "toddler who fights sleep"}],
    )
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    persona = response.json()["stories"][0]["micro_personas"][0]
    assert persona["child_profile"] == "toddler who fights sleep"
    assert persona["trigger_scenario"] == ""
    assert any(f"label {label.id} story {story.id}" in r.getMessage() for r in caplog.records)


def test_label_story_complete_record_logs_no_warning(client, db_session, caplog):
    label, _ = _label(
        db_session,
        failed_solutions=[{"solution": "Melatonin", "why_failed": "Wore off by 2am"}],
    )
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    assert not [r for r in caplog.records if r.name == "backend.schemas"]


@pytest.mark.parametrize("failed_solutions, micro_personas", [
    ([{"solution": "Melatonin", "why_failed": None}], None),
    (None, [{"child_age": 7}]),
    (None, ["Burnt-out mom of a 4yo"]),
])
def test_label_story_wrong_typed_values_still_render(
    client, db_session, caplog, failed_solutions, micro_personas,
):
    label, story = _label(
        db_session, failed_solutions=failed_solutions, micro_personas=micro_personas,
    )
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    rendered = response.json()["stories"][0]
    if failed_solutions:
        assert rendered["failed_solutions"] == [{"solution": "Melatonin", "why_failed": ""}]
    if micro_personas:
        assert rendered["micro_personas"][0]["child_age"] == ""
    assert any(f"label {label.id} story {story.id}" in r.getMessage() for r in caplog.records)


def test_label_wrong_typed_marketing_insights_still_renders(client, db_session, caplog):
    run = _completed_run(db_session)
    label = ParentLabel(
        pipeline_run_id=run.id, name="Sleep", slug="sleep", post_count=1,
        marketing_insights={"ad_hooks": None, "target_audience_description": "Exhausted parents"},
    )
    db_session.add(label)
    db_session.commit()
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    insights = response.json()["marketing_insights"]
    assert insights["ad_hooks"] == []
    assert insights["target_audience_description"] == "Exhausted parents"
    assert any(f"label {label.id}" in r.getMessage() and "ad_hooks" in r.getMessage() for r in caplog.records)


def test_label_story_wrong_typed_quote_item_still_renders(client, db_session, caplog):
    label, story = _label(db_session, representative_quotes=["ok", None])
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    assert response.json()["stories"][0]["representative_quotes"] == ["ok"]
    assert any(
        f"label {label.id} story {story.id}" in r.getMessage() and "representative_quotes" in r.getMessage()
        for r in caplog.records
    )


def test_label_wrong_typed_example_phrase_still_renders(client, db_session):
    run = _completed_run(db_session)
    label = ParentLabel(
        pipeline_run_id=run.id, name="Sleep", slug="sleep", post_count=1,
        example_phrases=["won't sleep", None],
    )
    db_session.add(label)
    db_session.commit()
    response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    assert response.json()["example_phrases"] == ["won't sleep"]


def test_topics_list_wrong_typed_pain_point_still_renders(client, db_session, caplog):
    topic = _topic(db_session, pain_points=["p", 3])
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get("/api/topics")
    assert response.status_code == 200
    assert response.json()["topics"][0]["pain_points"] == ["p"]
    assert any(f"topic {topic.id}" in r.getMessage() and "pain_points" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("field, stored", [
    ("failed_solutions", "None tried"),
    ("micro_personas", {"label": "Burnt-out mom"}),
])
def test_label_story_non_list_container_yields_no_records(client, db_session, caplog, field, stored):
    label, story = _label(db_session, **{field: stored})
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/labels/{label.id}")
    assert response.status_code == 200
    assert response.json()["stories"][0][field] is None
    warnings = [r for r in caplog.records if r.name == "backend.schemas"]
    assert len(warnings) == 1
    assert f"label {label.id} story {story.id}" in warnings[0].getMessage()
    assert field in warnings[0].getMessage()


def test_topic_non_list_container_yields_no_records(client, db_session, caplog):
    topic = _topic(db_session, personas="Exhausted new parent")
    with caplog.at_level(logging.WARNING, logger="backend.schemas"):
        response = client.get(f"/api/topics/{topic.id}")
    assert response.status_code == 200
    assert response.json()["personas"] == []
    assert [r.getMessage() for r in caplog.records if r.name == "backend.schemas"] == [
        f"topic {topic.id}: stored personas is 'Exhausted new parent', not a list; ignoring"
    ]


def test_topic_missing_persona_and_solution_keys_still_render(client, db_session):
    topic = _topic(
        db_session,
        personas=[{"type": "Exhausted new parent"}],
        failed_solutions=[{"solution": "Cry it out"}],
    )
    response = client.get(f"/api/topics/{topic.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["personas"][0] == {"type": "Exhausted new parent", "child_age_range": "", "key_struggle": ""}
    assert data["failed_solutions"][0] == {"solution": "Cry it out", "why_failed": ""}


# ── Health ──────────────────────────────────────────────────────────────────

def test_health_ok_when_db_reachable(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


class _DeadSession:
    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def close(self):
        pass


def test_health_degraded_when_db_unreachable(client):
    def dead_db():
        yield _DeadSession()

    app.dependency_overrides[get_db] = dead_db
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "unreachable"}
