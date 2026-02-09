import json
import logging
import time

from openai import OpenAI

from pipeline.config import PipelineConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are analyzing Reddit parenting communities to identify what parents care about most.
Given a topic cluster from a topic model, generate a concise human-readable label and summary.

Respond with a JSON object containing:
- "label": A 3-6 word title for this topic (e.g., "Sleep Training Struggles", "Screen Time Debates")
- "summary": A 2-3 sentence description of what this topic is about, what parents are discussing, and why it matters to them.

Be specific and insightful. Focus on the parenting concern, not generic descriptions."""


def summarize_topic(client: OpenAI, topic_data: dict, config: PipelineConfig) -> dict:
    """Summarize a single topic using GPT-4o-mini."""
    keywords = ", ".join(kw["word"] for kw in topic_data["keywords"][:10])
    excerpts = "\n---\n".join(
        doc["excerpt"][:300] for doc in topic_data.get("representative_docs", [])[:5]
    )

    user_prompt = f"""Topic Rank: #{topic_data['rank']}
Post Count: {topic_data['post_count']}
Average Upvotes: {topic_data['avg_upvotes']}
Top Keywords: {keywords}

Representative Post Excerpts:
{excerpts}"""

    try:
        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.GPT_TEMPERATURE,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        usage = response.usage

        return {
            "label": result.get("label", ""),
            "summary": result.get("summary", ""),
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }
    except Exception as e:
        logger.error(f"GPT summarization failed for topic #{topic_data['rank']}: {e}")
        # Fallback: keyword-based label
        top_words = [kw["word"] for kw in topic_data["keywords"][:3]]
        return {
            "label": " & ".join(w.title() for w in top_words),
            "summary": f"Parents discussing topics related to {', '.join(top_words)}.",
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(e),
        }


def summarize_all_topics(
    topics_data: list[dict], config: PipelineConfig
) -> tuple[list[dict], dict]:
    """Summarize all topics. Returns (updated topics_data, metrics)."""
    start_time = time.time()
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    total_input_tokens = 0
    total_output_tokens = 0
    failed = 0

    for topic in topics_data:
        result = summarize_topic(client, topic, config)
        topic["gpt_label"] = result["label"]
        topic["gpt_summary"] = result["summary"]
        total_input_tokens += result.get("input_tokens", 0)
        total_output_tokens += result.get("output_tokens", 0)
        if "error" in result:
            failed += 1

        logger.info(f"  Topic #{topic['rank']}: {result['label']}")

    # Cost estimate: gpt-4o-mini pricing
    input_cost = total_input_tokens * 0.15 / 1_000_000
    output_cost = total_output_tokens * 0.6 / 1_000_000
    estimated_cost = round(input_cost + output_cost, 4)

    metrics = {
        "llm_model": config.GPT_MODEL,
        "total_api_calls": len(topics_data),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": estimated_cost,
        "failed_summarizations": failed,
        "summarization_duration_seconds": round(time.time() - start_time, 1),
    }

    logger.info(
        f"Summarization complete: {len(topics_data)} topics, "
        f"{total_input_tokens + total_output_tokens} tokens, ~${estimated_cost}"
    )

    return topics_data, metrics
