"""Verify CRUD capabilities and request schemas are sourced from Sage OpenAPI."""

import pytest

from app.sage.catalog import (
    allowed_query_parameters,
    describe_resource,
    get_operation,
    request_body_schema,
    resolve_resource,
    resources,
    wrap_request_body,
)


def test_openapi_builds_broad_resource_catalog():
    catalog = resources()
    assert len(catalog) > 70
    assert {"contacts", "sales_invoices", "purchase_invoices", "bank_accounts", "ledger_accounts"} <= set(catalog)


def test_resource_resolution_accepts_path_slug_and_tag_label():
    assert resolve_resource("sales_invoices")["resource_type"] == "sales_invoices"
    assert resolve_resource("Contacts")["resource_type"] == "contacts"


def test_list_filters_come_from_openapi_query_parameters():
    operation = get_operation("contacts", "GET")["operation"]
    allowed = allowed_query_parameters(operation)
    assert "search" in allowed
    assert "items_per_page" in allowed
    assert "not_a_sage_parameter" not in allowed


def test_create_payload_is_wrapped_using_openapi_schema():
    operation = get_operation("contacts", "POST")["operation"]
    schema = request_body_schema(operation)
    assert schema is not None
    wrapped = wrap_request_body(operation, {"name": "Acme Ltd"})
    assert "contact" in wrapped
    assert wrapped["contact"]["name"] == "Acme Ltd"


def test_describe_exposes_create_and_update_schemas():
    create_info = describe_resource("contacts", "POST")
    update_info = describe_resource("contacts", "PUT")
    assert create_info["request_schema"]
    assert update_info["method"] == "PUT"
    assert "contact" in update_info["request_schema"].get("properties", {})


def test_unsupported_crud_is_actionable():
    with pytest.raises(ValueError, match="does not support"):
        get_operation("countries", "POST")
