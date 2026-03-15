"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import MermaidDiagram from "@/components/diagrams/MermaidDiagram";

interface Story {
  id: string;
  jira_issue_key: string;
  jira_summary: string;
  jira_description: string | null;
  status: string;
  tdd_document: string | null;
  mermaid_erd: string | null;
  package_xml: string | null;
  github_pr_url: string | null;
}

export default function PipelinePage() {
  const { storyId } = useParams<{ storyId: string }>();
  const [story, setStory] = useState<Story | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const load = () =>
    fetch(`/api/pipeline/stories/${storyId}`)
      .then((r) => r.json())
      .then(setStory)
      .catch(console.error);

  useEffect(() => { load(); }, [storyId]);

  const action = async (path: string, body?: object) => {
    setLoading(true);
    setMessage("");
    try {
      const r = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await r.json();
      setMessage(r.ok ? "Done." : data.detail ?? "Error");
      await load();
    } finally {
      setLoading(false);
    }
  };

  if (!story) return <div className="p-10 text-gray-400">Loading…</div>;

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-8">
      <div>
        <p className="text-sm text-gray-400 font-mono">{story.jira_issue_key}</p>
        <h1 className="text-2xl font-semibold text-gray-900">{story.jira_summary}</h1>
        <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded">
          {story.status}
        </span>
      </div>

      {message && <p className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded">{message}</p>}

      {/* Pipeline actions */}
      <div className="flex flex-wrap gap-3">
        {story.status === "STORY_LOADED" && (
          <Btn label="Draft TDD (Claude)" loading={loading}
            onClick={() => action(`/api/pipeline/stories/${storyId}/draft-tdd`)} />
        )}
        {story.status === "TDD_DRAFTED" && (
          <Btn label="Approve TDD" loading={loading}
            onClick={() => action(`/api/pipeline/stories/${storyId}/approve-tdd`, { approved: true })} />
        )}
      </div>

      {/* TDD Document */}
      {story.tdd_document && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Technical Design Document</h2>
          <pre className="bg-gray-50 border rounded p-4 text-sm whitespace-pre-wrap overflow-auto max-h-96">
            {story.tdd_document}
          </pre>
        </section>
      )}

      {/* Mermaid ERD */}
      {story.mermaid_erd && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">Entity Relationship Diagram</h2>
          <MermaidDiagram chart={`erDiagram\n${story.mermaid_erd}`} />
        </section>
      )}

      {/* Package XML */}
      {story.package_xml && (
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">package.xml</h2>
          <pre className="bg-gray-50 border rounded p-4 text-xs font-mono whitespace-pre overflow-auto max-h-64">
            {story.package_xml}
          </pre>
        </section>
      )}

      {/* PR link */}
      {story.github_pr_url && (
        <a
          href={story.github_pr_url}
          target="_blank"
          rel="noreferrer"
          className="inline-block text-sm text-blue-600 hover:underline"
        >
          View GitHub PR →
        </a>
      )}
    </div>
  );
}

function Btn({ label, onClick, loading }: { label: string; onClick: () => void; loading: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
    >
      {loading ? "Working…" : label}
    </button>
  );
}
