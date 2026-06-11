"""Tests for signaling ladder message builder."""

import pytest

from backend.app import create_app
from backend.services.ladder import (
    build_ladder_messages,
    build_ladder_messages_from_flow,
    build_ladder_payload,
    filter_ladder_by_nf,
    is_message_highlighted,
    ladder_actors,
)
from backend.services.master_story import build_story_ladder
from backend.services.nf_catalog import actors_for_flow


def test_ladder_actors_includes_udm():
    messages = build_ladder_messages_from_flow()
    actors = ladder_actors(messages)
    assert actors[0] == "UE"
    assert actors[-1] == "UE"
    assert "UDM" in actors
    assert "RAN" in actors


def test_build_ladder_messages_count():
    messages = build_ladder_messages("29.512")
    assert len(messages) == 12


def test_ladder_step1_ue_to_amf():
    messages = build_ladder_messages("29.512")
    step1 = next(m for m in messages if m["stepOrder"] == 1)
    assert step1["from"] == "UE"
    assert step1["to"] == "AMF"
    assert step1["interface"] == "N1"
    assert step1["messageKind"] == "procedural"
    assert step1.get("stepId")


def test_ladder_step2_post_sm_contexts():
    messages = build_ladder_messages("29.512")
    step2 = next(m for m in messages if m["stepOrder"] == 2)
    assert step2["from"] == "AMF"
    assert step2["to"] == "SMF"
    assert step2["operationId"] == "PostSmContexts"
    assert step2["interface"] == "N11"
    assert step2["messageKind"] == "sbi"
    assert step2["hasMessageDetail"] is True


def test_ladder_step3_udm():
    messages = build_ladder_messages("29.512")
    step3 = next(m for m in messages if m["stepOrder"] == 3)
    assert step3["to"] == "UDM"
    assert step3["operationId"] == "GetSmData"
    assert step3["interface"] == "N10"


def test_ladder_create_sm_policy():
    messages = build_ladder_messages("29.512")
    policy_req = next(m for m in messages if m.get("operationId") == "CreateSMPolicy" and m["direction"] == "request")
    assert policy_req["payload"] == "SmPolicyContextData"
    assert policy_req["interface"] == "N7"
    assert policy_req["inAnchor"] is True


def test_ladder_policy_response():
    messages = build_ladder_messages("29.512")
    policy_resp = next(m for m in messages if m.get("operationId") == "CreateSMPolicy" and m["direction"] == "response")
    assert policy_resp["response"] == "SmPolicyDecision"


def test_ladder_n4_steps():
    messages = build_ladder_messages("29.512")
    n4_steps = [m for m in messages if m["messageKind"] == "n4"]
    assert len(n4_steps) == 2
    assert n4_steps[0]["direction"] == "request"
    assert n4_steps[1]["direction"] == "response"


def test_ladder_update_sm_context():
    messages = build_ladder_messages("29.512")
    upd = next(m for m in messages if m.get("operationId") == "UpdateSmContext")
    assert upd["from"] == "SMF"
    assert upd["to"] == "AMF"


def test_ladder_terminator_ue_hop():
    messages = build_ladder_messages("29.512")
    term = next(m for m in messages if m.get("toTerminator"))
    assert term["from"] == "AMF"
    assert term["to"] == "UE"
    actors = actors_for_flow(messages)
    assert term["toIndex"] == len(actors) - 1


def test_ladder_next_step_ids():
    messages = build_ladder_messages("29.512")
    step2 = next(m for m in messages if m["stepOrder"] == 2)
    assert "s03_smf_udm_sm_data" in step2.get("nextStepIds", [])


def test_is_message_highlighted_multi_nf():
    msg = {"from": "SMF", "to": "PCF"}
    assert is_message_highlighted(msg, {"SMF", "PCF"}) is True
    assert is_message_highlighted(msg, {"SMF"}) is True
    assert is_message_highlighted(msg, {"AMF", "NRF"}) is False
    assert is_message_highlighted(msg, set()) is True


def test_filter_ladder_by_smf():
    messages = build_ladder_messages("29.512")
    filtered, peers = filter_ladder_by_nf(messages, "SMF")
    assert len(filtered) >= 6
    assert "SMF" in peers
    for m in filtered:
        assert m["from"] == "SMF" or m["to"] == "SMF"


def test_build_story_ladder_api_shape():
    payload = build_story_ladder("pdu-session-sm-policy")
    assert payload is not None
    assert payload["storyId"] == "pdu-session-sm-policy"
    assert "UDM" in payload["ladderActors"]
    assert len(payload["ladderMessages"]) == 12
    assert payload["flowId"] == "pdu-session-establishment"
    assert payload["knowledgeUrl"] == "/stories?id=pdu-session-sm-policy"


def test_build_ladder_payload():
    payload = build_ladder_payload("pdu-session-sm-policy", "29.512", "Test")
    assert payload["anchorSpec"] == "29.512"
    assert payload["title"] == "Test"
    assert payload["flowId"] == "pdu-session-establishment"


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_ladder_page_route(client):
    res = client.get("/ladder")
    assert res.status_code == 200
    assert b"Signaling Ladder" in res.data


def test_ladder_api_endpoint(client):
    res = client.get("/api/stories/pdu-session-sm-policy/ladder")
    assert res.status_code == 200
    data = res.get_json()
    assert "UDM" in data["ladderActors"]
    assert len(data["ladderMessages"]) == 12
    assert data["ladderMessages"][0].get("interface") == "N1"


def test_nfs_api_endpoint(client):
    res = client.get("/api/nfs?summary=true")
    assert res.status_code == 200
    data = res.get_json()
    assert data["count"] >= 10


def test_nf_detail_endpoint(client):
    res = client.get("/api/nfs/SMF")
    assert res.status_code == 200
    assert res.get_json()["id"] == "SMF"


def test_operation_request_view_endpoint(client):
    res = client.get("/api/operations/CreateSMPolicy?view=request")
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("responses") is None
    assert data["request"]["schemaRef"] == "SmPolicyContextData"
    assert data.get("envelope") is not None
    assert data["envelope"]["body"]["json"] is not None
