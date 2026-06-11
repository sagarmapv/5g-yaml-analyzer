import json
import re

from backend.config import BANK_DIR, YAML_DIR
from backend.services.nf_topology import get_topology
from backend.services.pdf_clauses import load_pdf_clauses, pdf_metadata
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.story_stitch import (
    _STITCH_TITLES,
    build_element_readiness,
    build_nf_gaps,
    build_spec_readiness,
    build_story_gaps,
    enrich_e2e_flow,
    minimal_narrative_for_stitch,
)
from backend.services.ts_catalog import get_ts_catalog
from backend.services.nf_map import build_spec_map

TS_VERSION_RE = re.compile(r"TS\s+(\d+\.\d+)\s+V([\d.]+)", re.I)


def _find_spec_entry(ts_number: str) -> dict | None:
    for spec in build_spec_map().get("specs", []):
        if spec.get("tsNumber") == ts_number:
            return spec
    return None


def _catalog_entry(ts_number: str) -> dict | None:
    for spec in get_ts_catalog().get("specs", []):
        if spec.get("tsNumber") == ts_number:
            return spec
    return None


def _yaml_version(ts_number: str, yamls: list[dict]) -> str:
    for entry in yamls:
        path = YAML_DIR / entry.get("sourceFile", "")
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
        match = TS_VERSION_RE.search(text)
        if match and match.group(1) == ts_number:
            return f"V{match.group(2)}"
    return ""


def _load_operations(source_files: list[str]) -> list[dict]:
    operations: list[dict] = []
    for source in source_files:
        bank_name = source.replace(".yaml", "_Bank.json")
        bank_path = BANK_DIR / bank_name
        if not bank_path.exists():
            continue
        with open(bank_path, "r", encoding="utf-8") as f:
            bank = json.load(f)
        for msg in bank.get("messages", []):
            operations.append(
                {
                    "sourceFile": source,
                    "service": bank.get("service", ""),
                    "nf": bank.get("nf", ""),
                    "path": msg.get("path", ""),
                    "method": msg.get("method", ""),
                    "operationId": msg.get("operationId", ""),
                    "summary": msg.get("summary", ""),
                }
            )
    return operations


def _resolve_spec_title(ts_number: str, spec: dict | None, catalog: dict | None, narrative: dict | None) -> str:
    if narrative and narrative.get("title"):
        return narrative["title"]
    title = ""
    if spec:
        title = spec.get("title", "")
    elif catalog:
        title = catalog.get("title", "")
    if title.startswith("(referenced"):
        title = _STITCH_TITLES.get(ts_number, "")
    return title


def _topology_slice(center_nf: str) -> dict:
    topo = get_topology(min_weight=1, core_only=False)
    nodes = {n["id"] for n in topo.get("nodes", [])}
    if center_nf not in nodes:
        return {"nodes": [], "edges": []}

    neighbor_ids = {center_nf}
    edges: list[dict] = []
    for edge in topo.get("edges", []):
        if edge["from"] == center_nf or edge["to"] == center_nf:
            neighbor_ids.add(edge["from"])
            neighbor_ids.add(edge["to"])
            edges.append(edge)

    nodes_out = [n for n in topo.get("nodes", []) if n["id"] in neighbor_ids]
    return {"nodes": nodes_out, "edges": edges}


def _layer_hints(ts_number: str, narrative: dict) -> dict:
    architecture_ts = ""
    for rel in narrative.get("relatedSpecs", []):
        ts = rel.get("ts", rel) if isinstance(rel, dict) else rel
        if str(ts).startswith("23."):
            architecture_ts = normalize_ts_number(str(ts))
            break
    if not architecture_ts:
        for ep in narrative.get("entryPoints", []):
            ref = ep.get("refSpec", "")
            if ref.startswith("23."):
                architecture_ts = normalize_ts_number(ref)
                break

    operations: list[dict] = []
    for ep in narrative.get("entryPoints", []):
        op_id = ep.get("operationId") or ep.get("name", "")
        if not op_id:
            continue
        operations.append(
            {
                "operationId": op_id,
                "explorerUrl": f"/?q={op_id}",
                "description": ep.get("description", ""),
            }
        )
        if len(operations) >= 3:
            break

    return {
        "architectureTs": architecture_ts,
        "serviceTs": ts_number,
        "operations": operations,
    }


def _preview_steps(narrative: dict, primary_nf: str) -> list[dict]:
    steps = narrative.get("e2eFlow", {}).get("steps", [])
    primary_nf = primary_nf or ""
    filtered = [s for s in steps if primary_nf and primary_nf in (s.get("actors") or [])]
    if not filtered:
        filtered = steps[:4]
    else:
        filtered = filtered[:4]
    return filtered


def build_spec_preview(ts_number: str) -> dict | None:
    ts_number = normalize_ts_number(ts_number)
    narrative = load_narrative(ts_number)
    if not narrative:
        narrative = minimal_narrative_for_stitch(ts_number, "29.512")
    if not narrative:
        return None

    primary_nf = narrative.get("primaryNf", "")
    entry_points = (narrative.get("entryPoints") or [])[:3]
    defines = (narrative.get("defines") or [])[:2]

    return {
        "tsNumber": ts_number,
        "title": narrative.get("title", f"TS {ts_number}"),
        "tagline": narrative.get("tagline", ""),
        "summary": narrative.get("summary", narrative.get("tagline", "")),
        "whyItMatters": narrative.get("whyItMatters", ""),
        "defines": defines,
        "primaryNf": primary_nf,
        "entryPoints": entry_points,
        "e2eFlowSteps": _preview_steps(narrative, primary_nf),
        "layerHints": _layer_hints(ts_number, narrative),
        "storyUrl": f"/specs/{ts_number}",
        "platformUrl": f"/specs?ts={ts_number}",
        "stitchAnchor": narrative.get("stitchAnchor"),
    }


def build_spec_detail(ts_number: str, refresh_pdf: bool = False) -> dict | None:
    ts_number = normalize_ts_number(ts_number)
    spec = _find_spec_entry(ts_number)
    catalog = _catalog_entry(ts_number)
    pdf_info = pdf_metadata(ts_number)
    if not spec and not catalog and not pdf_info:
        return None

    narrative = load_narrative(ts_number)
    stitch_anchor = "29.512"
    if not narrative:
        narrative = minimal_narrative_for_stitch(ts_number, stitch_anchor)
    yamls: list[dict] = []
    if spec:
        for nf_block in spec.get("nfs", []):
            yamls.extend(nf_block.get("yamls", []))

    source_files = sorted({y.get("sourceFile", "") for y in yamls if y.get("sourceFile")})
    operations = _load_operations(source_files)

    referenced_by = []
    if catalog:
        referenced_by = catalog.get("referenceOnlyIn", [])

    resolved_title = _resolve_spec_title(ts_number, spec, catalog, narrative)
    primary_nf = (narrative or {}).get("primaryNf") or (
        spec["nfs"][0]["nf"] if spec and spec.get("nfs") else "PCF"
    )
    topology = _topology_slice(primary_nf)

    pdf_clauses = load_pdf_clauses(ts_number, refresh=refresh_pdf)
    yaml_version = _yaml_version(ts_number, yamls)

    version_banner = None
    if pdf_info and yaml_version and pdf_info.get("version") and pdf_info["version"] != yaml_version:
        version_banner = (
            f"PDF is {pdf_info['version']}; YAML corpus is {yaml_version}. "
            "API list reflects YAML; narrative and clauses reflect PDF."
        )

    spec_out = dict(spec) if spec else {
        "tsNumber": ts_number,
        "title": "",
        "url": (catalog.get("urls") or [""])[0] if catalog else "",
        "versions": catalog.get("versions", []) if catalog else [],
        "nfs": [],
        "yamlCount": 0,
    }
    if resolved_title:
        spec_out["title"] = resolved_title

    return {
        "spec": spec_out,
        "catalog": {
            "referenceCount": catalog.get("referenceCount", 0) if catalog else 0,
            "referenceOnly": catalog.get("referenceOnly", False) if catalog else False,
        },
        "narrative": narrative,
        "pdf": pdf_info,
        "pdfClauses": pdf_clauses,
        "yamls": yamls,
        "operations": operations,
        "referencedBy": referenced_by,
        "topology": topology,
        "versions": {
            "yaml": yaml_version,
            "pdf": pdf_info.get("version", "") if pdf_info else "",
        },
        "versionBanner": version_banner,
        "relatedSpecs": narrative.get("relatedSpecs", []) if narrative else [],
        "storyGaps": build_story_gaps(stitch_anchor) if ts_number == stitch_anchor else None,
        "elementReadiness": (
            build_element_readiness(narrative.get("elements", []), stitch_anchor)
            if ts_number == stitch_anchor and narrative
            else None
        ),
        "nfGaps": (
            build_nf_gaps(narrative.get("elements", []), stitch_anchor)
            if ts_number == stitch_anchor and narrative
            else None
        ),
        "enrichedE2eFlow": (
            enrich_e2e_flow(ts_number, stitch_anchor)
            if narrative and narrative.get("e2eFlow")
            else None
        ),
        "specReadiness": build_spec_readiness(ts_number, narrative) if narrative else None,
        "stitchAnchor": narrative.get("stitchAnchor") if narrative else None,
        "highlightClauses": narrative.get("highlightClauses", []) if narrative else [],
    }
