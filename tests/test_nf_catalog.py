"""Tests for 3GPP NF catalog."""

from backend.services.nf_catalog import (
    catalog_summary,
    list_nfs,
    nf_by_id,
    validate_flow_participants,
)
from backend.services.flow_graph import load_flow, merge_layers


def test_nf_by_id_amf():
    amf = nf_by_id("AMF")
    assert amf is not None
    assert amf["tier"] == "core_control"
    assert "N11" in amf.get("interfaces", {}).get("served", [])


def test_nf_by_id_unknown():
    assert nf_by_id("NOT_AN_NF") is None


def test_list_nfs_e2e_default():
    rows = list_nfs(e2e_default=True)
    ids = {r["id"] for r in rows}
    assert "SMF" in ids
    assert "UDM" in ids
    assert "CHF" not in ids


def test_list_nfs_procedure_pdu():
    rows = list_nfs(procedure="pdu_session_establishment")
    ids = {r["id"] for r in rows}
    assert "UPF" in ids
    assert "PCF" in ids


def test_catalog_summary():
    summary = catalog_summary()
    assert summary["count"] >= 10
    assert "procedureRoles" in summary


def test_validate_flow_participants_ok():
    flow = load_flow("pdu-session-establishment")
    steps = merge_layers(flow)
    assert validate_flow_participants(steps) == []


def test_validate_flow_participants_rejects_unknown():
    errors = validate_flow_participants([{"id": "x", "from": "FOO", "to": "SMF"}])
    assert any("FOO" in e for e in errors)
