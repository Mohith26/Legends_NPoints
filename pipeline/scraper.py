import logging
import time
from datetime import datetime, timezone

import requests
from apify_client import ApifyClient

from pipeline.config import PipelineConfig
from pipeline.db import get_session, upsert_raw_post

logger = logging.getLogger(__name__)


def run_scraper(config: PipelineConfig) -> tuple[int, dict]:
    """Scrape Reddit posts via Apify. Returns (new_post_count, metrics_dict)."""
    metrics = {
        "subreddits_targeted": list(config.TARGET_SUBREDDITS),
        "subreddits_successfully_scraped": 0,
        "subreddits_failed": [],
        "total_threads_scraped": 0,
        "threads_per_subreddit": {},
        "total_comments_collected": 0,
        "date_range_of_posts": {"earliest": None, "latest": None},
        "scrape_duration_seconds": 0,
        "proxy_method": "apify_builtin",
        "apify_actor_version": config.APIFY_ACTOR,
    }

    start_time = time.time()
    session = get_session(config.DATABASE_URL)
    total_new = 0
    all_dates = []

    try:
        client = ApifyClient(config.APIFY_API_TOKEN)

        for subreddit in config.TARGET_SUBREDDITS:
            try:
                logger.info(f"Scraping r/{subreddit}...")
                sub_count = 0
                sub_comments = 0

                # maxItems counts posts+comments together, so multiply to account for comments
                max_items = config.MAX_POSTS_PER_SUBREDDIT * 6  # ~5 comments per post + the post itself
                actor_input = {
                    "startUrls": [
                        {"url": f"https://www.reddit.com/r/{subreddit}/top/?t={config.TIME_FILTER}"}
                    ],
                    "maxItems": max_items,
                    "maxPostCount": config.MAX_POSTS_PER_SUBREDDIT,
                    "maxComments": 5,
                    "sort": "top",
                    "time": config.TIME_FILTER,
                }

                if config.has_brightdata:
                    actor_input["proxy"] = {
                        "useApifyProxy": False,
                        "proxyUrls": [config.brightdata_proxy_url],
                    }
                    metrics["proxy_method"] = "brightdata_residential"

                run = client.actor(config.APIFY_ACTOR).call(run_input=actor_input)
                dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items

                # Separate posts and comments (regular actor mixes them)
                posts = [i for i in dataset_items if i.get("dataType") == "post" or "title" in i]
                comments_by_post: dict[str, list[str]] = {}
                for item in dataset_items:
                    if item.get("dataType") == "comment" and item.get("postId"):
                        post_id_key = item["postId"]
                        comments_by_post.setdefault(post_id_key, [])
                        if item.get("body"):
                            comments_by_post[post_id_key].append(item["body"])

                for item in posts:
                    reddit_id = item.get("parsedId") or item.get("id", "")
                    if not reddit_id:
                        continue

                    # Get comments for this post
                    full_id = item.get("id", "")
                    comment_texts = comments_by_post.get(full_id, [])[:5]
                    sub_comments += len(comment_texts)

                    created_utc = item.get("createdAt")
                    if created_utc and isinstance(created_utc, str):
                        try:
                            created_utc = datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
                            all_dates.append(created_utc)
                        except (ValueError, TypeError):
                            created_utc = None

                    post_data = {
                        "reddit_id": reddit_id,
                        "subreddit": item.get("parsedCommunityName") or subreddit,
                        "title": item.get("title", ""),
                        "body": item.get("body", ""),
                        "top_comments": comment_texts,
                        "upvotes": item.get("upVotes", 0),
                        "url": item.get("url", ""),
                        "author": item.get("username", ""),
                        "created_utc": created_utc,
                    }

                    post_id = upsert_raw_post(session, post_data)
                    if post_id:
                        sub_count += 1

                session.commit()
                metrics["threads_per_subreddit"][subreddit] = sub_count
                metrics["total_comments_collected"] += sub_comments
                metrics["subreddits_successfully_scraped"] += 1
                total_new += sub_count
                logger.info(f"  r/{subreddit}: {sub_count} posts scraped")

            except Exception as e:
                logger.error(f"  Failed to scrape r/{subreddit}: {e}")
                metrics["subreddits_failed"].append({"subreddit": subreddit, "error": str(e)})
                session.rollback()

        metrics["total_threads_scraped"] = total_new

        if all_dates:
            metrics["date_range_of_posts"] = {
                "earliest": min(all_dates).isoformat(),
                "latest": max(all_dates).isoformat(),
            }

    finally:
        metrics["scrape_duration_seconds"] = round(time.time() - start_time, 1)
        session.close()

    return total_new, metrics


def scrape_direct(config: PipelineConfig) -> tuple[int, dict]:
    """Fallback: scrape Reddit's old JSON API via BrightData proxies."""
    metrics = {
        "subreddits_targeted": list(config.TARGET_SUBREDDITS),
        "subreddits_successfully_scraped": 0,
        "subreddits_failed": [],
        "total_threads_scraped": 0,
        "threads_per_subreddit": {},
        "total_comments_collected": 0,
        "date_range_of_posts": {"earliest": None, "latest": None},
        "scrape_duration_seconds": 0,
        "proxy_method": "brightdata_residential_direct",
    }

    start_time = time.time()
    session = get_session(config.DATABASE_URL)
    total_new = 0
    all_dates = []

    proxies = {"https": config.brightdata_proxy_url} if config.has_brightdata else None
    headers = {"User-Agent": "LegendsScraper/1.0"}

    try:
        for subreddit in config.TARGET_SUBREDDITS:
            try:
                logger.info(f"Direct scraping r/{subreddit}...")
                sub_count = 0
                after = None

                while sub_count < config.MAX_POSTS_PER_SUBREDDIT:
                    url = f"https://old.reddit.com/r/{subreddit}/top.json?t={config.TIME_FILTER}&limit=100"
                    if after:
                        url += f"&after={after}"

                    resp = requests.get(url, headers=headers, proxies=proxies, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()

                    posts = data.get("data", {}).get("children", [])
                    if not posts:
                        break

                    for post in posts:
                        pd = post.get("data", {})
                        reddit_id = pd.get("id", "")
                        if not reddit_id:
                            continue

                        created_utc = None
                        if pd.get("created_utc"):
                            created_utc = datetime.fromtimestamp(pd["created_utc"], tz=timezone.utc)
                            all_dates.append(created_utc)

                        post_data = {
                            "reddit_id": reddit_id,
                            "subreddit": subreddit,
                            "title": pd.get("title", ""),
                            "body": pd.get("selftext", ""),
                            "top_comments": [],
                            "upvotes": pd.get("ups", 0),
                            "url": f"https://reddit.com{pd.get('permalink', '')}",
                            "author": pd.get("author", ""),
                            "created_utc": created_utc,
                        }

                        post_id = upsert_raw_post(session, post_data)
                        if post_id:
                            sub_count += 1

                    after = data.get("data", {}).get("after")
                    if not after:
                        break
                    time.sleep(1)  # Rate limiting

                session.commit()
                metrics["threads_per_subreddit"][subreddit] = sub_count
                metrics["subreddits_successfully_scraped"] += 1
                total_new += sub_count
                logger.info(f"  r/{subreddit}: {sub_count} posts scraped")

            except Exception as e:
                logger.error(f"  Failed to scrape r/{subreddit}: {e}")
                metrics["subreddits_failed"].append({"subreddit": subreddit, "error": str(e)})
                session.rollback()

        metrics["total_threads_scraped"] = total_new

        if all_dates:
            metrics["date_range_of_posts"] = {
                "earliest": min(all_dates).isoformat(),
                "latest": max(all_dates).isoformat(),
            }

    finally:
        metrics["scrape_duration_seconds"] = round(time.time() - start_time, 1)
        session.close()

    return total_new, metrics
