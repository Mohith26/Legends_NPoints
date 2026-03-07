"""Label Analysis pipeline — identifies parent-assigned labels for kids and extracts stories within each label.

Four phases:
1. Regex scan: match predefined label patterns against filtered posts
2. GPT discovery: find new labels from unmatched posts
3. Sub-clustering: KMeans within each label to find story clusters
4. GPT story extraction: summarize each sub-cluster into a story
"""
import json
import logging
import re
import time

import numpy as np
import pandas as pd
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from pipeline.config import PipelineConfig
from pipeline.db import store_label, store_label_story, store_post_label

logger = logging.getLogger(__name__)

# ── Predefined label patterns ──────────────────────────────────────────────
# Each entry: (label_name, slug, compiled_regex)
# Patterns are designed to match how parents describe/label their children.

_CHILD_WORDS = r"(?:kid|child|son|daughter|boy|girl|teen|teenager|toddler|preschooler)"

PREDEFINED_LABELS = [
    (
        "Gifted Kid",
        "gifted-kid",
        re.compile(
            r"\b(?:gifted|highly gifted|profoundly gifted)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:is|was)\s+gifted\b"
            r"|\bgifted\s+(?:program|testing|assessment)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ADHD Kid",
        "adhd-kid",
        re.compile(
            r"\b(?:adhd|add)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bdiagnosed\s+(?:with\s+)?adhd\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:has|with)\s+adhd\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Anxious Child",
        "anxious-child",
        re.compile(
            r"\b(?:anxious|anxiety[- ]ridden)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:has|with|struggles?\s+with)\s+anxiety\b"
            r"|\bchild(?:'s)?\s+anxiety\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Autistic Child",
        "autistic-child",
        re.compile(
            r"\b(?:autistic|autism|on the spectrum|asd)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bdiagnosed\s+(?:with\s+)?(?:autism|asd)\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:is|was)\s+(?:autistic|on the spectrum)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Strong-Willed Child",
        "strong-willed-child",
        re.compile(
            r"\b(?:strong[- ]willed|spirited)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+is\s+(?:so\s+)?(?:strong[- ]willed|spirited)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Sensitive Child",
        "sensitive-child",
        re.compile(
            r"\b(?:highly sensitive|hsp|overly sensitive)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+is\s+(?:so\s+)?(?:sensitive|emotional)\b"
            r"|\bsensitive\s+" + _CHILD_WORDS + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Shy Child",
        "shy-child",
        re.compile(
            r"\b(?:shy|extremely shy|painfully shy|introverted)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+is\s+(?:so\s+)?(?:shy|introverted)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Perfectionist Child",
        "perfectionist-child",
        re.compile(
            r"\bperfectionist\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+is\s+(?:a\s+)?perfectionist\b"
            r"|\bperfectionism\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Angry/Aggressive Child",
        "angry-aggressive-child",
        re.compile(
            r"\b(?:angry|aggressive|violent|rageful)\s*" + _CHILD_WORDS + r"?\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:is|gets)\s+(?:so\s+)?(?:angry|aggressive|violent)\b"
            r"|\bage\s*(?:rage|aggression)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Depressed Child",
        "depressed-child",
        re.compile(
            r"\b(?:depressed|depression)\b.*?\b" + _CHILD_WORDS + r"\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:is|seems?)\s+depressed\b"
            r"|\bchild(?:'s)?\s+depression\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Bullied Child",
        "bullied-child",
        re.compile(
            r"\b(?:bullied|being bullied|getting bullied)\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:is|gets)\s+bullied\b"
            r"|\bbully(?:ing)?\s+(?:at|in)\s+school\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Socially Struggling Child",
        "socially-struggling",
        re.compile(
            r"\b(?:no friends|has no friends|trouble making friends|socially awkward)\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:has|with)\s+no\s+friends\b"
            r"|\bsocial\s+skills?\s+(?:issues?|problems?|struggles?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "School Refuser",
        "school-refuser",
        re.compile(
            r"\b(?:school refusal|refuses? school|won't go to school|hates school)\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+(?:refuses?|won't)\s+(?:go to\s+)?school\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Twice-Exceptional (2e)",
        "twice-exceptional",
        re.compile(
            r"\b(?:twice exceptional|2e)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "ODD Child",
        "odd-child",
        re.compile(
            r"\b(?:oppositional defiant|odd\s+diagnosis|odd\s+" + _CHILD_WORDS + r")\b"
            r"|\bdiagnosed\s+(?:with\s+)?odd\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Sensory Child",
        "sensory-child",
        re.compile(
            r"\b(?:sensory processing|sensory issues|sensory seeking|sensory avoiding|spd)\b"
            r"|\bsensory\s+" + _CHILD_WORDS + r"\b",
            re.IGNORECASE,
        ),
    ),
    (
        "People Pleaser",
        "people-pleaser",
        re.compile(
            r"\b(?:people pleaser|people pleasing|approval seeking)\b"
            r"|\bmy\s+" + _CHILD_WORDS + r"\s+is\s+(?:a\s+)?people\s+pleaser\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Low Self-Esteem Child",
        "low-self-esteem",
        re.compile(
            r"\b(?:low self[- ]esteem|no self[- ]esteem|no self[- ]confidence)\b"
            r"|\bhates?\s+(?:him|her)self\b"
            r"|\bthinks?\s+(?:he|she|they)'?(?:s|re)\s+(?:stupid|dumb|ugly|worthless)\b"
            r"|\b(?:says?|thinks?)\s+(?:i'm|im)\s+(?:stupid|dumb|ugly|worthless)\b",
            re.IGNORECASE,
        ),
    ),
]


# ── GPT Prompts ─────────────────────────────────────────────────────────────

DISCOVERY_SYSTEM_PROMPT = """You are analyzing Reddit posts from parenting communities about children's mental health.

These posts did NOT match any of our predefined parent labels (like "gifted kid", "ADHD kid", "anxious child", etc.).

Your task: identify any PARENT-ASSIGNED LABELS or IDENTITY DESCRIPTIONS for the child in these posts.

Look for patterns like:
- "My child is [label]" (e.g., "the difficult one", "a worrier", "the class clown")
- Diagnostic or quasi-diagnostic labels (e.g., "sensory seeker", "emotionally immature")
- Identity descriptions parents use repeatedly (e.g., "explosive child", "the quiet one")

Respond with a JSON object:
{
  "discovered_labels": [
    {
      "name": "Label Name",
      "slug": "label-name",
      "example_phrases": ["phrase from post 1", "phrase from post 2"],
      "description": "One sentence describing this label pattern"
    }
  ]
}

Only include labels that appear in AT LEAST 2 different posts. Do not rediscover labels we already have: gifted, ADHD, anxious, autistic, strong-willed, sensitive, shy, perfectionist, angry/aggressive, depressed, bullied, socially struggling, school refuser, twice-exceptional, ODD, sensory, people pleaser, low self-esteem."""

STORY_SYSTEM_PROMPT = """You are a customer research analyst for Build Legends, a 5-minute daily confidence training app for kids ages 5-14.

You are analyzing a cluster of Reddit posts from parents who label their child as "{label_name}". These posts share a common STORY PATTERN — a specific struggle or scenario within this label.

IMPORTANT: Focus on the NEGATIVE posts — parents expressing pain, frustration, desperation. Ignore advice, success stories, or positive anecdotes. We want raw parent pain that drives them to seek help.

Extract the story pattern from these posts. Respond with a JSON object:

{{
  "title": "A vivid 5-10 word title for this story (e.g., 'Gifted kid melts down over imperfect homework')",
  "summary": "2-3 sentences describing this specific struggle pattern. Be vivid and specific, not clinical. Use the desperate language parents actually use.",
  "pain_points": ["3-5 specific pain points — pull near-direct quotes from the posts. These should be raw, emotional, and hit hard."],
  "failed_solutions": [
    {{"solution": "What they tried", "why_failed": "Why it fell short"}}
  ],
  "build_legends_angle": "2-3 sentences on how Build Legends addresses this specific story. Reference product mechanics: daily 5-min missions, confidence streaks, character growth, parent dashboard.",
  "representative_quotes": ["2-3 direct quotes or close paraphrases from the posts — pick the most visceral, desperate ones"],
  "micro_personas": [
    {{
      "description": "A hyper-specific parent profile with 3 layers: (1) child's specific challenge, (2) the specific trigger scenario, (3) the parent's life circumstance. Example: 'Former teacher turned homeschool mom of a gifted but emotionally dysregulated 9yo after public school kept calling her in weekly — she gave up her career to get this right'",
      "child_age": "e.g., 8-10",
      "specific_trigger": "The exact daily moment that breaks down — e.g., 'Every night at homework time he freezes, then sobs, then screams I'm stupid'"
    }}
  ]
}}

Include 2-3 micro_personas per story. Make them feel like real, specific people — not demographics. Layer specificity: child diagnosis + trigger scenario + parent sacrifice/circumstance.

Be specific and grounded in the actual post content. Use real parent language."""


# ── Phase 1: Regex Label Scan ──────────────────────────────────────────────

def _scan_labels_regex(df: pd.DataFrame) -> dict[str, list[tuple[int, str]]]:
    """Scan all documents against predefined label patterns.

    Returns: {slug: [(post_id, matched_phrase), ...]}
    """
    results: dict[str, list[tuple[int, str]]] = {}
    for _, row in df.iterrows():
        doc = row["document"]
        post_id = row["post_id"]
        for name, slug, pattern in PREDEFINED_LABELS:
            match = pattern.search(doc)
            if match:
                results.setdefault(slug, []).append((post_id, match.group()))
    return results


# ── Phase 2: GPT Discovery ────────────────────────────────────────────────

def _discover_labels_gpt(
    df: pd.DataFrame,
    matched_post_ids: set[int],
    config: PipelineConfig,
) -> list[dict]:
    """Use GPT to discover new labels from unmatched posts."""
    unmatched = df[~df["post_id"].isin(matched_post_ids)]
    if len(unmatched) < 10:
        logger.info("Too few unmatched posts for GPT discovery, skipping")
        return []

    sample = unmatched.sample(n=min(config.LABEL_GPT_DISCOVERY_SAMPLE, len(unmatched)), random_state=42)
    # Send in batches of 20
    batch_size = 20
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    all_discovered = []

    for i in range(0, len(sample), batch_size):
        batch = sample.iloc[i:i + batch_size]
        posts_text = "\n\n---\n\n".join(
            f"Post {j+1}: {row['document'][:400]}"
            for j, (_, row) in enumerate(batch.iterrows())
        )

        try:
            response = client.chat.completions.create(
                model=config.GPT_MODEL,
                messages=[
                    {"role": "system", "content": DISCOVERY_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze these {len(batch)} posts:\n\n{posts_text}"},
                ],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content)
            discovered = result.get("discovered_labels", [])
            all_discovered.extend(discovered)
        except Exception as e:
            logger.error(f"GPT discovery batch failed: {e}")

    # Deduplicate by slug
    seen_slugs = set()
    unique = []
    for label in all_discovered:
        slug = label.get("slug", "")
        if slug and slug not in seen_slugs:
            seen_slugs.add(slug)
            unique.append(label)

    logger.info(f"GPT discovered {len(unique)} new labels from {len(sample)} unmatched posts")
    return unique


def _scan_discovered_labels(
    df: pd.DataFrame, discovered_labels: list[dict]
) -> dict[str, list[tuple[int, str]]]:
    """Scan documents for GPT-discovered label patterns."""
    results: dict[str, list[tuple[int, str]]] = {}
    for label in discovered_labels:
        slug = label["slug"]
        phrases = label.get("example_phrases", [])
        if not phrases:
            continue
        # Build a regex from example phrases
        escaped = [re.escape(p) for p in phrases]
        pattern = re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)
        for _, row in df.iterrows():
            match = pattern.search(row["document"])
            if match:
                results.setdefault(slug, []).append((row["post_id"], match.group()))
    return results


# ── Phase 3: Sub-clustering Stories ────────────────────────────────────────

def _subcluster_label(
    df: pd.DataFrame,
    post_ids: list[int],
    config: PipelineConfig,
    embedding_model: SentenceTransformer,
) -> list[dict]:
    """Sub-cluster posts within a label to find story patterns.

    Returns list of sub-cluster dicts with post_ids, keywords, representative docs.
    """
    label_df = df[df["post_id"].isin(post_ids)].copy()
    has_pain = "pain_score" in label_df.columns
    if len(label_df) < 10:
        # Too few for sub-clustering — return as single story
        if has_pain:
            top_posts = label_df.sort_values(["pain_score", "upvotes"], ascending=[False, False]).head(5)
        else:
            top_posts = label_df.nlargest(min(5, len(label_df)), "upvotes")
        return [{
            "post_ids": label_df["post_id"].tolist(),
            "post_count": len(label_df),
            "keywords": [],
            "representative_docs": [
                {"post_id": int(r["post_id"]), "excerpt": r["document"][:500], "upvotes": int(r["upvotes"])}
                for _, r in top_posts.iterrows()
            ],
        }]

    documents = label_df["document"].tolist()
    n_stories = min(config.LABEL_MAX_STORIES, max(2, len(label_df) // 30))

    # Embed
    embeddings = embedding_model.encode(documents, show_progress_bar=False)

    # UMAP reduce
    n_neighbors = min(15, len(documents) // 2)
    umap_model = UMAP(
        n_neighbors=max(2, n_neighbors),
        n_components=min(5, len(documents) - 1),
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    reduced = umap_model.fit_transform(embeddings)

    # KMeans
    kmeans = KMeans(n_clusters=n_stories, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(reduced)
    label_df["sub_cluster"] = cluster_labels

    # Extract keywords per sub-cluster
    vectorizer = CountVectorizer(ngram_range=(1, 2), min_df=1, max_features=100, stop_words="english")

    sub_clusters = []
    for cluster_id in range(n_stories):
        cluster_posts = label_df[label_df["sub_cluster"] == cluster_id]
        if len(cluster_posts) == 0:
            continue

        # Keywords
        try:
            tfidf = vectorizer.fit_transform(cluster_posts["document"])
            word_counts = tfidf.sum(axis=0).A1
            vocab = vectorizer.get_feature_names_out()
            top_indices = word_counts.argsort()[-10:][::-1]
            keywords = [vocab[i] for i in top_indices]
        except Exception:
            keywords = []

        # Representative docs: prefer high-pain posts, then by upvotes
        if has_pain:
            top_posts = cluster_posts.sort_values(
                ["pain_score", "upvotes"], ascending=[False, False]
            ).head(min(5, len(cluster_posts)))
        else:
            top_posts = cluster_posts.nlargest(min(5, len(cluster_posts)), "upvotes")
        rep_docs = [
            {"post_id": int(r["post_id"]), "excerpt": r["document"][:500], "upvotes": int(r["upvotes"])}
            for _, r in top_posts.iterrows()
        ]

        sub_clusters.append({
            "post_ids": cluster_posts["post_id"].tolist(),
            "post_count": len(cluster_posts),
            "keywords": keywords,
            "representative_docs": rep_docs,
        })

    return sub_clusters


# ── Phase 4: GPT Story Extraction ─────────────────────────────────────────

def _extract_story_gpt(
    client: OpenAI,
    label_name: str,
    sub_cluster: dict,
    config: PipelineConfig,
) -> dict:
    """Use GPT to extract a story from a sub-cluster."""
    keywords = ", ".join(sub_cluster.get("keywords", [])[:10])
    excerpts = "\n---\n".join(
        doc["excerpt"][:400] for doc in sub_cluster.get("representative_docs", [])[:5]
    )

    prompt = STORY_SYSTEM_PROMPT.format(label_name=label_name)
    user_msg = f"""Label: {label_name}
Posts in this cluster: {sub_cluster['post_count']}
Top Keywords: {keywords}

Representative Post Excerpts:
{excerpts}"""

    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "title": result.get("title", "Untitled Story"),
            "summary": result.get("summary", ""),
            "pain_points": result.get("pain_points", []),
            "failed_solutions": result.get("failed_solutions", []),
            "build_legends_angle": result.get("build_legends_angle", ""),
            "representative_quotes": result.get("representative_quotes", []),
            "micro_personas": result.get("micro_personas", []),
            "post_count": sub_cluster["post_count"],
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
        }
    except Exception as e:
        logger.error(f"GPT story extraction failed for '{label_name}': {e}")
        return {
            "title": f"{label_name} — Story Pattern",
            "summary": "",
            "pain_points": [],
            "failed_solutions": [],
            "build_legends_angle": "",
            "representative_quotes": [],
            "post_count": sub_cluster["post_count"],
            "input_tokens": 0,
            "output_tokens": 0,
        }


# ── GPT Marketing Insights ─────────────────────────────────────────────────

MARKETING_SYSTEM_PROMPT = """You are a marketing strategist for Build Legends, a 5-minute daily confidence training app for kids ages 5-14.

Given a parent label (how parents describe their child) and the stories/struggles within it, generate marketing insights.

Respond with a JSON object:
{
  "ad_hooks": ["3-5 one-line ad hooks that would resonate with these parents"],
  "messaging_angles": ["2-3 messaging angles explaining how Build Legends helps"],
  "target_audience_description": "1-2 sentences describing the ideal target parent for this label",
  "emotional_triggers": ["3-5 emotional triggers that drive these parents to seek help"]
}"""


def _generate_marketing_insights(
    client: OpenAI,
    label_name: str,
    stories: list[dict],
    config: PipelineConfig,
) -> dict:
    """Generate marketing insights for a label."""
    stories_summary = "\n".join(
        f"- {s.get('title', 'Story')}: {s.get('summary', '')[:200]}"
        for s in stories
    )

    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": MARKETING_SYSTEM_PROMPT},
                {"role": "user", "content": f"Label: {label_name}\n\nStories:\n{stories_summary}"},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "ad_hooks": result.get("ad_hooks", []),
            "messaging_angles": result.get("messaging_angles", []),
            "target_audience_description": result.get("target_audience_description", ""),
            "emotional_triggers": result.get("emotional_triggers", []),
        }
    except Exception as e:
        logger.error(f"GPT marketing insights failed for '{label_name}': {e}")
        return {}


# ── Main Orchestrator ──────────────────────────────────────────────────────

def run_label_analysis(
    session,
    df: pd.DataFrame,
    pipeline_run_id: int,
    config: PipelineConfig,
) -> dict:
    """Run the full label analysis pipeline. Returns metrics dict."""
    start_time = time.time()
    metrics = {}

    logger.info(f"Starting label analysis on {len(df)} documents...")

    # ── Phase 1: Regex scan ──
    logger.info("Phase 1: Regex label scan...")
    regex_results = _scan_labels_regex(df)

    matched_post_ids = set()
    for slug, matches in regex_results.items():
        for post_id, _ in matches:
            matched_post_ids.add(post_id)

    regex_label_counts = {slug: len(matches) for slug, matches in regex_results.items()}
    logger.info(f"Phase 1 complete: {len(regex_results)} labels matched, {len(matched_post_ids)} unique posts")
    metrics["phase1_regex"] = {
        "labels_matched": len(regex_results),
        "unique_posts_matched": len(matched_post_ids),
        "label_counts": regex_label_counts,
    }

    # ── Phase 2: GPT discovery ──
    logger.info("Phase 2: GPT label discovery...")
    discovered_labels = _discover_labels_gpt(df, matched_post_ids, config)
    gpt_results = {}
    if discovered_labels:
        gpt_results = _scan_discovered_labels(df, discovered_labels)
        for slug, matches in gpt_results.items():
            for post_id, _ in matches:
                matched_post_ids.add(post_id)

    metrics["phase2_gpt_discovery"] = {
        "labels_discovered": len(discovered_labels),
        "discovered_label_names": [l["name"] for l in discovered_labels],
        "posts_matched_by_discovered": sum(len(m) for m in gpt_results.values()),
    }
    logger.info(f"Phase 2 complete: {len(discovered_labels)} new labels discovered")

    # ── Merge results and filter by min posts ──
    # Build combined label data
    all_labels: dict[str, dict] = {}

    # From regex
    for name, slug, _ in PREDEFINED_LABELS:
        if slug in regex_results and len(regex_results[slug]) >= config.LABEL_MIN_POSTS:
            all_labels[slug] = {
                "name": name,
                "slug": slug,
                "discovery_method": "regex",
                "matches": regex_results[slug],
                "example_phrases": list(set(phrase for _, phrase in regex_results[slug]))[:10],
            }

    # From GPT discovery
    for label in discovered_labels:
        slug = label["slug"]
        if slug in gpt_results and len(gpt_results[slug]) >= config.LABEL_MIN_POSTS:
            all_labels[slug] = {
                "name": label["name"],
                "slug": slug,
                "discovery_method": "gpt",
                "matches": gpt_results[slug],
                "example_phrases": label.get("example_phrases", []),
                "description": label.get("description", ""),
            }

    logger.info(f"Labels above {config.LABEL_MIN_POSTS} post threshold: {len(all_labels)}")
    metrics["labels_above_threshold"] = len(all_labels)

    # ── Phase 3 & 4: Sub-cluster and extract stories ──
    logger.info("Phase 3-4: Sub-clustering and GPT story extraction...")
    embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    total_input_tokens = 0
    total_output_tokens = 0
    total_stories = 0

    for slug, label_data in sorted(all_labels.items(), key=lambda x: len(x[1]["matches"]), reverse=True):
        label_name = label_data["name"]
        post_ids = [pid for pid, _ in label_data["matches"]]
        post_count = len(post_ids)

        logger.info(f"  Processing label '{label_name}' ({post_count} posts)...")

        # Sub-cluster
        sub_clusters = _subcluster_label(df, post_ids, config, embedding_model)

        # GPT story extraction for each sub-cluster
        stories = []
        for sc in sub_clusters:
            story = _extract_story_gpt(client, label_name, sc, config)
            stories.append(story)
            total_input_tokens += story.get("input_tokens", 0)
            total_output_tokens += story.get("output_tokens", 0)

        # GPT marketing insights
        marketing = _generate_marketing_insights(client, label_name, stories, config)

        # ── Store in DB ──
        label_record = store_label(session, {
            "pipeline_run_id": pipeline_run_id,
            "name": label_name,
            "slug": slug,
            "description": label_data.get("description", f"Parents who describe their child as '{label_name}'"),
            "post_count": post_count,
            "discovery_method": label_data["discovery_method"],
            "example_phrases": label_data["example_phrases"],
            "marketing_insights": marketing,
        })

        # Store stories
        for story in stories:
            store_label_story(session, {
                "label_id": label_record.id,
                "title": story["title"],
                "summary": story.get("summary", ""),
                "post_count": story.get("post_count", 0),
                "pain_points": story.get("pain_points"),
                "failed_solutions": story.get("failed_solutions"),
                "build_legends_angle": story.get("build_legends_angle", ""),
                "representative_quotes": story.get("representative_quotes"),
                "micro_personas": story.get("micro_personas"),
            })
            total_stories += 1

        # Store post-label mappings
        for post_id, phrase in label_data["matches"]:
            store_post_label(session, {
                "raw_post_id": post_id,
                "label_id": label_record.id,
                "pipeline_run_id": pipeline_run_id,
                "matched_phrase": phrase,
            })

        logger.info(f"    Stored: {len(stories)} stories, {post_count} post mappings")

    session.commit()

    # Cost estimate
    input_cost = total_input_tokens * 0.15 / 1_000_000
    output_cost = total_output_tokens * 0.6 / 1_000_000

    metrics.update({
        "total_labels_stored": len(all_labels),
        "total_stories_stored": total_stories,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": round(input_cost + output_cost, 4),
        "label_analysis_duration_seconds": round(time.time() - start_time, 1),
    })

    logger.info(
        f"Label analysis complete: {len(all_labels)} labels, {total_stories} stories, "
        f"~${metrics['estimated_cost_usd']}"
    )
    return metrics
