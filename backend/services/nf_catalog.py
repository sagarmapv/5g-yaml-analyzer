"""3GPP-aligned NF catalog — load, filter, validate flow participants."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.config import CONTENT_DIR, INDEX_JSON

CATALOG_PATH = CONTENT_DIR / "nf-catalog.json"

_ACCESS_ACTORS = frozenset({"UE", "RAN", "DN"})
_VALID_EXTRA = _ACCESS_ACTORS | frozenset({""})

_TIER_RANK: dict[str, int] = {
    "access": 0,
    "core_control": 1,
    "user_plane": 2,
    "data": 3,
    "charging": 4,
    "exposure": 5,
    "analytics": 6,
    "security_roaming": 7,
    "extended": 8,
}


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {"networkFunctions": [], "procedureRoles": {}, "interfaces": {}}
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _index_by_id(catalog: dict) -> dict[str, dict]:
    return {nf["id"]: nf for nf in catalog.get("networkFunctions", []) if nf.get("id")}


def _bank_coverage() -> dict[str, dict]:
    if not INDEX_JSON.exists():
        return {}
    with open(INDEX_JSON, "r", encoding="utf-8") as f:
        index = json.load(f)
    out: dict[str, dict] = {}
    for nf_id, services in index.items():
        if not isinstance(services, list):
            continue
        out[nf_id] = {
            "inCorpus": True,
            "serviceCount": len(services),
            "sourceFiles": [s.get("sourceFile", "") for s in services if isinstance(s, dict)],
        }
    return out


def list_nfs(
    *,
    tier: str | None = None,
    procedure: str | None = None,
    e2e_default: bool | None = None,
    in_corpus_only: bool = False,
) -> list[dict]:
    catalog = load_catalog()
    by_id = _index_by_id(catalog)
    coverage = _bank_coverage()
    roles = catalog.get("procedureRoles", {})

    procedure_nfs: set[str] | None = None
    if procedure:
        role = roles.get(procedure, {})
        procedure_nfs = set(role.get("required", []) + role.get("common", []) + role.get("optional", []))

    rows: list[dict] = []
    for nf_id, nf in by_id.items():
        if tier and nf.get("tier") != tier:
            continue
        if e2e_default is not None and nf.get("e2eDefault") is not e2e_default:
            continue
        cov = coverage.get(nf_id, {"inCorpus": False, "serviceCount": 0, "sourceFiles": []})
        if in_corpus_only and not cov.get("inCorpus"):
            continue
        if procedure_nfs is not None and nf_id not in procedure_nfs and nf.get("actorKind") != "access":
            continue
        rows.append({**nf, "bankCoverage": cov})

    tier_order = catalog.get("tierOrder", list(_TIER_RANK.keys()))
    rank = {t: i for i, t in enumerate(tier_order)}

    def sort_key(row: dict) -> tuple:
        return (rank.get(row.get("tier", "extended"), 99), row.get("id", ""))

    return sorted(rows, key=sort_key)


def nf_by_id(nf_id: str) -> dict | None:
    catalog = load_catalog()
    nf = _index_by_id(catalog).get((nf_id or "").strip())
    if not nf:
        return None
    cov = _bank_coverage().get(nf_id, {"inCorpus": False, "serviceCount": 0, "sourceFiles": []})
    return {**nf, "bankCoverage": cov}


def validate_flow_participants(steps: list[dict]) -> list[str]:
    """Return list of validation errors (empty if valid)."""
    catalog = load_catalog()
    known = set(_index_by_id(catalog)) | _VALID_EXTRA
    errors: list[str] = []
    for step in steps:
        sid = step.get("id", step.get("stepId", "?"))
        for key in ("from", "to"):
            actor = step.get(key, "")
            if actor and actor not in known:
                errors.append(f"step {sid}: unknown actor '{actor}' in {key}")
    return errors


def actors_for_flow(messages: list[dict], *, include_ran: bool = True) -> list[str]:
    """Ordered lifeline columns: UE (origin), optional RAN, NFs by tier, UE (terminator)."""
    catalog = load_catalog()
    by_id = _index_by_id(catalog)
    first_seen: list[str] = []
    seen: set[str] = set()

    for msg in messages:
        if msg.get("async"):
            continue
        for actor in (msg.get("from"), msg.get("to")):
            if not actor or actor in ("UE",) or actor in seen:
                continue
            seen.add(actor)
            first_seen.append(actor)

    def tier_rank(actor: str) -> int:
        tier = (by_id.get(actor) or {}).get("tier", "extended")
        return _TIER_RANK.get(tier, 99)

    middle = sorted(first_seen, key=lambda a: (tier_rank(a), first_seen.index(a)))
    middle = [a for a in middle if a not in ("UE", "RAN")]

    actors: list[str] = ["UE"]
    if include_ran:
        actors.append("RAN")
    actors.extend(middle)
    actors.append("UE")
    return actors


def catalog_summary() -> dict:
    catalog = load_catalog()
    nfs = list_nfs()
    return {
        "catalogVersion": catalog.get("catalogVersion", ""),
        "references": catalog.get("references", []),
        "architecture": catalog.get("architecture", {}),
        "procedureRoles": catalog.get("procedureRoles", {}),
        "interfaces": catalog.get("interfaces", {}),
        "networkFunctions": nfs,
        "count": len(nfs),
    }
