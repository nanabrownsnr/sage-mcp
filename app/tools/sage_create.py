"""Create a record in a Sage Accounting resource."""

from typing import Any

from fastmcp.tools import ToolResult

from app.sage.client import SageAPIError, sage_request
from app.sage.results import record_identity


def register_tool(mcp):
    @mcp.tool()
    async def sage_create(resource_type: str, data: dict[str, Any]) -> ToolResult:
        """Create a Sage Accounting record after the user requests creation.

        First use ``sage_resources`` to resolve the correct resource, then
        call ``sage_describe(resource_type, "POST")`` to inspect the relevant
        Sage schema/requirements before creating financial
        records. The tool shapes the payload envelope from Sage's OpenAPI spec;
        provide the inner resource fields (for example ``{"name": "Acme"}``
        for a contact). Do not invent IDs for related accounts, tax rates, or
        contacts. Ask for missing required financial values rather than
        guessing. Only create when the user has clearly requested it.

        Args:
            resource_type: Exact Sage collection name, e.g. ``contacts``.
            data: Fields for the new record, matching the Sage request schema.

        Returns:
            Success/error summary plus the complete created record data when
            Sage returns it.
        """
        try:
            created = await sage_request(resource_type, "POST", data=data)
        except (ValueError, SageAPIError) as exc:
            return ToolResult(
                content=f"Unable to create {resource_type}: {exc}",
                structured_content={"error": str(exc), "resource_type": resource_type},
                meta={"toolname": "sage_create"},
            )
        record_id = record_identity(created)
        summary = f"Created Sage {resource_type} record"
        if record_id:
            summary += f" with ID {record_id}"
        summary += ". Full created data is included."
        return ToolResult(
            content=summary,
            structured_content={
                "summary": summary,
                "resource_type": resource_type,
                "record_id": record_id,
                "data": created,
            },
            meta={"toolname": "sage_create"},
        )
