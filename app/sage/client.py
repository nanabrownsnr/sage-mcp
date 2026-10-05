"""Authenticated Sage Accounting HTTP client with encrypted-token refresh."""

from datetime import UTC, datetime, timedelta
from logging import getLogger
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp.server.dependencies import get_http_headers
from starlette.exceptions import HTTPException

from app.auth import get_identity_from_headers
from app.config import settings
from app.connection_store import ConnectionStore, get_active_store
from app.sage.catalog import allowed_query_parameters, get_operation, wrap_request_body

logger = getLogger(__name__)


class SageAPIError(RuntimeError):
    """Safe, actionable error for rejected or unavailable Sage API requests."""


async def _identity_and_store() -> tuple[Any, ConnectionStore]:
    identity = await get_identity_from_headers(get_http_headers())
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Sage connection storage is not available")
    return identity, store


async def _refresh_tokens(tokens: dict[str, Any], store: ConnectionStore, identity: Any) -> dict[str, Any]:
    form = {
        "client_id": settings.SAGE_CLIENT_ID,
        "client_secret": settings.SAGE_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(settings.SAGE_OAUTH_TOKEN_URL, data=form)
        response.raise_for_status()
        refreshed = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Sage OAuth refresh failed: %s", type(exc).__name__)
        raise SageAPIError(
            "Sage authorization expired and could not be refreshed; reconnect Sage in Twynity"
        ) from exc

    access_token = refreshed.get("access_token")
    if not access_token:
        raise SageAPIError("Sage refresh response did not contain a new access token; reconnect Sage")
    expires_in = int(refreshed.get("expires_in", 3600))
    renewed = {
        **tokens,
        "access_token": access_token,
        "refresh_token": refreshed.get("refresh_token") or tokens["refresh_token"],
        "resource_owner_id": str(
            refreshed.get("resource_owner_id") or tokens["resource_owner_id"]
        ),
        "expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
        "token_type": refreshed.get("token_type", tokens.get("token_type", "Bearer")),
    }
    await store.save(identity.user_id, identity.persona_id, renewed)
    return renewed


async def current_sage_tokens() -> tuple[dict[str, Any], Any, ConnectionStore]:
    """Return refreshed tokens and trusted identity for this MCP call."""
    identity, store = await _identity_and_store()
    tokens = await store.get(identity.user_id, identity.persona_id)
    if not tokens:
        raise HTTPException(status_code=400, detail="Sage is not connected for the active Twynity persona")
    try:
        expires_at = datetime.fromisoformat(tokens["expires_at"])
    except (KeyError, TypeError, ValueError):
        expires_at = datetime.min.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC) + timedelta(seconds=60):
        tokens = await _refresh_tokens(tokens, store, identity)
    return tokens, identity, store


async def sage_request(
    resource_type: str,
    method: str,
    *,
    record_id: str | None = None,
    filters: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> Any:
    """Perform an OpenAPI-declared Sage CRUD operation for the active persona."""
    operation_data = get_operation(resource_type, method, record_id=record_id)
    operation = operation_data["operation"]
    query = filters or {}
    allowed = allowed_query_parameters(operation)
    unknown = sorted(set(query) - allowed)
    if unknown:
        raise ValueError(
            f"Unsupported query parameter(s) for {resource_type}: {', '.join(unknown)}. "
            f"Allowed parameters: {', '.join(sorted(allowed)) or 'none'}"
        )
    tokens, _identity, _store = await current_sage_tokens()
    path = operation_data["path"]
    if record_id is not None:
        path = path.replace("{key}", quote(record_id, safe=""))
    body = wrap_request_body(operation, data) if data is not None else None
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-Site": tokens["resource_owner_id"],
        "Ocp-Apim-Subscription-Key": settings.SAGE_SUBSCRIPTION_KEY,
        "Accept": "application/json",
    }
    url = f"{settings.SAGE_API_BASE_URL.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                operation_data["method"], url, params=query, json=body, headers=headers
            )
        if response.status_code in (401, 403):
            raise SageAPIError(
                f"Sage denied {operation_data['method']} {resource_type} ({response.status_code}); "
                "check the Sage user's permissions and reconnect if the grant was revoked"
            )
        if response.status_code == 429:
            raise SageAPIError("Sage rate limit reached; wait briefly and retry")
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {"deleted": True, "resource_type": resource_type, "record_id": record_id}
        return response.json()
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            payload = exc.response.json()
            errors = payload.get("$diagnostics", {}).get("errors", [])
            detail = "; ".join(
                str(item.get("message", "")) for item in errors if item.get("message")
            )
            if not detail and isinstance(payload.get("error"), dict):
                detail = str(payload["error"].get("message", ""))
        except (ValueError, AttributeError):
            pass
        suffix = f" Details: {detail}" if detail else ""
        raise SageAPIError(
            f"Sage rejected {operation_data['method']} {resource_type} "
            f"with HTTP {exc.response.status_code}.{suffix}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise SageAPIError("Sage did not respond within 30 seconds; retry the request") from exc
    except httpx.RequestError as exc:
        raise SageAPIError("Could not reach Sage Accounting; check upstream availability") from exc
