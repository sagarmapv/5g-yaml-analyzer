import pytest

from backend.services.nf_classifier import classify_nf


def test_classify_from_title_prefix():
    assert classify_nf("TS29510_Namf_Communication.yaml", {"title": "Namf_Communication"}) == "AMF"


def test_classify_from_filename_n_prefix():
    assert (
        classify_nf(
            "TS29519_Npcf_PolicyAuthorization.yaml",
            {"title": "AM Policy Authorization"},
        )
        == "PCF"
    )


def test_classify_from_description_keywords():
    info = {
        "title": "MBS User Service Announcement",
        "description": "MBS User Service Announcement Element units.",
    }
    assert classify_nf("TS26517_MBSUserServiceAnnouncement.yaml", info) == "MBS"


def test_classify_edge_from_description():
    info = {
        "title": "Eees_EASDiscovery",
        "description": "API for Edge Enabler EAS Discovery.",
    }
    assert classify_nf("TS24558_Eees_EASDiscovery.yaml", info) == "EDGE"


def test_classify_nwdaf_from_filename():
    assert (
        classify_nf(
            "TS29520_Nnwdaf_AnalyticsInfo.yaml",
            {"title": "Nnwdaf_AnalyticsInfo"},
        )
        == "NWDAF"
    )


def test_classify_udr_from_description():
    info = {
        "title": "Subscription",
        "description": "Unified Data Repository Service API file for subscription data",
    }
    assert classify_nf("TS29503_Subscription.yaml", info) == "UDR"


def test_classify_other_fallback():
    assert classify_nf("unknown.yaml", {"title": "Custom Internal API"}) == "OTHER"
