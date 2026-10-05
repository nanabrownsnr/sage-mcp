"""List or search a Sage Accounting resource collection."""

from typing import Any

from fastmcp.tools import ToolResult

from app.sage.client import SageAPIError, sage_request
from app.sage.results import list_summary


def register_tool(mcp):
    @mcp.tool()
    async def sage_list(resource_type: str, filters: dict[str, Any] | None = None) -> ToolResult:
        """List or search records in a Sage Accounting resource.

        Use this for requests such as finding contacts, invoices, payments,
        ledger accounts, or bank transactions. Call ``sage_resources`` first
        if the correct resource type is unclear. The resource argument is an
        API collection name from Sage's OpenAPI catalog. Use only filters/query
        parameter names supported by that resource; validation errors list the
        exact allowed parameter names. Use ``sage_get`` for full details of a
        specific result, passing its Sage ``id``.

        Args:
            resource_type: Exact Sage collection, e.g. ``contacts`` or
                ``sales_invoices``.
            filters: Optional mapping of Sage OpenAPI query parameter names to
                values, e.g. ``{"search": "Acme", "items_per_page": 20}``.

        Returns:
            A concise count and up to five record names/IDs in model-readable
            text, plus the complete Sage response in structured data.
        """
        try:
            result = await sage_request(resource_type, "GET", filters=filters)
        except (ValueError, SageAPIError) as exc:
            message = f"Unable to list {resource_type}: {exc}"
            return ToolResult(
                content=message,
                structured_content={"error": str(exc), "resource_type": resource_type},
                meta={"toolname": "sage_list"},
            )
        summary, count = list_summary(resource_type, result)
        return ToolResult(
            content=summary,
            structured_content={
                "summary": summary,
                "count": count,
                "resource_type": resource_type,
                "data": result,
            },
            meta={"toolname": "sage_list"},
        )
