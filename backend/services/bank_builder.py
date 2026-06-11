import json
import os
from pathlib import Path

from backend.config import BANK_DIR, HTTP_METHODS, INDEX_JSON, PARSED_JSON_DIR
from backend.services.nf_classifier import classify_nf


def _extract_operation(path: str, method_name: str, op: dict) -> dict:
    params = [
        {
            "name": param.get("name", ""),
            "in": param.get("in", ""),
            "required": param.get("required", False),
        }
        for param in op.get("parameters", [])
    ]

    request_body_required_fields = []
    if "requestBody" in op:
        content = op["requestBody"].get("content", {})
        for media_obj in content.values():
            schema = media_obj.get("schema", {})
            request_body_required_fields.extend(schema.get("required", []))

    responses = [
        {
            "statusCode": status_code,
            "description": response_obj.get("description", ""),
        }
        for status_code, response_obj in op.get("responses", {}).items()
    ]

    return {
        "path": path,
        "method": method_name.upper(),
        "operationId": op.get("operationId", ""),
        "summary": op.get("summary", ""),
        "description": op.get("description", ""),
        "parameters": params,
        "requestBodyRequiredFields": request_body_required_fields,
        "responses": responses,
    }


def parse_swagger_to_messages(swagger_json: dict) -> list[dict]:
    messages = []
    for path, path_item in swagger_json.get("paths", {}).items():
        for method_name, op in path_item.items():
            if method_name.lower() not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            messages.append(_extract_operation(path, method_name, op))
    return messages


def build_bank_from_parsed_json(parsed_json_dir: Path | None = None) -> dict:
    parsed_dir = parsed_json_dir or PARSED_JSON_DIR
    os.makedirs(BANK_DIR, exist_ok=True)

    index_dict: dict[str, list[dict]] = {}
    parsed_files = sorted(f for f in os.listdir(parsed_dir) if f.endswith(".json"))

    for json_filename in parsed_files:
        json_path = parsed_dir / json_filename
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                swagger_json = json.load(f)

            info = swagger_json.get("info", {}) or {}
            api_group = info.get("title", "UNKNOWN")
            source_file = json_filename.replace(".json", ".yaml")
            nf_name = classify_nf(source_file, info)
            messages = parse_swagger_to_messages(swagger_json)

            bank_obj = {
                "nf": nf_name,
                "service": api_group,
                "sourceFile": source_file,
                "serviceDescription": (info.get("description") or "").strip(),
                "messages": messages,
            }

            bank_filename = source_file.replace(".yaml", "_Bank.json")
            bank_path = BANK_DIR / bank_filename
            with open(bank_path, "w", encoding="utf-8") as f:
                json.dump(bank_obj, f, indent=2)

            if nf_name not in index_dict:
                index_dict[nf_name] = []

            existing_services = [entry["service"] for entry in index_dict[nf_name]]
            if api_group not in existing_services:
                index_dict[nf_name].append(
                    {"service": api_group, "sourceFile": source_file}
                )
        except Exception as exc:
            print(f"Failed to process {json_filename}: {exc}")

    with open(INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(index_dict, f, indent=2)

    return index_dict
