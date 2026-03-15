"""
Celery tasks for Salesforce metadata operations.

pull_metadata_task: pull all metadata for an org and store in S3.
"""
import asyncio
from backend.workers.celery_app import celery_app


@celery_app.task(bind=True, name="metadata.pull", max_retries=3, default_retry_delay=30)
def pull_metadata_task(self, org_id: str):
    """
    Pull the full metadata catalogue for the given org and store in S3.

    Steps:
      1. Load org from DB (sync via asyncio.run)
      2. Decrypt + refresh access token if needed
      3. Call metadata_puller.pull_all_metadata()
      4. Return summary
    """
    try:
        return asyncio.run(_pull_metadata(org_id))
    except Exception as exc:
        raise self.retry(exc=exc)


async def _pull_metadata(org_id: str) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from backend.core.config import get_settings
    from backend.core.security import decrypt_token
    from backend.engines.sf.connector import get_sf_session, refresh_access_token
    from backend.engines.sf.metadata_puller import pull_all_metadata
    from backend.models.org import Org
    import uuid

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        org = await db.get(Org, uuid.UUID(org_id))
        if not org:
            raise ValueError(f"Org {org_id} not found")

        try:
            access_token = decrypt_token(org.access_token_enc)
        except Exception:
            raise ValueError("Cannot decrypt org token")

        # Refresh token if org has a refresh token stored
        if org.refresh_token_enc:
            try:
                access_token = await refresh_access_token(org.refresh_token_enc, org.is_sandbox)
                from backend.core.security import encrypt_token
                org.access_token_enc = encrypt_token(access_token)
                await db.commit()
            except Exception:
                pass  # fall back to stored access token

        sf = get_sf_session(org.instance_url, access_token)
        catalogue = pull_all_metadata(sf, org.org_id)

    await engine.dispose()
    return {
        "org_id": org_id,
        "types_pulled": list(catalogue.keys()),
        "total_components": sum(len(v) for v in catalogue.values()),
    }
