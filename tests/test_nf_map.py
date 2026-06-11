from backend.services.nf_map import build_nf_map, build_spec_map


def test_build_nf_map_structure(tmp_path):
    yaml_dir = tmp_path / "yamls"
    yaml_dir.mkdir()
    (yaml_dir / "TS29518_Namf_Communication.yaml").write_text(
        """openapi: 3.0.0
info:
  title: Namf_Communication
externalDocs:
  description: 3GPP TS 29.518 V18.5.0; Access and Mobility Management Services
  url: 'https://www.3gpp.org/ftp/Specs/archive/29_series/29.518/'
""",
        encoding="utf-8",
    )
    (yaml_dir / "TS29518_Namf_EventExposure.yaml").write_text(
        """openapi: 3.0.0
info:
  title: Namf_EventExposure
externalDocs:
  description: 3GPP TS 29.518 V18.5.0; Access and Mobility Management Services
""",
        encoding="utf-8",
    )
    (yaml_dir / "TS29502_Nsmf_PDUSession.yaml").write_text(
        """openapi: 3.0.0
info:
  title: Nsmf_PDUSession
externalDocs:
  description: 3GPP TS 29.502 V18.5.0; Session Management Services
""",
        encoding="utf-8",
    )

    result = build_nf_map(yaml_dir)
    assert result["meta"]["nfCount"] >= 2
    amf = next(n for n in result["nfs"] if n["nf"] == "AMF")
    assert amf["specCount"] == 1
    assert amf["yamlCount"] == 2
    assert amf["specs"][0]["tsNumber"] == "29.518"
    assert len(amf["specs"][0]["yamls"]) == 2


def test_build_spec_map_inverts_nf_map():
    result = build_spec_map()
    assert result["meta"]["specCount"] > 0
    spec = next(s for s in result["specs"] if s["tsNumber"] == "29.518")
    assert spec["nfCount"] >= 1
    amf = next(n for n in spec["nfs"] if n["nf"] == "AMF")
    assert amf["yamlCount"] >= 1


def test_build_nf_map_on_real_corpus():
    result = build_nf_map()
    assert result["meta"]["yamlCount"] > 0
    assert result["meta"]["nfCount"] > 0
    amf = next((n for n in result["nfs"] if n["nf"] == "AMF"), None)
    assert amf is not None
    ts518 = next((s for s in amf["specs"] if s["tsNumber"] == "29.518"), None)
    assert ts518 is not None
    assert ts518["yamlCount"] >= 1
