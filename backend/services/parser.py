import json
from pathlib import Path

from backend.config import PARSED_JSON_DIR, YAML_DIR
from backend.services.bank_builder import parse_swagger_to_messages
from backend.services.swagger_bundle import bundle_yaml_to_json


def ensure_parsed_json(filename: str) -> Path:
    json_path = PARSED_JSON_DIR / filename.replace(".yaml", ".json")
    yaml_path = YAML_DIR / filename

    if json_path.exists():
        return json_path

    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {filename}")

    bundle_yaml_to_json(yaml_path, json_path)
    return json_path


def load_parsed_summary(filename: str) -> list[dict]:
    json_path = ensure_parsed_json(filename)
    with open(json_path, "r", encoding="utf-8") as f:
        swagger_json = json.load(f)
    return parse_swagger_to_messages(swagger_json)


def load_swagger_json(filename: str) -> dict:
    json_path = ensure_parsed_json(filename)
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)
