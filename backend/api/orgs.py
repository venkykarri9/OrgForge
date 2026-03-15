"""
Salesforce org management endpoints.

GET  /api/orgs               → list connected orgs
GET  /api/orgs/{org_id}      → get org detail
DELETE /api/orgs/{org_id}    → disconnect org
POST /api/orgs/{org_id}/sync → trigger metadata pull (async via Celery)
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.org import Org
from backend.workers.metadata_tasks import pull_metadata_task

router = APIRouter()


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    instance_url: str
    org_id: str
    username: str
    is_sandbox: bool
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[OrgOut])
async def list_orgs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Org).where(Org.is_active == True))
    return result.scalars().all()


@router.get("/{org_id}", response_model=OrgOut)
async def get_org(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return org


@router.delete("/{org_id}", status_code=204)
async def disconnect_org(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    org.is_active = False
    return None


@router.post("/{org_id}/sync")
async def sync_metadata(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Enqueue an async Celery task to pull all metadata for this org."""
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    task = pull_metadata_task.delay(str(org_id))
    return {"task_id": task.id, "status": "queued"}
