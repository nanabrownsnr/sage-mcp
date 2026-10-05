"""Compact model summaries while preserving complete structured result data."""

from typing import Any


def _record_list(value: Any, resource_type: str) -> list[dict[str, Any]] | None:
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    if isinstance(value, dict):
        preferred = (resource_type, f"${resource_type}", "$items", "items", "data")
        for key in preferred:
            if key in value:
                found = _record_list(value[key], resource_type)
                if found is not None:
                    return found
        for child in value.values():
            found = _record_list(child, resource_type)
            if found is not None:
                return found
    return None


def list_summary(resource_type: str, payload: Any) -> tuple[str, int | None]:
    """Summarize result count and up to five identifying values for the model."""
    records = _record_list(payload, resource_type)
    if records is None:
        return f"Sage returned data for {resource_type}; full response is in structured content.", None
    total = len(records)
    examples = []
    for record in records[:5]:
        item = record.get(resource_type.rstrip("s"), record)
        if not isinstance(item, dict):
            item = record
        identifier = item.get("id") or item.get("displayed_as") or item.get("reference")
        name = item.get("name") or item.get("displayed_as")
        if identifier and name and str(identifier) != str(name):
            examples.append(f"{name} (ID: {identifier})")
        elif identifier or name:
            examples.append(str(name or identifier))
    summary = f"Found {total} {resource_type} record{'s' if total != 1 else ''}."
    if examples:
        summary += " Records: " + "; ".join(examples) + "."
    summary += " Full data is available in structured content."
    return summary, total


def record_identity(payload: Any) -> str | None:
    """Find a returned Sage record identifier in common response envelopes."""
    if isinstance(payload, dict):
        if payload.get("id"):
            return str(payload["id"])
        for child in payload.values():
            found = record_identity(child)
            if found:
                return found
    elif isinstance(payload, list):
        for child in payload:
            found = record_identity(child)
            if found:
                return found
    return None
