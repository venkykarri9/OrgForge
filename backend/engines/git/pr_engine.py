"""
GitHub Pull Request creation and management via the GitHub REST API.

Uses httpx — no GitHub SDK dependency needed for the narrow set of operations
OrgForge requires.
"""
import httpx
from dataclasses import dataclass


GITHUB_API = "https://api.github.com"


@dataclass
class PullRequest:
    number: int
    url: str
    html_url: str
    title: str
    state: str


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def create_pull_request(
    github_token: str,
    owner: str,
    repo: str,
    head_branch: str,
    base_branch: str,
    title: str,
    body: str,
    draft: bool = False,
) -> PullRequest:
    """
    Open a GitHub pull request.

    Args:
        github_token: Personal access token or OAuth token with repo scope
        owner: GitHub org or user name
        repo: Repository name
        head_branch: Branch with changes (source)
        base_branch: Target branch (usually 'main')
        title: PR title
        body: PR description (Markdown)
        draft: Whether to open as a draft

    Returns a PullRequest dataclass.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
            headers=_headers(github_token),
            json={
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
                "draft": draft,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return PullRequest(
        number=data["number"],
        url=data["url"],
        html_url=data["html_url"],
        title=data["title"],
        state=data["state"],
    )


async def get_pull_request(
    github_token: str, owner: str, repo: str, pr_number: int
) -> PullRequest:
    """Fetch an existing pull request by number."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=_headers(github_token),
        )
        resp.raise_for_status()
        data = resp.json()

    return PullRequest(
        number=data["number"],
        url=data["url"],
        html_url=data["html_url"],
        title=data["title"],
        state=data["state"],
    )


async def add_pr_comment(
    github_token: str, owner: str, repo: str, pr_number: int, body: str
) -> None:
    """Add a comment to a pull request."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            headers=_headers(github_token),
            json={"body": body},
        )
        resp.raise_for_status()


def parse_repo_parts(repo_url: str) -> tuple[str, str]:
    """
    Extract (owner, repo) from a GitHub URL.
    Handles https://github.com/owner/repo.git and git@github.com:owner/repo.git
    """
    url = repo_url.rstrip("/").removesuffix(".git")
    if "github.com/" in url:
        parts = url.split("github.com/")[-1].split("/")
    elif "github.com:" in url:
        parts = url.split("github.com:")[-1].split("/")
    else:
        raise ValueError(f"Cannot parse GitHub URL: {repo_url}")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from: {repo_url}")
    return parts[0], parts[1]
