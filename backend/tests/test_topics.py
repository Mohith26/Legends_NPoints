from datetime import datetime, timezone

from backend.models import PipelineRun, Topic


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_topics_empty(client):
    response = client.get("/api/topics")
    assert response.status_code == 200
    data = response.json()
    assert data["topics"] == []
    assert data["pipeline_run_id"] is None


def test_get_topics_with_data(client, db_session):
    run = PipelineRun(
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.flush()

    topic = Topic(
        pipeline_run_id=run.id,
        topic_index=0,
        rank=1,
        keywords=[{"word": "sleep", "weight": 0.15}, {"word": "training", "weight": 0.10}],
        gpt_label="Sleep Training Struggles",
        gpt_summary="Parents discuss challenges with sleep training.",
        post_count=120,
        avg_upvotes=245.3,
        representative_docs=[],
    )
    db_session.add(topic)
    db_session.commit()

    response = client.get("/api/topics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) == 1
    assert data["topics"][0]["gpt_label"] == "Sleep Training Struggles"
    assert data["topics"][0]["rank"] == 1
    assert data["pipeline_run_id"] == run.id


def test_get_topic_detail(client, db_session):
    run = PipelineRun(
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.flush()

    topic = Topic(
        pipeline_run_id=run.id,
        topic_index=0,
        rank=1,
        keywords=[{"word": "sleep", "weight": 0.15}],
        gpt_label="Sleep Training",
        gpt_summary="About sleep training.",
        post_count=50,
        avg_upvotes=100.0,
        representative_docs=[
            {"post_id": 1, "excerpt": "My baby won't sleep", "upvotes": 200, "subreddit": "Parenting"}
        ],
    )
    db_session.add(topic)
    db_session.commit()

    response = client.get(f"/api/topics/{topic.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["gpt_label"] == "Sleep Training"
    assert len(data["representative_docs"]) == 1


def test_get_topic_not_found(client):
    response = client.get("/api/topics/9999")
    assert response.status_code == 404


def test_get_stats_empty(client):
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_posts"] == 0
    assert data["total_subreddits"] == 0


def test_get_methodology_not_found(client):
    response = client.get("/api/methodology")
    assert response.status_code == 404
