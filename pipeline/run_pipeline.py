"""Pipeline orchestrator — CLI entry point.

Usage:
    python -m pipeline.run_pipeline                    # Full pipeline
    python -m pipeline.run_pipeline --skip-scrape      # Reuse existing data
    python -m pipeline.run_pipeline --skip-summarize   # Skip GPT labels
    python -m pipeline.run_pipeline --direct-scrape    # Use BrightData direct instead of Apify
    python -m pipeline.run_pipeline --build-legends    # Build Legends analysis lens
"""
import argparse
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
from pipeline.scraper import run_scraper, scrape_direct
from pipeline.summarizer import summarize_all_topics, summarize_all_topics_build_legends
from pipeline.topic_modeler import extract_topic_data, run_topic_modeling

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Legends NPoints Pipeline")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip scraping, use existing data")
    parser.add_argument("--skip-summarize", action="store_true", help="Skip GPT summarization")
    parser.add_argument("--direct-scrape", action="store_true", help="Use BrightData direct scraping")
    parser.add_argument("--build-legends", action="store_true", help="Build Legends analysis lens (filter + targeted summarization)")
    args = parser.parse_args()

    config = PipelineConfig()
    ensure_tables(config.DATABASE_URL)
    session = get_session(config.DATABASE_URL)

    pipeline_start = time.time()
    methodology = {}

    # Create pipeline run record
    run = create_pipeline_run(session, config_dict={
        "skip_scrape": args.skip_scrape,
        "skip_summarize": args.skip_summarize,
        "direct_scrape": args.direct_scrape,
        "build_legends_mode": args.build_legends,
        "subreddits": list(config.TARGET_SUBREDDITS),
        "max_posts_per_subreddit": config.MAX_POSTS_PER_SUBREDDIT,
    })
    logger.info(f"Pipeline run #{run.id} started (build_legends={args.build_legends})")

    try:
        # Step 1: Scrape
        if not args.skip_scrape:
            logger.info("=== STEP 1: Scraping Reddit ===")
            if args.direct_scrape:
                new_posts, scrape_metrics = scrape_direct(config)
            else:
                new_posts, scrape_metrics = run_scraper(config)
            methodology["ingestion"] = scrape_metrics
            logger.info(f"Scraped {new_posts} new posts")
        else:
            logger.info("=== STEP 1: Scraping SKIPPED ===")
            methodology["ingestion"] = {"skipped": True}

        # Step 2: Preprocess
        logger.info("=== STEP 2: Preprocessing ===")
        filter_mode = "build_legends" if args.build_legends else None
        df, preprocess_metrics = load_and_preprocess(session, filter_mode=filter_mode)
        methodology["preprocessing"] = preprocess_metrics

        if len(df) < 50:
            raise ValueError(f"Not enough documents ({len(df)}) for topic modeling. Need at least 50.")

        # Step 3: Topic modeling
        logger.info("=== STEP 3: Topic Modeling ===")
        mode = "build_legends" if args.build_legends else "default"
        topic_model, results_df, model_metrics = run_topic_modeling(df, config, mode=mode)
        methodology["topic_modeling"] = model_metrics

        # Extract topic data
        num_topics = config.BL_NUM_TOPICS if args.build_legends else config.NUM_TOPICS
        topics_data = extract_topic_data(topic_model, results_df, num_topics)

        # Step 4: Summarize
        if not args.skip_summarize:
            logger.info("=== STEP 4: GPT Summarization ===")
            if args.build_legends:
                topics_data, summarize_metrics = summarize_all_topics_build_legends(topics_data, config)
            else:
                topics_data, summarize_metrics = summarize_all_topics(topics_data, config)
            methodology["summarization"] = summarize_metrics
        else:
            logger.info("=== STEP 4: Summarization SKIPPED ===")
            methodology["summarization"] = {"skipped": True}
            for topic in topics_data:
                top_words = [kw["word"] for kw in topic["keywords"][:3]]
                topic["gpt_label"] = " & ".join(w.title() for w in top_words)
                topic["gpt_summary"] = f"Posts related to {', '.join(top_words)}."

        # Step 5: Store results
        logger.info("=== STEP 5: Storing Results ===")
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
                "personas": topic_data.get("personas"),
                "failed_solutions": topic_data.get("failed_solutions"),
                "pain_points": topic_data.get("pain_points"),
                "build_legends_angle": topic_data.get("build_legends_angle"),
            })

            # Map posts to topics
            topic_posts = results_df[results_df["topic"] == topic_data["topic_index"]]
            for _, post_row in topic_posts.iterrows():
                store_post_topic(session, {
                    "raw_post_id": int(post_row["post_id"]),
                    "topic_id": topic_record.id,
                    "pipeline_run_id": run.id,
                    "probability": float(post_row["probability"]) if post_row["probability"] is not None else None,
                })

        session.commit()

        # Finalize
        total_elapsed = round(time.time() - pipeline_start, 1)
        methodology["total_pipeline_duration_seconds"] = total_elapsed
        methodology["pipeline_version"] = config.PIPELINE_VERSION
        methodology["run_timestamp"] = datetime.now(timezone.utc).isoformat()

        update_pipeline_run(session, run.id, status="completed", methodology=methodology)
        logger.info(f"Pipeline run #{run.id} completed in {total_elapsed}s")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        methodology["error"] = str(e)
        update_pipeline_run(session, run.id, status="failed", methodology=methodology, error_message=str(e))
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
