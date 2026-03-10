import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useLabel, useLabelPosts } from "../hooks/useLabels";
import PostTable from "./PostTable";
import type { MicroPersona, StoryDetail } from "../types";

function PersonaCard({ persona }: { persona: MicroPersona }) {
  const isNewFormat = !!(persona.label || persona.child_profile || persona.trigger_scenario);

  if (isNewFormat) {
    return (
      <div className="bg-white rounded-lg border border-purple-200 shadow-sm overflow-hidden">
        {persona.label && (
          <div className="bg-purple-700 text-white px-4 py-2 text-sm font-bold">
            {persona.label}
          </div>
        )}
        <div className="p-4 space-y-3">
          {persona.child_profile && (
            <div>
              <p className="text-xs font-bold text-purple-600 uppercase tracking-wide mb-1">
                The Child
              </p>
              <p className="text-sm text-gray-800">{persona.child_profile}</p>
            </div>
          )}
          {persona.trigger_scenario && (
            <div>
              <p className="text-xs font-bold text-red-600 uppercase tracking-wide mb-1">
                The Trigger
              </p>
              <p className="text-sm text-gray-800">{persona.trigger_scenario}</p>
            </div>
          )}
          {persona.parent_circumstance && (
            <div>
              <p className="text-xs font-bold text-amber-600 uppercase tracking-wide mb-1">
                The Parent
              </p>
              <p className="text-sm text-gray-800">{persona.parent_circumstance}</p>
            </div>
          )}
          {persona.ad_hook && (
            <div className="bg-indigo-50 rounded-lg px-3 py-2 mt-2">
              <p className="text-xs font-bold text-indigo-600 uppercase tracking-wide mb-1">
                Ad Hook
              </p>
              <p className="text-sm font-medium text-indigo-900 italic">
                &ldquo;{persona.ad_hook}&rdquo;
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Old format fallback
  return (
    <div className="bg-purple-50 rounded-lg p-3">
      <p className="text-sm font-medium text-purple-900">
        {persona.description}
      </p>
      {persona.child_age && (
        <span className="text-xs text-purple-600 mt-1 inline-block mr-3">
          Age: {persona.child_age}
        </span>
      )}
      {persona.specific_trigger && (
        <p className="text-xs text-purple-700 mt-1 italic">
          Trigger: {persona.specific_trigger}
        </p>
      )}
    </div>
  );
}

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

      {/* Visceral Quotes — ad-ready quotes section */}
      {story.visceral_quotes && story.visceral_quotes.length > 0 && (
        <div className="mb-5">
          <h4 className="text-sm font-semibold text-red-700 mb-2">
            Ad-Ready Quotes
          </h4>
          <div className="space-y-2">
            {story.visceral_quotes.map((quote, i) => (
              <blockquote
                key={i}
                className="text-base text-red-900 bg-red-50 border-l-4 border-red-400 pl-4 pr-3 py-3 rounded-r-lg italic font-medium"
              >
                &ldquo;{quote}&rdquo;
              </blockquote>
            ))}
          </div>
        </div>
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
                className="text-sm text-amber-800 bg-amber-50 px-3 py-2 rounded flex items-start justify-between gap-2"
              >
                <span>&ldquo;{point.text}&rdquo;</span>
                {point.source_post?.url && (
                  <a
                    href={point.source_post.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-amber-600 hover:text-amber-900 flex-shrink-0 underline"
                  >
                    r/{point.source_post.subreddit} &rarr;
                  </a>
                )}
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

      {story.micro_personas && story.micro_personas.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            Micro-Personas (Ad Targeting)
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {story.micro_personas.map((persona, i) => (
              <PersonaCard key={i} persona={persona} />
            ))}
          </div>
        </div>
      )}

      {story.source_posts && story.source_posts.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Source Threads
          </h4>
          <div className="space-y-1.5">
            {story.source_posts.map((post) => (
              <div key={post.id} className="flex items-center gap-2 text-sm">
                <span className="text-gray-400 flex-shrink-0">r/{post.subreddit}</span>
                {post.url ? (
                  <a
                    href={post.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:text-indigo-800 hover:underline truncate"
                  >
                    {post.title}
                  </a>
                ) : (
                  <span className="text-gray-700 truncate">{post.title}</span>
                )}
                <span className="text-gray-400 flex-shrink-0 ml-auto">
                  {post.upvotes.toLocaleString()} pts
                </span>
              </div>
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
  const labelId = Number(id);
  const { data: label, isLoading, error } = useLabel(labelId);
  const [postsPage, setPostsPage] = useState(1);
  const [postsSort, setPostsSort] = useState<"pain" | "upvotes">("pain");
  const { data: postsData } = useLabelPosts(labelId, postsPage, 20, postsSort);

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

      {/* Source Posts */}
      {postsData && postsData.total > 0 && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-gray-900">
              Source Reddit Posts ({postsData.total})
            </h2>
            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
              <button
                onClick={() => { setPostsSort("pain"); setPostsPage(1); }}
                className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                  postsSort === "pain"
                    ? "bg-white text-red-700 shadow-sm font-medium"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Most Painful
              </button>
              <button
                onClick={() => { setPostsSort("upvotes"); setPostsPage(1); }}
                className={`text-xs px-3 py-1.5 rounded-md transition-colors ${
                  postsSort === "upvotes"
                    ? "bg-white text-gray-900 shadow-sm font-medium"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Most Upvoted
              </button>
            </div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200">
            <PostTable
              posts={postsData.posts}
              total={postsData.total}
              page={postsData.page}
              pageSize={postsData.page_size}
              onPageChange={setPostsPage}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default LabelDetail;
