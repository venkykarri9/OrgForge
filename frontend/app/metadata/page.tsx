"use client";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

interface CatalogueEntry {
  fullName: string;
  lastModifiedDate: string;
}

function MetadataBrowserInner() {
  const params = useSearchParams();
  const orgId = params.get("org_id");
  const [catalogue, setCatalogue] = useState<Record<string, CatalogueEntry[]>>({});
  const [selectedType, setSelectedType] = useState<string>("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!orgId) return;
    fetch(`/api/metadata/${orgId}/catalogue`)
      .then((r) => {
        if (!r.ok) throw new Error("Not synced yet");
        return r.json();
      })
      .then(setCatalogue)
      .catch((e) => setError(e.message));
  }, [orgId]);

  const types = Object.keys(catalogue).sort();

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 space-y-6">
      <h1 className="text-2xl font-semibold">Metadata Browser</h1>
      {!orgId && <p className="text-gray-400 text-sm">Select an org from the Orgs page first.</p>}
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {types.length > 0 && (
        <div className="flex gap-6">
          <aside className="w-48 shrink-0 space-y-1">
            {types.map((t) => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`block w-full text-left text-sm px-3 py-1.5 rounded ${
                  selectedType === t ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {t}
                <span className="ml-1 text-xs opacity-60">({catalogue[t].length})</span>
              </button>
            ))}
          </aside>
          <main className="flex-1">
            {selectedType && (
              <ul className="space-y-1">
                {catalogue[selectedType].map((item) => (
                  <li key={item.fullName} className="text-sm text-gray-700 px-3 py-1.5 bg-white border rounded">
                    {item.fullName}
                  </li>
                ))}
              </ul>
            )}
            {!selectedType && <p className="text-gray-400 text-sm">Select a type on the left.</p>}
          </main>
        </div>
      )}
    </div>
  );
}

export default function MetadataPage() {
  return (
    <Suspense>
      <MetadataBrowserInner />
    </Suspense>
  );
}
