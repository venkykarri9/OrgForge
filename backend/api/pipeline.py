"""
Story pipeline endpoints — drives the state machine.

POST /api/pipeline/stories/load          → BACKLOG → STORY_LOADED (pull from Jira)
POST /api/pipeline/stories/{id}/draft-tdd → STORY_LOADED → TDD_DRAFTED (Claude)
POST /api/pipeline/stories/{id}/approve-tdd → TDD_DRAFTED → TDD_APPROVED
POST /api/pipeline/stories/{id}/build-package → IN_DEVELOPMENT → PACKAGE_READY
GET  /api/pipeline/stories               → list all stories
GET  /api/pipeline/stories/{id}          → get story detail
PATCH /api/pipeline/stories/{id}/status  → manual status override (admin)
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.story import Story, StoryStatus
from backend.models.project import Project

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class StoryOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    jira_issue_key: str
    jira_summary: str
    status: StoryStatus
    git_branch: str | None
    github_pr_url: str | None
    tdd_document: str | None
    mermaid_erd: str | None

    model_config = {"from_attributes": True}


class LoadStoriesRequest(BaseModel):
    project_id: uuid.UUID
    jira_server_url: str
    jira_token: str
    max_results: int = 20


class ApproveTDDRequest(BaseModel):
    approved: bool = True


class BuildPackageRequest(BaseModel):
    git_repo_local_path: str
    base_branch: str = "main"


class StatusOverrideRequest(BaseModel):
    status: StoryStatus


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/stories", response_model=list[StoryOut])
async def list_stories(
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(Story)
    if project_id:
        q = q.where(Story.project_id == project_id)
    result = await db.execute(q.order_by(Story.created_at.desc()))
    return result.scalars().all()


@router.get("/stories/{story_id}", response_model=StoryOut)
async def get_story(story_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.post("/stories/load", response_model=list[StoryOut])
async def load_stories(req: LoadStoriesRequest, db: AsyncSession = Depends(get_db)):
    """Pull backlog stories from Jira and upsert them into the DB."""
    from backend.engines.jira.jira_engine import get_jira_client, get_backlog_stories

    project = await db.get(Project, req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    jira = get_jira_client(req.jira_server_url, req.jira_token)
    try:
        jira_stories = get_backlog_stories(jira, project.jira_project_key, req.max_results)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jira error: {exc}")

    created: list[Story] = []
    for js in jira_stories:
        # Skip if already loaded
        existing = await db.execute(
            select(Story).where(
                Story.project_id == req.project_id,
                Story.jira_issue_key == js.key,
            )
        )
        if existing.scalar_one_or_none():
            continue

        story = Story(
            project_id=req.project_id,
            jira_issue_key=js.key,
            jira_summary=js.summary,
            jira_description=js.description,
            jira_acceptance_criteria=js.acceptance_criteria,
            status=StoryStatus.STORY_LOADED,
        )
        db.add(story)
        created.append(story)

    await db.flush()
    return created


@router.post("/stories/{story_id}/draft-tdd")
async def draft_tdd(
    story_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Enqueue Claude TDD generation (async). Returns task confirmation."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != StoryStatus.STORY_LOADED:
        raise HTTPException(
            status_code=409,
            detail=f"Story must be in STORY_LOADED state, currently: {story.status}",
        )

    from backend.workers.deploy_tasks import generate_tdd_task
    task = generate_tdd_task.delay(str(story_id))
    story.status = StoryStatus.TDD_DRAFTED  # optimistic update; worker sets final content
    return {"task_id": task.id, "status": "queued"}


@router.post("/stories/{story_id}/approve-tdd", response_model=StoryOut)
async def approve_tdd(
    story_id: uuid.UUID,
    req: ApproveTDDRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.status != StoryStatus.TDD_DRAFTED:
        raise HTTPException(status_code=409, detail="Story is not in TDD_DRAFTED state")
    if req.approved:
        story.status = StoryStatus.TDD_APPROVED
    else:
        story.status = StoryStatus.STORY_LOADED  # send back for re-drafting
    return story


@router.post("/stories/{story_id}/build-package", response_model=StoryOut)
async def build_package(
    story_id: uuid.UUID,
    req: BuildPackageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Detect changed metadata from git diff and build package.xml."""
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    from git import Repo
    from backend.engines.sf.package_builder import detect_changed_components, build_package_xml
    from backend.engines.git.git_engine import get_diff_files

    try:
        repo = Repo(req.git_repo_local_path)
        diff_files = get_diff_files(repo, req.base_branch)
        components = detect_changed_components(diff_files)
        if not components:
            raise HTTPException(status_code=400, detail="No changed SF metadata components detected")
        package_xml = build_package_xml(components)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    story.package_xml = package_xml
    story.status = StoryStatus.PACKAGE_READY
    return story


@router.patch("/stories/{story_id}/status", response_model=StoryOut)
async def override_status(
    story_id: uuid.UUID,
    req: StatusOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.status = req.status
    return story
