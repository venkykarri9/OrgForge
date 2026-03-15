"""
Git operations using GitPython.

Handles: cloning, branching, staging, committing, and pushing
for Salesforce org source repos.
"""
import os
from pathlib import Path
from git import Repo, GitCommandError
from backend.core.config import get_settings

settings = get_settings()


def clone_or_open(repo_url: str, local_path: str, github_token: str) -> Repo:
    """
    Clone a GitHub repo if it doesn't exist locally, or open the existing one.
    Uses token-based authentication via the remote URL.
    """
    path = Path(local_path)
    if (path / ".git").exists():
        return Repo(local_path)

    # Inject token into URL: https://token@github.com/owner/repo.git
    auth_url = _inject_token(repo_url, github_token)
    return Repo.clone_from(auth_url, local_path)


def create_branch(repo: Repo, branch_name: str, base_branch: str = "main") -> None:
    """
    Create and checkout a new branch from base_branch.
    If branch already exists, just check it out.
    """
    repo.git.fetch("origin", base_branch)
    origin_ref = f"origin/{base_branch}"
    if branch_name in [b.name for b in repo.branches]:
        repo.git.checkout(branch_name)
    else:
        repo.git.checkout("-b", branch_name, origin_ref)


def stage_and_commit(repo: Repo, message: str, paths: list[str] | None = None) -> str:
    """
    Stage changed files and create a commit.
    If paths is None, stages all changes (git add -A).
    Returns the commit SHA.
    """
    if paths:
        repo.index.add(paths)
    else:
        repo.git.add("-A")

    if not repo.index.diff("HEAD") and not repo.untracked_files:
        raise ValueError("Nothing to commit — working tree is clean")

    commit = repo.index.commit(message)
    return commit.hexsha


def push_branch(repo: Repo, branch_name: str, github_token: str) -> None:
    """Push the branch to origin using token authentication."""
    origin = repo.remote("origin")
    # Temporarily set authenticated URL
    old_url = origin.url
    origin.set_url(_inject_token(old_url, github_token))
    try:
        origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
    finally:
        origin.set_url(old_url)


def get_diff_files(repo: Repo, base_branch: str = "main") -> list[str]:
    """
    Return a list of file paths that differ between the current HEAD and base_branch.
    Used by the package builder to detect what metadata changed.
    """
    repo.git.fetch("origin", base_branch)
    diff = repo.git.diff(f"origin/{base_branch}...HEAD", name_only=True)
    return [f for f in diff.splitlines() if f.strip()]


def _inject_token(url: str, token: str) -> str:
    """Inject a GitHub token into an HTTPS repo URL."""
    if "://" in url:
        scheme, rest = url.split("://", 1)
        return f"{scheme}://{token}@{rest}"
    return url
