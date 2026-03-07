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

BUILD_LEGENDS_SYSTEM_PROMPT = """You are a customer research analyst for Build Legends, a 5-minute daily confidence training app for kids ages 5-14. You are analyzing Reddit posts to extract insights specifically about children's MENTAL HEALTH challenges.

SCOPE — you ONLY care about these themes:
- Anxiety (social anxiety, separation anxiety, school refusal, test anxiety, generalized worry)
- Confidence & self-esteem (self-doubt, insecurity, fear of judgment)
- Perfectionism (fear of failure, won't try new things, meltdowns over mistakes)
- Emotional regulation (meltdowns, outbursts, rage, big emotions, inability to cope)
- ADHD & neurodivergent challenges (focus, impulsivity, executive function, sensory overload)
- Behavioral issues (defiance, aggression, oppositional behavior)
- Social skills (making friends, bullying, peer rejection, social isolation)
- Depression & mood (sadness, withdrawal, loss of interest)
- Resilience & grit (giving up easily, low frustration tolerance, fixed mindset)

IMPORTANT: Every cluster has been pre-filtered to contain mental-health-relevant posts. DO NOT flag any cluster as off-topic. Instead, find the strongest mental health angle in every cluster and extract insights from that angle. Even if a cluster seems broad (e.g., "discipline challenges" or "parenting stress"), find and focus on how it connects to children's emotional wellbeing.

IMPORTANT: Focus on NEGATIVE posts — parents expressing pain, frustration, desperation, and struggle. Ignore advice posts, success stories, or positive anecdotes. We want the raw pain that drives parents to seek help.

Given a topic cluster with keywords and representative posts, extract structured insights.

Respond with a JSON object:

1. "label": A 3-6 word title for this mental health pain point (e.g., "Gifted Kid Perfectionism Spiral", "ADHD Homework Meltdown Cycle", "Social Anxiety School Refusal")

2. "summary": 2-3 sentences describing the core emotional/behavioral problem. Write from the parent's perspective. Be specific and visceral, not clinical. Use the desperate, raw language parents actually use in these posts.

3. "personas": Array of 3-4 MICRO-PERSONAS. These are NOT generic demographics — they are hyper-specific parent profiles that could be targeted in a Meta ad. Each object has:
   - "type": A full micro-persona sentence with 3 layers of specificity: (1) the child's specific challenge/diagnosis, (2) the specific trigger or scenario, (3) the parent's specific life circumstance or sacrifice. Make this feel like a real, specific person.
     - BAD: "Mom of anxious 8yo"
     - GOOD: "Stay-at-home mom of a twice-exceptional 8yo who was just told by the school he needs to repeat 2nd grade — she's terrified he's losing confidence forever"
     - GOOD: "Working single dad of a 10yo with ADHD who gets called by the school 3x a week because his son had another meltdown — he's running out of PTO"
     - GOOD: "Former teacher turned homeschool mom of a gifted but emotionally dysregulated 9yo after public school kept calling her in weekly — she gave up her career to get this right"
   - "child_age_range": e.g., "6-8", "9-12"
   - "key_struggle": The specific daily moment that breaks them — not a category, but a scene. e.g., "Every night at 6pm homework starts and within 10 minutes he's sobbing on the floor saying he's stupid while she stands there not knowing if holding him or pushing him will make it worse"

4. "failed_solutions": Array of 3-5 things parents tried that didn't work. Each object has:
   - "solution": What they tried (e.g., "Weekly talk therapy", "Reward charts", "Positive affirmations")
   - "why_failed": Why it fell short (e.g., "Child clams up in sessions", "Feels hollow — child sees through it")

5. "pain_points": Array of 3-5 vivid pain points using the actual desperate language from these posts. Pull near-direct quotes where possible. These should hit hard emotionally — the kind of raw confessions a parent would whisper at 2am. (e.g., "I watched my daughter rip up her drawing because one line was crooked and I realized she got this from me", "He told me he wishes he was never born and he's only 7")

6. "build_legends_angle": 2-3 sentences on how Build Legends specifically addresses this. Reference concrete product mechanics: daily 5-minute missions, confidence streaks, character growth system, parent dashboard insights. Explain why this works better than what they've tried.

Be specific and grounded in the actual post content. Use the real language parents use. Do not fabricate quotes unsupported by the excerpts."""


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


def summarize_topic_build_legends(client: OpenAI, topic_data: dict, config: PipelineConfig) -> dict:
    """Summarize a single topic with Build Legends customer research lens."""
    keywords = ", ".join(kw["word"] for kw in topic_data["keywords"][:10])
    excerpts = "\n---\n".join(
        doc["excerpt"][:400] for doc in topic_data.get("representative_docs", [])[:5]
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
                {"role": "system", "content": BUILD_LEGENDS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=config.GPT_TEMPERATURE,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
        usage = response.usage

        # Off-topic detection
        if result.get("off_topic"):
            logger.info(
                f"  Topic #{topic_data['rank']} flagged as off-topic: "
                f"{result.get('reason', 'no reason')}"
            )
            return {
                "label": result.get("label", ""),
                "summary": "",
                "personas": [],
                "failed_solutions": [],
                "pain_points": [],
                "build_legends_angle": "",
                "off_topic": True,
                "off_topic_reason": result.get("reason", ""),
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
            }

        return {
            "label": result.get("label", ""),
            "summary": result.get("summary", ""),
            "personas": result.get("personas", []),
            "failed_solutions": result.get("failed_solutions", []),
            "pain_points": result.get("pain_points", []),
            "build_legends_angle": result.get("build_legends_angle", ""),
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }
    except Exception as e:
        logger.error(f"GPT summarization failed for topic #{topic_data['rank']}: {e}")
        top_words = [kw["word"] for kw in topic_data["keywords"][:3]]
        return {
            "label": " & ".join(w.title() for w in top_words),
            "summary": f"Parents discussing topics related to {', '.join(top_words)}.",
            "personas": [],
            "failed_solutions": [],
            "pain_points": [],
            "build_legends_angle": "",
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


def summarize_all_topics_build_legends(
    topics_data: list[dict], config: PipelineConfig
) -> tuple[list[dict], dict]:
    """Summarize all topics with Build Legends customer research lens."""
    start_time = time.time()
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    total_input_tokens = 0
    total_output_tokens = 0
    failed = 0

    off_topic_count = 0
    for topic in topics_data:
        result = summarize_topic_build_legends(client, topic, config)
        topic["gpt_label"] = result["label"]
        topic["gpt_summary"] = result["summary"]
        topic["personas"] = result.get("personas", [])
        topic["failed_solutions"] = result.get("failed_solutions", [])
        topic["pain_points"] = result.get("pain_points", [])
        topic["build_legends_angle"] = result.get("build_legends_angle", "")
        topic["off_topic"] = result.get("off_topic", False)
        total_input_tokens += result.get("input_tokens", 0)
        total_output_tokens += result.get("output_tokens", 0)
        if "error" in result:
            failed += 1
        if result.get("off_topic"):
            off_topic_count += 1

        logger.info(f"  Topic #{topic['rank']}: {result['label']}")

    # Remove off-topic clusters
    before_filter = len(topics_data)
    topics_data = [t for t in topics_data if not t.get("off_topic")]
    if off_topic_count > 0:
        logger.info(f"  Removed {off_topic_count} off-topic clusters ({before_filter} -> {len(topics_data)})")
    # Re-rank after removing off-topic
    for i, topic in enumerate(topics_data, 1):
        topic["rank"] = i

    input_cost = total_input_tokens * 0.15 / 1_000_000
    output_cost = total_output_tokens * 0.6 / 1_000_000
    estimated_cost = round(input_cost + output_cost, 4)

    metrics = {
        "llm_model": config.GPT_MODEL,
        "analysis_lens": "build_legends",
        "total_api_calls": len(topics_data),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": estimated_cost,
        "failed_summarizations": failed,
        "summarization_duration_seconds": round(time.time() - start_time, 1),
    }

    logger.info(
        f"Build Legends summarization complete: {len(topics_data)} topics, "
        f"{total_input_tokens + total_output_tokens} tokens, ~${estimated_cost}"
    )

    return topics_data, metrics
