from datetime import datetime

from pydantic import BaseModel, ConfigDict


class KeywordSchema(BaseModel):
    word: str
    weight: float


class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rank: int
    gpt_label: str | None
    gpt_summary: str | None
    post_count: int
    avg_upvotes: float
    keywords: list[KeywordSchema]


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


class HealthResponse(BaseModel):
    status: str
