"""Delete a Sage Accounting record, only after explicit user confirmation."""

from fastmcp.tools import ToolResult

from app.sage.client import SageAPIError, sage_request


def register_tool(mcp):
    @mcp.tool()
    async def sage_delete(resource_type: str, record_id: str, confirmed: bool = False) -> ToolResult:
        """Delete a Sage Accounting record after explicit user confirmation.

        Deletion is destructive. Never call this with ``confirmed=True`` unless
        the user has explicitly confirmed deletion of this specific Sage record
        in the current conversation. Call ``sage_get`` first if the record's
        identity is not certain. Some Sage resource types do not support delete;
        the tool checks the OpenAPI contract and reports that clearly.

        Args:
            resource_type: Exact Sage collection name.
            record_id: Sage ``id`` of the record to delete.
            confirmed: Must be true only after explicit user confirmation.

        Returns:
            Deletion success or an actionable error.
        """
        if not confirmed:
            message = "Deletion not performed. Ask the user to explicitly confirm this record deletion."
            return ToolResult(
                content=message,
                structured_content={"error": message, "resource_type": resource_type, "record_id": record_id},
                meta={"toolname": "sage_delete"},
            )
        try:
            result = await sage_request(resource_type, "DELETE", record_id=record_id)
        except (ValueError, SageAPIError) as exc:
            return ToolResult(
                content=f"Unable to delete {resource_type} record {record_id}: {exc}",
                structured_content={"error": str(exc), "resource_type": resource_type, "record_id": record_id},
                meta={"toolname": "sage_delete"},
            )
        summary = f"Deleted Sage {resource_type} record {record_id}."
        return ToolResult(
            content=summary,
            structured_content={
                "summary": summary,
                "resource_type": resource_type,
                "record_id": record_id,
                "data": result,
            },
            meta={"toolname": "sage_delete"},
        )
