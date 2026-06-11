import pytest

from backend.services.nf_topology import (
    _extract_edges_from_yaml_text,
    _target_nf_from_ref_yaml,
    build_topology,
)


def test_target_nf_from_ref_yaml_maps_npcf():
    assert _target_nf_from_ref_yaml("TS29507_Npcf_AMPolicyControl.yaml") == "PCF"


def test_target_nf_skips_common_data():
    assert _target_nf_from_ref_yaml("TS29571_CommonData.yaml") is None


def test_extract_edges_from_yaml_text_finds_refs():
    text = """
    paths:
      /foo:
        post:
          requestBody:
            content:
              application/json:
                schema:
                  $ref: 'TS29502_Nsmf_PDUSession.yaml#/components/schemas/Foo'
    """
    edges = _extract_edges_from_yaml_text("TS29518_Namf_Communication.yaml", text)
    assert ("AMF", "SMF") in edges
    assert edges[("AMF", "SMF")]["count"] >= 1


def test_detect_scp_proxy_edge():
    text = "paths:\n  /scp-domain-routing-info:\n    get:\n      summary: SCP domain info\n"
    edges = _extract_edges_from_yaml_text("TS29510_Nnrf_NFDiscovery.yaml", text)
    assert ("NRF", "SCP") in edges


def test_detect_sepp_from_ts29573_ref():
    text = "$ref: 'TS29573_N32_Handshake.yaml#/components/schemas/N32Purpose'"
    edges = _extract_edges_from_yaml_text("TS29510_Nnrf_NFDiscovery.yaml", text)
    assert ("NRF", "SEPP") in edges


def test_build_topology_structure(tmp_path):
    yaml_dir = tmp_path / "yamls"
    yaml_dir.mkdir()
    (yaml_dir / "TS29518_Namf_Communication.yaml").write_text(
        "paths:\n  /x:\n    get:\n      responses:\n        '200':\n          $ref: 'TS29502_Nsmf_PDUSession.yaml#/components/responses/200'\n",
        encoding="utf-8",
    )
    (yaml_dir / "TS29502_Nsmf_PDUSession.yaml").write_text(
        "info:\n  title: Nsmf_PDUSession\n",
        encoding="utf-8",
    )

    topo = build_topology(yaml_dir=yaml_dir, core_only=True, min_weight=1)
    assert topo["meta"]["nodeCount"] >= 2
    assert any(e["from"] == "AMF" and e["to"] == "SMF" for e in topo["edges"])
