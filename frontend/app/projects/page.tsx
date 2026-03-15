"use client";
import { useEffect, useState } from "react";
import Link from "next/link";

interface Project {
  id: string;
  jira_project_key: string;
  jira_project_name: string;
  github_repo_url: string | null;
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    fetch("/api/pipeline/stories")
      .then((r) => r.json())
      .catch(() => []);
    // Projects aren't a direct API yet — placeholder
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-6 py-10 space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>
      <p className="text-sm text-gray-500">
        Projects link a Jira project to a Salesforce org and GitHub repo.
      </p>
      {projects.length === 0 && (
        <div className="bg-white border rounded-lg p-8 text-center text-gray-400 text-sm">
          No projects yet. Connect an org and a Jira project to get started.
        </div>
      )}
    </div>
  );
}
