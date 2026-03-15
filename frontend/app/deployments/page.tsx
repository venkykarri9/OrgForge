"use client";
import { useEffect, useState } from "react";

interface Deployment {
  id: string;
  story_id: string;
  deployment_type: string;
  status: string;
  sf_deploy_id: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-gray-100 text-gray-600",
  RUNNING: "bg-yellow-100 text-yellow-700",
  SUCCEEDED: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
  CANCELLED: "bg-gray-100 text-gray-500",
};

export default function DeploymentsPage() {
  const [deployments] = useState<Deployment[]>([]);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <h1 className="text-2xl font-semibold">Deployment History</h1>
      {deployments.length === 0 && (
        <div className="bg-white border rounded-lg p-8 text-center text-gray-400 text-sm">
          No deployments yet. Deployments appear here after you validate or deploy a story.
        </div>
      )}
      <ul className="space-y-3">
        {deployments.map((d) => (
          <li key={d.id} className="bg-white border rounded-lg p-4 space-y-1">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">{d.deployment_type}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[d.status]}`}>
                {d.status}
              </span>
            </div>
            {d.sf_deploy_id && (
              <p className="text-xs text-gray-400 font-mono">SF Job: {d.sf_deploy_id}</p>
            )}
            {d.error_message && (
              <p className="text-xs text-red-600">{d.error_message}</p>
            )}
            <p className="text-xs text-gray-400">
              {d.started_at ? new Date(d.started_at).toLocaleString() : "—"}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
