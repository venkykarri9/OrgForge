"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface Org {
  id: string;
  name: string;
  instance_url: string;
  username: string;
  is_sandbox: boolean;
}

export default function OrgsPage() {
  const [orgs, setOrgs] = useState<Org[]>([]);

  useEffect(() => {
    fetch("/api/orgs/")
      .then((r) => r.json())
      .then(setOrgs)
      .catch(console.error);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Connected Orgs</h1>
        <a
          href="/api/auth/sf/login"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          + Connect Org
        </a>
      </div>
      {orgs.length === 0 && (
        <p className="text-gray-500 text-sm">No orgs connected yet.</p>
      )}
      <ul className="space-y-3">
        {orgs.map((org) => (
          <li key={org.id} className="bg-white border rounded-lg p-4 flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-800">{org.name}</p>
              <p className="text-sm text-gray-500">{org.username} · {org.instance_url}</p>
              {org.is_sandbox && (
                <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">Sandbox</span>
              )}
            </div>
            <div className="flex gap-3">
              <Link href={`/orgs/${org.id}`} className="text-sm text-blue-600 hover:underline font-medium">
                View Metrics →
              </Link>
              <Link href={`/metadata?org_id=${org.id}`} className="text-sm text-gray-600 hover:underline">
                Browse
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
