"""Provide safe environment defaults and shared fixtures for starter tests.

Add reusable fixtures here; never replace these placeholders with live secrets.
"""

import os

import pytest

# The production settings remain required by the application. Tests use local
# placeholders so contributors do not need private infrastructure or a .env.
os.environ.setdefault("USAGE_REPORT_ENDPOINT", "http://usage.invalid/report")
os.environ.setdefault("ACCOUNT_SERVICE_URL", "http://account.invalid")
os.environ.setdefault("ACCOUNT_SERVICE_JWKS_ENDPOINT", "/.well-known/jwks.json")
os.environ.setdefault("ACCOUNT_SERVICE_JWKS_CACHE_TTL", "300")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "test_mcp")
os.environ.setdefault(
    "ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
)
os.environ.setdefault("PUBLIC_URL", "http://localhost:8000")
os.environ.setdefault("SAGE_CLIENT_ID", "test-sage-client")
os.environ.setdefault("SAGE_CLIENT_SECRET", "test-sage-secret")
os.environ.setdefault("SAGE_SUBSCRIPTION_KEY", "test-sage-subscription-key")
os.environ.setdefault("SAGE_OAUTH_TOKEN_URL", "http://sage.invalid/token")
os.environ.setdefault("SAGE_OAUTH_AUTHORIZE_URL", "http://sage.invalid/authorize")
os.environ.setdefault("SAGE_OAUTH_SCOPES", "full_access")
os.environ.setdefault("SAGE_API_BASE_URL", "http://sage.invalid/v3.1")
os.environ.setdefault("SAGE_OAUTH_REDIRECT_URIS", "http://twynity.invalid/callback")
os.environ.setdefault("LICENSE_KEY", "test-license")
os.environ.setdefault("LICENSE_SERVER_BASE_URL", "http://license.invalid")
os.environ.setdefault("LICENSE_SERVER_JWKS_ENDPOINT", "/.well-known/jwks.json")
os.environ.setdefault("LICENSE_SERVER_ACTIVATION_ENDPOINT", "/activate")


@pytest.fixture
def greeting_name():
    """Legacy UI fixture retained while the starter UI is being replaced."""
    return "Ada"
