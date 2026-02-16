import { useTopics, useStats } from "../hooks/useTopics";
import TopicCard from "./TopicCard";
import TopicChart from "./TopicChart";

function TopicList() {
  const { data, isLoading, error } = useTopics();
  const { data: stats } = useStats();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading topics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">Failed to load topics.</p>
        <p className="text-sm text-gray-500 mt-2">
          Make sure the API is running and the pipeline has completed.
        </p>
      </div>
    );
  }

  const topics = data?.topics || [];

  if (topics.length === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">
          No topics yet
        </h2>
        <p className="text-gray-500">
          Run the pipeline to discover what parents care about.
        </p>
      </div>
    );
  }

  return (
    <div>
      {stats && (
        <div className="mb-8 bg-white rounded-lg border border-gray-200 p-6">
          <p className="text-lg text-gray-700">
            Filtered{" "}
            <span className="font-bold text-gray-900">
              {stats.total_posts.toLocaleString()}
            </span>{" "}
            parenting threads for emotional & behavioral challenges across{" "}
            <span className="font-bold text-gray-900">
              {stats.total_subreddits}
            </span>{" "}
            subreddits
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Lens: Meltdowns, anxiety, confidence, perfectionism, ADHD, behavioral issues
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
        Top {topics.length} Pain Points for Build Legends
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {topics.map((topic) => (
          <TopicCard key={topic.id} topic={topic} />
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Posts per Topic
        </h3>
        <TopicChart topics={topics} />
      </div>
    </div>
  );
}

export default TopicList;
