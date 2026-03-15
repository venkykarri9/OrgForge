"""
LLM chat endpoint for TDD refinement.

POST /api/chat/stories/{story_id}/refine
  Body: { message: str, history: [{role, content}] }
  Returns: { reply: str, updated_tdd: str | null }

The user can send natural-language instructions to refine the generated TDD
before approving it. Claude always sees the current TDD + story context.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import anthropic

from backend.core.database import get_db
from backend.core.config import get_settings
from backend.models.story import Story

settings = get_settings()
router = APIRouter()

TDD_REFINE_SYSTEM = """You are a Salesforce technical architect assisting a developer in refining a Technical Design Document (TDD).

The developer will ask you to adjust, expand, correct, or clarify sections of the TDD.
- When asked to change the TDD, output the FULL updated TDD inside <TDD>...</TDD> tags.
- When just answering a question, respond conversationally without the <TDD> block.
- Keep responses focused and concise. Do not add unnecessary sections.
- Always maintain Salesforce best-practices (bulkification, selector/service layers, CRUD/FLS).
"""


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class RefineRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


class RefineResponse(BaseModel):
    reply: str
    updated_tdd: str | None = None


@router.post("/stories/{story_id}/refine", response_model=RefineResponse)
async def refine_tdd(
    story_id: uuid.UUID,
    req: RefineRequest,
    db: AsyncSession = Depends(get_db),
):
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if not story.tdd_document:
        raise HTTPException(status_code=400, detail="No TDD generated yet — draft it first")

    # Build the messages list
    messages: list[dict] = []

    # Inject current TDD as the first user/assistant context turn
    context_msg = (
        f"## Story: {story.jira_issue_key} — {story.jira_summary}\n\n"
        f"## Current TDD\n{story.tdd_document}"
    )
    messages.append({"role": "user", "content": context_msg})
    messages.append({"role": "assistant", "content": "I have the current TDD loaded. What would you like to change or ask?"})

    # Append conversation history
    for h in req.history:
        messages.append({"role": h.role, "content": h.content})

    # Append the new user message
    messages.append({"role": "user", "content": req.message})

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        system=TDD_REFINE_SYSTEM,
        messages=messages,
    )

    reply_text = response.content[0].text.strip()

    # Extract updated TDD if Claude produced one
    updated_tdd: str | None = None
    import re
    tdd_match = re.search(r"<TDD>(.*?)</TDD>", reply_text, re.DOTALL)
    if tdd_match:
        updated_tdd = tdd_match.group(1).strip()
        # Persist the update immediately
        story.tdd_document = updated_tdd
        await db.commit()
        # Return the reply without the raw XML tags
        reply_text = re.sub(r"<TDD>.*?</TDD>", "", reply_text, flags=re.DOTALL).strip()
        if not reply_text:
            reply_text = "TDD updated as requested."

    return RefineResponse(reply=reply_text, updated_tdd=updated_tdd)
