"""Define service identity, environment settings, and logging.

Set ``mcp_name`` and extend ``Settings`` when your MCP needs new configuration.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

# Put your MCP name here. Keeping this value in one place makes the service
# identity, display title, and log filenames easy to customise.
mcp_name = "sage"


def configured_mcp_name() -> str:
    """Return a runnable default until the template owner chooses a name."""
    return mcp_name.strip() or "sage"


def configure_logging():
    os.makedirs("./logs", exist_ok=True)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    handler = TimedRotatingFileHandler(
        filename=f"./logs/{configured_mcp_name()}-mcp.log",
        when="midnight", interval=1, backupCount=7,
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    detailed_handler = TimedRotatingFileHandler(
        filename=f"./logs/{configured_mcp_name()}-mcp-detailed.log",
        when="midnight", interval=1, backupCount=7,
    )
    detailed_handler.setFormatter(formatter)
    detailed_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(detailed_handler)

class Settings(BaseSettings):
    SERVICE_ID: str = "sage-mcp"
    APP_TITLE: str = "Sage Accounting MCP"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development | staging | production
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: str = "*"
    RELEASE_ID: str = "1.0.0"
    PERSONA_ID_HEADER: str = "Persona-Id"
    PUBLIC_URL: str = "http://localhost:8000"

    # MongoDB stores one encrypted external connection per Twynity user/persona.
    MONGODB_URI: str
    DATABASE_NAME: str = "twynity_mcp"
    ENCRYPTION_KEY: str

    # Sage Accounting OAuth configuration. Select the token URL for the region
    # in which the Sage developer application was registered.
    SAGE_OAUTH_AUTHORIZE_URL: str = "https://www.sageone.com/oauth2/auth/central"
    SAGE_OAUTH_TOKEN_URL: str
    SAGE_CLIENT_ID: str
    SAGE_CLIENT_SECRET: str
    # API subscription key issued when the Sage Accounting API is added to
    # the developer application. Sent on API calls, never to the browser.
    SAGE_SUBSCRIPTION_KEY: str
    SAGE_OAUTH_SCOPES: str = "full_access"
    SAGE_OAUTH_REDIRECT_URIS: str = ""
    SAGE_API_BASE_URL: str = "https://api.accounting.sage.com/v3.1"

    # Usage reporting
    USAGE_REPORT_ENDPOINT: str

    # Account Service
    ACCOUNT_SERVICE_URL: str
    ACCOUNT_SERVICE_JWKS_ENDPOINT: str
    ACCOUNT_SERVICE_JWKS_CACHE_TTL: int

    # License Service
    LICENSE_KEY: str
    LICENSE_SERVER_BASE_URL: str
    LICENSE_SERVER_JWKS_ENDPOINT: str
    LICENSE_SERVER_ACTIVATION_ENDPOINT: str



settings = Settings()
configure_logging()
