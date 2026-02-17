from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import PipelineRun, PostTopic, RawPost, Topic
from backend.schemas import (
    FailedSolutionSchema,
    KeywordSchema,
    PersonaSchema,
    PostListResponse,
    PostSummary,
    RepresentativeDoc,
    StatsResponse,
    TopicDetailResponse,
    TopicListResponse,
    TopicSummary,
)

router = APIRouter(tags=["topics"])


def _get_latest_run(db: Session) -> PipelineRun | None:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .first()
    )


@router.get("/api/topics", response_model=TopicListResponse)
def get_topics(db: Session = Depends(get_db)):
    run = _get_latest_run(db)
    if not run:
        return TopicListResponse(topics=[], pipeline_run_id=None, run_completed_at=None)

    topics = (
        db.query(Topic)
        .filter(Topic.pipeline_run_id == run.id)
        .order_by(Topic.rank)
        .all()
    )

    topic_summaries = []
    for t in topics:
        keywords = [KeywordSchema(word=kw["word"], weight=kw["weight"]) for kw in (t.keywords or [])]
        topic_summaries.append(TopicSummary(
            id=t.id,
            rank=t.rank,
            gpt_label=t.gpt_label,
            gpt_summary=t.gpt_summary,
            post_count=t.post_count,
            avg_upvotes=t.avg_upvotes,
            keywords=keywords,
            pain_points=t.pain_points,
            build_legends_angle=t.build_legends_angle,
        ))

    return TopicListResponse(
        topics=topic_summaries,
        pipeline_run_id=run.id,
        run_completed_at=run.completed_at,
    )


@router.get("/api/topics/{topic_id}", response_model=TopicDetailResponse)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    keywords = [KeywordSchema(word=kw["word"], weight=kw["weight"]) for kw in (topic.keywords or [])]
    rep_docs = [
        RepresentativeDoc(**doc) for doc in (topic.representative_docs or [])
    ]

    return TopicDetailResponse(
        id=topic.id,
        rank=topic.rank,
        gpt_label=topic.gpt_label,
        gpt_summary=topic.gpt_summary,
        post_count=topic.post_count,
        avg_upvotes=topic.avg_upvotes,
        keywords=keywords,
        representative_docs=rep_docs,
        personas=[PersonaSchema(**p) for p in (topic.personas or [])],
        failed_solutions=[FailedSolutionSchema(**f) for f in (topic.failed_solutions or [])],
        pain_points=topic.pain_points,
        build_legends_angle=topic.build_legends_angle,
    )


@router.get("/api/topics/{topic_id}/posts", response_model=PostListResponse)
def get_topic_posts(
    topic_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    query = (
        db.query(RawPost, PostTopic.probability)
        .join(PostTopic, PostTopic.raw_post_id == RawPost.id)
        .filter(PostTopic.topic_id == topic_id)
        .order_by(RawPost.upvotes.desc())
    )

    total = query.count()
    offset = (page - 1) * page_size
    results = query.offset(offset).limit(page_size).all()

    posts = []
    for post, probability in results:
        posts.append(PostSummary(
            id=post.id,
            reddit_id=post.reddit_id,
            subreddit=post.subreddit,
            title=post.title,
            upvotes=post.upvotes or 0,
            url=post.url,
            author=post.author,
            created_utc=post.created_utc,
            probability=probability,
        ))

    return PostListResponse(posts=posts, total=total, page=page, page_size=page_size)


@router.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_posts = db.query(func.count(RawPost.id)).scalar() or 0
    subreddits = [
        r[0] for r in db.query(RawPost.subreddit).distinct().all()
    ]

    run = _get_latest_run(db)
    total_topics = 0
    filtered_posts = None
    if run:
        total_topics = db.query(func.count(Topic.id)).filter(Topic.pipeline_run_id == run.id).scalar() or 0
        if run.methodology:
            bl_filter = (run.methodology.get("preprocessing") or {}).get("build_legends_filter")
            if bl_filter:
                filtered_posts = bl_filter.get("total_after_filtering")

    return StatsResponse(
        total_posts=total_posts,
        total_subreddits=len(subreddits),
        subreddits=sorted(subreddits),
        last_run_date=run.completed_at if run else None,
        last_run_status=run.status if run else None,
        total_topics=total_topics,
        filtered_posts=filtered_posts,
    )


@router.get("/api/methodology")
def get_methodology(db: Session = Depends(get_db)):
    run = _get_latest_run(db)
    if not run or not run.methodology:
        raise HTTPException(status_code=404, detail="No methodology data available")

    return {
        "pipeline_run_id": run.id,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "methodology": run.methodology,
    }
