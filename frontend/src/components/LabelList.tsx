import { Link } from "react-router-dom";
import { useLabels, useLabelStats } from "../hooks/useLabels";
import type { LabelSummary } from "../types";

function LabelCard({ label }: { label: LabelSummary }) {
  return (
    <Link
      to={`/labels/${label.id}`}
      className="block bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-5"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900 leading-tight">
          {label.name}
        </h3>
        {label.discovery_method === "gpt" && (
          <span className="flex-shrink-0 text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
            AI discovered
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
        <span className="font-medium text-gray-900">
          {label.post_count} posts
        </span>
        <span>{label.story_count} stories</span>
      </div>

      {label.stories.length > 0 && (
        <div className="space-y-1.5">
          {label.stories.slice(0, 3).map((story) => (
            <div
              key={story.id}
              className="text-sm text-gray-600 flex items-start gap-2"
            >
              <span className="text-indigo-400 mt-0.5 flex-shrink-0">
                &bull;
              </span>
              <span className="line-clamp-1">{story.title}</span>
            </div>
          ))}
          {label.stories.length > 3 && (
            <p className="text-xs text-gray-400 pl-4">
              +{label.stories.length - 3} more stories
            </p>
          )}
        </div>
      )}
    </Link>
  );
}

function LabelList() {
  const { data, isLoading, error } = useLabels();
  const { data: stats } = useLabelStats();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading labels...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">Failed to load labels.</p>
        <p className="text-sm text-gray-500 mt-2">
          Make sure the pipeline has run with label analysis enabled.
        </p>
      </div>
    );
  }

  const labels = data?.labels || [];

  if (labels.length === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">
          No labels yet
        </h2>
        <p className="text-gray-500">
          Run the pipeline with --build-legends to discover parent labels.
        </p>
      </div>
    );
  }

  return (
    <div>
      {stats && (
        <div className="mb-8 bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-lg text-gray-700">
            Discovered{" "}
            <span className="font-bold text-gray-900">{stats.total_labels}</span>{" "}
            parent labels across{" "}
            <span className="font-bold text-indigo-600">
              {stats.total_labeled_posts.toLocaleString()}
            </span>{" "}
            posts with{" "}
            <span className="font-bold text-gray-900">{stats.total_stories}</span>{" "}
            story patterns
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Labels are how parents describe and categorize their children's challenges
          </p>
          {data?.run_completed_at && (
            <p className="text-sm text-gray-500 mt-1">
              Last updated:{" "}
              {new Date(data.run_completed_at).toLocaleDateString()}
            </p>
          )}
        </div>
      )}

      <h2 className="text-xl font-bold text-gray-900 mb-6">
        Parent Labels for Kids
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {labels.map((label) => (
          <LabelCard key={label.id} label={label} />
        ))}
      </div>
    </div>
  );
}

export default LabelList;
