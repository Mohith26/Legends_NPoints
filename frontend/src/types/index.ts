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
