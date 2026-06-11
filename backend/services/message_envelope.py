"""Structured request envelopes — headers map + body JSON for analyzer and ladder."""

from __future__ import annotations

import json
from pathlib import Path

from backend.config import CONTENT_DIR
from backend.services.operation_detail import build_operation_detail

FIXTURES_DIR = CONTENT_DIR / "fixtures" / "messages"

_SBI_DEFAULT_HEADERS = {
    "Content-Type": {"type": "string", "required": True, "default": "application/json"},
    "Accept": {"type": "string", "required": False, "default": "application/json"},
    "3gpp-Sbi-Message-Priority": {"type": "integer", "required": False},
}


def _load_fixture(operation_id: str) -> dict | None:
    path = FIXTURES_DIR / f"{operation_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _headers_map(detail: dict) -> dict:
    headers: dict = {}
    for h in detail.get("requestHeaders") or []:
        name = h.get("name", "")
        if not name:
            continue
        headers[name] = {
            "type": h.get("schemaRef") or "string",
            "required": bool(h.get("required")),
        }
    req = detail.get("request") or {}
    ct = req.get("contentType") or "application/json"
    if "Content-Type" not in headers:
        headers["Content-Type"] = {"type": "string", "required": True, "default": ct}
    for name, meta in _SBI_DEFAULT_HEADERS.items():
        if name not in headers:
            headers[name] = dict(meta)
    return headers


def _body_schema_stub(detail: dict) -> dict:
    req = detail.get("request") or {}
    props = {}
    for p in req.get("properties") or []:
        props[p.get("name", "")] = {"type": p.get("type") or "string"}
    return {
        "type": "object",
        "required": req.get("requiredProperties") or [],
        "properties": props,
    }


def build_message_envelope(operation_id: str) -> dict | None:
    detail = build_operation_detail(operation_id, view="request")
    if not detail:
        return None

    fixture = _load_fixture(operation_id)
    req = detail.get("request") or {}

    return {
        "operationId": operation_id,
        "method": detail.get("method", ""),
        "path": detail.get("path", ""),
        "headers": _headers_map(detail),
        "body": {
            "contentType": req.get("contentType") or "application/json",
            "schemaRef": req.get("schemaRef", ""),
            "json": fixture,
            "schema": _body_schema_stub(detail),
        },
    }


def attach_envelope_to_detail(detail: dict | None) -> dict | None:
    if not detail:
        return None
    op_id = detail.get("operationId", "")
    if not op_id:
        return detail
    envelope = build_message_envelope(op_id)
    if envelope:
        detail = dict(detail)
        detail["envelope"] = envelope
    return detail
