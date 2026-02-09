import { useState } from "react";
import type { PostSummary } from "../types";

interface PostTableProps {
  posts: PostSummary[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

type SortField = "upvotes" | "title" | "subreddit";

function PostTable({ posts, total, page, pageSize, onPageChange }: PostTableProps) {
  const [sortField, setSortField] = useState<SortField>("upvotes");
  const [sortAsc, setSortAsc] = useState(false);

  const sortedPosts = [...posts].sort((a, b) => {
    const dir = sortAsc ? 1 : -1;
    if (sortField === "upvotes") return (a.upvotes - b.upvotes) * dir;
    if (sortField === "title") return a.title.localeCompare(b.title) * dir;
    return a.subreddit.localeCompare(b.subreddit) * dir;
  });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize);
  const sortIcon = (field: SortField) =>
    sortField === field ? (sortAsc ? " \u2191" : " \u2193") : "";

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                onClick={() => toggleSort("title")}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700"
              >
                Title{sortIcon("title")}
              </th>
              <th
                onClick={() => toggleSort("subreddit")}
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700"
              >
                Subreddit{sortIcon("subreddit")}
              </th>
              <th
                onClick={() => toggleSort("upvotes")}
                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:text-gray-700"
              >
                Upvotes{sortIcon("upvotes")}
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedPosts.map((post) => (
              <tr key={post.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  {post.url ? (
                    <a
                      href={post.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-indigo-600 hover:text-indigo-800"
                    >
                      {post.title}
                    </a>
                  ) : (
                    <span className="text-sm text-gray-900">{post.title}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-600">
                  r/{post.subreddit}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">
                  {post.upvotes.toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4 px-4">
          <p className="text-sm text-gray-600">
            Showing {(page - 1) * pageSize + 1}-
            {Math.min(page * pageSize, total)} of {total}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default PostTable;
