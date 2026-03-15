import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-blue-50 to-white px-4">
      <div className="max-w-3xl text-center space-y-6">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900">
          OrgForge
        </h1>
        <p className="text-xl text-gray-600">
          Ship Salesforce faster. Story → TDD → Deploy → PR — fully automated.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition"
          >
            Go to Dashboard
          </Link>
          <Link
            href="/api/auth/sf/login"
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition"
          >
            Connect Salesforce Org
          </Link>
        </div>
        <div className="grid grid-cols-3 gap-6 mt-12 text-left">
          {[
            { title: "Pull from Jira", desc: "Import backlog stories automatically" },
            { title: "AI-generated TDD", desc: "Claude produces technical design docs in seconds" },
            { title: "1-click deploy", desc: "Validate & deploy to Salesforce via SF CLI" },
          ].map((f) => (
            <div key={f.title} className="p-4 border rounded-lg bg-white shadow-sm">
              <h3 className="font-semibold text-gray-900">{f.title}</h3>
              <p className="text-sm text-gray-500 mt-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
