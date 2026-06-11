#!/usr/bin/env python3
"""Audit 3GPP spec corpus: PDF, clauses, narratives, YAML, and Bank coverage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import BANK_DIR
from backend.services.pdf_clauses import clauses_cache_path, pdf_metadata
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.story_stitch import load_stitch_manifest
from backend.services.ts_catalog import get_ts_catalog

JOURNEY_EXTRA_TS = {"29.519"}  # Referenced in 29.512 interactions (PCF policy data)
ANCHOR = "29.512"


def _series(ts: str) -> str:
    major = ts.split(".")[0]
    if major == "23":
        return "architecture"
    if major == "29":
        return "service"
    if major == "32":
        return "charging"
    return "other"


def _bank_path_for_yaml(yaml_file: str) -> Path:
    return BANK_DIR / yaml_file.replace(".yaml", "_Bank.json")


def journey_ts_set(anchor: str = ANCHOR) -> set[str]:
    out: set[str] = {normalize_ts_number(anchor), *JOURNEY_EXTRA_TS}
    manifest = load_stitch_manifest(anchor)
    if manifest:
        for entry in manifest.get("stitchSpecs", []):
            out.add(normalize_ts_number(entry["ts"]))
        for row in manifest.get("stepStitch", []):
            out.add(normalize_ts_number(row["spec"]))
    narrative = load_narrative(anchor)
    if narrative:
        for el in narrative.get("elements", []):
            if el.get("primarySpec"):
                out.add(normalize_ts_number(el["primarySpec"]))
        for ix in narrative.get("interactions", []):
            if ix.get("refSpec"):
                out.add(normalize_ts_number(ix["refSpec"]))
    return out


def _gap_parts(item: dict) -> list[str]:
    """Journey TS: PDF + clauses + narrative. Other YAML specs: bank only. Reference-only: none."""
    gaps: list[str] = []
    if item.get("referenceOnly"):
        return gaps

    yaml_count = item.get("yamlCount", 0)
    in_journey = item.get("inJourney", False)

    if in_journey:
        if not item.get("hasPdf"):
            gaps.append("pdf")
        if not item.get("hasClauses"):
            gaps.append("clauses")
        if not item.get("hasNarrative"):
            gaps.append("narrative")
    elif yaml_count == 0:
        return gaps

    if item.get("series") != "architecture" and yaml_count > 0:
        if item.get("bankCount", 0) < yaml_count:
            gaps.append("bank")
    return gaps


def audit_entry(ts: str, catalog_entry: dict | None, in_journey: bool) -> dict:
    ts = normalize_ts_number(ts)
    series = _series(ts)
    yaml_files = list(catalog_entry.get("yamlFiles", [])) if catalog_entry else []
    reference_only = bool(catalog_entry.get("referenceOnly")) if catalog_entry else False
    bank_files = [_bank_path_for_yaml(yf) for yf in yaml_files]
    bank_present = [p for p in bank_files if p.exists()]

    has_pdf = pdf_metadata(ts) is not None
    has_clauses = clauses_cache_path(ts).exists()
    has_narrative = load_narrative(ts) is not None

    item = {
        "tsNumber": ts,
        "series": series,
        "inJourney": in_journey,
        "title": (catalog_entry or {}).get("title", ""),
        "hasPdf": has_pdf,
        "hasClauses": has_clauses,
        "hasNarrative": has_narrative,
        "yamlCount": len(yaml_files),
        "bankCount": len(bank_present),
        "referenceOnly": reference_only,
        "referenceCount": (catalog_entry or {}).get("referenceCount", 0),
    }
    item["gaps"] = _gap_parts(item)
    item["gapSummary"] = ", ".join(item["gaps"]) if item["gaps"] else ""
    return item


def build_audit(anchor: str = ANCHOR) -> dict:
    catalog = get_ts_catalog()
    catalog_by_ts = {s["tsNumber"]: s for s in catalog.get("specs", [])}
    journey = journey_ts_set(anchor)

    items: list[dict] = []
    seen: set[str] = set()

    for entry in catalog.get("specs", []):
        ts = entry["tsNumber"]
        seen.add(ts)
        items.append(audit_entry(ts, entry, ts in journey))

    for ts in sorted(journey):
        if ts not in seen:
            items.append(audit_entry(ts, catalog_by_ts.get(ts), True))

    items.sort(key=lambda x: (not x["inJourney"], x["series"], x["tsNumber"]))

    journey_items = [i for i in items if i["inJourney"]]
    gap_items = [i for i in items if i["gaps"]]
    journey_gaps = [i for i in journey_items if i["gaps"]]

    return {
        "anchor": anchor,
        "journeyTs": sorted(journey),
        "items": items,
        "meta": {
            "total": len(items),
            "inJourney": len(journey_items),
            "withPdf": sum(1 for i in items if i["hasPdf"]),
            "withClauses": sum(1 for i in items if i["hasClauses"]),
            "withNarrative": sum(1 for i in items if i["hasNarrative"]),
            "withYaml": sum(1 for i in items if i["yamlCount"] > 0),
            "referenceOnly": sum(1 for i in items if i["referenceOnly"]),
            "withGaps": len(gap_items),
            "journeyGaps": len(journey_gaps),
        },
        "journeyGaps": journey_gaps,
    }


def print_table(report: dict, *, show_all: bool = False) -> None:
    meta = report["meta"]
    print(f"Corpus audit — anchor TS {report['anchor']}")
    print(
        f"  {meta['total']} TS entries | {meta['inJourney']} in journey | "
        f"{meta['journeyGaps']} journey gaps | {meta['withGaps']} total with gaps"
    )
    print()
    header = f"{'TS':<10} {'Journey':<8} {'PDF':<4} {'Cl':<4} {'Story':<6} {'YAML':<5} {'Bank':<5} {'Gaps'}"
    print(header)
    print("-" * len(header))
    for item in report["items"]:
        if not show_all and not item["gaps"] and not item["inJourney"]:
            continue
        j = "yes" if item["inJourney"] else ""
        print(
            f"{item['tsNumber']:<10} {j:<8} "
            f"{'Y' if item['hasPdf'] else '-':<4} "
            f"{'Y' if item['hasClauses'] else '-':<4} "
            f"{'Y' if item['hasNarrative'] else '-':<6} "
            f"{item['yamlCount']:<5} {item['bankCount']:<5} "
            f"{item['gapSummary'] or 'ok'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit 3GPP spec corpus coverage")
    parser.add_argument("--json", type=Path, help="Write full report JSON to path")
    parser.add_argument("--anchor", default=ANCHOR, help="Stitch anchor TS (default 29.512)")
    parser.add_argument("--journey-only", action="store_true", help="Print only in-journey TS")
    parser.add_argument("--gaps-only", action="store_true", help="Print only TS with gaps")
    parser.add_argument("--all", action="store_true", help="Print every TS in catalog")
    args = parser.parse_args()

    report = build_audit(args.anchor)

    display_items = report["items"]
    if args.journey_only:
        display_items = [i for i in display_items if i["inJourney"]]
    if args.gaps_only:
        display_items = [i for i in display_items if i["gaps"]]

    print_report = {**report, "items": display_items}
    print_table(print_report, show_all=args.all or args.journey_only or args.gaps_only)

    if report["journeyGaps"]:
        print("\nJourney gaps (review before ladder work):")
        for item in report["journeyGaps"]:
            print(f"  TS {item['tsNumber']}: {item['gapSummary']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote {args.json}")

    return 1 if report["meta"]["journeyGaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
