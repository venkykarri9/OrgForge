import Link from "next/link";

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">OrgForge</h1>
        <nav className="flex gap-6 text-sm text-gray-600">
          <Link href="/orgs" className="hover:text-blue-600">Orgs</Link>
          <Link href="/projects" className="hover:text-blue-600">Projects</Link>
          <Link href="/metadata" className="hover:text-blue-600">Metadata</Link>
        </nav>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-10 space-y-8">
        <h2 className="text-2xl font-semibold text-gray-800">Dashboard</h2>
        <div className="grid grid-cols-3 gap-6">
          <DashCard title="Connected Orgs" href="/orgs" cta="Manage orgs" />
          <DashCard title="Active Projects" href="/projects" cta="View projects" />
          <DashCard title="Deployments" href="/deployments" cta="View history" />
        </div>
      </main>
    </div>
  );
}

function DashCard({ title, href, cta }: { title: string; href: string; cta: string }) {
  return (
    <div className="bg-white rounded-lg border p-6 shadow-sm flex flex-col gap-4">
      <h3 className="font-medium text-gray-700">{title}</h3>
      <Link href={href} className="text-sm text-blue-600 hover:underline mt-auto">
        {cta} →
      </Link>
    </div>
  );
}
