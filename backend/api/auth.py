"""
OAuth2 callback handlers for Salesforce, GitHub, and Jira.

Each provider follows the same pattern:
  GET /api/auth/{provider}/login   → redirect to provider
  GET /api/auth/{provider}/callback → exchange code, store tokens
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.config import get_settings
from backend.core.security import encrypt_token
from backend.engines.sf import connector as sf_connector
from backend.models.org import Org

settings = get_settings()
router = APIRouter()


# ── Salesforce ──────────────────────────────────────────────────────────────

@router.get("/sf/login")
async def sf_login(sandbox: bool = False):
    """Redirect user to Salesforce OAuth2 authorization page."""
    url = sf_connector.get_auth_url(is_sandbox=sandbox)
    return RedirectResponse(url)


@router.get("/sf/callback")
async def sf_callback(
    code: str = Query(...),
    sandbox: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange SF authorization code for tokens.
    Stores encrypted tokens in the orgs table.
    Returns the new org ID for the frontend to use.
    """
    try:
        token_data = await sf_connector.exchange_code(code, is_sandbox=sandbox)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"SF token exchange failed: {exc}")

    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    instance_url = token_data["instance_url"]

    # Fetch org info via the identity URL
    sf = sf_connector.get_sf_session(instance_url, access_token)
    try:
        identity = sf.restful("sobjects/Organization", params={"fields": "Id,Name"})
        org_sf_id = identity["records"][0]["Id"] if identity.get("records") else token_data.get("id", "")
        org_name = identity["records"][0]["Name"] if identity.get("records") else "Unknown Org"
        username = token_data.get("id", "").split("/")[-1]
    except Exception:
        org_sf_id = str(uuid.uuid4())[:18]
        org_name = "Unknown Org"
        username = "unknown"

    org = Org(
        name=org_name,
        instance_url=instance_url,
        org_id=org_sf_id,
        username=username,
        access_token_enc=encrypt_token(access_token),
        refresh_token_enc=encrypt_token(refresh_token) if refresh_token else None,
        is_sandbox=sandbox,
    )
    db.add(org)
    await db.flush()
    return {"org_id": str(org.id), "org_name": org_name, "instance_url": instance_url}


# ── GitHub ───────────────────────────────────────────────────────────────────

@router.get("/github/login")
async def github_login():
    """Redirect user to GitHub OAuth2 authorization page."""
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_callback_url}"
        f"&scope=repo"
    )
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str = Query(...)):
    """
    Exchange GitHub authorization code for an access token.
    Returns the token for the frontend session.
    In production, store encrypted in a user/session table.
    """
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_callback_url,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=400, detail=f"GitHub token exchange failed: {data}")

    return {"github_token": token}


# ── Jira ─────────────────────────────────────────────────────────────────────

@router.get("/jira/login")
async def jira_login():
    """Redirect user to Jira OAuth2 authorization page (Atlassian Cloud)."""
    url = (
        f"https://auth.atlassian.com/authorize"
        f"?audience=api.atlassian.com"
        f"&client_id={settings.jira_client_id}"
        f"&scope=read%3Ajira-work%20manage%3Ajira-project"
        f"&redirect_uri={settings.jira_callback_url}"
        f"&state=jira-oauth"
        f"&response_type=code"
        f"&prompt=consent"
    )
    return RedirectResponse(url)


@router.get("/jira/callback")
async def jira_callback(code: str = Query(...)):
    """Exchange Jira authorization code for access token."""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://auth.atlassian.com/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": settings.jira_client_id,
                "client_secret": settings.jira_client_secret,
                "code": code,
                "redirect_uri": settings.jira_callback_url,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {"jira_token": data.get("access_token"), "expires_in": data.get("expires_in")}
