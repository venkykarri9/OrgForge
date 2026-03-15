"""
Salesforce OAuth2 connector and authenticated session factory.

Handles:
- OAuth2 web-server flow (authorization URL, callback exchange)
- Token refresh
- Returns a simple_salesforce Salesforce instance ready for API calls
"""
import httpx
from simple_salesforce import Salesforce
from backend.core.config import get_settings
from backend.core.security import encrypt_token, decrypt_token

settings = get_settings()

SF_LOGIN_URL = "https://login.salesforce.com"
SF_SANDBOX_LOGIN_URL = "https://test.salesforce.com"


def get_auth_url(is_sandbox: bool = False) -> str:
    """Return the Salesforce OAuth2 authorization URL to redirect the user to."""
    base = SF_SANDBOX_LOGIN_URL if is_sandbox else SF_LOGIN_URL
    params = (
        f"response_type=code"
        f"&client_id={settings.sf_client_id}"
        f"&redirect_uri={settings.sf_callback_url}"
        f"&scope=full+refresh_token+offline_access"
        f"&prompt=login+consent"
    )
    return f"{base}/services/oauth2/authorize?{params}"


async def exchange_code(code: str, is_sandbox: bool = False) -> dict:
    """
    Exchange an authorization code for access + refresh tokens.

    Returns a dict with:
      access_token, refresh_token, instance_url, id (user identity URL)
    """
    base = SF_SANDBOX_LOGIN_URL if is_sandbox else SF_LOGIN_URL
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/services/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.sf_client_id,
                "client_secret": settings.sf_client_secret,
                "redirect_uri": settings.sf_callback_url,
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(refresh_token_enc: str, is_sandbox: bool = False) -> str:
    """
    Use a stored (encrypted) refresh token to get a new access token.
    Returns the new plaintext access token.
    """
    refresh_token = decrypt_token(refresh_token_enc)
    base = SF_SANDBOX_LOGIN_URL if is_sandbox else SF_LOGIN_URL
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/services/oauth2/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.sf_client_id,
                "client_secret": settings.sf_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def get_sf_session(instance_url: str, access_token: str) -> Salesforce:
    """Return an authenticated simple_salesforce session."""
    return Salesforce(instance_url=instance_url, session_id=access_token)
