import pytest

from backend.services.master_story import build_master_story, list_stories
from backend.services.spec_narrative import load_narrative
from backend.services.spec_story import build_spec_detail


def test_list_stories_finds_pdu_session():
    data = list_stories()
    ids = {s["id"] for s in data["stories"]}
    assert "pdu-session-sm-policy" in ids


def test_journey_audit_all_narratives():
    from scripts.audit_spec_corpus import build_audit

    report = build_audit("29.512")
    journey_gaps = report.get("journeyGaps", [])
    assert journey_gaps == [], f"unexpected journey gaps: {journey_gaps}"


def test_build_master_story_composes_payload():
    detail = build_master_story("pdu-session-sm-policy")
    assert detail is not None
    assert detail["anchorSpec"] == "29.512"
    assert detail["enrichedE2eFlow"] is not None
    assert len(detail["enrichedE2eFlow"]["steps"]) >= 5
    assert detail["elementReadiness"]["meta"]["total"] >= 10
    assert len(detail["nfLens"]) >= 10
    assert len(detail["specStories"]) == 8
    assert detail["meta"]["stitchTotal"] == 8


def test_master_story_spec_stories_have_readiness():
    detail = build_master_story("pdu-session-sm-policy")
    for spec in detail["specStories"]:
        assert "ts" in spec
        assert "storyUrl" in spec
        assert spec["specReadiness"] is not None
        assert "hasStory" in spec["specReadiness"]


def test_master_story_flow_steps_have_ref_spec_for_linking():
    detail = build_master_story("pdu-session-sm-policy")
    with_ref = [s for s in detail["enrichedE2eFlow"]["steps"] if s.get("refSpec")]
    assert len(with_ref) >= 3


def test_build_master_story_unknown():
    assert build_master_story("nonexistent-story") is None


def test_build_master_story_nf_gaps():
    detail = build_master_story("pdu-session-sm-policy")
    assert detail["nfGaps"] is not None
    assert detail["nfGaps"]["meta"]["total"] == 11
    assert "fullNarrative" in detail["nfGaps"]["meta"]
    assert "needsFullNarrative" in detail["nfGaps"]["meta"]
    assert detail["meta"]["nfFullNarrative"] == detail["nfGaps"]["meta"]["fullNarrative"]
    by_nf = {i["nf"]: i for i in detail["nfGaps"]["items"]}
    assert by_nf["PCF"]["ready"] is True
    assert by_nf["PCF"]["hasFullNarrative"] is True
    assert by_nf["PCF"]["storyKind"] == "full"
    assert by_nf["PCF"]["blockers"] == []
    assert "needsPdf" in by_nf["AMF"]
    assert "blockers" in by_nf["SMF"]
    assert by_nf["AMF"]["hasFullNarrative"] is True
    assert by_nf["AMF"]["storyKind"] == "full"
    assert by_nf["UPF"]["hasFullNarrative"] is True
    assert by_nf["UPF"]["storyKind"] == "full"
    # When NF primary PDFs are installed, all elements can be fully ready.
    if detail["meta"]["nfNeedsPdf"] == 0:
        assert detail["nfGaps"]["meta"]["ready"] == 11
        assert all(i["ready"] for i in detail["nfGaps"]["items"])
        assert detail["meta"]["nfFullNarrative"] == 11
    else:
        assert by_nf["AMF"]["needsPdf"] is True
        assert "spec PDF" in by_nf["AMF"]["blockers"]


@pytest.mark.parametrize(
    "ts,title_fragment,nf",
    [
        ("29.503", "Data Management", "UDM"),
        ("29.504", "Data Repository", "UDR"),
        ("29.519", "Policy Data", "PCF"),
        ("29.521", "Binding", "BSF"),
        ("29.522", "Exposure", "NEF"),
        ("32.291", "Charging", "CHF"),
        ("29.518", "Mobility", "AMF"),
        ("29.564", "User Plane", "UPF"),
    ],
)
def test_journey_nf_narratives(ts, title_fragment, nf):
    narrative = load_narrative(ts)
    assert narrative is not None
    assert title_fragment.lower() in narrative["title"].lower()
    assert narrative["stitchAnchor"] == "29.512"
    assert narrative["primaryNf"] == nf
    assert len(narrative["entryPoints"]) >= 2
    assert len(narrative["e2eFlow"]["steps"]) >= 3
    assert narrative.get("highlightClauses")


@pytest.mark.parametrize(
    "ts,title_fragment",
    [
        ("29.513", "signalling"),
        ("23.501", "architecture"),
        ("23.503", "Policy"),
        ("29.501", "Principles"),
        ("29.510", "Repository"),
        ("29.514", "Authorization"),
    ],
)
def test_stitch_narratives_exist(ts, title_fragment):
    narrative = load_narrative(ts)
    assert narrative is not None
    assert title_fragment.lower() in narrative["title"].lower()
    assert narrative["stitchAnchor"] == "29.512"
    assert len(narrative["entryPoints"]) >= 2
    assert len(narrative["e2eFlow"]["steps"]) >= 3


from backend.config import CONTENT_DIR


@pytest.mark.skipif(not (CONTENT_DIR / "specs" / "29.513-clauses.json").exists(), reason="no 29.513 PDF")
def test_29513_detail_has_highlight_clauses():
    detail = build_spec_detail("29.513")
    assert detail is not None
    assert len(detail["highlightClauses"]) >= 1
    assert not detail["spec"]["title"].startswith("(referenced")
