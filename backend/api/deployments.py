"""
Deployment endpoints — validate and deploy to Salesforce.

POST /api/deployments/validate/{story_id}  → start validate-only deploy
POST /api/deployments/deploy/{story_id}    → start full deploy
GET  /api/deployments/{deployment_id}      → get deployment status
GET  /api/deployments/story/{story_id}     → list all deployments for a story
POST /api/deployments/{deployment_id}/poll → poll SF CLI for latest status
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.story import Story, StoryStatus
from backend.models.deployment import Deployment, DeploymentType, DeploymentStatus

router = APIRouter()


class DeploymentOut(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    deployment_type: DeploymentType
    status: DeploymentStatus
    sf_deploy_id: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class DeployRequest(BaseModel):
    org_alias: str           # SF CLI alias for the target org
    project_dir: str         # local path to the SFDX project
    test_level: str = "RunLocalTests"


@router.post("/validate/{story_id}", response_model=DeploymentOut)
async def validate_story(
    story_id: uuid.UUID,
    req: DeployRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a check-only (validate) deploy for a story's package.xml."""
    story = await _require_story_with_package(story_id, db)

    deployment = Deployment(
        story_id=story_id,
        deployment_type=DeploymentType.VALIDATE,
        status=DeploymentStatus.RUNNING,
        check_only=True,
        package_xml_snapshot=story.package_xml,
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    story.status = StoryStatus.VALIDATING
    await db.flush()

    from backend.engines.sf.deployer import validate
    try:
        result = validate(req.org_alias, story.package_xml, req.project_dir, req.test_level)
    except Exception as exc:
        deployment.status = DeploymentStatus.FAILED
        deployment.error_message = str(exc)
        deployment.finished_at = datetime.now(timezone.utc)
        story.status = StoryStatus.PACKAGE_READY
        return deployment

    deployment.sf_deploy_id = result.job_id
    deployment.log_output = result.stdout
    if result.success:
        deployment.status = DeploymentStatus.SUCCEEDED
        story.status = StoryStatus.VALIDATED
    else:
        deployment.status = DeploymentStatus.FAILED
        deployment.error_message = result.error_message
        story.status = StoryStatus.PACKAGE_READY

    deployment.finished_at = datetime.now(timezone.utc)
    return deployment


@router.post("/deploy/{story_id}", response_model=DeploymentOut)
async def deploy_story(
    story_id: uuid.UUID,
    req: DeployRequest,
    db: AsyncSession = Depends(get_db),
):
    """Deploy a story's package.xml to the target SF org."""
    story = await _require_story_with_package(story_id, db)
    if story.status != StoryStatus.VALIDATED:
        raise HTTPException(
            status_code=409,
            detail="Story must be VALIDATED before deploying",
        )

    deployment = Deployment(
        story_id=story_id,
        deployment_type=DeploymentType.DEPLOY,
        status=DeploymentStatus.RUNNING,
        check_only=False,
        package_xml_snapshot=story.package_xml,
        started_at=datetime.now(timezone.utc),
    )
    db.add(deployment)
    story.status = StoryStatus.DEPLOYING
    await db.flush()

    from backend.engines.sf.deployer import deploy
    try:
        result = deploy(req.org_alias, story.package_xml, req.project_dir, req.test_level)
    except Exception as exc:
        deployment.status = DeploymentStatus.FAILED
        deployment.error_message = str(exc)
        deployment.finished_at = datetime.now(timezone.utc)
        story.status = StoryStatus.VALIDATED
        return deployment

    deployment.sf_deploy_id = result.job_id
    deployment.log_output = result.stdout
    if result.success:
        deployment.status = DeploymentStatus.SUCCEEDED
        story.status = StoryStatus.DEPLOYED
    else:
        deployment.status = DeploymentStatus.FAILED
        deployment.error_message = result.error_message
        story.status = StoryStatus.VALIDATED

    deployment.finished_at = datetime.now(timezone.utc)
    return deployment


@router.get("/story/{story_id}", response_model=list[DeploymentOut])
async def list_story_deployments(
    story_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Deployment)
        .where(Deployment.story_id == story_id)
        .order_by(Deployment.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{deployment_id}", response_model=DeploymentOut)
async def get_deployment(deployment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    dep = await db.get(Deployment, deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep


@router.post("/{deployment_id}/poll", response_model=DeploymentOut)
async def poll_deployment(deployment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Poll SF CLI for the latest status of a running deploy."""
    dep = await db.get(Deployment, deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    if not dep.sf_deploy_id:
        raise HTTPException(status_code=400, detail="No SF deploy ID recorded")

    story = await db.get(Story, dep.story_id)
    org_alias = "default"  # TODO: resolve real alias from story/project/org

    from backend.engines.sf.deployer import poll_status
    result = poll_status(dep.sf_deploy_id, org_alias)

    dep.log_output = (dep.log_output or "") + "\n" + result.stdout
    if result.success:
        dep.status = DeploymentStatus.SUCCEEDED
        dep.finished_at = datetime.now(timezone.utc)
        if story:
            story.status = (
                StoryStatus.DEPLOYED
                if dep.deployment_type == DeploymentType.DEPLOY
                else StoryStatus.VALIDATED
            )
    elif result.error_message:
        dep.status = DeploymentStatus.FAILED
        dep.error_message = result.error_message
        dep.finished_at = datetime.now(timezone.utc)

    return dep


async def _require_story_with_package(story_id: uuid.UUID, db: AsyncSession) -> Story:
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not story.package_xml:
        raise HTTPException(status_code=400, detail="Story has no package.xml — build it first")
    return story
