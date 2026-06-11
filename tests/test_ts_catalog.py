from pathlib import Path

from backend.services.ts_catalog import build_ts_catalog, _ts_from_filename


def test_ts_from_filename():
    assert _ts_from_filename("TS29518_Namf_Communication.yaml") == "29.518"


def test_build_ts_catalog_on_real_corpus():
    catalog = build_ts_catalog()
    assert catalog["meta"]["totalSpecs"] > 0
    assert catalog["meta"]["totalYamlFiles"] > 0
    numbers = {s["tsNumber"] for s in catalog["specs"]}
    assert "29.518" in numbers


def test_build_ts_catalog_fixture(tmp_path):
    yaml_dir = tmp_path / "yamls"
    yaml_dir.mkdir()
    (yaml_dir / "TS29518_Namf_Communication.yaml").write_text(
        """openapi: 3.0.0
info:
  title: Namf_Communication
externalDocs:
  description: 3GPP TS 29.518 V18.5.0; 5G System; Access and Mobility Management Services
  url: 'https://www.3gpp.org/ftp/Specs/archive/29_series/29.518/'
servers: []
""",
        encoding="utf-8",
    )
    catalog = build_ts_catalog(yaml_dir)
    assert catalog["meta"]["totalSpecs"] == 1
    spec = catalog["specs"][0]
    assert spec["tsNumber"] == "29.518"
    assert "Access and Mobility" in spec["title"]
    assert "TS29518_Namf_Communication.yaml" in spec["yamlFiles"]
