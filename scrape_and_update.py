"""Scrape all subreddits, then re-run topic modeling + GPT to update dashboard."""
import logging
import time
from datetime import datetime, timezone

from pipeline.config import PipelineConfig
from pipeline.db import (
    create_pipeline_run,
    ensure_tables,
    get_session,
    store_post_topic,
    store_topic,
    update_pipeline_run,
)
from pipeline.preprocessor import load_and_preprocess
from pipeline.scraper import run_scraper
from pipeline.summarizer import summarize_all_topics
from pipeline.topic_modeler import extract_topic_data, run_topic_modeling
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

config = PipelineConfig()

# Only scrape subreddits we don't already have data for
ALREADY_SCRAPED = {
    "Parenting", "Mommit", "daddit", "beyondthebump",
    "toddlers", "NewParents", "Preschoolers", "ScienceBasedParenting",
}
NEW_SUBS = [s for s in config.TARGET_SUBREDDITS if s not in ALREADY_SCRAPED]

ensure_tables(config.DATABASE_URL)
session = get_session(config.DATABASE_URL)

pipeline_start = time.time()
methodology = {}

run = create_pipeline_run(session, config_dict={
    "target": "6000 posts",
    "new_subreddits": NEW_SUBS,
    "all_subreddits": list(config.TARGET_SUBREDDITS),
    "max_posts_per_subreddit": config.MAX_POSTS_PER_SUBREDDIT,
})
logger.info(f"Pipeline run #{run.id} started — targeting 6000 posts")
logger.info(f"New subreddits to scrape: {NEW_SUBS}")

try:
    # Step 1: Scrape only new subreddits
    logger.info("=== SCRAPING NEW SUBREDDITS ===")
    scrape_config = PipelineConfig()
    scrape_config.TARGET_SUBREDDITS = NEW_SUBS
    new_posts, scrape_metrics = run_scraper(scrape_config)
    methodology["ingestion"] = scrape_metrics

    total_posts = session.execute(text("SELECT COUNT(*) FROM raw_posts")).scalar()
    logger.info(f"Scraped {new_posts} new posts. Total in DB: {total_posts}")

    # Step 2: Preprocess
    logger.info("=== PREPROCESSING ===")
    df, preprocess_metrics = load_and_preprocess(session)
    methodology["preprocessing"] = preprocess_metrics

    # Step 3: Topic modeling
    logger.info("=== TOPIC MODELING ===")
    topic_model, results_df, model_metrics = run_topic_modeling(df, config)
    methodology["topic_modeling"] = model_metrics
    topics_data = extract_topic_data(topic_model, results_df, config.NUM_TOPICS)

    # Step 4: GPT summarize
    logger.info("=== GPT SUMMARIZATION ===")
    topics_data, summarize_metrics = summarize_all_topics(topics_data, config)
    methodology["summarization"] = summarize_metrics

    # Step 5: Clear old topics for this run and store new ones
    logger.info("=== STORING RESULTS ===")
    for topic_data in topics_data:
        topic_record = store_topic(session, {
            "pipeline_run_id": run.id,
            "topic_index": topic_data["topic_index"],
            "rank": topic_data["rank"],
            "keywords": topic_data["keywords"],
            "gpt_label": topic_data["gpt_label"],
            "gpt_summary": topic_data["gpt_summary"],
            "post_count": topic_data["post_count"],
            "avg_upvotes": topic_data["avg_upvotes"],
            "representative_docs": topic_data["representative_docs"],
        })
        topic_posts = results_df[results_df["topic"] == topic_data["topic_index"]]
        for _, post_row in topic_posts.iterrows():
            store_post_topic(session, {
                "raw_post_id": int(post_row["post_id"]),
                "topic_id": topic_record.id,
                "pipeline_run_id": run.id,
                "probability": float(post_row["probability"]) if post_row["probability"] is not None else None,
            })
    session.commit()

    total_elapsed = round(time.time() - pipeline_start, 1)
    methodology["total_pipeline_duration_seconds"] = total_elapsed
    methodology["pipeline_version"] = config.PIPELINE_VERSION
    methodology["run_timestamp"] = datetime.now(timezone.utc).isoformat()
    update_pipeline_run(session, run.id, status="completed", methodology=methodology)

    logger.info(f"=== DONE === Pipeline run #{run.id} completed in {total_elapsed}s")
    logger.info(f"Total posts: {total_posts} | Topics: {len(topics_data)}")
    for t in topics_data:
        logger.info(f"  #{t['rank']:2d} {t['gpt_label']} ({t['post_count']} posts)")

except Exception as e:
    logger.error(f"Pipeline failed: {e}", exc_info=True)
    update_pipeline_run(session, run.id, status="failed", error_message=str(e))
    raise
finally:
    session.close()
