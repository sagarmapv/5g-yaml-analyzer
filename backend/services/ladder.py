"""Build signaling ladder messages from canonical flow graph."""

from __future__ import annotations

from backend.config import BANK_DIR
from backend.services.flow_graph import load_flow, merge_layers, next_step_ids
from backend.services.nf_catalog import actors_for_flow
from backend.services.search import find_operation, load_bank
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.story_stitch import enrich_e2e_flow

_NON_NF_ACTORS = frozenset({"UE", "RAN", "DN", ""})

DEFAULT_FLOW_ID = "pdu-session-establishment"


def ladder_actors(messages: list[dict] | None = None) -> list[str]:
    if messages:
        return actors_for_flow(messages)
    return actors_for_flow(_fallback_messages())


def _fallback_messages() -> list[dict]:
    return build_ladder_messages_from_flow(DEFAULT_FLOW_ID)


def _column_index(actor: str, actors: list[str], *, terminator: bool = False) -> int:
    if actor == "UE" and terminator:
        return len(actors) - 1
    try:
        return actors.index(actor)
    except ValueError:
        return -1


def _attach_columns(msg: dict, actors: list[str]) -> dict:
    out = dict(msg)
    to_term = out.get("toTerminator") is True
    out["fromIndex"] = _column_index(out.get("from", ""), actors)
    out["toIndex"] = _column_index(out.get("to", ""), actors, terminator=to_term)
    return out


def _resolve_source_file(operation_id: str) -> str:
    if not operation_id or not BANK_DIR.exists():
        return ""
    for bank_file in sorted(BANK_DIR.glob("*_Bank.json")):
        bank = load_bank(bank_file.name.replace("_Bank.json", ".yaml"))
        if bank and find_operation(bank, operation_id):
            return bank.get("sourceFile", "")
    return ""


def _has_message_detail(operation_id: str, source_file: str) -> bool:
    if not operation_id:
        return False
    if source_file:
        return True
    return operation_id == "SmPolicyUpdateNotification"


def _build_flow_message(step: dict, anchor: str, flow: dict) -> dict:
    operation_id = step.get("operationId") or None
    source_file = _resolve_source_file(operation_id) if operation_id else ""
    direction = step.get("direction", "procedural")
    message_kind = step.get("messageKind", "procedural")

    label = step.get("label") or ""
    if not label and operation_id:
        if direction == "response":
            label = f"{operation_id} response"
        elif direction == "notify":
            label = operation_id
        else:
            label = operation_id
    if not label:
        label = step.get("action", "")

    service_ts = step.get("serviceTs", "")
    if not service_ts and step.get("inAnchor"):
        service_ts = normalize_ts_number(anchor)

    msg = {
        "stepId": step.get("id", ""),
        "stepOrder": step.get("order", 0),
        "from": step.get("from", ""),
        "to": step.get("to", ""),
        "interface": step.get("interface", ""),
        "direction": direction,
        "label": label,
        "action": step.get("action", ""),
        "operationId": operation_id,
        "serviceTs": normalize_ts_number(service_ts) if service_ts else "",
        "procedureTs": normalize_ts_number(step.get("procedureTs", flow.get("procedureTs", ""))),
        "payload": step.get("payload", ""),
        "response": step.get("response", ""),
        "sourceFile": source_file,
        "hasMessageDetail": _has_message_detail(operation_id or "", source_file),
        "messageKind": message_kind,
        "inAnchor": bool(step.get("inAnchor")),
        "layer": step.get("layer", ""),
        "nextStepIds": next_step_ids(flow, step.get("id", "")),
        "async": bool(step.get("async")),
        "toTerminator": bool(step.get("toTerminator")),
    }
    return msg


def build_ladder_messages_from_flow(
    flow_id: str = DEFAULT_FLOW_ID,
    layers: list[str] | None = None,
) -> list[dict]:
    flow = load_flow(flow_id)
    if not flow:
        return []

    anchor = normalize_ts_number(flow.get("anchorSpec", "29.512"))
    steps = merge_layers(flow, layers)
    raw_messages = [_build_flow_message(step, anchor, flow) for step in steps]
    raw_messages = [m for m in raw_messages if m.get("from") or m.get("to")]

    actors = actors_for_flow(raw_messages)
    return [_attach_columns(m, actors) for m in raw_messages]


def build_ladder_messages(anchor: str = "29.512", flow_id: str | None = None) -> list[dict]:
    """Build ladder messages — prefers flow graph when available."""
    fid = flow_id or DEFAULT_FLOW_ID
    if load_flow(fid):
        return build_ladder_messages_from_flow(fid)

    anchor = normalize_ts_number(anchor)
    narrative = load_narrative(anchor)
    if not narrative:
        return []

    flow = enrich_e2e_flow(anchor, anchor)
    interactions = narrative.get("interactions", [])
    messages: list[dict] = []

    for step in (flow or {}).get("steps", []):
        from_nf = step.get("actors", ["", ""])[0] if step.get("actors") else ""
        to_nf = step.get("actors", ["", ""])[-1] if len(step.get("actors", [])) > 1 else ""
        if step.get("order") == 1:
            from_nf, to_nf = "UE", "AMF"
        msg = {
            "stepId": f"legacy_{step.get('order', 0)}",
            "stepOrder": step.get("order", 0),
            "from": from_nf,
            "to": to_nf,
            "interface": "",
            "direction": "request",
            "label": step.get("action", ""),
            "action": step.get("action", ""),
            "operationId": step.get("operationId"),
            "serviceTs": "",
            "procedureTs": "",
            "payload": "",
            "response": "",
            "sourceFile": _resolve_source_file(step.get("operationId", "") or ""),
            "hasMessageDetail": bool(step.get("operationId")),
            "messageKind": step.get("messageKind", "procedural"),
            "inAnchor": bool(step.get("in512")),
            "layer": "",
            "nextStepIds": [],
            "async": False,
            "toTerminator": False,
        }
        if msg["from"] or msg["to"]:
            messages.append(msg)

    actors = actors_for_flow(messages)
    return [_attach_columns(m, actors) for m in messages]


def build_ladder_payload(
    story_id: str,
    anchor: str,
    title: str,
    flow_id: str | None = None,
) -> dict:
    fid = flow_id or DEFAULT_FLOW_ID
    messages = build_ladder_messages(anchor, flow_id=fid)
    return {
        "storyId": story_id,
        "title": title,
        "anchorSpec": normalize_ts_number(anchor),
        "flowId": fid,
        "ladderActors": actors_for_flow(messages),
        "ladderMessages": messages,
        "knowledgeUrl": f"/stories?id={story_id}",
    }


def is_message_highlighted(msg: dict, selected: set[str]) -> bool:
    if not selected:
        return True
    if len(selected) == 1:
        nf = next(iter(selected))
        return msg.get("from") == nf or msg.get("to") == nf
    return msg.get("from") in selected and msg.get("to") in selected


def filter_ladder_by_nf(messages: list[dict], nf: str) -> tuple[list[dict], list[str]]:
    nf = (nf or "").strip()
    if not nf:
        return messages, _peer_nfs(messages)

    filtered = [m for m in messages if m.get("from") == nf or m.get("to") == nf]
    return filtered, _peer_nfs(filtered, focus=nf)


def _peer_nfs(messages: list[dict], focus: str = "") -> list[str]:
    peers: list[str] = []
    for m in messages:
        for key in ("from", "to"):
            actor = m.get(key, "")
            if actor and actor not in _NON_NF_ACTORS and actor not in peers:
                peers.append(actor)
    if focus and focus in peers:
        peers.remove(focus)
        peers.insert(0, focus)
    return peers
