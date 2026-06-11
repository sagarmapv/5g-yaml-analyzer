import json
from pathlib import Path

import pytest

from backend.config import PROJECT_ROOT
from backend.services.bank_builder import build_bank_from_parsed_json, parse_swagger_to_messages
from backend.services.curl_generator import generate_curl
from backend.services.search import find_operation, load_bank, search_bank

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_swagger():
    with open(FIXTURES / "sample_api.json", encoding="utf-8") as f:
        return json.load(f)


def test_project_root_is_windows_safe():
    assert PROJECT_ROOT.exists()
    assert PROJECT_ROOT.name in ("5g-visualizer", "5g-yaml-analyzer")


def test_parse_swagger_to_messages(sample_swagger):
    messages = parse_swagger_to_messages(sample_swagger)
    assert len(messages) == 3
    op_ids = {m["operationId"] for m in messages}
    assert op_ids == {"GetUeContext", "UpdateUeContext", "RegistrationRequest"}
    get_op = next(m for m in messages if m["operationId"] == "GetUeContext")
    assert get_op["method"] == "GET"
    assert len(get_op["parameters"]) == 2


def test_build_bank_from_parsed_json(tmp_path):
    parsed_dir = tmp_path / "Parsed-JSON"
    bank_dir = tmp_path / "Bank"
    index_path = tmp_path / "index.json"
    parsed_dir.mkdir()
    bank_dir.mkdir()

    fixture_copy = parsed_dir / "TS29510_Namf_Communication.json"
    fixture_copy.write_text((FIXTURES / "sample_api.json").read_text(encoding="utf-8"), encoding="utf-8")

    import backend.services.bank_builder as bank_module

    original_parsed = bank_module.PARSED_JSON_DIR
    original_bank = bank_module.BANK_DIR
    original_index = bank_module.INDEX_JSON
    bank_module.PARSED_JSON_DIR = parsed_dir
    bank_module.BANK_DIR = bank_dir
    bank_module.INDEX_JSON = index_path

    try:
        index = build_bank_from_parsed_json(parsed_dir)
        assert "AMF" in index
        assert len(index["AMF"]) == 1

        bank_file = bank_dir / "TS29510_Namf_Communication_Bank.json"
        assert bank_file.exists()
        with open(bank_file, encoding="utf-8") as f:
            bank = json.load(f)
        assert bank["nf"] == "AMF"
        assert len(bank["messages"]) == 3
    finally:
        bank_module.PARSED_JSON_DIR = original_parsed
        bank_module.BANK_DIR = original_bank
        bank_module.INDEX_JSON = original_index


def test_search_bank(tmp_path):
    bank_dir = tmp_path / "Bank"
    bank_dir.mkdir()
    bank = {
        "nf": "AMF",
        "service": "Namf_Communication",
        "sourceFile": "sample_api.yaml",
        "messages": [
            {
                "path": "/registrations",
                "method": "POST",
                "operationId": "RegistrationRequest",
                "summary": "UE registration",
                "description": "",
            }
        ],
    }
    with open(bank_dir / "sample_api_Bank.json", "w", encoding="utf-8") as f:
        json.dump(bank, f)

    results = search_bank("registration", bank_dir)
    assert len(results) == 1
    assert results[0]["operationId"] == "RegistrationRequest"


def test_generate_curl(sample_swagger):
    operation = {
        "path": "/ue-contexts/{ueContextId}",
        "method": "PUT",
        "parameters": [{"name": "ueContextId", "in": "path", "required": True}],
        "requestBodyRequiredFields": ["supi"],
    }
    curl = generate_curl(sample_swagger, operation)
    assert "curl -X PUT" in curl
    assert "amf.example.org" in curl
    assert "Content-Type: application/json" in curl


def test_find_operation():
    bank = {
        "messages": [
            {"operationId": "GetUeContext", "path": "/foo"},
            {"operationId": "UpdateUeContext", "path": "/bar"},
        ]
    }
    assert find_operation(bank, "GetUeContext")["path"] == "/foo"
    assert find_operation(bank, "Missing") is None
