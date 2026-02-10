import logging
import time

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

DOMAIN_STOP_WORDS = [
    "kid", "kids", "child", "children", "baby", "babies",
    "parent", "parenting", "parents",
    "mom", "moms", "mother", "mothers",
    "dad", "dads", "father", "fathers",
    "husband", "wife", "partner", "spouse",
    "year", "years", "old", "month", "months",
    "son", "daughter", "boy", "girl",
    "just", "like", "really", "know", "think",
    "want", "get", "got", "going", "would",
    "one", "time", "things", "thing", "way",
    "said", "says", "told", "tell", "asked",
    "feel", "feeling", "felt", "don", "doesn",
]


def run_topic_modeling(
    df: pd.DataFrame, config: PipelineConfig
) -> tuple[BERTopic, pd.DataFrame, dict]:
    """Run BERTopic on preprocessed documents. Returns (model, results_df, metrics)."""
    start_time = time.time()
    documents = df["document"].tolist()

    logger.info(f"Running topic modeling on {len(documents)} documents...")

    # Auto-adjust parameters for small datasets
    min_cluster_size = config.MIN_CLUSTER_SIZE
    min_samples = config.MIN_SAMPLES
    n_neighbors = 15
    if len(documents) < 300:
        min_cluster_size = max(5, len(documents) // 20)
        min_samples = max(2, min_cluster_size // 3)
        n_neighbors = min(15, len(documents) // 10)
        logger.info(
            f"Small dataset: adjusted min_cluster_size={min_cluster_size}, "
            f"min_samples={min_samples}, n_neighbors={n_neighbors}"
        )

    # Embedding model
    embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)

    # UMAP
    umap_model = UMAP(
        n_neighbors=n_neighbors,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )

    # HDBSCAN
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        prediction_data=True,
    )

    # Vectorizer with domain stop words
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    all_stop_words = list(ENGLISH_STOP_WORDS) + DOMAIN_STOP_WORDS

    vectorizer = CountVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        stop_words=all_stop_words,
    )

    # BERTopic
    topic_model = BERTopic(
        embedding_model=embedding_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer,
        nr_topics=config.NUM_TOPICS,
        top_n_words=10,
        verbose=True,
    )

    topics, probs = topic_model.fit_transform(documents)

    # Add results to dataframe
    df = df.copy()
    df["topic"] = topics
    df["probability"] = probs if probs is not None else [None] * len(topics)

    # Metrics
    unique_topics = set(topics)
    outlier_count = sum(1 for t in topics if t == -1)
    initial_clusters = len(topic_model.get_topic_info()) - 1  # Exclude -1

    metrics = {
        "embedding_model": config.EMBEDDING_MODEL,
        "embedding_dimensions": 384,
        "umap_params": {
            "n_neighbors": 15,
            "n_components": 5,
            "min_dist": 0.0,
            "metric": "cosine",
        },
        "hdbscan_params": {
            "min_cluster_size": config.MIN_CLUSTER_SIZE,
            "min_samples": config.MIN_SAMPLES,
        },
        "initial_clusters_found": initial_clusters,
        "final_topics_after_merge": len([t for t in unique_topics if t != -1]),
        "outlier_count": outlier_count,
        "outlier_percentage": round(outlier_count / len(documents) * 100, 1) if documents else 0,
        "modeling_duration_seconds": round(time.time() - start_time, 1),
    }

    logger.info(
        f"Topic modeling complete: {metrics['final_topics_after_merge']} topics, "
        f"{outlier_count} outliers ({metrics['outlier_percentage']}%)"
    )

    return topic_model, df, metrics


def extract_topic_data(
    topic_model: BERTopic, df: pd.DataFrame, num_topics: int = 20
) -> list[dict]:
    """Extract the top N topics with keywords, stats, and representative docs."""
    topic_info = topic_model.get_topic_info()
    # Exclude outlier topic (-1)
    topic_info = topic_info[topic_info["Topic"] != -1].head(num_topics)

    topics_data = []
    for rank, (_, row) in enumerate(topic_info.iterrows(), start=1):
        topic_idx = row["Topic"]
        topic_words = topic_model.get_topic(topic_idx)

        # Keywords with weights
        keywords = [{"word": word, "weight": round(float(weight), 4)} for word, weight in topic_words[:10]]

        # Posts in this topic
        topic_posts = df[df["topic"] == topic_idx]
        post_count = len(topic_posts)
        avg_upvotes = round(float(topic_posts["upvotes"].mean()), 1) if post_count > 0 else 0.0

        # Representative docs: top 5 by upvotes
        top_posts = topic_posts.nlargest(5, "upvotes")
        representative_docs = []
        for _, post_row in top_posts.iterrows():
            doc = post_row["document"]
            representative_docs.append({
                "post_id": int(post_row["post_id"]),
                "excerpt": doc[:500],
                "upvotes": int(post_row["upvotes"]),
                "subreddit": post_row["subreddit"],
            })

        topics_data.append({
            "topic_index": int(topic_idx),
            "rank": rank,
            "keywords": keywords,
            "post_count": post_count,
            "avg_upvotes": avg_upvotes,
            "representative_docs": representative_docs,
        })

    return topics_data
