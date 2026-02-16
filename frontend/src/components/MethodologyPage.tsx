import { useMethodology } from "../hooks/useTopics";

function MetricCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      {children}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string | number | undefined }) {
  if (value === undefined || value === null) return null;
  return (
    <div className="flex justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-sm font-medium text-gray-900">
        {typeof value === "number" ? value.toLocaleString() : value}
      </span>
    </div>
  );
}

function MethodologyPage() {
  const { data, isLoading, error } = useMethodology();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading methodology data...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">No methodology data available.</p>
        <p className="text-sm text-gray-500 mt-2">
          Run the pipeline first to generate methodology metrics.
        </p>
      </div>
    );
  }

  const m = data.methodology;
  const ingestion = m.ingestion as Record<string, unknown> | undefined;
  const preprocessing = m.preprocessing as Record<string, unknown> | undefined;
  const topicModeling = m.topic_modeling as Record<string, unknown> | undefined;
  const summarization = m.summarization as Record<string, unknown> | undefined;

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Methodology</h2>
      <p className="text-gray-500 mb-8">
        Detailed metrics from the latest pipeline run
        {data.completed_at &&
          ` (${new Date(data.completed_at).toLocaleDateString()})`}
      </p>

      {/* Summary banner */}
      {preprocessing && !preprocessing.skipped && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6 mb-8">
          <p className="text-lg text-indigo-900">
            Analyzed{" "}
            <strong>
              {(preprocessing.total_documents_after_cleaning as number)?.toLocaleString()}
            </strong>{" "}
            threads containing{" "}
            <strong>
              {(preprocessing.total_words_processed as number)?.toLocaleString()}
            </strong>{" "}
            words across{" "}
            <strong>
              {(ingestion?.subreddits_successfully_scraped as number) ?? "?"}
            </strong>{" "}
            subreddits
            {ingestion?.date_range_of_posts &&
              typeof ingestion.date_range_of_posts === "object" ? (
                <>
                  {" "}spanning{" "}
                  <strong>
                    {String((ingestion.date_range_of_posts as Record<string, string>).earliest ?? "").slice(0, 7)}
                  </strong>{" "}
                  to{" "}
                  <strong>
                    {String((ingestion.date_range_of_posts as Record<string, string>).latest ?? "").slice(0, 7)}
                  </strong>
                </>
              ) : null}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Data Collection */}
        {ingestion && !ingestion.skipped && (
          <MetricCard title="Data Collection">
            <MetricRow
              label="Subreddits targeted"
              value={Array.isArray(ingestion.subreddits_targeted) ? (ingestion.subreddits_targeted as string[]).length : undefined}
            />
            <MetricRow
              label="Successfully scraped"
              value={ingestion.subreddits_successfully_scraped as number}
            />
            <MetricRow
              label="Failed"
              value={Array.isArray(ingestion.subreddits_failed) ? (ingestion.subreddits_failed as unknown[]).length : 0}
            />
            <MetricRow
              label="Total threads"
              value={ingestion.total_threads_scraped as number}
            />
            <MetricRow
              label="Total comments"
              value={ingestion.total_comments_collected as number}
            />
            <MetricRow
              label="Scrape duration"
              value={`${ingestion.scrape_duration_seconds}s`}
            />
            <MetricRow
              label="Proxy method"
              value={ingestion.proxy_method as string}
            />
          </MetricCard>
        )}

        {/* Processing */}
        {preprocessing && !preprocessing.skipped && (
          <MetricCard title="Text Processing">
            <MetricRow
              label="Documents before cleaning"
              value={preprocessing.total_documents_before_cleaning as number}
            />
            <MetricRow
              label="Removed (too short)"
              value={preprocessing.documents_removed_too_short as number}
            />
            <MetricRow
              label="Removed (duplicates)"
              value={preprocessing.documents_removed_duplicates as number}
            />
            <MetricRow
              label="Documents after cleaning"
              value={preprocessing.total_documents_after_cleaning as number}
            />
            <MetricRow
              label="Total words"
              value={preprocessing.total_words_processed as number}
            />
            <MetricRow
              label="Avg words/document"
              value={preprocessing.avg_words_per_document as number}
            />
            <MetricRow
              label="Min words"
              value={preprocessing.min_words_in_document as number}
            />
            <MetricRow
              label="Max words"
              value={preprocessing.max_words_in_document as number}
            />
          </MetricCard>
        )}

        {/* Build Legends Filter */}
        {(() => {
          const blFilter = preprocessing?.build_legends_filter as Record<string, unknown> | undefined;
          if (!blFilter) return null;
          const catCounts = (blFilter.keyword_category_counts as Record<string, number>) || {};
          return (
            <MetricCard title="Build Legends Filter">
              <MetricRow label="Documents before filter" value={blFilter.total_before_filtering as number} />
              <MetricRow label="Documents after filter" value={blFilter.total_after_filtering as number} />
              <MetricRow label="Filter pass rate" value={`${blFilter.filter_pass_rate}%`} />
              {Object.entries(catCounts).map(([cat, count]) => (
                <MetricRow key={cat} label={`Matched: ${cat}`} value={count} />
              ))}
            </MetricCard>
          );
        })()}

        {/* Analysis */}
        {topicModeling && !topicModeling.skipped && (
          <MetricCard title="Topic Modeling">
            <MetricRow
              label="Embedding model"
              value={topicModeling.embedding_model as string}
            />
            <MetricRow
              label="Embedding dimensions"
              value={topicModeling.embedding_dimensions as number}
            />
            <MetricRow
              label="Initial clusters"
              value={topicModeling.initial_clusters_found as number}
            />
            <MetricRow
              label="Final topics"
              value={topicModeling.final_topics_after_merge as number}
            />
            <MetricRow
              label="Outlier count"
              value={topicModeling.outlier_count as number}
            />
            <MetricRow
              label="Outlier rate"
              value={`${topicModeling.outlier_percentage}%`}
            />
            <MetricRow
              label="Duration"
              value={`${topicModeling.modeling_duration_seconds}s`}
            />
          </MetricCard>
        )}

        {/* Summarization */}
        {summarization && !summarization.skipped && (
          <MetricCard title="GPT Summarization">
            <MetricRow
              label="LLM model"
              value={summarization.llm_model as string}
            />
            <MetricRow
              label="API calls"
              value={summarization.total_api_calls as number}
            />
            <MetricRow
              label="Input tokens"
              value={summarization.total_input_tokens as number}
            />
            <MetricRow
              label="Output tokens"
              value={summarization.total_output_tokens as number}
            />
            <MetricRow
              label="Estimated cost"
              value={`$${summarization.estimated_cost_usd}`}
            />
            <MetricRow
              label="Failed"
              value={summarization.failed_summarizations as number}
            />
            <MetricRow
              label="Duration"
              value={`${summarization.summarization_duration_seconds}s`}
            />
          </MetricCard>
        )}
      </div>

      {/* Pipeline info */}
      <div className="mt-6 bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Pipeline Info
        </h3>
        <MetricRow
          label="Pipeline version"
          value={m.pipeline_version as string}
        />
        <MetricRow
          label="Total duration"
          value={
            m.total_pipeline_duration_seconds
              ? `${m.total_pipeline_duration_seconds}s`
              : undefined
          }
        />
        <MetricRow
          label="Run timestamp"
          value={
            m.run_timestamp
              ? new Date(m.run_timestamp as string).toLocaleString()
              : undefined
          }
        />
      </div>
    </div>
  );
}

export default MethodologyPage;
