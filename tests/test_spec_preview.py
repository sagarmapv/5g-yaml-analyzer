import pytest

from backend.services.master_story import build_master_story
from backend.services.spec_narrative import load_narrative
from backend.services.spec_story import build_spec_preview


def test_build_master_story_hub_view():
    hub = build_master_story("pdu-session-sm-policy", view="hub")
    assert hub is not None
    assert hub.get("view") == "hub"
    assert hub.get("nfGaps") is None
    assert hub.get("specStories") is None
    assert hub.get("elementReadiness") is None
    assert len(hub.get("nfLens", [])) >= 10
    assert len(hub.get("supportingSpecs", [])) == 8
    lens = hub["nfLens"][0]
    assert "inSpec" in lens
    assert "ready" not in lens
    assert "hasSpec" not in lens
    in_flow = {item["nf"] for item in hub.get("nfInFlow", [])}
    ecosystem = {item["nf"] for item in hub.get("nfEcosystem", [])}
    assert in_flow == {"AMF", "SMF", "NRF", "PCF", "UDR", "UPF"}
    assert ecosystem == {"AF", "BSF", "CHF", "NEF", "UDM"}
    assert hub.get("flowNfOrder") == ["AMF", "SMF", "NRF", "PCF", "UDR", "UPF"]
    for item in hub["nfInFlow"]:
        assert item["inFlow"] is True
        assert item["flowOrder"] >= 0
    for item in hub["nfEcosystem"]:
        assert item["inFlow"] is False
        assert item["flowOrder"] == -1
    assert hub.get("ladderUrl", "").startswith("/ladder?id=")
    assert hub.get("ladderMessages") is None


def test_build_master_story_full_still_has_gaps():
    full = build_master_story("pdu-session-sm-policy", view="full")
    assert full is not None
    assert full.get("nfGaps") is not None
    assert full.get("specStories") is not None


@pytest.mark.parametrize("ts", ["29.502", "29.518", "29.503", "29.519"])
def test_build_spec_preview(ts):
    preview = build_spec_preview(ts)
    assert preview is not None
    assert preview["tsNumber"] == ts
    assert preview["title"]
    assert preview["storyUrl"] == f"/specs/{ts}"
    assert "layerHints" in preview
    assert preview["layerHints"]["serviceTs"] == ts
    narrative = load_narrative(ts)
    if narrative:
        assert preview["primaryNf"] == narrative.get("primaryNf", "")


def test_build_spec_preview_smf_has_architecture_layer():
    preview = build_spec_preview("29.502")
    assert preview is not None
    assert preview["layerHints"]["architectureTs"] == "23.502"
    assert any(op["operationId"] == "PostSmContexts" for op in preview["layerHints"]["operations"])
