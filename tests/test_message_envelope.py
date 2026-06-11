"""Tests for structured message envelopes."""

from backend.services.message_envelope import build_message_envelope


def test_envelope_create_sm_policy():
    env = build_message_envelope("CreateSMPolicy")
    assert env is not None
    assert env["method"] == "POST"
    assert "Content-Type" in env["headers"]
    assert env["body"]["schemaRef"] == "SmPolicyContextData"
    assert env["body"]["json"] is not None
    assert "supi" in env["body"]["json"]


def test_envelope_post_sm_contexts():
    env = build_message_envelope("PostSmContexts")
    assert env is not None
    assert env["body"]["json"] is not None
