"""Get a single Sage Accounting record by its resource ID."""

from fastmcp.tools import ToolResult

from app.sage.client import SageAPIError, sage_request


def register_tool(mcp):
    @mcp.tool()
    async def sage_get(resource_type: str, record_id: str) -> ToolResult:
        """Retrieve the full details of one Sage Accounting record.

        Use after ``sage_list`` identifies a matching record. Sage record IDs
        are UUID-like ``id`` values returned by list results, not display names.
        Call ``sage_resources`` first if the resource type is ambiguous.

        Args:
            resource_type: Exact Sage API collection, e.g. ``contacts``.
            record_id: The Sage ``id`` value returned by ``sage_list``.

        Returns:
            The full Sage record in both readable summary text and structured
            data, suitable for detailed UI rendering or a later update.
        """
        try:
            record = await sage_request(resource_type, "GET", record_id=record_id)
        except (ValueError, SageAPIError) as exc:
            message = f"Unable to get {resource_type} record {record_id}: {exc}"
            return ToolResult(
                content=message,
                structured_content={"error": str(exc), "resource_type": resource_type, "record_id": record_id},
                meta={"toolname": "sage_get"},
            )
        summary = f"Retrieved Sage {resource_type} record {record_id}. Full record data is included."
        return ToolResult(
            content=summary,
            structured_content={
                "summary": summary,
                "resource_type": resource_type,
                "record_id": record_id,
                "data": record,
            },
            meta={"toolname": "sage_get"},
        )
