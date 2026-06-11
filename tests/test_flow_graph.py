"""Tests for canonical flow graph."""

from backend.services.flow_graph import load_flow, merge_layers, next_step_ids, list_flows


def test_load_pdu_flow():
    flow = load_flow("pdu-session-establishment")
    assert flow is not None
    assert flow["procedure"] == "pdu_session_establishment"


def test_merge_layers_count():
    flow = load_flow("pdu-session-establishment")
    steps = merge_layers(flow)
    assert len(steps) == 12
    orders = [s["order"] for s in steps]
    assert orders == sorted(orders)


def test_next_step_after_post_sm():
    flow = load_flow("pdu-session-establishment")
    nxt = next_step_ids(flow, "s02_amf_smf_create_sm")
    assert "s03_smf_udm_sm_data" in nxt


def test_flow_has_update_sm_context():
    flow = load_flow("pdu-session-establishment")
    steps = merge_layers(flow)
    ops = [s.get("operationId") for s in steps]
    assert "UpdateSmContext" in ops
    assert "GetSmData" in ops


def test_list_flows():
    flows = list_flows()
    assert any(f["id"] == "pdu-session-establishment" for f in flows)
