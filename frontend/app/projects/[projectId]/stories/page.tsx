"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Story {
  id: string;
  jira_issue_key: string;
  jira_summary: string;
  status: string;
  github_pr_url: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  BACKLOG: "bg-gray-100 text-gray-600",
  STORY_LOADED: "bg-blue-100 text-blue-700",
  TDD_DRAFTED: "bg-yellow-100 text-yellow-700",
  TDD_APPROVED: "bg-green-100 text-green-700",
  IN_DEVELOPMENT: "bg-purple-100 text-purple-700",
  PACKAGE_READY: "bg-orange-100 text-orange-700",
  VALIDATING: "bg-yellow-100 text-yellow-700",
  VALIDATED: "bg-teal-100 text-teal-700",
  DEPLOYING: "bg-orange-100 text-orange-700",
  DEPLOYED: "bg-green-100 text-green-700",
  COMMITTED: "bg-indigo-100 text-indigo-700",
  PR_OPEN: "bg-blue-100 text-blue-700",
  MERGED: "bg-green-200 text-green-800",
};

export default function StoriesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [stories, setStories] = useState<Story[]>([]);

  useEffect(() => {
    fetch(`/api/pipeline/stories?project_id=${projectId}`)
      .then((r) => r.json())
      .then(setStories)
      .catch(console.error);
  }, [projectId]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <h1 className="text-2xl font-semibold">Stories</h1>
      <ul className="space-y-3">
        {stories.map((s) => (
          <li key={s.id} className="bg-white border rounded-lg p-4 flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm text-gray-500">{s.jira_issue_key}</span>
                <span className={`text-xs px-2 py-0.5 rounded font-medium ${STATUS_COLORS[s.status] ?? "bg-gray-100"}`}>
                  {s.status}
                </span>
              </div>
              <p className="text-gray-800">{s.jira_summary}</p>
            </div>
            <div className="flex gap-3 items-center">
              {s.github_pr_url && (
                <a href={s.github_pr_url} target="_blank" rel="noreferrer" className="text-sm text-blue-600 hover:underline">
                  PR
                </a>
              )}
              <Link
                href={`/projects/${projectId}/pipeline/${s.id}`}
                className="text-sm text-gray-600 hover:underline"
              >
                Pipeline →
              </Link>
            </div>
          </li>
        ))}
        {stories.length === 0 && (
          <p className="text-gray-400 text-sm">No stories loaded. Use Load Stories to pull from Jira.</p>
        )}
      </ul>
    </div>
  );
}
