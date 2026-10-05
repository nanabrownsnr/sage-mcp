"""Verify Sage API requests include both OAuth and developer subscription auth."""

import pytest

from app.config import settings
from app.sage import client as sage_client


@pytest.mark.asyncio
async def test_sage_request_sends_subscription_key_and_persona_tokens(monkeypatch):
    settings.SAGE_SUBSCRIPTION_KEY = "test-subscription-key"

    async def fake_current_sage_tokens():
        return (
            {
                "access_token": "user-access-token",
                "resource_owner_id": "sage-company-123",
            },
            object(),
            object(),
        )

    monkeypatch.setattr(sage_client, "current_sage_tokens", fake_current_sage_tokens)
    captured = {}

    class FakeResponse:
        status_code = 200
        content = b'{"contacts": []}'

        def json(self):
            return {"contacts": []}

        def raise_for_status(self):
            return None

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, method, url, **kwargs):
            captured.update(method=method, url=url, **kwargs)
            return FakeResponse()

    monkeypatch.setattr(sage_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await sage_client.sage_request("contacts", "GET")

    assert result == {"contacts": []}
    assert captured["headers"]["Authorization"] == "Bearer user-access-token"
    assert captured["headers"]["X-Site"] == "sage-company-123"
    assert captured["headers"]["Ocp-Apim-Subscription-Key"] == "test-subscription-key"
