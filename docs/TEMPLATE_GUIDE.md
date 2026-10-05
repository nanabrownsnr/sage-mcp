# Sage MCP implementation notes

## Twynity OAuth contract

This Sage MCP declares only the OAuth external-connection category. Its
manifest is served at `/.well-known/mcp.json` and declares
`external_connections.oauth.provider = "sage"`.

The Twynity server first calls `GET /api/v1/auth/sage/login` with the exact
registered `redirect_uri`. This MCP validates the URI against
`SAGE_OAUTH_REDIRECT_URIS` and redirects the browser to Sage's OAuth authorize
endpoint. Sage sends the authorization code to Twynity's callback; the
Twynity host validates its OAuth state and then calls this MCP's
`POST /api/v1/auth/sage/token-callback` with the same `redirect_uri` and code.
The MCP exchanges the code at Sage's region-specific token endpoint.

Token callback responses contain only connection success/provider metadata.
Access tokens, refresh tokens, and `resource_owner_id` are encrypted using
Fernet and stored under the verified `(user_id, persona_id)` pair. All custom
routes validate the Twynity bearer JWT and require `Persona-Id`. The callback
URI must be an exact allowlisted value and match the URI registered in Sage.

On API calls the client uses:

- `Authorization: Bearer <access_token>`
- `X-Site: <resource_owner_id>`
- `Ocp-Apim-Subscription-Key: <SAGE_SUBSCRIPTION_KEY>`

The subscription key belongs to the registered Sage developer application and
is configured server-side. It is shared across users; the OAuth tokens and
`resource_owner_id` are isolated per Twynity user/persona.

Access tokens are refreshed before expiry using the stored refresh token. If
refresh fails or is revoked, the tool returns an actionable reconnect error.
Logout deletes only the current user/persona's token document.

## OpenAPI-driven CRUD

The 3.1 OpenAPI snapshot in `app/data/` is the source of truth for collection
names, endpoint paths, supported verbs, query parameters, body envelopes, and
schemas. `sage_resources` lets the model discover resource types;
`sage_describe` returns operation-specific schemas. CRUD tools accept the Sage
collection name as an argument, rather than baking every Sage type into a
separate tool or field list.

For write requests, pass the resource fields as `data`. The client wraps them
in Sage's resource envelope when the OpenAPI request schema defines one. List
filters are checked against the operation's documented query parameters.
Unsupported operations and invalid filters return actionable errors. Use
`sage_get` with the `id` returned by `sage_list` to fetch a complete record.

The OpenAPI includes special operations beyond CRUD (for example release,
reissue, reconciliation, and transfer workflows). These need explicit
operation semantics and safety review before being exposed; do not silently
map them to generic create/update calls.

## MCP Apps header forwarding

The browser UI cannot inject arbitrary headers through `app.callServerTool()`.
Twynity must forward both bearer auth and `Persona-Id` for tool calls initiated
by an MCP App, just as for model-initiated calls. Do not ask users to provide
persona IDs as tool arguments.
