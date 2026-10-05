"""Update an existing Sage Accounting record."""

from typing import Any

from fastmcp.tools import ToolResult

from app.sage.client import SageAPIError, sage_request


def register_tool(mcp):
    @mcp.tool()
    async def sage_update(
        resource_type: str, record_id: str, data: dict[str, Any]
    ) -> ToolResult:
        """Update specified fields on an existing Sage Accounting record.

        Use ``sage_get`` first when the target or current value is unclear.
        This uses the update operation defined by the Sage OpenAPI spec and
        sends only the fields the user asked to change. Do not guess financial
        amounts, tax treatment, or linked IDs. Confirmation is required before
        changing accounting records unless the user clearly instructed the
        exact update.

        Args:
            resource_type: Exact Sage collection name, e.g. ``sales_invoices``.
            record_id: Sage record ``id`` from list/get results.
            data: Only the fields to change, in Sage's expected field format.

        Returns:
            Success/error summary and the complete updated record when returned
            by Sage.
        """
        try:
            updated = await sage_request(resource_type, "PUT", record_id=record_id, data=data)
        except (ValueError, SageAPIError) as exc:
            return ToolResult(
                content=f"Unable to update {resource_type} record {record_id}: {exc}",
                structured_content={"error": str(exc), "resource_type": resource_type, "record_id": record_id},
                meta={"toolname": "sage_update"},
            )
        summary = f"Updated Sage {resource_type} record {record_id}. Full response is included."
        return ToolResult(
            content=summary,
            structured_content={
                "summary": summary,
                "resource_type": resource_type,
                "record_id": record_id,
                "data": updated,
            },
            meta={"toolname": "sage_update"},
        )
