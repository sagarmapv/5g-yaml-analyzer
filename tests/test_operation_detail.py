"""Tests for operation detail API builder."""

import pytest

from backend.services.operation_detail import build_operation_detail


def test_create_sm_policy_detail():
    detail = build_operation_detail("CreateSMPolicy")
    assert detail is not None
    assert detail["operationId"] == "CreateSMPolicy"
    assert detail["method"] == "POST"
    assert detail["request"]["schemaRef"] == "SmPolicyContextData"
    assert "supi" in detail["request"]["requiredProperties"]
    assert any(r["statusCode"] == "201" for r in detail["responses"])
    loc = next(r for r in detail["responses"] if r["statusCode"] == "201")
    assert any(h["name"] == "Location" for h in loc["headers"])


def test_post_sm_contexts_detail():
    detail = build_operation_detail("PostSmContexts")
    assert detail is not None
    assert detail["operationId"] == "PostSmContexts"
    assert detail["nf"] == "SMF"


def test_search_nf_instances_detail():
    detail = build_operation_detail("SearchNFInstances")
    assert detail is not None
    assert detail["method"] in ("GET", "POST")


def test_unknown_operation():
    assert build_operation_detail("NotARealOperationId_xyz") is None


def test_create_sm_policy_request_view():
    detail = build_operation_detail("CreateSMPolicy", view="request")
    assert detail is not None
    assert detail.get("responses") is None
    assert detail["view"] == "request"
    assert detail["request"]["schemaRef"] == "SmPolicyContextData"
    assert len(detail["request"].get("properties", [])) > 0
