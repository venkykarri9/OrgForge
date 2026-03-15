"""
AI endpoints — expose Claude-powered operations.

POST /api/ai/stories/{id}/review-code    → Apex code review vs TDD
POST /api/ai/orgs/{org_id}/diagram       → on-demand ERD for selected objects
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.story import Story
from backend.ai.code_reviewer import review
from backend.ai.diagram_builder import build_erd

router = APIRouter()


class CodeReviewRequest(BaseModel):
    apex_files: dict[str, str]  # {class_name: apex_body}


class DiagramRequest(BaseModel):
    objects: list[dict]  # [{name, fields: [...]}]


@router.post("/stories/{story_id}/review-code")
async def review_code(
    story_id: uuid.UUID,
    req: CodeReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    try:
        notes = await review(story, req.apex_files)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Claude error: {exc}")

    story.code_review_notes = notes
    return {"story_id": str(story_id), "review": notes}


@router.post("/orgs/{org_id}/diagram")
async def generate_diagram(org_id: uuid.UUID, req: DiagramRequest):
    try:
        erd = await build_erd(req.objects)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Claude error: {exc}")
    return {"erd": erd}
