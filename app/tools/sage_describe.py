"""Describe Sage resource query parameters and request/response schema."""

from typing import Any

from app.sage.catalog import describe_resource


def register_tool(mcp):
    @mcp.tool()
    def sage_describe(resource_type: str, method: str = "GET") -> dict[str, Any]:
        """Inspect the Sage OpenAPI schema for a resource operation.

        Use this before creating or updating accounting records to discover the
        exact fields, required fields, envelope, and valid list filters. Use
        ``sage_resources`` first when the user's wording could refer to more
        than one Sage resource. This only reads the bundled schema; it does not
        call Sage or require a live connection.

        Args:
            resource_type: Exact Sage collection name, e.g. ``contacts`` or
                ``sales_invoices``.
            method: ``GET`` for list/query parameters, ``POST`` for create
                fields, or ``PUT`` for update fields.

        Returns:
            Sage operation summary and schema details extracted from the
            versioned OpenAPI document.
        """
        try:
            return describe_resource(resource_type, method)
        except ValueError as exc:
            return {"error": str(exc), "resource_type": resource_type}
