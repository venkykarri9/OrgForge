"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface MetricItem {
  type: string;
  label: string;
  count: number;
  last_modified: string | null;
}

interface MetricGroup {
  group: string;
  total: number;
  items: MetricItem[];
}

interface Metrics {
  groups: MetricGroup[];
  grand_total: number;
}

interface Org {
  id: string;
  name: string;
  instance_url: string;
  username: string;
  is_sandbox: boolean;
}

const GROUP_ICONS: Record<string, string> = {
  "Data Model": "🗂️",
  "Apex & Code": "⚡",
  "Lightning & UI": "🎨",
  "Automation": "🔁",
  "Security & Access": "🔐",
  "Integration": "🔌",
  "Analytics": "📊",
  "Email & Content": "📧",
  "Sites & Communities": "🌐",
  "Territory Management": "🗺️",
  "Other": "📦",
};

export default function OrgDetailPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const [org, setOrg] = useState<Org | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const loadOrg = () =>
    fetch(`/api/orgs/${orgId}`)
      .then((r) => r.json())
      .then(setOrg)
      .catch(console.error);

  const loadMetrics = () =>
    fetch(`/api/metadata/${orgId}/metrics`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setMetrics(d))
      .catch(() => {});

  useEffect(() => {
    loadOrg();
    loadMetrics();
  }, [orgId]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncMsg("Sync queued — pulling all metadata from Salesforce…");
    try {
      await fetch(`/api/orgs/${orgId}/sync`, { method: "POST" });
      setTimeout(() => { loadMetrics(); setSyncing(false); }, 10000);
    } catch {
      setSyncMsg("Sync failed.");
      setSyncing(false);
    }
  };

  const toggleGroup = (group: string) =>
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      next.has(group) ? next.delete(group) : next.add(group);
      return next;
    });

  if (!org) return <div className="p-10 text-gray-400">Loading…</div>;

  return (
    <div className="max-w-6xl mx-auto px-6 py-10 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/orgs" className="text-sm text-blue-600 hover:underline">← All Orgs</Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{org.name}</h1>
          <p className="text-sm text-gray-500">{org.username} · {org.instance_url}</p>
          {org.is_sandbox && (
            <span className="mt-1 inline-block text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
              Sandbox
            </span>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "Syncing…" : "↺ Sync Metadata"}
          </button>
          <Link
            href={`/metadata?org_id=${orgId}`}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg text-sm hover:bg-gray-50"
          >
            Browse Raw Catalogue
          </Link>
        </div>
      </div>

      {syncMsg && (
        <p className="text-sm bg-blue-50 text-blue-700 px-4 py-2 rounded">{syncMsg}</p>
      )}

      {metrics ? (
        <>
          {/* Grand total banner */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl px-6 py-5 text-white flex items-center justify-between">
            <div>
              <p className="text-sm opacity-80">Total Metadata Components</p>
              <p className="text-4xl font-bold">{metrics.grand_total.toLocaleString()}</p>
            </div>
            <div className="text-5xl opacity-30">🏗️</div>
          </div>

          {/* Group summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {metrics.groups.map((g) => (
              <button
                key={g.group}
                onClick={() => toggleGroup(g.group)}
                className={`text-left bg-white border rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow ${
                  expandedGroups.has(g.group) ? "ring-2 ring-blue-500" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">{GROUP_ICONS[g.group] ?? "📦"}</span>
                  <span className={`text-xl font-bold ${g.total > 0 ? "text-gray-900" : "text-gray-300"}`}>
                    {g.total.toLocaleString()}
                  </span>
                </div>
                <p className="text-sm font-medium text-gray-700">{g.group}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {g.items.filter((i) => i.count > 0).length} types with data
                </p>
              </button>
            ))}
          </div>

          {/* Expanded group detail tables */}
          {metrics.groups
            .filter((g) => expandedGroups.has(g.group))
            .map((g) => (
              <section key={g.group} className="bg-white border rounded-xl overflow-hidden shadow-sm">
                <div className="flex items-center justify-between px-5 py-3 border-b bg-gray-50">
                  <h3 className="font-semibold text-gray-800">
                    {GROUP_ICONS[g.group]} {g.group}
                  </h3>
                  <span className="text-sm text-gray-500">{g.total.toLocaleString()} total</span>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-400 uppercase border-b">
                      <th className="text-left px-5 py-2 font-medium">Metadata Type</th>
                      <th className="text-right px-5 py-2 font-medium">Count</th>
                      <th className="text-right px-5 py-2 font-medium">Last Modified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((item) => (
                      <tr key={item.type} className={`border-b last:border-0 ${item.count === 0 ? "opacity-40" : ""}`}>
                        <td className="px-5 py-2 text-gray-700">{item.label}</td>
                        <td className="px-5 py-2 text-right font-mono font-semibold text-gray-900">
                          {item.count.toLocaleString()}
                        </td>
                        <td className="px-5 py-2 text-right text-gray-400">
                          {item.last_modified
                            ? new Date(item.last_modified).toLocaleDateString()
                            : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            ))}
        </>
      ) : (
        <div className="bg-gray-50 border border-dashed border-gray-300 rounded-xl p-12 text-center space-y-4">
          <p className="text-3xl">🏗️</p>
          <p className="text-gray-600 font-medium">No metadata synced yet</p>
          <p className="text-sm text-gray-400">
            Click Sync Metadata to pull all objects, flows, Apex classes, and more from this org.
          </p>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {syncing ? "Syncing…" : "↺ Sync Now"}
          </button>
        </div>
      )}
    </div>
  );
}
