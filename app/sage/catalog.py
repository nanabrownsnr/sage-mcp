"""OpenAPI-backed Sage resource and operation discovery."""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
SPEC_PATH = Path(__file__).resolve().parents[1] / "data" / "sage_accounting_v3.1.openapi.json"


@lru_cache(maxsize=1)
def load_spec() -> dict[str, Any]:
    """Load the checked-in Sage 3.1 OpenAPI document once per process."""
    with SPEC_PATH.open(encoding="utf-8") as spec_file:
        return json.load(spec_file)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _collection_for_path(path: str) -> str | None:
    segments = [segment for segment in path.strip("/").split("/") if segment]
    if len(segments) == 1 and not segments[0].startswith("{"):
        return segments[0]
    return None


@lru_cache(maxsize=1)
def resources() -> dict[str, dict[str, Any]]:
    """Build the collection catalog directly from top-level OpenAPI paths."""
    spec = load_spec()
    found: dict[str, dict[str, Any]] = {}
    for path, path_item in spec.get("paths", {}).items():
        slug = _collection_for_path(path)
        if not slug:
            continue
        item_path = f"/{slug}/{{key}}"
        item_item = spec.get("paths", {}).get(item_path, {})
        tags: list[str] = []
        methods: set[str] = set()
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS:
                methods.add(method.upper())
                for tag in operation.get("tags", []):
                    if tag not in tags:
                        tags.append(tag)
        for method, operation in item_item.items():
            if method.lower() in HTTP_METHODS:
                methods.add(method.upper())
                for tag in operation.get("tags", []):
                    if tag not in tags:
                        tags.append(tag)
        if not methods:
            continue
        found[slug] = {
            "resource_type": slug,
            "collection_path": path,
            "item_path": item_path if item_item else None,
            "tags": tags,
            "methods": sorted(methods),
        }
    return found


def resolve_resource(resource_type: str) -> dict[str, Any]:
    """Resolve an API path slug or a human-readable OpenAPI tag name."""
    requested = _slug(resource_type)
    catalog = resources()
    if requested in catalog:
        return catalog[requested]
    matches = [
        resource
        for resource in catalog.values()
        if requested in {_slug(tag) for tag in resource["tags"]}
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        choices = ", ".join(item["resource_type"] for item in matches)
        raise ValueError(f"Resource type '{resource_type}' is ambiguous; use one of: {choices}")
    choices = ", ".join(sorted(catalog))
    raise ValueError(f"Unsupported Sage resource '{resource_type}'. Discover supported types with sage_resources. Available: {choices}")


def get_operation(resource_type: str, method: str, *, record_id: str | None = None) -> dict[str, Any]:
    """Return an OpenAPI operation for one collection/item CRUD action."""
    resource = resolve_resource(resource_type)
    verb = method.lower()
    if verb not in HTTP_METHODS:
        raise ValueError(f"Unsupported HTTP operation '{method}'")
    is_item = record_id is not None
    path = resource["item_path"] if is_item else resource["collection_path"]
    if not path:
        raise ValueError(f"Sage resource '{resource['resource_type']}' has no item endpoint")
    operation = load_spec()["paths"].get(path, {}).get(verb)
    if not operation:
        kind = "record" if is_item else "collection"
        raise ValueError(
            f"Sage resource '{resource['resource_type']}' does not support {verb.upper()} on a {kind}"
        )
    return {"path": path, "method": verb.upper(), "operation": operation, "resource": resource}


def allowed_query_parameters(operation: dict[str, Any]) -> set[str]:
    """List query parameter names declared for an OpenAPI operation."""
    result = set()
    for parameter in operation.get("parameters", []):
        resolved = resolve_ref(parameter)
        if resolved.get("in") == "query":
            result.add(resolved["name"])
    return result


def resolve_ref(value: dict[str, Any]) -> dict[str, Any]:
    """Resolve a local OpenAPI component reference, including nested refs."""
    ref = value.get("$ref")
    if not ref:
        return value
    if not ref.startswith("#/components/"):
        raise ValueError(f"External OpenAPI references are not supported: {ref}")
    target: Any = load_spec()
    for part in ref[2:].split("/"):
        target = target[part.replace("~1", "/").replace("~0", "~")]
    merged = {**target, **{key: item for key, item in value.items() if key != "$ref"}}
    return merged


def request_body_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the JSON request schema for a create/update operation."""
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {}).get("application/json", {})
    schema = content.get("schema")
    return resolve_ref(schema) if schema else None


def response_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the successful JSON response schema, if documented."""
    responses = operation.get("responses", {})
    response = responses.get("200") or responses.get("201") or responses.get("202") or {}
    schema = response.get("content", {}).get("application/json", {}).get("schema")
    return resolve_ref(schema) if schema else None


def describe_resource(resource_type: str, method: str = "GET") -> dict[str, Any]:
    """Return operation requirements and query/body schema to guide tool calls."""
    record_id = "__schema__" if method.upper() in {"PUT", "PATCH", "DELETE"} else None
    details = get_operation(resource_type, method, record_id=record_id)
    operation = details["operation"]
    parameters = [resolve_ref(item) for item in operation.get("parameters", [])]
    request_schema = request_body_schema(operation)
    return {
        "resource_type": details["resource"]["resource_type"],
        "label": details["resource"]["tags"][0] if details["resource"]["tags"] else resource_type,
        "method": method.upper(),
        "summary": operation.get("summary", ""),
        "query_parameters": [
            {
                "name": item["name"],
                "required": item.get("required", False),
                "description": item.get("description", ""),
                "schema": item.get("schema", {}),
            }
            for item in parameters if item.get("in") == "query"
        ],
        "request_schema": request_schema,
        "response_schema": response_schema(operation),
        "required_body_fields": request_schema.get("required", []) if request_schema else [],
    }


def wrap_request_body(operation: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """Wrap user fields in the single Sage resource envelope required by spec."""
    schema = request_body_schema(operation)
    if not schema:
        return data
    properties = schema.get("properties", {})
    object_fields = [
        name for name, item in properties.items()
        if resolve_ref(item).get("type") == "object"
    ]
    if len(object_fields) == 1 and object_fields[0] not in data:
        return {object_fields[0]: data}
    return data


def resource_summary() -> list[dict[str, Any]]:
    """Return a compact catalog for the LLM's resource-type selection."""
    return [
        {
            "resource_type": item["resource_type"],
            "label": item["tags"][0] if item["tags"] else item["resource_type"],
            "methods": item["methods"],
        }
        for item in sorted(resources().values(), key=lambda entry: entry["resource_type"])
    ]
