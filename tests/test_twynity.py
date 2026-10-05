"""Exercise Twynity's OAuth-category routes without live auth/Sage services."""

from urllib.parse import parse_qs, urlparse

import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient

from app.auth import TwynityIdentity
from app.twynity import register_routes


@pytest.fixture
def oauth_app():
    mcp = FastMCP("sage_test")
    register_routes(mcp)
    return mcp.http_app()


class FakeStore:
    def __init__(self):
        self.saved = {}

    async def save(self, user_id, persona_id, values):
        self.saved[(user_id, persona_id)] = values

    async def get(self, user_id, persona_id):
        return self.saved.get((user_id, persona_id))

    async def delete(self, user_id, persona_id):
        return self.saved.pop((user_id, persona_id), None) is not None


class FakeTokenResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "access_token": "access-secret",
            "refresh_token": "refresh-secret",
            "resource_owner_id": "sage-site-123",
            "expires_in": 3600,
            "token_type": "Bearer",
        }


def install_identity_and_store(monkeypatch, store):
    import app.twynity as routes

    async def fake_identity(_request):
        return TwynityIdentity(user_id="owner-1", persona_id="persona-1")

    monkeypatch.setattr(routes, "get_identity", fake_identity)
    monkeypatch.setattr(routes, "get_active_store", lambda: store)
    return routes


def test_manifest_declares_oauth_provider(oauth_app):
    response = TestClient(oauth_app).get("/.well-known/mcp.json")
    assert response.status_code == 200
    body = response.json()
    assert body["base_url"].endswith("/mcp")
    assert body["external_connections"] == {"oauth": {"provider": "sage"}}


def test_login_redirects_to_sage_with_registered_callback(monkeypatch, oauth_app):
    store = FakeStore()
    install_identity_and_store(monkeypatch, store)
    response = TestClient(oauth_app).get(
        "/api/v1/auth/sage/login",
        params={"redirect_uri": "http://twynity.invalid/callback"},
        headers={"Authorization": "Bearer twynity-token", "Persona-Id": "persona-1"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = urlparse(response.headers["location"])
    query = parse_qs(location.query)
    assert location.netloc == "sage.invalid"
    assert query["client_id"] == ["test-sage-client"]
    assert query["redirect_uri"] == ["http://twynity.invalid/callback"]
    assert query["scope"] == ["full_access"]
    assert query["state"]


@pytest.mark.asyncio
async def test_token_callback_exchanges_code_and_stores_tokens_encrypted_by_identity(monkeypatch):
    import app.twynity as routes

    store = FakeStore()
    install_identity_and_store(monkeypatch, store)

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, data):
            assert url == "http://sage.invalid/token"
            assert data["code"] == "one-time-code"
            assert data["grant_type"] == "authorization_code"
            assert data["client_secret"] == "test-sage-secret"
            return FakeTokenResponse()

    monkeypatch.setattr(routes.httpx, "AsyncClient", FakeAsyncClient)
    mcp = FastMCP("sage_token_test")
    register_routes(mcp)
    response = TestClient(mcp.http_app()).post(
        "/api/v1/auth/sage/token-callback",
        params={"code": "one-time-code", "redirect_uri": "http://twynity.invalid/callback"},
        headers={"Authorization": "Bearer twynity-token", "Persona-Id": "persona-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "provider": "sage"}
    saved = store.saved[("owner-1", "persona-1")]
    assert saved["access_token"] == "access-secret"
    assert saved["refresh_token"] == "refresh-secret"
    assert saved["resource_owner_id"] == "sage-site-123"
    assert "access-secret" not in response.text


def test_oauth_logout_removes_only_active_persona_connection(monkeypatch):

    store = FakeStore()
    store.saved[("owner-1", "persona-1")] = {"access_token": "encrypted-by-store"}
    store.saved[("owner-1", "persona-2")] = {"access_token": "other-project"}
    install_identity_and_store(monkeypatch, store)
    mcp = FastMCP("sage_logout_test")
    register_routes(mcp)
    response = TestClient(mcp.http_app()).post(
        "/api/v1/auth/sage/logout",
        headers={"Authorization": "Bearer twynity-token", "Persona-Id": "persona-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "provider": "sage"}
    assert ("owner-1", "persona-1") not in store.saved
    assert ("owner-1", "persona-2") in store.saved


def test_connection_me_requires_connected_tokens(monkeypatch):

    store = FakeStore()
    install_identity_and_store(monkeypatch, store)
    mcp = FastMCP("sage_me_test")
    register_routes(mcp)
    response = TestClient(mcp.http_app()).get(
        "/api/v1/external-connection/me",
        headers={"Authorization": "Bearer twynity-token", "Persona-Id": "persona-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"connected": False}
