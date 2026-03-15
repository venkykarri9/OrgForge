/**
 * Thin typed wrappers around the OrgForge backend API.
 * All functions assume Next.js rewrites proxy /api/* → backend.
 */

const BASE = "";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(err.detail ?? r.statusText);
  }
  return r.json();
}

// ── Orgs ─────────────────────────────────────────────────────────────────────
export const listOrgs = () => req<Org[]>("/api/orgs/");
export const syncOrg = (orgId: string) => req(`/api/orgs/${orgId}/sync`, { method: "POST" });

// ── Pipeline ──────────────────────────────────────────────────────────────────
export const listStories = (projectId?: string) =>
  req<Story[]>(`/api/pipeline/stories${projectId ? `?project_id=${projectId}` : ""}`);

export const getStory = (id: string) => req<Story>(`/api/pipeline/stories/${id}`);

export const draftTDD = (id: string) =>
  req(`/api/pipeline/stories/${id}/draft-tdd`, { method: "POST" });

export const approveTDD = (id: string, approved = true) =>
  req<Story>(`/api/pipeline/stories/${id}/approve-tdd`, {
    method: "POST",
    body: JSON.stringify({ approved }),
  });

// ── Deployments ───────────────────────────────────────────────────────────────
export const validateStory = (storyId: string, body: DeployRequest) =>
  req<Deployment>(`/api/deployments/validate/${storyId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export const deployStory = (storyId: string, body: DeployRequest) =>
  req<Deployment>(`/api/deployments/deploy/${storyId}`, {
    method: "POST",
    body: JSON.stringify(body),
  });

// ── Types ─────────────────────────────────────────────────────────────────────
export interface Org {
  id: string;
  name: string;
  instance_url: string;
  username: string;
  is_sandbox: boolean;
}

export interface Story {
  id: string;
  project_id: string;
  jira_issue_key: string;
  jira_summary: string;
  jira_description: string | null;
  jira_acceptance_criteria: string | null;
  status: string;
  tdd_document: string | null;
  mermaid_erd: string | null;
  package_xml: string | null;
  git_branch: string | null;
  github_pr_url: string | null;
}

export interface Deployment {
  id: string;
  story_id: string;
  deployment_type: string;
  status: string;
  sf_deploy_id: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface DeployRequest {
  org_alias: string;
  project_dir: string;
  test_level?: string;
}
