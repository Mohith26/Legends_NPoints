import logging
import re
import time

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import RawPost

logger = logging.getLogger(__name__)

# Keywords organized by category for Build Legends relevance filtering
BUILD_LEGENDS_KEYWORDS = {
    "emotional": [
        "meltdown", "meltdowns", "tantrum", "tantrums", "outburst", "outbursts",
        "emotional regulation", "dysregulation", "dysregulated", "big emotions",
        "emotional breakdown", "rage", "raging", "screaming fit",
    ],
    "confidence": [
        "confidence", "self-esteem", "self esteem", "self-worth", "self worth",
        "insecure", "insecurity", "self-doubt", "self doubt",
        "low confidence", "no confidence",
    ],
    "perfectionism": [
        "perfectionist", "perfectionism", "afraid to fail", "fear of failure",
        "won't try", "refuses to try", "gives up easily", "gives up",
        "afraid of making mistakes", "hates losing", "sore loser",
        "can't handle losing", "won't try new things",
    ],
    "anxiety": [
        "anxiety", "anxious", "worried", "worrying", "panic",
        "panic attack", "separation anxiety", "school anxiety",
        "social anxiety", "nervous", "fearful",
        "scared", "phobia", "overthinking", "catastrophizing",
    ],
    "adhd_neuro": [
        "adhd", "add", "attention deficit", "hyperactive", "impulsive",
        "impulsivity", "executive function", "focus issues",
        "can't focus", "can't sit still", "fidget", "sensory",
        "sensory processing", "neurodivergent", "neurodiverse",
        "spectrum", "asd", "autism", "autistic", "gifted",
        "twice exceptional", "2e",
    ],
    "behavioral": [
        "defiant", "defiance", "oppositional", "odd",
        "behavior issues", "behavioral issues", "acting out",
        "aggressive", "aggression", "hitting", "biting",
        "lashing out", "destructive", "disobedient", "won't listen",
        "disrespectful", "back talk", "backtalk",
    ],
    "resilience": [
        "resilience", "resilient", "coping", "cope",
        "frustrated", "frustration", "easily frustrated",
        "low frustration tolerance", "gives up", "quit",
        "quitting", "perseverance", "grit", "growth mindset",
        "fixed mindset",
    ],
    "interventions": [
        "therapy", "therapist", "counseling", "counselor",
        "psychologist", "psychiatrist", "medication",
        "occupational therapy", "behavioral therapy",
        "cbt", "play therapy", "iep", "504 plan",
    ],
}


def _build_keyword_pattern(keyword_groups: dict[str, list[str]]) -> re.Pattern:
    """Build a single compiled regex from all keyword groups."""
    all_keywords = []
    for group_keywords in keyword_groups.values():
        all_keywords.extend(group_keywords)
    # Sort by length descending so longer phrases match first
    all_keywords.sort(key=len, reverse=True)
    pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in all_keywords) + r')\b'
    return re.compile(pattern, re.IGNORECASE)


_BL_PATTERN = _build_keyword_pattern(BUILD_LEGENDS_KEYWORDS)


def filter_for_build_legends(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Filter documents to those relevant to Build Legends themes."""
    before_count = len(df)

    mask = df["document"].str.contains(_BL_PATTERN, regex=True)
    filtered_df = df[mask].copy()

    # Track which keyword categories matched for each document
    _category_patterns = {}
    for category, keywords in BUILD_LEGENDS_KEYWORDS.items():
        cat_pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
        _category_patterns[category] = re.compile(cat_pattern, re.IGNORECASE)

    def get_matched_categories(text: str) -> list[str]:
        return [cat for cat, pat in _category_patterns.items() if pat.search(text)]

    filtered_df["matched_categories"] = filtered_df["document"].apply(get_matched_categories)

    after_count = len(filtered_df)
    metrics = {
        "total_before_filtering": int(before_count),
        "total_after_filtering": int(after_count),
        "filter_pass_rate": round(after_count / before_count * 100, 1) if before_count > 0 else 0,
        "keyword_category_counts": {
            cat: int(filtered_df["matched_categories"].apply(lambda cats, c=cat: c in cats).sum())
            for cat in BUILD_LEGENDS_KEYWORDS
        },
    }

    return filtered_df, metrics


def clean_text(text: str) -> str:
    """Strip URLs, markdown formatting, collapse whitespace."""
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove markdown links [text](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove markdown bold/italic
    text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove blockquotes
    text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_documents(posts: list[RawPost]) -> pd.DataFrame:
    """Concatenate title + body + top 3 comments into one document per post."""
    records = []
    for post in posts:
        title = clean_text(post.title or "")
        body = clean_text(post.body or "")

        comments = post.top_comments or []
        comment_text = " ".join(clean_text(c) for c in comments[:3])

        document = f"{title} {body} {comment_text}".strip()
        records.append({
            "post_id": post.id,
            "document": document,
            "subreddit": post.subreddit,
            "upvotes": post.upvotes or 0,
        })

    return pd.DataFrame(records)


def load_and_preprocess(
    session: Session, filter_mode: str | None = None
) -> tuple[pd.DataFrame, dict]:
    """Load posts from DB, build documents, filter, dedup. Returns (df, metrics)."""
    start_time = time.time()

    posts = session.query(RawPost).all()
    logger.info(f"Loaded {len(posts)} posts from database")

    df = build_documents(posts)
    total_before = len(df)

    # Word count per document
    df["word_count"] = df["document"].apply(lambda x: len(x.split()))

    # Filter short documents (< 10 words)
    short_mask = df["word_count"] < 10
    removed_short = short_mask.sum()
    df = df[~short_mask].copy()

    # Deduplicate by document text
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["document"]).copy()
    removed_dupes = before_dedup - len(df)

    total_after = len(df)
    total_words = df["word_count"].sum()

    metrics = {
        "total_documents_before_cleaning": int(total_before),
        "documents_removed_too_short": int(removed_short),
        "documents_removed_duplicates": int(removed_dupes),
        "total_documents_after_cleaning": int(total_after),
        "total_words_processed": int(total_words),
        "avg_words_per_document": int(total_words / total_after) if total_after > 0 else 0,
        "min_words_in_document": int(df["word_count"].min()) if total_after > 0 else 0,
        "max_words_in_document": int(df["word_count"].max()) if total_after > 0 else 0,
        "preprocessing_duration_seconds": round(time.time() - start_time, 1),
    }

    logger.info(
        f"Preprocessing: {total_before} -> {total_after} documents "
        f"(removed {removed_short} short, {removed_dupes} dupes)"
    )

    # Apply Build Legends filter if requested
    if filter_mode == "build_legends":
        df, filter_metrics = filter_for_build_legends(df)
        metrics["build_legends_filter"] = filter_metrics
        logger.info(
            f"Build Legends filter: {filter_metrics['total_before_filtering']} -> "
            f"{filter_metrics['total_after_filtering']} documents "
            f"({filter_metrics['filter_pass_rate']}% pass rate)"
        )

    return df, metrics
