"""Unified spec platform index — catalog, map, and content readiness in one payload."""

from backend.config import CONTENT_DIR
from backend.services.nf_map import get_spec_map
from backend.services.pdf_clauses import pdf_metadata
from backend.services.spec_narrative import load_narrative
from backend.services.story_stitch import load_stitch_manifest
from backend.services.ts_catalog import get_ts_catalog


def _narrative_exists(ts: str) -> bool:
    return (CONTENT_DIR / "specs" / f"{ts}.json").exists()


def _stitch_specs(anchor: str = "29.512") -> set[str]:
    manifest = load_stitch_manifest(anchor)
    if not manifest:
        return set()
    return {e["ts"] for e in manifest.get("stitchSpecs", [])}


def build_platform_index(refresh: bool = False) -> dict:
    catalog = get_ts_catalog(refresh=refresh)
    spec_map = get_spec_map(refresh=refresh)
    map_by_ts = {s["tsNumber"]: s for s in spec_map.get("specs", [])}
    stitch_set = _stitch_specs()

    items: list[dict] = []
    for entry in catalog.get("specs", []):
        ts = entry["tsNumber"]
        mapped = map_by_ts.get(ts, {})
        nfs = mapped.get("nfs") or []
        nf_names = [n["nf"] for n in nfs if n.get("nf")]
        pdf = pdf_metadata(ts)
        has_narrative = _narrative_exists(ts)

        items.append(
            {
                "tsNumber": ts,
                "title": entry.get("title", ""),
                "yamlCount": entry.get("yamlCount", 0) or mapped.get("yamlCount", 0),
                "nfCount": mapped.get("nfCount", len(nf_names)),
                "nfServices": nf_names or entry.get("nfServices", []),
                "referenceOnly": bool(entry.get("referenceOnly")) or (
                    not entry.get("yamlFiles") and entry.get("referenceCount", 0) > 0
                ),
                "referenceCount": entry.get("referenceCount", 0),
                "url": (entry.get("urls") or [""])[0],
                "versions": entry.get("versions", []),
                "hasYaml": bool(entry.get("yamlFiles")),
                "hasNarrative": has_narrative,
                "hasPdf": pdf is not None,
                "pdfVersion": pdf.get("version", "") if pdf else "",
                "isStitchSpec": ts in stitch_set,
                "isAnchorStory": ts == "29.512",
                "platformUrl": f"/specs?ts={ts}",
                "storyUrl": f"/specs/{ts}",
                "mapUrl": f"/specs?ts={ts}&view=map",
            }
        )

    items.sort(key=lambda x: (not x["isAnchorStory"], not x["hasYaml"], x["tsNumber"]))

    return {
        "specs": items,
        "meta": {
            **catalog.get("meta", {}),
            **spec_map.get("meta", {}),
            "withStory": sum(1 for i in items if i["hasNarrative"]),
            "withPdf": sum(1 for i in items if i["hasPdf"]),
            "stitchCount": len(stitch_set),
            "anchor": "29.512",
        },
        "map": spec_map,
    }
