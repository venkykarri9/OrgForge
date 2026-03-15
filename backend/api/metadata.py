"""
Metadata browser endpoints.

GET /api/metadata/{org_id}/metrics         → org metrics snapshot (counts per type)
GET /api/metadata/{org_id}/catalogue       → return cached metadata catalogue from S3
GET /api/metadata/{org_id}/object/{name}   → describe a specific SF object's fields
GET /api/metadata/{org_id}/apex/{name}     → retrieve Apex class body
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import decrypt_token
from backend.models.org import Org
from backend.engines.sf.connector import get_sf_session, refresh_access_token
from backend.engines.sf.metadata_puller import (
    load_catalogue_from_s3,
    load_metrics_from_s3,
    compute_metrics,
    get_object_fields,
    get_apex_class_body,
)

router = APIRouter()


async def _get_sf(org_id: uuid.UUID, db: AsyncSession):
    """Helper: load org, refresh token if needed, return SF session."""
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    try:
        access_token = decrypt_token(org.access_token_enc)
    except Exception:
        raise HTTPException(status_code=401, detail="Cannot decrypt org token")

    # Attempt to use the stored token; if it fails the caller should refresh
    return get_sf_session(org.instance_url, access_token), org


@router.get("/{org_id}/metrics")
async def get_metrics(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Return org metadata metrics: count of each important type (objects, flows, apex, etc.).
    Falls back to computing from the catalogue if the metrics snapshot is missing.
    """
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    metrics = load_metrics_from_s3(org.org_id)
    if metrics is None:
        # Try computing from catalogue if metrics file not yet written
        catalogue = load_catalogue_from_s3(org.org_id)
        if catalogue is None:
            raise HTTPException(
                status_code=404,
                detail="Metadata not yet synced. POST /api/orgs/{org_id}/sync first.",
            )
        metrics = compute_metrics(catalogue)

    return metrics


@router.get("/{org_id}/catalogue")
async def get_catalogue(org_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return the metadata catalogue from S3 (must have been synced first)."""
    org = await db.get(Org, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    catalogue = load_catalogue_from_s3(org.org_id)
    if catalogue is None:
        raise HTTPException(
            status_code=404,
            detail="Metadata not yet synced. POST /api/orgs/{org_id}/sync first.",
        )
    return catalogue


@router.get("/{org_id}/object/{object_name}")
async def describe_object(
    org_id: uuid.UUID,
    object_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Return field definitions for a Salesforce object."""
    sf, _ = await _get_sf(org_id, db)
    try:
        fields = get_object_fields(sf, object_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"object": object_name, "fields": fields}


@router.get("/{org_id}/apex/{class_name}")
async def get_apex(
    org_id: uuid.UUID,
    class_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Return the body of an Apex class."""
    sf, _ = await _get_sf(org_id, db)
    try:
        body = get_apex_class_body(sf, class_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if body is None:
        raise HTTPException(status_code=404, detail=f"Apex class '{class_name}' not found")
    return {"class_name": class_name, "body": body}
