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
        "phobia", "overthinking", "catastrophizing",
        "school refusal", "test anxiety", "performance anxiety",
    ],
    "adhd_neuro": [
        "adhd", "attention deficit", "hyperactive", "impulsive",
        "impulsivity", "executive function", "focus issues",
        "can't focus", "can't sit still", "fidget",
        "sensory overload", "sensory meltdown", "sensory issues",
        "sensory processing", "neurodivergent", "neurodiverse",
        "asd", "autism", "autistic", "gifted",
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
        "resilience", "resilient",
        "easily frustrated", "low frustration tolerance",
        "gives up", "quit", "quitting",
        "perseverance", "grit", "growth mindset", "fixed mindset",
    ],
    "interventions": [
        "child therapist", "child therapy", "play therapy",
        "behavioral therapy", "talk therapy", "child psychologist",
        "child psychiatrist", "counseling", "counselor",
        "anxiety medication", "adhd medication", "ssri",
        "stimulant medication", "cbt", "iep", "504 plan",
    ],
    "social_emotional": [
        "social skills", "making friends", "no friends", "lonely",
        "bullied", "bullying", "peer rejection", "left out",
        "social isolation", "depression", "depressed",
        "withdrawal", "withdrawn", "self harm", "suicidal",
    ],
}

# Exclusion patterns — posts matching these are rejected even if they
# matched inclusion keywords. Catches physical health, infant care, and
# non-mental-health parenting topics.
BUILD_LEGENDS_EXCLUDE_PATTERNS = [
    # Sleep / infant care
    r"\bsleep\s*train", r"\bcrib\b", r"\bnap\s*schedule",
    r"\bnight\s*wean", r"\bferber\b", r"\bcry\s*it\s*out\b",
    r"\bswaddle\b", r"\bmelatonin\b", r"\bco.?sleep",
    # Feeding / breastfeeding / food
    r"\bbreastfeed", r"\bformula\s*feed", r"\blatching\b",
    r"\bnursing\b", r"\bpicky\s*eat", r"\bsolids\b",
    r"\bweaning\b", r"\bbottle\s*refus", r"\bpumping\b",
    r"\bmilk\s*supply\b", r"\bpuree\b", r"\bhigh\s*chair\b",
    # Potty / diapers
    r"\bpotty\s*train", r"\bdiaper", r"\bbed\s*wett",
    r"\btoilet\s*train", r"\bpull.?ups?\b",
    # Physical health
    r"\bvaccin", r"\bteething\b", r"\bearache\b",
    r"\bear\s*infect", r"\bfever\b", r"\brash\b",
    r"\beczema\b", r"\basthma\b", r"\bbroken\s*bone",
    r"\bstrep\b", r"\bRSV\b", r"\bflu\b",
    # Pets / safety
    r"\bdog\s*bit", r"\bcat\s*scratch", r"\bpet\s*safe",
    r"\bchild\s*proof", r"\bbaby\s*gate\b", r"\bcar\s*seat\b",
    r"\bdog\b", r"\bcat\b", r"\bpet\b",
    # Pregnancy / postpartum physical
    r"\bpregnancy\b", r"\bpregnant\b", r"\bc-section\b",
    r"\blabor\s*and\s*delivery\b", r"\bpostpartum\b",
    r"\bnewborn\b", r"\binfant\b",
    # Birthday / party / gifts / holidays
    r"\bbirthday\s*party\b", r"\bgift\s*idea", r"\bparty\s*plan",
    r"\bchristmas\b", r"\bgift\b", r"\bpresent\b",
    r"\bhalloween\b", r"\bholiday\b",
    # Custody / divorce logistics
    r"\bcustody\b", r"\bdivorce\b", r"\bchild\s*support\b",
    # Climate / politics / societal
    r"\bclimate\b", r"\bglobal\s*warming\b", r"\belection\b",
    r"\bgun\s*violence\b", r"\bschool\s*shoot",
    # Screen time (unless emotional impact)
    r"\bscreen\s*time\b", r"\bipad\b", r"\btablet\b",
    r"\bvideo\s*game", r"\bfortnite\b", r"\broblox\b",
    r"\byoutube\b", r"\btiktok\b",
    # General noise topics
    r"\bstroller\b", r"\bclothing\b", r"\boutfit\b",
    r"\bgenital\b", r"\bcircumcis", r"\bchurch\b",
    r"\breligion\b", r"\bbaptis",
]


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
    """Filter documents to kids' mental health topics only.

    Two-pass filter:
    1. Include posts matching mental health keywords
    2. Exclude posts matching physical/daily-life patterns
    """
    before_count = len(df)

    # Pass 1: Include posts matching mental health keywords
    mask = df["document"].str.contains(_BL_PATTERN, regex=True)
    filtered_df = df[mask].copy()
    after_include = len(filtered_df)

    # Pass 2: Exclude posts about non-mental-health topics
    exclude_pattern = '|'.join(BUILD_LEGENDS_EXCLUDE_PATTERNS)
    exclude_re = re.compile(exclude_pattern, re.IGNORECASE)
    exclude_mask = filtered_df["document"].str.contains(exclude_re, regex=True)
    filtered_df = filtered_df[~exclude_mask].copy()
    after_exclude = len(filtered_df)

    # Track which keyword categories matched for each document
    _category_patterns = {}
    for category, keywords in BUILD_LEGENDS_KEYWORDS.items():
        cat_pattern = r'\b(?:' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'
        _category_patterns[category] = re.compile(cat_pattern, re.IGNORECASE)

    def get_matched_categories(text: str) -> list[str]:
        return [cat for cat, pat in _category_patterns.items() if pat.search(text)]

    filtered_df["matched_categories"] = filtered_df["document"].apply(get_matched_categories)

    # Pass 3: Require posts to match at least 2 different keyword categories.
    # This ensures the post is genuinely about mental health rather than
    # mentioning a single keyword in passing (e.g. "anxiety" about vaccines).
    multi_cat_mask = filtered_df["matched_categories"].apply(lambda cats: len(cats) >= 2)
    filtered_df = filtered_df[multi_cat_mask].copy()
    after_multi = len(filtered_df)

    after_count = len(filtered_df)
    metrics = {
        "total_before_filtering": int(before_count),
        "total_after_include": int(after_include),
        "excluded_by_negative_filter": int(after_include - after_exclude),
        "excluded_single_category": int(after_exclude - after_multi),
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
