from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KeywordSchema(BaseModel):
    word: str
    weight: float


class PersonaSchema(BaseModel):
    type: str
    child_age_range: str
    key_struggle: str


class FailedSolutionSchema(BaseModel):
    solution: str
    why_failed: str


class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rank: int
    gpt_label: str | None
    gpt_summary: str | None
    post_count: int
    avg_upvotes: float
    keywords: list[KeywordSchema]
    pain_points: list[str] | None = None
    build_legends_angle: str | None = None


class TopicListResponse(BaseModel):
    topics: list[TopicSummary]
    pipeline_run_id: int | None
    run_completed_at: datetime | None


class RepresentativeDoc(BaseModel):
    post_id: int
    excerpt: str
    upvotes: int
    subreddit: str


class TopicDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rank: int
    gpt_label: str | None
    gpt_summary: str | None
    post_count: int
    avg_upvotes: float
    keywords: list[KeywordSchema]
    representative_docs: list[RepresentativeDoc]
    personas: list[PersonaSchema] | None = None
    failed_solutions: list[FailedSolutionSchema] | None = None
    pain_points: list[str] | None = None
    build_legends_angle: str | None = None


class PostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reddit_id: str
    subreddit: str
    title: str
    upvotes: int
    url: str | None
    author: str | None
    created_utc: datetime | None
    probability: float | None


class PostListResponse(BaseModel):
    posts: list[PostSummary]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total_posts: int
    total_subreddits: int
    subreddits: list[str]
    last_run_date: datetime | None
    last_run_status: str | None
    total_topics: int
    filtered_posts: int | None = None


class HealthResponse(BaseModel):
    status: str


# ── Label Analysis Schemas ──────────────────────────────────────────────────

class MarketingInsightsSchema(BaseModel):
    ad_hooks: list[str] = []
    messaging_angles: list[str] = []
    target_audience_description: str = ""
    emotional_triggers: list[str] = []


class MicroPersonaSchema(BaseModel):
    description: str
    child_age: str = ""
    specific_trigger: str = ""


class StorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    post_count: int
    build_legends_angle: str | None = None


class StoryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    post_count: int
    pain_points: list[str] | None = None
    failed_solutions: list[FailedSolutionSchema] | None = None
    build_legends_angle: str | None = None
    representative_quotes: list[str] | None = None
    micro_personas: list[MicroPersonaSchema] | None = None


class LabelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    post_count: int
    discovery_method: str
    story_count: int = 0
    stories: list[StorySummary] = []


class LabelListResponse(BaseModel):
    labels: list[LabelSummary]
    pipeline_run_id: int | None
    run_completed_at: datetime | None


class LabelDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    post_count: int
    discovery_method: str
    example_phrases: list[str] | None = None
    marketing_insights: MarketingInsightsSchema | None = None
    stories: list[StoryDetailResponse] = []


class LabelStatsResponse(BaseModel):
    total_labels: int
    total_stories: int
    total_labeled_posts: int
    top_labels: list[LabelSummary] = []
