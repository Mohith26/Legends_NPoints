from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import LabelStory, ParentLabel, PipelineRun, PostLabel
from backend.schemas import (
    FailedSolutionSchema,
    LabelDetailResponse,
    LabelListResponse,
    LabelStatsResponse,
    LabelSummary,
    MarketingInsightsSchema,
    StoryDetailResponse,
    StorySummary,
)

router = APIRouter(tags=["labels"])


def _get_latest_run(db: Session) -> PipelineRun | None:
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.status == "completed")
        .order_by(PipelineRun.completed_at.desc())
        .first()
    )


@router.get("/api/labels", response_model=LabelListResponse)
def get_labels(db: Session = Depends(get_db)):
    run = _get_latest_run(db)
    if not run:
        return LabelListResponse(labels=[], pipeline_run_id=None, run_completed_at=None)

    labels = (
        db.query(ParentLabel)
        .filter(ParentLabel.pipeline_run_id == run.id)
        .order_by(ParentLabel.post_count.desc())
        .all()
    )

    label_summaries = []
    for label in labels:
        stories = (
            db.query(LabelStory)
            .filter(LabelStory.label_id == label.id)
            .order_by(LabelStory.post_count.desc())
            .all()
        )
        story_summaries = [
            StorySummary(
                id=s.id,
                title=s.title,
                summary=s.summary,
                post_count=s.post_count,
                build_legends_angle=s.build_legends_angle,
            )
            for s in stories
        ]
        label_summaries.append(LabelSummary(
            id=label.id,
            name=label.name,
            slug=label.slug,
            post_count=label.post_count,
            discovery_method=label.discovery_method,
            story_count=len(stories),
            stories=story_summaries,
        ))

    return LabelListResponse(
        labels=label_summaries,
        pipeline_run_id=run.id,
        run_completed_at=run.completed_at,
    )


@router.get("/api/labels/stats", response_model=LabelStatsResponse)
def get_label_stats(db: Session = Depends(get_db)):
    run = _get_latest_run(db)
    if not run:
        return LabelStatsResponse(total_labels=0, total_stories=0, total_labeled_posts=0)

    total_labels = (
        db.query(func.count(ParentLabel.id))
        .filter(ParentLabel.pipeline_run_id == run.id)
        .scalar() or 0
    )
    total_stories = (
        db.query(func.count(LabelStory.id))
        .join(ParentLabel)
        .filter(ParentLabel.pipeline_run_id == run.id)
        .scalar() or 0
    )
    total_labeled_posts = (
        db.query(func.count(func.distinct(PostLabel.raw_post_id)))
        .filter(PostLabel.pipeline_run_id == run.id)
        .scalar() or 0
    )

    # Top 5 labels
    top_labels_db = (
        db.query(ParentLabel)
        .filter(ParentLabel.pipeline_run_id == run.id)
        .order_by(ParentLabel.post_count.desc())
        .limit(5)
        .all()
    )
    top_labels = [
        LabelSummary(
            id=l.id,
            name=l.name,
            slug=l.slug,
            post_count=l.post_count,
            discovery_method=l.discovery_method,
            story_count=db.query(func.count(LabelStory.id)).filter(LabelStory.label_id == l.id).scalar() or 0,
        )
        for l in top_labels_db
    ]

    return LabelStatsResponse(
        total_labels=total_labels,
        total_stories=total_stories,
        total_labeled_posts=total_labeled_posts,
        top_labels=top_labels,
    )


@router.get("/api/labels/{label_id}", response_model=LabelDetailResponse)
def get_label(label_id: int, db: Session = Depends(get_db)):
    label = db.query(ParentLabel).filter(ParentLabel.id == label_id).first()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    stories = (
        db.query(LabelStory)
        .filter(LabelStory.label_id == label.id)
        .order_by(LabelStory.post_count.desc())
        .all()
    )

    story_details = []
    for s in stories:
        failed_solutions = None
        if s.failed_solutions:
            failed_solutions = [FailedSolutionSchema(**fs) for fs in s.failed_solutions]

        story_details.append(StoryDetailResponse(
            id=s.id,
            title=s.title,
            summary=s.summary,
            post_count=s.post_count,
            pain_points=s.pain_points,
            failed_solutions=failed_solutions,
            build_legends_angle=s.build_legends_angle,
            representative_quotes=s.representative_quotes,
        ))

    marketing = None
    if label.marketing_insights:
        marketing = MarketingInsightsSchema(**label.marketing_insights)

    return LabelDetailResponse(
        id=label.id,
        name=label.name,
        slug=label.slug,
        description=label.description,
        post_count=label.post_count,
        discovery_method=label.discovery_method,
        example_phrases=label.example_phrases,
        marketing_insights=marketing,
        stories=story_details,
    )
