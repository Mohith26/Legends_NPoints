import logging
import re
import time

import pandas as pd
from sqlalchemy.orm import Session

from backend.models import RawPost

logger = logging.getLogger(__name__)


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


def load_and_preprocess(session: Session) -> tuple[pd.DataFrame, dict]:
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

    return df, metrics
