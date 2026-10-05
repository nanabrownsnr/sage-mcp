"""Twynity manifest and OAuth connection contract for Sage Accounting."""

import secrets
from datetime import UTC, datetime, timedelta
from logging import getLogger
from urllib.parse import urlencode

import httpx
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.auth import get_identity
from app.config import settings
from app.connection_store import get_active_store

logger = getLogger(__name__)
OAUTH_PROVIDER = "sage"


def _allowed_redirect_uri(redirect_uri: str) -> bool:
    configured = {
        value.strip()
        for value in settings.SAGE_OAUTH_REDIRECT_URIS.split(",")
        if value.strip()
    }
    return bool(configured) and redirect_uri in configured


def _require_provider(request: Request) -> None:
    provider = request.path_params["provider"]
    if provider != OAUTH_PROVIDER:
        raise HTTPException(status_code=404, detail="Unsupported OAuth provider")


def register_routes(mcp):
    @mcp.custom_route("/.well-known/mcp.json", methods=["GET"])
    async def manifest(request: Request) -> JSONResponse:
        return JSONResponse({
            "name": settings.APP_TITLE,
            "base_url": f"{settings.PUBLIC_URL.rstrip('/')}/mcp",
            "version": settings.APP_VERSION,
            "external_connections": {"oauth": {"provider": OAUTH_PROVIDER}},
        })

    @mcp.custom_route("/api/v1/auth/{provider}/login", methods=["GET"])
    async def oauth_login(request: Request) -> RedirectResponse:
        _require_provider(request)
        await get_identity(request)
        redirect_uri = request.query_params.get("redirect_uri", "")
        if not _allowed_redirect_uri(redirect_uri):
            raise HTTPException(
                status_code=400,
                detail="redirect_uri must exactly match a configured Twynity OAuth callback URI",
            )
        # Twynity receives this state on its registered callback and validates
        # it before it posts the authorization code to our token-callback route.
        query = urlencode({
            "client_id": settings.SAGE_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": settings.SAGE_OAUTH_SCOPES,
            "state": secrets.token_urlsafe(32),
        })
        return RedirectResponse(
            f"{settings.SAGE_OAUTH_AUTHORIZE_URL}?{query}", status_code=302
        )

    @mcp.custom_route(
        "/api/v1/auth/{provider}/token-callback", methods=["POST"]
    )
    async def oauth_token_callback(request: Request) -> JSONResponse:
        _require_provider(request)
        identity = await get_identity(request)
        code = request.query_params.get("code", "")
        redirect_uri = request.query_params.get("redirect_uri", "")
        if not code:
            raise HTTPException(status_code=400, detail="OAuth callback is missing the authorization code")
        if not _allowed_redirect_uri(redirect_uri):
            raise HTTPException(
                status_code=400,
                detail="redirect_uri must exactly match a configured Twynity OAuth callback URI",
            )

        form = {
            "client_id": settings.SAGE_CLIENT_ID,
            "client_secret": settings.SAGE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(settings.SAGE_OAUTH_TOKEN_URL, data=form)
            response.raise_for_status()
            token_response = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Sage OAuth code exchange failed: %s", type(exc).__name__)
            raise HTTPException(
                status_code=502,
                detail="Sage token exchange failed; check the OAuth app, callback URI, and authorization code",
            ) from exc

        required = ("access_token", "refresh_token", "resource_owner_id")
        missing = [field for field in required if not token_response.get(field)]
        if missing:
            logger.error("Sage token response missing required fields: %s", ", ".join(missing))
            raise HTTPException(
                status_code=502,
                detail="Sage token response did not include the access token, refresh token, and resource owner ID",
            )

        expires_in = int(token_response.get("expires_in", 3600))
        tokens = {
            "access_token": token_response["access_token"],
            "refresh_token": token_response["refresh_token"],
            "resource_owner_id": str(token_response["resource_owner_id"]),
            "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "token_type": token_response.get("token_type", "Bearer"),
        }
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth credential storage is not available")
        await store.save(identity.user_id, identity.persona_id, tokens)
        return JSONResponse({"authenticated": True, "provider": OAUTH_PROVIDER})

    @mcp.custom_route("/api/v1/auth/{provider}/logout", methods=["POST"])
    async def oauth_logout(request: Request) -> JSONResponse:
        _require_provider(request)
        identity = await get_identity(request)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth credential storage is not available")
        await store.delete(identity.user_id, identity.persona_id)
        return JSONResponse({"authenticated": False, "provider": OAUTH_PROVIDER})

    @mcp.custom_route("/api/v1/external-connection/me", methods=["GET"])
    async def external_connection_me(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth credential storage is not available")
        connected = await store.get(identity.user_id, identity.persona_id) is not None
        return JSONResponse({"connected": connected})

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def health_status(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})
