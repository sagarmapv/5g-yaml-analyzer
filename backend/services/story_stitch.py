"""Cross-spec story stitching — gaps, clause links, enriched call flows."""

import json
import re
from pathlib import Path

from backend.config import CONTENT_DIR
from backend.services.nf_map import build_spec_map, get_nf_map
from backend.services.pdf_clauses import clauses_cache_path, load_pdf_clauses, pdf_metadata
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.ts_catalog import get_ts_catalog

STITCH_MANIFEST = CONTENT_DIR / "specs" / "stitch-29.512.json"


def load_stitch_manifest(anchor: str = "29.512") -> dict | None:
    path = CONTENT_DIR / "specs" / f"stitch-{anchor}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _catalog_by_ts() -> dict[str, dict]:
    return {s["tsNumber"]: s for s in get_ts_catalog().get("specs", [])}


def _yaml_specs() -> set[str]:
    return {s["tsNumber"] for s in build_spec_map().get("specs", [])}


def _find_clause(clauses: list[dict], clause_num: str = "", search: list[str] | None = None) -> dict | None:
    if clause_num:
        for c in clauses:
            if c["number"] == clause_num or c["number"].startswith(clause_num + "."):
                return c
    if search:
        for term in search:
            q = term.lower()
            for c in clauses:
                if q in c.get("title", "").lower() or q in c.get("number", ""):
                    return c
    return None


def _stitch_status(ts: str) -> dict:
    ts = normalize_ts_number(ts)
    catalog = _catalog_by_ts().get(ts, {})
    pdf = pdf_metadata(ts)
    clauses = load_pdf_clauses(ts)
    narrative = load_narrative(ts)
    has_yaml = ts in _yaml_specs()

    title = catalog.get("title", "")
    if title.startswith("(referenced"):
        title = ""

    return {
        "tsNumber": ts,
        "title": title,
        "hasPdf": pdf is not None,
        "pdfVersion": pdf.get("version", "") if pdf else "",
        "hasYaml": has_yaml,
        "hasNarrative": narrative is not None,
        "clauseCount": clauses.get("clauseCount", 0) if clauses else 0,
        "hasClauses": bool(clauses and clauses.get("clauses")),
        "referenceOnly": catalog.get("referenceOnly", False) or not has_yaml,
        "ready": pdf is not None or has_yaml,
    }


def _nf_in_map(nf: str) -> bool:
    return any(block.get("nf") == nf for block in get_nf_map().get("nfs", []))


def _nf_has_yaml_for_spec(nf: str, ts: str) -> bool:
    for block in get_nf_map().get("nfs", []):
        if block.get("nf") != nf:
            continue
        for spec in block.get("specs", []):
            if spec.get("tsNumber") == ts and spec.get("yamls"):
                return True
    return False


def _story_ready(status: dict) -> bool:
    return bool(status.get("hasNarrative") or (status.get("hasPdf") and status.get("hasClauses")))


def _has_full_narrative(ts: str) -> bool:
    return load_narrative(ts) is not None


def _story_kind(status: dict, has_full_narrative: bool) -> str:
    if has_full_narrative:
        return "full"
    if _story_ready(status):
        return "pdf-clauses"
    return "gap"


def build_element_readiness(elements: list[dict], anchor: str = "29.512") -> dict:
    """Per-NF readiness: green only when PDF (spec), YAML, and story are all available."""
    items: list[dict] = []
    ready_count = 0

    for el in elements:
        nf = el.get("nf", "")
        primary_ts = normalize_ts_number(el.get("primarySpec") or anchor)
        status = _stitch_status(primary_ts)
        has_spec = bool(status.get("hasPdf"))
        has_full_narrative = _has_full_narrative(primary_ts)
        has_story = _story_ready(status)
        if _nf_in_map(nf):
            has_yaml = _nf_has_yaml_for_spec(nf, primary_ts)
        else:
            has_yaml = bool(status.get("hasYaml"))

        ready = has_spec and has_yaml and has_story
        if ready:
            ready_count += 1

        items.append(
            {
                "nf": nf,
                "primarySpec": primary_ts,
                "hasSpec": has_spec,
                "hasYaml": has_yaml,
                "hasStory": has_story,
                "hasFullNarrative": has_full_narrative,
                "storyKind": _story_kind(status, has_full_narrative),
                "ready": ready,
                "state": "ready" if ready else ("partial" if (has_spec or has_yaml or has_story) else "gap"),
                "storyUrl": f"/specs/{primary_ts}",
                "platformUrl": f"/specs?ts={primary_ts}",
            }
        )

    return {
        "items": items,
        "meta": {
            "total": len(items),
            "ready": ready_count,
            "complete": ready_count == len(items) and len(items) > 0,
        },
    }


def _readiness_blockers(item: dict) -> list[str]:
    blockers: list[str] = []
    if not item.get("hasSpec"):
        blockers.append("spec PDF")
    if not item.get("hasYaml"):
        blockers.append("YAML")
    if not item.get("hasStory"):
        blockers.append("story")
    return blockers


def _narrative_blockers(item: dict) -> list[str]:
    blockers = _readiness_blockers(item)
    if not item.get("hasFullNarrative"):
        blockers.append("full narrative")
    return blockers


def build_nf_gaps(elements: list[dict], anchor: str = "29.512") -> dict:
    """Incomplete NF stories — blockers and PDF import hints per element."""
    readiness = build_element_readiness(elements, anchor)
    by_nf = {i["nf"]: i for i in readiness.get("items", [])}
    role_by_nf = {el.get("nf", ""): el.get("role", "") for el in elements}

    items: list[dict] = []
    needs_pdf = 0
    needs_narrative = 0
    needs_full_narrative = 0
    full_narrative = 0
    incomplete = 0

    for el in elements:
        nf = el.get("nf", "")
        primary_ts = normalize_ts_number(el.get("primarySpec") or anchor)
        ready_item = by_nf.get(nf, {})
        blockers = _narrative_blockers(ready_item)
        needs_pdf_flag = not ready_item.get("hasSpec", False)
        needs_story = not ready_item.get("hasStory", False)
        needs_full = not ready_item.get("hasFullNarrative", False)
        if needs_pdf_flag:
            needs_pdf += 1
        if needs_story:
            needs_narrative += 1
        if needs_full:
            needs_full_narrative += 1
        else:
            full_narrative += 1
        if not ready_item.get("ready", False):
            incomplete += 1

        items.append(
            {
                "nf": nf,
                "primarySpec": primary_ts,
                "role": role_by_nf.get(nf, el.get("role", "")),
                "hasSpec": ready_item.get("hasSpec", False),
                "hasYaml": ready_item.get("hasYaml", False),
                "hasStory": ready_item.get("hasStory", False),
                "hasFullNarrative": ready_item.get("hasFullNarrative", False),
                "storyKind": ready_item.get("storyKind", "gap"),
                "ready": ready_item.get("ready", False),
                "state": ready_item.get("state", "gap"),
                "blockers": blockers,
                "needsPdf": needs_pdf_flag,
                "needsFullNarrative": needs_full,
                "storyUrl": ready_item.get("storyUrl", f"/specs/{primary_ts}"),
                "platformUrl": ready_item.get("platformUrl", f"/specs?ts={primary_ts}"),
                "importHint": f"python scripts/extract_spec_pdf.py {primary_ts}",
            }
        )

    items.sort(key=lambda x: (not x["needsPdf"], x["nf"]))

    return {
        "items": items,
        "meta": {
            "total": len(items),
            "ready": readiness.get("meta", {}).get("ready", 0),
            "fullNarrative": full_narrative,
            "needsPdf": needs_pdf,
            "needsNarrative": needs_narrative,
            "needsFullNarrative": needs_full_narrative,
            "incomplete": incomplete,
        },
    }


def build_story_gaps(anchor: str = "29.512") -> dict:
    manifest = load_stitch_manifest(anchor)
    items: list[dict] = []
    if manifest:
        for entry in manifest.get("stitchSpecs", []):
            ts = entry["ts"]
            status = _stitch_status(ts)
            status["priority"] = entry.get("priority", "")
            status["role"] = entry.get("role", "")
            status["storyUrl"] = f"/specs/{ts}"
            items.append(status)
    else:
        narrative = load_narrative(anchor)
        for rel in narrative.get("relatedSpecs", []) if narrative else []:
            ts = rel["ts"]
            status = _stitch_status(ts)
            status["role"] = rel.get("role", "")
            status["storyUrl"] = f"/specs/{ts}"
            items.append(status)

    ready = sum(1 for i in items if i["ready"])
    return {
        "anchor": anchor,
        "items": items,
        "meta": {
            "total": len(items),
            "ready": ready,
            "complete": ready == len(items) and len(items) > 0,
        },
    }


def build_spec_readiness(ts_number: str, narrative: dict | None = None) -> dict:
    """Readiness for a single spec page: PDF + YAML + story."""
    ts = normalize_ts_number(ts_number)
    narrative = narrative or load_narrative(ts)
    status = _stitch_status(ts)
    has_spec = bool(status.get("hasPdf"))
    has_story = _story_ready(status)
    primary_nf = (narrative or {}).get("primaryNf", "")
    if primary_nf and _nf_in_map(primary_nf):
        has_yaml = _nf_has_yaml_for_spec(primary_nf, ts)
    else:
        has_yaml = bool(status.get("hasYaml"))

    ready = has_spec and has_yaml and has_story
    return {
        "tsNumber": ts,
        "primaryNf": primary_nf,
        "hasSpec": has_spec,
        "hasYaml": has_yaml,
        "hasStory": has_story,
        "ready": ready,
        "state": "ready" if ready else ("partial" if (has_spec or has_yaml or has_story) else "gap"),
        "platformUrl": f"/specs?ts={ts}",
        "storyUrl": f"/specs/{ts}",
    }


def _step_layer_hint(step: dict, anchor_ts: str, flow_ref_specs: list) -> dict:
    """Three-layer chain for UI: procedure (23.xxx) → NF → service (29.xxx) → message."""
    procedure_ts = ""
    for ref in step.get("stitchRefs") or []:
        ts = str(ref.get("ts", ""))
        if ts.startswith("23."):
            procedure_ts = normalize_ts_number(ts)
            break
    if not procedure_ts:
        for row in flow_ref_specs:
            ts = row.get("ts", row) if isinstance(row, dict) else row
            if str(ts).startswith("23."):
                procedure_ts = normalize_ts_number(str(ts))
                break

    nfs = [a for a in step.get("actors", []) if a not in ("UE", "RAN", "")]

    service_ts = ""
    if step.get("in512") or step.get("inSpec"):
        service_ts = normalize_ts_number(anchor_ts)
    elif step.get("refSpec"):
        service_ts = normalize_ts_number(str(step["refSpec"]))
    if not service_ts:
        for ref in step.get("stitchRefs") or []:
            ts = str(ref.get("ts", ""))
            if ts.startswith("29."):
                service_ts = normalize_ts_number(ts)
                break

    return {
        "procedureTs": procedure_ts,
        "nfs": nfs,
        "serviceTs": service_ts,
        "operationId": step.get("operationId", "") or "",
    }


def enrich_e2e_flow(ts_number: str = "29.512", stitch_anchor: str = "29.512") -> dict | None:
    ts_number = normalize_ts_number(ts_number)
    narrative = load_narrative(ts_number)
    if not narrative or not narrative.get("e2eFlow"):
        return None

    manifest = load_stitch_manifest(stitch_anchor)
    step_stitch = manifest.get("stepStitch", []) if manifest else []
    stitch_by_order: dict[int, list[dict]] = {}
    for row in step_stitch:
        stitch_by_order.setdefault(row["order"], []).append(row)

    flow_ref_specs = narrative["e2eFlow"].get("refSpecs", [])
    enriched_steps = []
    for step in narrative["e2eFlow"]["steps"]:
        order = step.get("order", 0)
        refs: list[dict] = []
        for hint in stitch_by_order.get(order, []):
            ts = hint["spec"]
            clauses_data = load_pdf_clauses(ts)
            clauses = clauses_data.get("clauses", []) if clauses_data else []
            found = _find_clause(clauses, hint.get("clause", ""), hint.get("search"))
            if found:
                refs.append(
                    {
                        "ts": ts,
                        "clause": found["number"],
                        "title": found["title"].strip().rstrip("."),
                        "storyUrl": f"/specs/{ts}",
                    }
                )
            elif hint.get("clause"):
                refs.append(
                    {
                        "ts": ts,
                        "clause": hint["clause"],
                        "title": "",
                        "storyUrl": f"/specs/{ts}",
                    }
                )
        enriched = dict(step)
        if refs:
            enriched["stitchRefs"] = refs
        enriched["layerHint"] = _step_layer_hint(enriched, ts_number, flow_ref_specs)
        enriched_steps.append(enriched)

    return {
        "name": narrative["e2eFlow"].get("name", ""),
        "refSpecs": narrative["e2eFlow"].get("refSpecs", []),
        "steps": enriched_steps,
    }


_STITCH_TITLES = {
    "23.502": "Procedures for the 5G System (5GS)",
    "23.501": "System architecture for the 5G System (5GS)",
    "23.503": "Policy and charging control framework for the 5G System (5GS)",
    "29.513": "Policy and Charging Control signalling flows; Stage 3",
    "29.501": "Principles and Guidelines for Services Definition; Stage 3",
    "29.502": "Session Management Services; Stage 3 (SMF SBI)",
    "29.510": "Network Repository Services; Stage 3 (NRF SBI)",
    "29.514": "Policy Authorization Service; Stage 3",
}


def _stitch_summary(ts: str, anchor: str, role: str, primary_nf: str) -> str:
    if ts == "29.502":
        return (
            f"TS 29.502 is the SMF PDU Session SBI (Stage 3). In the {anchor} story, SMF uses these "
            "APIs while establishing or modifying PDU sessions — then calls PCF for session policy. "
            "The **when** (procedure timing) is in TS 23.502; this spec is the **how** (SMF service APIs)."
        )
    if ts == "23.502":
        return (
            f"TS 23.502 defines Stage-2 procedures. For the {anchor} story, clause 4.3.2 PDU Session "
            "Establishment explains when SMF must request session management policy from PCF."
        )
    nf_prefix = f"{primary_nf} — " if primary_nf else ""
    return f"This spec supports the TS {anchor} story. {nf_prefix}{role}"


def minimal_narrative_for_stitch(ts: str, anchor: str = "29.512") -> dict | None:
    """Stitch spec page — role blurb from manifest (works with or without PDF)."""
    manifest = load_stitch_manifest(anchor)
    if not manifest:
        return None
    ts = normalize_ts_number(ts)
    for entry in manifest.get("stitchSpecs", []):
        if entry["ts"] != ts:
            continue
        catalog = _catalog_by_ts().get(ts, {})
        title = catalog.get("title", "")
        if not title or title.startswith("(referenced"):
            title = _STITCH_TITLES.get(ts, f"TS {ts}")
        role = entry.get("role", "")
        primary_nf = entry.get("primaryNf", "")
        return {
            "tsNumber": ts,
            "title": title,
            "tagline": role,
            "summary": _stitch_summary(ts, anchor, role, primary_nf),
            "stitchAnchor": anchor,
            "stitchRole": role,
            "primaryNf": primary_nf,
            "priority": entry.get("priority", ""),
            "relatedStory": entry.get("relatedStory", []),
        }
    return None
