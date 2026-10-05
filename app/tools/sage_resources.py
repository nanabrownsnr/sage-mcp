"""Discover Sage Accounting resources and supported CRUD operations."""

from typing import Any

from app.sage.catalog import resource_summary


def register_tool(mcp):
    @mcp.tool()
    def sage_resources(search: str = "") -> dict[str, Any]:
        """List Sage Accounting resource types supported by this MCP.

        Use this first when the user asks about Sage data, or when unsure which
        resource type to pass to a CRUD tool. The catalog is generated from the
        Sage Accounting 3.1 OpenAPI specification. Prefer exact API resource
        names such as ``contacts``, ``sales_invoices``, ``purchase_invoices``,
        ``bank_accounts``, or ``ledger_accounts``. If multiple resource types
        might match the request, show the relevant choices and ask the user.

        Args:
            search: Optional substring to filter resource names and labels.

        Returns:
            Resource type, display label, and supported collection/record
            methods. This discovery call does not access the user's Sage data.
        """
        matches = resource_summary()
        if search.strip():
            needle = search.strip().lower()
            matches = [
                item for item in matches
                if needle in item["resource_type"].lower() or needle in item["label"].lower()
            ]
        return {"resources": matches, "count": len(matches)}
