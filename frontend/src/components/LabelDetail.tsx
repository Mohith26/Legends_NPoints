import { useParams, Link } from "react-router-dom";
import { useLabel } from "../hooks/useLabels";
import type { StoryDetail } from "../types";

function StoryCard({ story }: { story: StoryDetail }) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-gray-900">{story.title}</h3>
        <span className="text-sm text-gray-500 flex-shrink-0 ml-4">
          {story.post_count} posts
        </span>
      </div>

      {story.summary && (
        <p className="text-gray-600 mb-4">{story.summary}</p>
      )}

      {story.pain_points && story.pain_points.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Pain Points
          </h4>
          <ul className="space-y-1.5">
            {story.pain_points.map((point, i) => (
              <li
                key={i}
                className="text-sm text-amber-800 bg-amber-50 px-3 py-2 rounded"
              >
                &ldquo;{point}&rdquo;
              </li>
            ))}
          </ul>
        </div>
      )}

      {story.failed_solutions && story.failed_solutions.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            What Parents Tried (and Why It Fell Short)
          </h4>
          <div className="space-y-2">
            {story.failed_solutions.map((fs, i) => (
              <div key={i} className="text-sm bg-red-50 px-3 py-2 rounded">
                <span className="font-medium text-red-800">{fs.solution}</span>
                <span className="text-red-600"> — {fs.why_failed}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {story.representative_quotes && story.representative_quotes.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Parent Voices
          </h4>
          <div className="space-y-2">
            {story.representative_quotes.map((quote, i) => (
              <blockquote
                key={i}
                className="text-sm italic text-gray-600 border-l-3 border-indigo-300 pl-3 py-1"
              >
                &ldquo;{quote}&rdquo;
              </blockquote>
            ))}
          </div>
        </div>
      )}

      {story.build_legends_angle && (
        <div className="bg-indigo-50 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-indigo-800 mb-1">
            How Build Legends Addresses This
          </h4>
          <p className="text-sm text-indigo-700">{story.build_legends_angle}</p>
        </div>
      )}
    </div>
  );
}

function LabelDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: label, isLoading, error } = useLabel(Number(id));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-gray-500">Loading label...</div>
      </div>
    );
  }

  if (error || !label) {
    return (
      <div className="text-center py-20">
        <p className="text-red-600">Label not found.</p>
        <Link to="/labels" className="text-indigo-600 hover:underline mt-2 inline-block">
          Back to labels
        </Link>
      </div>
    );
  }

  return (
    <div>
      <Link
        to="/labels"
        className="text-sm text-indigo-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to labels
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-3">
          <h1 className="text-2xl font-bold text-gray-900">{label.name}</h1>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                label.discovery_method === "gpt"
                  ? "bg-purple-100 text-purple-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {label.discovery_method === "gpt" ? "AI discovered" : "Pattern matched"}
            </span>
          </div>
        </div>

        {label.description && (
          <p className="text-gray-600 mb-4">{label.description}</p>
        )}

        <div className="flex items-center gap-6 text-sm text-gray-500">
          <span>
            <span className="font-semibold text-gray-900">
              {label.post_count}
            </span>{" "}
            posts
          </span>
          <span>
            <span className="font-semibold text-gray-900">
              {label.stories.length}
            </span>{" "}
            stories
          </span>
        </div>

        {label.example_phrases && label.example_phrases.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              How Parents Say It
            </h4>
            <div className="flex flex-wrap gap-2">
              {label.example_phrases.slice(0, 8).map((phrase, i) => (
                <span
                  key={i}
                  className="text-sm bg-gray-100 text-gray-700 px-3 py-1 rounded-full"
                >
                  &ldquo;{phrase}&rdquo;
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Marketing Insights */}
      {label.marketing_insights && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">
            Marketing Insights
          </h2>

          {label.marketing_insights.target_audience_description && (
            <p className="text-gray-600 mb-4">
              {label.marketing_insights.target_audience_description}
            </p>
          )}

          {label.marketing_insights.ad_hooks.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Ad Hooks
              </h4>
              <ul className="space-y-1">
                {label.marketing_insights.ad_hooks.map((hook, i) => (
                  <li
                    key={i}
                    className="text-sm text-indigo-700 bg-indigo-50 px-3 py-2 rounded"
                  >
                    {hook}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {label.marketing_insights.emotional_triggers.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Emotional Triggers
              </h4>
              <div className="flex flex-wrap gap-2">
                {label.marketing_insights.emotional_triggers.map(
                  (trigger, i) => (
                    <span
                      key={i}
                      className="text-sm bg-amber-50 text-amber-700 px-3 py-1 rounded-full"
                    >
                      {trigger}
                    </span>
                  )
                )}
              </div>
            </div>
          )}

          {label.marketing_insights.messaging_angles.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2">
                Messaging Angles
              </h4>
              <ul className="space-y-1">
                {label.marketing_insights.messaging_angles.map((angle, i) => (
                  <li key={i} className="text-sm text-gray-600 flex gap-2">
                    <span className="text-indigo-400">&bull;</span>
                    {angle}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Stories */}
      <h2 className="text-lg font-bold text-gray-900 mb-4">
        Story Patterns ({label.stories.length})
      </h2>
      <div className="space-y-4">
        {label.stories.map((story) => (
          <StoryCard key={story.id} story={story} />
        ))}
      </div>
    </div>
  );
}

export default LabelDetail;
