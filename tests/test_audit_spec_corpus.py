"""Tests for corpus audit script."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_spec_corpus.py"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_spec_corpus", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def audit():
    return _load_audit_module()


def test_journey_ts_set_includes_anchor_and_nfs(audit):
    journey = audit.journey_ts_set("29.512")
    assert "29.512" in journey
    assert "23.502" in journey
    assert "29.518" in journey
    assert "29.502" in journey
    assert "29.519" in journey


def test_build_audit_structure(audit):
    report = audit.build_audit("29.512")
    assert "items" in report
    assert "meta" in report
    assert report["meta"]["total"] > 0
    assert report["meta"]["inJourney"] >= 15
    by_ts = {i["tsNumber"]: i for i in report["items"]}
    assert by_ts["29.512"]["inJourney"] is True
    assert by_ts["29.502"]["yamlCount"] > 0


def test_audit_entry_gap_fields(audit):
    item = audit.audit_entry("29.512", {"yamlFiles": ["TS29512_Npcf_SMPolicyControl.yaml"]}, True)
    assert "gaps" in item
    assert "gapSummary" in item
    assert item["hasNarrative"] is True


def test_non_journey_yaml_spec_only_flags_bank(audit):
    assert audit._gap_parts(
        {"referenceOnly": False, "inJourney": False, "yamlCount": 2, "bankCount": 0, "series": "service"}
    ) == ["bank"]
    assert (
        audit._gap_parts(
            {
                "referenceOnly": False,
                "inJourney": False,
                "yamlCount": 2,
                "bankCount": 2,
                "hasPdf": False,
                "hasNarrative": False,
                "series": "service",
            }
        )
        == []
    )
