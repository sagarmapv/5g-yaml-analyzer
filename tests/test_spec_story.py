import json
from pathlib import Path

import pytest

from backend.config import CONTENT_DIR, PROJECT_ROOT, YAML_DIR
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.spec_story import build_spec_detail
from backend.services.story_stitch import build_element_readiness, build_story_gaps, enrich_e2e_flow


def test_normalize_ts_number():
    assert normalize_ts_number("29.512") == "29.512"
    assert normalize_ts_number("29512") == "29.512"


def test_narrative_512_exists():
    path = CONTENT_DIR / "specs" / "29.512.json"
    assert path.exists()
    narrative = load_narrative("29.512")
    assert narrative["tsNumber"] == "29.512"
    assert len(narrative["entryPoints"]) >= 4
    assert len(narrative["e2eFlow"]["steps"]) >= 5


@pytest.mark.skipif(not (YAML_DIR / "TS29512_Npcf_SMPolicyControl.yaml").exists(), reason="no YAML corpus")
def test_build_spec_detail_512():
    detail = build_spec_detail("29.512")
    assert detail is not None
    assert detail["spec"]["tsNumber"] == "29.512"
    assert len(detail["operations"]) >= 4
    assert len(detail["referencedBy"]) >= 10
    assert detail["narrative"] is not None
    assert any(op["operationId"] == "CreateSMPolicy" for op in detail["operations"])
    pcf_nodes = [n for n in detail["topology"]["nodes"] if n["id"] == "PCF"]
    assert pcf_nodes


def test_build_spec_detail_unknown():
    assert build_spec_detail("99.999") is None


def test_story_gaps_512():
    gaps = build_story_gaps("29.512")
    assert gaps["meta"]["total"] >= 6
    ts_nums = {i["tsNumber"] for i in gaps["items"]}
    assert "23.502" in ts_nums
    assert "29.513" in ts_nums


def test_enriched_e2e_has_stitch_refs():
    flow = enrich_e2e_flow("29.512")
    assert flow is not None
    with_refs = [s for s in flow["steps"] if s.get("stitchRefs")]
    assert len(with_refs) >= 3


def test_enriched_e2e_steps_have_layer_hints():
    flow = enrich_e2e_flow("29.512")
    assert flow is not None
    for step in flow["steps"]:
        assert "layerHint" in step
        hint = step["layerHint"]
        assert "procedureTs" in hint
        assert "nfs" in hint
        assert "serviceTs" in hint
        assert "operationId" in hint
    step4 = next(s for s in flow["steps"] if s.get("order") == 4)
    assert step4["layerHint"]["operationId"] == "CreateSMPolicy"
    assert step4["layerHint"]["serviceTs"] == "29.512"
    assert "SMF" in step4["layerHint"]["nfs"]
    assert step4["layerHint"]["procedureTs"] == "23.502"


def test_narrative_29502_exists():
    narrative = load_narrative("29.502")
    assert narrative is not None
    assert narrative["primaryNf"] == "SMF"
    assert len(narrative["entryPoints"]) >= 3
    assert len(narrative["e2eFlow"]["steps"]) >= 5


def test_narrative_23502_exists():
    narrative = load_narrative("23.502")
    assert narrative is not None
    assert "Procedures" in narrative["title"]
    assert narrative.get("highlightClauses")


@pytest.mark.skipif(not (CONTENT_DIR / "specs" / "23.502-clauses.json").exists(), reason="no 23.502 PDF")
def test_build_spec_detail_23502_full_narrative():
    detail = build_spec_detail("23.502")
    assert detail is not None
    assert detail["narrative"]["stitchAnchor"] == "29.512"
    assert "Procedures" in detail["spec"]["title"]
    assert not detail["spec"]["title"].startswith("(referenced")
    assert detail["pdfClauses"] is not None
    assert detail["specReadiness"] is not None
    assert detail["specReadiness"]["hasStory"] is True
    assert detail["specReadiness"]["hasSpec"] is True
    assert detail["enrichedE2eFlow"] is not None
    assert len(detail["highlightClauses"]) >= 1


@pytest.mark.skipif(not (YAML_DIR / "TS29502_Nsmf_PDUSession.yaml").exists(), reason="no 29.502 YAML")
def test_build_spec_detail_29502_full_narrative():
    detail = build_spec_detail("29.502")
    assert detail is not None
    assert detail["narrative"]["stitchAnchor"] == "29.512"
    assert detail["narrative"]["primaryNf"] == "SMF"
    assert len(detail["narrative"]["entryPoints"]) >= 3
    assert detail["enrichedE2eFlow"] is not None
    assert any(s.get("in502") for s in detail["enrichedE2eFlow"]["steps"])
    assert any(r["ts"] == "23.502" for r in detail["narrative"]["relatedStory"])
    assert len(detail["operations"]) >= 1
    assert detail["specReadiness"] is not None
    assert detail["specReadiness"]["hasYaml"] is True
    assert detail["specReadiness"]["hasStory"] is True


@pytest.mark.skipif(not (YAML_DIR / "TS29512_Npcf_SMPolicyControl.yaml").exists(), reason="no YAML corpus")
def test_build_spec_detail_512_has_gaps():
    detail = build_spec_detail("29.512")
    assert detail["storyGaps"]["meta"]["ready"] >= 5
    assert detail["enrichedE2eFlow"] is not None


def test_element_readiness_requires_all_three():
    narrative = load_narrative("29.512")
    readiness = build_element_readiness(narrative["elements"], "29.512")
    by_nf = {i["nf"]: i for i in readiness["items"]}
    assert by_nf["PCF"]["hasYaml"] is True
    assert by_nf["SMF"]["hasYaml"] is True
    assert "hasFullNarrative" in by_nf["PCF"]
    assert "storyKind" in by_nf["PCF"]
    if by_nf["PCF"]["hasSpec"] and by_nf["PCF"]["hasStory"]:
        assert by_nf["PCF"]["ready"] is True
        assert by_nf["PCF"]["hasFullNarrative"] is True
        assert by_nf["PCF"]["storyKind"] == "full"


@pytest.mark.skipif(not (YAML_DIR / "TS29512_Npcf_SMPolicyControl.yaml").exists(), reason="no YAML corpus")
def test_build_spec_detail_512_element_readiness():
    detail = build_spec_detail("29.512")
    assert detail["elementReadiness"] is not None
    assert detail["elementReadiness"]["meta"]["total"] == len(detail["narrative"]["elements"])


@pytest.mark.skipif(not (YAML_DIR / "TS29512_Npcf_SMPolicyControl.yaml").exists(), reason="no YAML corpus")
def test_build_spec_detail_512_nf_gaps():
    detail = build_spec_detail("29.512")
    assert detail["nfGaps"] is not None
    assert detail["nfGaps"]["meta"]["total"] == 11
    assert "fullNarrative" in detail["nfGaps"]["meta"]
    by_nf = {i["nf"]: i for i in detail["nfGaps"]["items"]}
    assert by_nf["PCF"]["ready"] is True
    assert by_nf["PCF"]["hasFullNarrative"] is True
    assert by_nf["AMF"]["hasFullNarrative"] is True
    assert by_nf["UPF"]["hasFullNarrative"] is True
    smf = by_nf["SMF"]
    if smf["needsPdf"]:
        assert "spec PDF" in smf["blockers"]
    else:
        assert smf["hasSpec"] is True
        assert smf["ready"] is True
        assert smf["hasFullNarrative"] is True


@pytest.mark.parametrize("ts,nf", [("29.518", "AMF"), ("29.564", "UPF")])
def test_amf_upf_spec_detail(ts, nf):
    detail = build_spec_detail(ts)
    assert detail is not None
    assert detail["narrative"]["primaryNf"] == nf
    assert detail["narrative"]["stitchAnchor"] == "29.512"
    assert len(detail["highlightClauses"]) >= 1
    assert detail["enrichedE2eFlow"] is not None
    assert detail["specReadiness"] is not None


def test_pdf_only_nf_has_story_kind():
    detail = build_spec_detail("29.512")
    by_nf = {i["nf"]: i for i in detail["nfGaps"]["items"]}
    udm = by_nf.get("UDM")
    if udm and udm["ready"] and not udm["hasFullNarrative"]:
        assert udm["storyKind"] == "pdf-clauses"
        assert "full narrative" in udm["blockers"]


def test_pdf_present_if_user_added():
    pdfs = list(YAML_DIR.glob("*129512*.pdf"))
    if not pdfs:
        pytest.skip("PDF not in Yaml-Files/5GC_APIs")
    assert pdfs[0].stat().st_size > 100_000


def test_all_stitch_specs_have_narratives():
    gaps = build_story_gaps("29.512")
    for item in gaps["items"]:
        narrative = load_narrative(item["tsNumber"])
        assert narrative is not None, f"missing narrative for {item['tsNumber']}"
        assert item["hasNarrative"] is True


@pytest.mark.skipif(not (YAML_DIR / "TS29510_Nnrf_NFDiscovery.yaml").exists(), reason="no 29.510 YAML")
def test_build_spec_detail_29510_nrf_narrative():
    detail = build_spec_detail("29.510")
    assert detail is not None
    assert detail["narrative"]["primaryNf"] == "NRF"
    assert detail["specReadiness"]["hasYaml"] is True
    assert detail["specReadiness"]["hasStory"] is True


@pytest.mark.skipif(not (YAML_DIR / "TS29514_Npcf_PolicyAuthorization.yaml").exists(), reason="no 29.514 YAML")
def test_build_spec_detail_29514_af_narrative():
    detail = build_spec_detail("29.514")
    assert detail is not None
    assert detail["narrative"]["primaryNf"] == "AF"
    assert detail["specReadiness"]["hasStory"] is True
