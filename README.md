# Sage Accounting MCP

Twynity-connected MCP server for Sage Business Cloud Accounting API v3.1.
Each user connects with Sage OAuth; the Sage developer subscription key is
shared app configuration. OAuth tokens are stored encrypted in MongoDB, and
generic CRUD tools derive resource types and schemas from the checked-in Sage
OpenAPI document.

## Tool surface

- `sage_resources` — discover supported Sage collections and their operations.
- `sage_describe` — inspect query parameters and create/update schemas before
  calling Sage.
- `sage_list` — list/search a resource using only documented Sage filters.
- `sage_get` — retrieve the full record by Sage `id`.
- `sage_create` / `sage_update` / `sage_delete` — generic writes parameterized
  by resource type. Delete requires explicit user confirmation.

The OpenAPI snapshot is `app/data/sage_accounting_v3.1.openapi.json`. This lets
the MCP resolve resource paths, valid query parameters, request wrappers, and
schemas without hand-maintained per-resource field lists. Sage operations that
are not standard CRUD (for example release/reissue actions) are not exposed by
these initial tools.

## Sage OAuth and Twynity contract

The manifest at `GET /.well-known/mcp.json` declares:

```json
{"external_connections":{"oauth":{"provider":"sage"}}}
```

Twynity uses these authenticated routes:

- `GET /api/v1/auth/sage/login?redirect_uri=...` — validates the configured
  Twynity callback URI and redirects to Sage authorization.
- `POST /api/v1/auth/sage/token-callback?redirect_uri=...&code=...` — exchanges
  the authorization code and stores encrypted access/refresh tokens plus
  Sage's `resource_owner_id`.
- `POST /api/v1/auth/sage/logout` — removes the saved tokens for the current
  user/persona.
- `GET /api/v1/external-connection/me` — returns connection status.

Every request from Twynity must include its verified bearer JWT and
`Persona-Id`. MongoDB scopes a connection to the exact `(user_id, persona_id)`
pair. Sage API calls send the access token in `Authorization: Bearer ...` and
the saved `resource_owner_id` in `X-Site`. Refresh tokens are used to renew
expired access tokens. The MCP does not return OAuth tokens to Twynity or the
model after exchange.

The OAuth app must register the exact Twynity callback URI. List the accepted
URI(s) in `SAGE_OAUTH_REDIRECT_URIS`; configure `SAGE_OAUTH_TOKEN_URL` for the
Sage app's region. The Sage developer portal also issues an API subscription
key when you subscribe the app to Sage Accounting. Configure it as
`SAGE_SUBSCRIPTION_KEY`; the server sends it as `Ocp-Apim-Subscription-Key` on
Sage API requests. This is an app-level secret, not a per-user credential. The
example `.env.example` token endpoint is for UK/GB and must be checked against
the actual Sage developer app.

## Local setup

1. Copy `.env.example` to `.env` and set Sage OAuth credentials/URLs, Twynity
   account-service and license settings, MongoDB, and public URL.
2. Generate a Fernet key:

   ```bash
   uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Keep `ENCRYPTION_KEY` stable and secret; changing it makes stored OAuth
   tokens unreadable.
3. Install, build the starter MCP App bundle, and test:

   ```bash
   uv sync --locked
   cd app/ui/say_hello && npm ci && npm run build && cd ../../..
   uv run pytest -q
   uv run ruff check app tests
   ```
4. Start the service:

   ```bash
   uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

The UI directory is retained from the starter scaffold; it is not currently
attached to the Sage CRUD tools. Docker builds the UI bundle as part of its
multi-stage build.
