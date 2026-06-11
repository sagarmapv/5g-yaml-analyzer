"""Resolve OpenAPI operation detail from Bank + Parsed-JSON."""

from __future__ import annotations

import json
from pathlib import Path

from backend.config import BANK_DIR, HTTP_METHODS
from backend.services.parser import load_swagger_json
from backend.services.search import find_operation, load_bank


def _ref_name(ref: str) -> str:
    if not ref:
        return ""
    return ref.rsplit("/", 1)[-1]


def _resolve_schema_required(swagger: dict, schema: dict) -> list[str]:
    if not schema:
        return []
    if "$ref" in schema:
        ref = schema["$ref"]
        name = _ref_name(ref)
        components = swagger.get("components", {}).get("schemas", {})
        resolved = components.get(name, {})
        return list(resolved.get("required", []))
    return list(schema.get("required", []))


def _schema_ref_from_content(swagger: dict, content: dict) -> tuple[str, str, list[str]]:
    if not content:
        return "", "", []
    for content_type, media in content.items():
        schema = media.get("schema", {})
        ref = _ref_name(schema.get("$ref", ""))
        required = _resolve_schema_required(swagger, schema)
        return content_type, ref, required
    return "", "", []


def _resolve_schema_properties(swagger: dict, schema: dict) -> list[dict]:
    if not schema:
        return []
    if "$ref" in schema:
        name = _ref_name(schema["$ref"])
        schema = swagger.get("components", {}).get("schemas", {}).get(name, {})
    props = schema.get("properties", {})
    rows: list[dict] = []
    for prop_name, prop_schema in props.items():
        if not isinstance(prop_schema, dict):
            continue
        prop_type = prop_schema.get("type", "")
        if "$ref" in prop_schema:
            prop_type = _ref_name(prop_schema["$ref"])
        rows.append(
            {
                "name": prop_name,
                "type": prop_type,
                "required": prop_name in schema.get("required", []),
            }
        )
    return rows


def _extract_request(swagger: dict, op: dict) -> dict | None:
    body = op.get("requestBody")
    if not body:
        return None
    content = body.get("content", {})
    content_type, schema_ref, required = _schema_ref_from_content(swagger, content)
    properties: list[dict] = []
    if not content_type and not schema_ref:
        for ct, media in content.items():
            schema = media.get("schema", {})
            content_type = ct
            schema_ref = _ref_name(schema.get("$ref", ""))
            required = _resolve_schema_required(swagger, schema)
            properties = _resolve_schema_properties(swagger, schema)
            break
    else:
        for _ct, media in content.items():
            properties = _resolve_schema_properties(swagger, media.get("schema", {}))
            break
    return {
        "contentType": content_type,
        "schemaRef": schema_ref,
        "requiredProperties": required,
        "properties": properties,
    }


def _extract_responses(swagger: dict, op: dict) -> list[dict]:
    rows: list[dict] = []
    for status_code, response_obj in op.get("responses", {}).items():
        headers = [
            {
                "name": name,
                "description": (hdr.get("description") or "").strip(),
                "required": hdr.get("required", False),
            }
            for name, hdr in (response_obj.get("headers") or {}).items()
        ]
        content = response_obj.get("content", {})
        content_type, schema_ref, required = _schema_ref_from_content(swagger, content)
        if content and not schema_ref:
            for ct, media in content.items():
                schema = media.get("schema", {})
                content_type = ct
                schema_ref = _ref_name(schema.get("$ref", ""))
                required = _resolve_schema_required(swagger, schema)
                break
        rows.append(
            {
                "statusCode": status_code,
                "description": response_obj.get("description", ""),
                "headers": headers,
                "contentType": content_type,
                "schemaRef": schema_ref,
                "requiredProperties": required,
            }
        )
    return rows


def _find_operation_in_swagger(swagger: dict, operation_id: str) -> tuple[str, str, dict] | None:
    for path, path_item in swagger.get("paths", {}).items():
        for method_name, op in path_item.items():
            if method_name.lower() not in HTTP_METHODS:
                continue
            if isinstance(op, dict) and op.get("operationId") == operation_id:
                return path, method_name.upper(), op

    for _name, callback_obj in swagger.get("callbacks", {}).items():
        if not isinstance(callback_obj, dict):
            continue
        for _expr, path_item in callback_obj.items():
            if not isinstance(path_item, dict):
                continue
            for path, methods in path_item.items():
                if not isinstance(methods, dict):
                    continue
                for method_name, op in methods.items():
                    if method_name.lower() not in HTTP_METHODS:
                        continue
                    if isinstance(op, dict) and op.get("operationId") == operation_id:
                        return path, method_name.upper(), op
    return None


def _find_bank_for_operation(operation_id: str) -> tuple[dict, dict] | None:
    if not BANK_DIR.exists():
        return None
    for bank_file in sorted(BANK_DIR.glob("*_Bank.json")):
        with open(bank_file, "r", encoding="utf-8") as f:
            bank = json.load(f)
        msg = find_operation(bank, operation_id)
        if msg:
            return bank, msg
    return None


def build_operation_detail(operation_id: str, view: str = "full") -> dict | None:
    operation_id = (operation_id or "").strip()
    if not operation_id:
        return None

    found = _find_bank_for_operation(operation_id)
    source_file = ""
    nf = ""
    service = ""
    bank_msg: dict | None = None

    if found:
        bank, bank_msg = found
        source_file = bank.get("sourceFile", "")
        nf = bank.get("nf", "")
        service = bank.get("service", "")

    if not source_file:
        for bank_file in sorted(BANK_DIR.glob("*_Bank.json")):
            with open(bank_file, "r", encoding="utf-8") as f:
                bank = json.load(f)
            source_file = bank.get("sourceFile", "")
            if not source_file:
                continue
            try:
                swagger = load_swagger_json(source_file)
            except (FileNotFoundError, RuntimeError):
                continue
            if _find_operation_in_swagger(swagger, operation_id):
                nf = bank.get("nf", "")
                service = bank.get("service", "")
                break
        else:
            if operation_id != "SmPolicyUpdateNotification":
                return None
            source_file = "TS29512_Npcf_SMPolicyControl.yaml"
            nf = "PCF"
            service = "Npcf_SMPolicyControl API"

    try:
        swagger = load_swagger_json(source_file)
    except (FileNotFoundError, RuntimeError):
        return None

    located = _find_operation_in_swagger(swagger, operation_id)
    if not located:
        return None

    path, method, op = located
    parameters = [
        {
            "name": p.get("name", ""),
            "in": p.get("in", ""),
            "required": p.get("required", False),
            "schemaRef": _ref_name((p.get("schema") or {}).get("$ref", "")),
        }
        for p in op.get("parameters", [])
    ]
    request_headers = [p for p in parameters if p.get("in") == "header"]
    path_params = [p for p in parameters if p.get("in") == "path"]
    query_params = [p for p in parameters if p.get("in") == "query"]

    result = {
        "operationId": operation_id,
        "method": method,
        "path": path,
        "summary": op.get("summary", bank_msg.get("summary", "") if bank_msg else ""),
        "description": op.get("description", ""),
        "parameters": parameters,
        "requestHeaders": request_headers,
        "pathParams": path_params,
        "queryParams": query_params,
        "request": _extract_request(swagger, op),
        "sourceFile": source_file,
        "nf": nf,
        "service": service,
        "explorerUrl": f"/?q={operation_id}",
        "storyUrl": f"/specs/{_ts_from_source(source_file)}",
        "view": view,
    }
    if view != "request":
        result["responses"] = _extract_responses(swagger, op)
    return result


def _ts_from_source(source_file: str) -> str:
    name = Path(source_file).stem
    if name.startswith("TS") and len(name) >= 8:
        digits = name[2:7]
        if digits.isdigit():
            return f"{digits[:2]}.{digits[2:]}"
    return ""
