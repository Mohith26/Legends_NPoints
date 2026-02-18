import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PipelineConfig:
    # Apify
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    APIFY_ACTOR: str = "trudax/reddit-scraper"

    # BrightData proxy (optional fallback)
    BRIGHTDATA_PROXY_HOST: str = os.getenv("BRIGHTDATA_PROXY_HOST", "")
    BRIGHTDATA_PROXY_PORT: str = os.getenv("BRIGHTDATA_PROXY_PORT", "")
    BRIGHTDATA_PROXY_USERNAME: str = os.getenv("BRIGHTDATA_PROXY_USERNAME", "")
    BRIGHTDATA_PROXY_PASSWORD: str = os.getenv("BRIGHTDATA_PROXY_PASSWORD", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/legends_npoints")

    # Subreddits
    TARGET_SUBREDDITS: list[str] = field(default_factory=lambda: [
        "Parenting",
        "Mommit",
        "daddit",
        "beyondthebump",
        "toddlers",
        "NewParents",
        "Preschoolers",
        "ScienceBasedParenting",
        "sleeptrain",
        "breastfeeding",
        "SAHP",
        "workingmoms",
        "raisingkids",
    ])

    # Scraping
    MAX_POSTS_PER_SUBREDDIT: int = 750
    TIME_FILTER: str = "year"
    SORT_BY: str = "top"

    # Topic modeling
    NUM_TOPICS: int = 20
    MIN_CLUSTER_SIZE: int = 15
    MIN_SAMPLES: int = 5
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Build Legends mode overrides
    BL_NUM_TOPICS: int = 15
    BL_MIN_CLUSTER_SIZE: int = 8
    BL_MIN_SAMPLES: int = 3

    # Summarization
    GPT_MODEL: str = "gpt-4o-mini"
    GPT_TEMPERATURE: float = 0.3

    # Pipeline version
    PIPELINE_VERSION: str = "3.0.0"

    @property
    def has_brightdata(self) -> bool:
        return bool(self.BRIGHTDATA_PROXY_HOST and self.BRIGHTDATA_PROXY_USERNAME)

    @property
    def brightdata_proxy_url(self) -> str:
        return (
            f"http://{self.BRIGHTDATA_PROXY_USERNAME}:{self.BRIGHTDATA_PROXY_PASSWORD}"
            f"@{self.BRIGHTDATA_PROXY_HOST}:{self.BRIGHTDATA_PROXY_PORT}"
        )
