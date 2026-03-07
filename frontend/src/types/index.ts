export interface Keyword {
  word: string;
  weight: number;
}

export interface Persona {
  type: string;
  child_age_range: string;
  key_struggle: string;
}

export interface FailedSolution {
  solution: string;
  why_failed: string;
}

export interface TopicSummary {
  id: number;
  rank: number;
  gpt_label: string | null;
  gpt_summary: string | null;
  post_count: number;
  avg_upvotes: number;
  keywords: Keyword[];
  pain_points: string[] | null;
  build_legends_angle: string | null;
}

export interface TopicListResponse {
  topics: TopicSummary[];
  pipeline_run_id: number | null;
  run_completed_at: string | null;
}

export interface RepresentativeDoc {
  post_id: number;
  excerpt: string;
  upvotes: number;
  subreddit: string;
}

export interface TopicDetail {
  id: number;
  rank: number;
  gpt_label: string | null;
  gpt_summary: string | null;
  post_count: number;
  avg_upvotes: number;
  keywords: Keyword[];
  representative_docs: RepresentativeDoc[];
  personas: Persona[] | null;
  failed_solutions: FailedSolution[] | null;
  pain_points: string[] | null;
  build_legends_angle: string | null;
}

export interface PostSummary {
  id: number;
  reddit_id: string;
  subreddit: string;
  title: string;
  upvotes: number;
  url: string | null;
  author: string | null;
  created_utc: string | null;
  probability: number | null;
}

export interface PostListResponse {
  posts: PostSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface Stats {
  total_posts: number;
  total_subreddits: number;
  subreddits: string[];
  last_run_date: string | null;
  last_run_status: string | null;
  total_topics: number;
  filtered_posts: number | null;
}

// ── Label Analysis Types ──────────────────────────────────────────────────

export interface MarketingInsights {
  ad_hooks: string[];
  messaging_angles: string[];
  target_audience_description: string;
  emotional_triggers: string[];
}

export interface StorySummary {
  id: number;
  title: string;
  summary: string | null;
  post_count: number;
  build_legends_angle: string | null;
}

export interface MicroPersona {
  description: string;
  child_age: string;
  specific_trigger: string;
}

export interface SourcePost {
  id: number;
  title: string;
  url: string | null;
  subreddit: string;
  upvotes: number;
}

export interface StoryDetail {
  id: number;
  title: string;
  summary: string | null;
  post_count: number;
  pain_points: string[] | null;
  failed_solutions: FailedSolution[] | null;
  build_legends_angle: string | null;
  representative_quotes: string[] | null;
  micro_personas: MicroPersona[] | null;
  source_posts: SourcePost[];
}

export interface LabelSummary {
  id: number;
  name: string;
  slug: string;
  post_count: number;
  discovery_method: string;
  story_count: number;
  stories: StorySummary[];
}

export interface LabelListResponse {
  labels: LabelSummary[];
  pipeline_run_id: number | null;
  run_completed_at: string | null;
}

export interface LabelDetail {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  post_count: number;
  discovery_method: string;
  example_phrases: string[] | null;
  marketing_insights: MarketingInsights | null;
  stories: StoryDetail[];
}

export interface LabelStats {
  total_labels: number;
  total_stories: number;
  total_labeled_posts: number;
  top_labels: LabelSummary[];
}

export interface MethodologyData {
  pipeline_run_id: number;
  completed_at: string | null;
  methodology: {
    ingestion?: Record<string, unknown>;
    preprocessing?: Record<string, unknown>;
    topic_modeling?: Record<string, unknown>;
    summarization?: Record<string, unknown>;
    total_pipeline_duration_seconds?: number;
    pipeline_version?: string;
    run_timestamp?: string;
  };
}
