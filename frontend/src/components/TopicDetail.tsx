import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useTopic, useTopicPosts } from "../hooks/useTopics";
import PostTable from "./PostTable";

function TopicDetail() {
  const { id } = useParams<{ id: string }>();
  const topicId = Number(id);
  const [page, setPage] = useState(1);

  const { data: topic, isLoading, error } = useTopic(topicId);
  const { data: postsData } = useTopicPosts(topicId, page);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading topic...</div>
      </div>
    );
  }

  if (error || !topic) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">Topic not found.</p>
        <Link to="/" className="text-indigo-600 hover:underline mt-2 inline-block">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link
        to="/"
        className="text-sm text-indigo-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to all topics
      </Link>

      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start gap-4 mb-4">
          <span className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-600 text-white text-lg font-bold flex items-center justify-center">
            {topic.rank}
          </span>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              {topic.gpt_label || `Topic ${topic.rank}`}
            </h2>
            <p className="text-gray-600 mt-1">{topic.gpt_summary}</p>
          </div>
        </div>

        <div className="flex items-center gap-6 text-sm text-gray-500 mb-4">
          <span>{topic.post_count} posts</span>
          <span>{topic.avg_upvotes.toFixed(0)} avg upvotes</span>
        </div>

        <div className="flex flex-wrap gap-2">
          {topic.keywords.map((kw) => (
            <span
              key={kw.word}
              className="inline-flex items-center gap-1 px-3 py-1 text-sm bg-indigo-50 text-indigo-700 rounded-full"
            >
              {kw.word}
              <span className="text-xs text-indigo-400">
                ({(kw.weight * 100).toFixed(1)}%)
              </span>
            </span>
          ))}
        </div>
      </div>

      {topic.representative_docs.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Representative Posts
          </h3>
          <div className="space-y-4">
            {topic.representative_docs.map((doc) => (
              <div key={doc.post_id} className="border-l-2 border-indigo-200 pl-4">
                <p className="text-sm text-gray-700">{doc.excerpt}</p>
                <p className="text-xs text-gray-400 mt-1">
                  r/{doc.subreddit} &middot; {doc.upvotes} upvotes
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {postsData && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            All Posts in This Topic
          </h3>
          <PostTable
            posts={postsData.posts}
            total={postsData.total}
            page={postsData.page}
            pageSize={postsData.page_size}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}

export default TopicDetail;
