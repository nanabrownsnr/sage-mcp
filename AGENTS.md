# Coding-agent instructions for Sage MCP

- Work only in this Sage repository; the reusable template is a separate
  repository and should not receive Sage-specific edits.
- Preserve Twynity JWT verification plus the required `Persona-Id` header.
  Scope credential reads/writes to the exact `(user_id, persona_id)` pair.
- This service uses the Twynity OAuth category, not API-key or project/schema
  configuration. Keep the manifest, login, token-callback, logout, and `/me`
  contracts aligned with `docs/TEMPLATE_GUIDE.md`.
- Never return or log Sage access/refresh tokens or client secrets. Store token
  fields Fernet-encrypted and return only safe connection status.
- Use the checked-in Sage OpenAPI document as the source of truth for resource
  paths, fields, query parameters, and CRUD support. Keep generic tools
  parameterized by Sage resource type; do not add hand-maintained per-resource
  field lists.
- Put each MCP tool in its own module. Give each tool a detailed LLM docstring
  covering when to call it, resource ambiguity, arguments, and safety rules.
- Financial writes must not guess amounts or linked IDs. Delete is destructive
  and requires explicit confirmation. Keep non-CRUD workflows unexposed until
  their semantics are reviewed.
- Test successful operations, invalid inputs, auth/identity failures, cross-
  persona isolation, encryption, Sage API errors, and OAuth refresh behavior.
- Before commit, run `uv run pytest -q`, `uv run ruff check app tests`, build
  the MCP App, and run `git diff --check`.
