"""
Celery tasks for AI generation and deploy operations.

generate_tdd_task: call Claude to generate TDD + Mermaid ERD for a story.
"""
import asyncio
from backend.workers.celery_app import celery_app


@celery_app.task(bind=True, name="ai.generate_tdd", max_retries=2, default_retry_delay=60)
def generate_tdd_task(self, story_id: str):
    """
    Generate a TDD document and Mermaid ERD for a story using Claude.

    Steps:
      1. Load story + project + org from DB
      2. Load metadata catalogue from S3 for context
      3. Call ai.tdd_generator.generate()
      4. Persist TDD + ERD back to the story row
    """
    try:
        return asyncio.run(_generate_tdd(story_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _generate_tdd(story_id: str) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from backend.core.config import get_settings
    from backend.models.story import Story, StoryStatus
    from backend.models.project import Project
    from backend.engines.sf.metadata_puller import load_catalogue_from_s3
    from backend.ai.tdd_generator import generate as generate_tdd
    import uuid

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        story = await db.get(Story, uuid.UUID(story_id))
        if not story:
            raise ValueError(f"Story {story_id} not found")

        project = await db.get(Project, story.project_id)
        if not project:
            raise ValueError(f"Project not found for story {story_id}")

        # Load metadata catalogue for context (may be None if not yet synced)
        catalogue = load_catalogue_from_s3(str(project.org_id))

        result = await generate_tdd(story=story, metadata_catalogue=catalogue)

        story.tdd_document = result["tdd"]
        story.mermaid_erd = result.get("erd")
        story.status = StoryStatus.TDD_DRAFTED

        await db.commit()

    await engine.dispose()
    return {"story_id": story_id, "status": "TDD_DRAFTED"}
