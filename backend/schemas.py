import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, ValidationError, ValidationInfo, model_validator

logger = logging.getLogger(__name__)

# Upper bound for the `page` query parameter; keeps (page - 1) * page_size far below any integer limit.
MAX_PAGE = 1_000_000


class StoredRecord(BaseModel):
    """A GPT-produced JSON object re-validated from the database at read time.

    Validate with ``model_validate(data, context=<owning record>)``. Data that is
    not an object, omits keys, or holds wrong-typed values degrades to the field
    defaults with one warning naming the owner, so a single malformed stored
    record cannot fail the whole response.
    """

    @classmethod
    def _stored_keys(cls) -> Iterable[str]:
        return cls.model_fields

    @model_validator(mode="wrap")
    @classmethod
    def _tolerate_malformed(cls, data, handler, info: ValidationInfo):
        if isinstance(data, cls):
            return handler(data)
        where = info.context or "unknown record"
        if not isinstance(data, dict):
            logger.warning("%s: stored %s is %r, not an object; using defaults", where, cls.__name__, data)
            return handler({})
        try:
            record = handler(data)
            invalid = []
        except ValidationError as exc:
            invalid = sorted({str(err["loc"][0]) for err in exc.errors() if err["loc"]})
            record = handler({k: v for k, v in data.items() if k not in invalid})
        problems = []
        missing = [k for k in cls._stored_keys() if k not in data]
        if missing:
            problems.append("missing " + ", ".join(missing))
        if invalid:
            problems.append("invalid " + ", ".join(invalid))
        if problems:
            logger.warning("%s: stored %s %s; using defaults", where, cls.__name__, "; ".join(problems))
        return record


def stored_list(value, *, where: str, name: str) -> list:
    """Return a stored JSON list column, treating a non-list value as empty."""
    if value is None or isinstance(value, list):
        return value or []
    logger.warning("%s: stored %s is %r, not a list; ignoring", where, name, value)
    return []


def _keep_strings(value, info: ValidationInfo) -> list[str]:
    where = info.context or "unknown record"
    items = stored_list(value, where=where, name=info.field_name)
    kept = [item for item in items if isinstance(item, str)]
    if len(kept) < len(items):
        logger.warning(
            "%s: stored %s has %d non-string items; dropped", where, info.field_name, len(items) - len(kept),
        )
    return kept


# A stored GPT-produced list of strings; wrong-typed items are dropped instead of failing the response.
StoredStrings = Annotated[list[str], BeforeValidator(_keep_strings)]


class KeywordSchema(BaseModel):
    word: str
    weight: float


class PersonaSchema(StoredRecord):
    type: str = ""
    child_age_range: str = ""
    key_struggle: str = ""


class FailedSolutionSchema(StoredRecord):
    solution: str = ""
    why_failed: str = ""


class TopicSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rank: int
    gpt_label: str | None
    gpt_summary: str | None
    post_count: int
    avg_upvotes: float
    keywords: list[KeywordSchema]
    pain_points: StoredStrings | None = None
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
    pain_points: StoredStrings | None = None
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
    db: str


# ── Label Analysis Schemas ──────────────────────────────────────────────────

class MarketingInsightsSchema(StoredRecord):
    ad_hooks: list[str] = []
    messaging_angles: list[str] = []
    target_audience_description: str = ""
    emotional_triggers: list[str] = []


class SourcePostSchema(BaseModel):
    id: int
    title: str
    url: str | None
    subreddit: str
    upvotes: int


class StoredMicroPersona(StoredRecord):
    label: str = ""
    child_profile: str = ""
    trigger_scenario: str = ""
    parent_circumstance: str = ""
    ad_hook: str = ""


class MicroPersonaSchema(StoredMicroPersona):
    source_post: SourcePostSchema | None = None
    # Backward compat with old format
    description: str = ""
    child_age: str = ""
    specific_trigger: str = ""

    @classmethod
    def _stored_keys(cls) -> Iterable[str]:
        return StoredMicroPersona.model_fields


class StorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    post_count: int
    build_legends_angle: str | None = None


class PainPointSchema(BaseModel):
    text: str
    source_post: SourcePostSchema | None = None


class StoryDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str | None
    post_count: int
    pain_points: list[PainPointSchema] | None = None
    failed_solutions: list[FailedSolutionSchema] | None = None
    build_legends_angle: str | None = None
    representative_quotes: StoredStrings | None = None
    visceral_quotes: StoredStrings | None = None
    micro_personas: list[MicroPersonaSchema] | None = None
    source_posts: list[SourcePostSchema] = []


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
    example_phrases: StoredStrings | None = None
    marketing_insights: MarketingInsightsSchema | None = None
    stories: list[StoryDetailResponse] = []


class LabelStatsResponse(BaseModel):
    total_labels: int
    total_stories: int
    total_labeled_posts: int
    top_labels: list[LabelSummary] = []
