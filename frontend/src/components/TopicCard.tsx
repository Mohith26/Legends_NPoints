import { Link } from "react-router-dom";
import type { TopicSummary } from "../types";

interface TopicCardProps {
  topic: TopicSummary;
}

function TopicCard({ topic }: TopicCardProps) {
  return (
    <Link
      to={`/topic/${topic.id}`}
      className="block bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-5"
    >
      <div className="flex items-start gap-3 mb-3">
        <span className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-bold flex items-center justify-center">
          {topic.rank}
        </span>
        <h3 className="text-lg font-semibold text-gray-900 leading-tight">
          {topic.gpt_label || `Topic ${topic.rank}`}
        </h3>
      </div>

      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
        {topic.gpt_summary || "No summary available."}
      </p>

      <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
        <span>{topic.post_count} posts</span>
        <span>{topic.avg_upvotes.toFixed(0)} avg upvotes</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {topic.keywords.slice(0, 5).map((kw) => (
          <span
            key={kw.word}
            className="inline-block px-2 py-0.5 text-xs bg-indigo-50 text-indigo-700 rounded-full"
          >
            {kw.word}
          </span>
        ))}
      </div>
    </Link>
  );
}

export default TopicCard;
