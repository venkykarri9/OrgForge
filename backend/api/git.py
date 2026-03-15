"""
Git / GitHub endpoints — commit story changes and open a PR.

POST /api/git/stories/{story_id}/commit  → commit + push branch
POST /api/git/stories/{story_id}/pr      → open GitHub PR
GET  /api/git/stories/{story_id}/pr      → get PR status
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.story import Story, StoryStatus
from backend.engines.git.git_engine import clone_or_open, create_branch, stage_and_commit, push_branch
from backend.engines.git.pr_engine import create_pull_request, get_pull_request, parse_repo_parts

router = APIRouter()


class CommitRequest(BaseModel):
    repo_url: str
    local_path: str
    github_token: str
    commit_message: str | None = None
    base_branch: str = "main"


class PRRequest(BaseModel):
    repo_url: str
    github_token: str
    base_branch: str = "main"
    pr_title: str | None = None
    pr_body: str | None = None
    draft: bool = False


class CommitOut(BaseModel):
    branch: str
    commit_sha: str


class PROut(BaseModel):
    pr_number: int
    html_url: str
    state: str


@router.post("/stories/{story_id}/commit", response_model=CommitOut)
async def commit_story(
    story_id: uuid.UUID,
    req: CommitRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a branch from the story key, commit all staged changes, and push.
    Transitions story to COMMITTED.
    """
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != StoryStatus.DEPLOYED:
        raise HTTPException(status_code=409, detail="Story must be DEPLOYED before committing")

    branch_name = f"orgforge/{story.jira_issue_key.lower()}"
    commit_message = req.commit_message or f"feat({story.jira_issue_key}): {story.jira_summary}"

    try:
        repo = clone_or_open(req.repo_url, req.local_path, req.github_token)
        create_branch(repo, branch_name, req.base_branch)
        sha = stage_and_commit(repo, commit_message)
        push_branch(repo, branch_name, req.github_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Git error: {exc}")

    story.git_branch = branch_name
    story.status = StoryStatus.COMMITTED
    return CommitOut(branch=branch_name, commit_sha=sha)


@router.post("/stories/{story_id}/pr", response_model=PROut)
async def open_pr(
    story_id: uuid.UUID,
    req: PRRequest,
    db: AsyncSession = Depends(get_db),
):
    """Open a GitHub PR for the story branch."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != StoryStatus.COMMITTED:
        raise HTTPException(status_code=409, detail="Story must be COMMITTED before opening a PR")
    if not story.git_branch:
        raise HTTPException(status_code=400, detail="No git branch recorded for this story")

    title = req.pr_title or f"[{story.jira_issue_key}] {story.jira_summary}"
    body = req.pr_body or _default_pr_body(story)

    try:
        owner, repo_name = parse_repo_parts(req.repo_url)
        pr = await create_pull_request(
            github_token=req.github_token,
            owner=owner,
            repo=repo_name,
            head_branch=story.git_branch,
            base_branch=req.base_branch,
            title=title,
            body=body,
            draft=req.draft,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"GitHub error: {exc}")

    story.github_pr_url = pr.html_url
    story.status = StoryStatus.PR_OPEN
    return PROut(pr_number=pr.number, html_url=pr.html_url, state=pr.state)


@router.get("/stories/{story_id}/pr", response_model=PROut)
async def get_pr(
    story_id: uuid.UUID,
    repo_url: str,
    github_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch the current state of the story's GitHub PR."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not story.github_pr_url:
        raise HTTPException(status_code=404, detail="No PR linked to this story")

    # Extract PR number from URL
    try:
        pr_number = int(story.github_pr_url.rstrip("/").split("/")[-1])
        owner, repo_name = parse_repo_parts(repo_url)
        pr = await get_pull_request(github_token, owner, repo_name, pr_number)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if pr.state == "closed":
        story.status = StoryStatus.MERGED

    return PROut(pr_number=pr.number, html_url=pr.html_url, state=pr.state)


def _default_pr_body(story: Story) -> str:
    lines = [
        f"## {story.jira_issue_key}: {story.jira_summary}",
        "",
        "### Description",
        story.jira_description or "_No description provided._",
        "",
    ]
    if story.jira_acceptance_criteria:
        lines += ["### Acceptance Criteria", story.jira_acceptance_criteria, ""]
    if story.tdd_document:
        lines += ["### TDD Summary", "_See TDD document attached to story._", ""]
    lines += ["---", "_Generated by OrgForge_"]
    return "\n".join(lines)
