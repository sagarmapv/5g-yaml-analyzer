"""Master story hub — compose anchor narrative, stitch manifest, and NF lenses."""

import json
from pathlib import Path

from backend.config import CONTENT_DIR
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.ladder import build_ladder_payload
from backend.services.story_stitch import (
    build_element_readiness,
    build_nf_gaps,
    build_spec_readiness,
    build_story_gaps,
    enrich_e2e_flow,
    load_stitch_manifest,
)

STORIES_DIR = CONTENT_DIR / "stories"


def _load_registry(story_id: str) -> dict | None:
    path = STORIES_DIR / f"{story_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_stories() -> dict:
    items: list[dict] = []
    if not STORIES_DIR.exists():
        return {"stories": items}
    for path in sorted(STORIES_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        sid = data.get("id", path.stem)
        items.append(
            {
                "id": sid,
                "title": data.get("title", ""),
                "tagline": data.get("tagline", ""),
                "anchorSpec": data.get("anchorSpec", ""),
                "url": f"/stories?id={sid}",
            }
        )
    return {"stories": items}


_NON_NF_ACTORS = frozenset({"UE", "RAN", ""})


def _flow_nf_order(flow: dict | None) -> list[str]:
    """NF actors in first-seen order across establishment flow steps."""
    order: list[str] = []
    if not flow:
        return order
    for step in flow.get("steps", []):
        for actor in step.get("actors", []):
            if actor in _NON_NF_ACTORS or actor in order:
                continue
            order.append(actor)
    return order


def _annotate_nf_lens(nf_lens: list[dict], flow: dict | None) -> tuple[list[dict], list[dict]]:
    order = _flow_nf_order(flow)
    rank = {nf: i for i, nf in enumerate(order)}
    in_flow: list[dict] = []
    ecosystem: list[dict] = []
    for item in nf_lens:
        nf = item.get("nf", "")
        annotated = {
            **item,
            "inFlow": nf in rank,
            "flowOrder": rank.get(nf, -1),
        }
        if annotated["inFlow"]:
            in_flow.append(annotated)
        else:
            ecosystem.append(annotated)
    in_flow.sort(key=lambda x: x["flowOrder"])
    ecosystem.sort(key=lambda x: x.get("nf", ""))
    return in_flow, ecosystem


def _supporting_specs(anchor: str) -> list[dict]:
    manifest = load_stitch_manifest(anchor)
    items: list[dict] = []
    if not manifest:
        return items
    for entry in manifest.get("stitchSpecs", []):
        ts = normalize_ts_number(entry["ts"])
        ts_narrative = load_narrative(ts)
        title = ts_narrative.get("title", "") if ts_narrative else f"TS {ts}"
        items.append(
            {
                "ts": ts,
                "title": title,
                "role": entry.get("role", ""),
                "priority": entry.get("priority", ""),
                "storyUrl": f"/specs/{ts}",
                "platformUrl": f"/specs?ts={ts}",
            }
        )
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "": 9}
    items.sort(key=lambda s: (priority_order.get(s.get("priority", ""), 9), s["ts"]))
    return items


def build_master_story(story_id: str, view: str = "full") -> dict | None:
    registry = _load_registry(story_id)
    if not registry:
        return None

    anchor = normalize_ts_number(registry.get("anchorSpec", "29.512"))
    narrative = load_narrative(anchor)
    if not narrative:
        return None

    hub_mode = view == "hub"
    elements = narrative.get("elements", [])
    element_readiness = build_element_readiness(elements, anchor)
    nf_gaps = build_nf_gaps(elements, anchor)
    by_nf = {i["nf"]: i for i in element_readiness.get("items", [])}

    nf_lens: list[dict] = []
    for el in narrative.get("elements", []):
        nf = el.get("nf", "")
        primary = normalize_ts_number(el.get("primarySpec") or anchor)
        ready_item = by_nf.get(nf, {})
        lens_item = {
            "nf": nf,
            "primarySpec": primary,
            "role": el.get("role", ""),
            "inSpec": el.get("inSpec", False),
            "storyUrl": ready_item.get("storyUrl", f"/specs/{primary}"),
            "platformUrl": ready_item.get("platformUrl", f"/specs?ts={primary}"),
        }
        if not hub_mode:
            lens_item.update(
                {
                    "hasSpec": ready_item.get("hasSpec", False),
                    "hasYaml": ready_item.get("hasYaml", False),
                    "hasStory": ready_item.get("hasStory", False),
                    "hasFullNarrative": ready_item.get("hasFullNarrative", False),
                    "storyKind": ready_item.get("storyKind", "gap"),
                    "ready": ready_item.get("ready", False),
                    "state": ready_item.get("state", "gap"),
                }
            )
        nf_lens.append(lens_item)

    if hub_mode:
        enriched_flow = enrich_e2e_flow(anchor, anchor)
        nf_in_flow, nf_ecosystem = _annotate_nf_lens(nf_lens, enriched_flow)
        return {
            "id": registry.get("id", story_id),
            "title": registry.get("title", ""),
            "tagline": registry.get("tagline", ""),
            "summary": registry.get("summary", ""),
            "whyItMatters": registry.get("whyItMatters", ""),
            "anchorSpec": anchor,
            "anchorStoryUrl": f"/specs/{anchor}",
            "anchorPlatformUrl": f"/specs?ts={anchor}&view=story",
            "enrichedE2eFlow": enriched_flow,
            "nfLens": nf_lens,
            "nfInFlow": nf_in_flow,
            "nfEcosystem": nf_ecosystem,
            "flowNfOrder": _flow_nf_order(enriched_flow),
            "ladderUrl": f"/ladder?id={registry.get('id', story_id)}",
            "supportingSpecs": _supporting_specs(anchor),
            "view": "hub",
        }

    gaps = build_story_gaps(anchor)
    spec_stories: list[dict] = []
    for item in gaps.get("items", []):
        ts = item["tsNumber"]
        ts_narrative = load_narrative(ts)
        title = ""
        if ts_narrative:
            title = ts_narrative.get("title", "")
        if not title:
            title = item.get("title", f"TS {ts}")
        spec_stories.append(
            {
                "ts": ts,
                "title": title,
                "storyUrl": item.get("storyUrl", f"/specs/{ts}"),
                "platformUrl": f"/specs?ts={ts}",
                "hasNarrative": bool(item.get("hasNarrative")),
                "hasPdf": bool(item.get("hasPdf")),
                "hasYaml": bool(item.get("hasYaml")),
                "priority": item.get("priority", ""),
                "role": item.get("role", ""),
                "specReadiness": build_spec_readiness(ts, ts_narrative),
            }
        )

    priority_order = {"P0": 0, "P1": 1, "P2": 2, "": 9}
    spec_stories.sort(key=lambda s: (priority_order.get(s.get("priority", ""), 9), s["ts"]))

    narrative_count = sum(1 for s in spec_stories if s["hasNarrative"])
    pdf_count = sum(1 for s in spec_stories if s["hasPdf"])

    return {
        "id": registry.get("id", story_id),
        "title": registry.get("title", ""),
        "tagline": registry.get("tagline", ""),
        "summary": registry.get("summary", ""),
        "whyItMatters": registry.get("whyItMatters", ""),
        "anchorSpec": anchor,
        "anchorStoryUrl": f"/specs/{anchor}",
        "anchorPlatformUrl": f"/specs?ts={anchor}&view=story",
        "enrichedE2eFlow": enrich_e2e_flow(anchor, anchor),
        "elementReadiness": element_readiness,
        "nfGaps": nf_gaps,
        "nfLens": nf_lens,
        "storyGaps": gaps,
        "specStories": spec_stories,
        "meta": {
            "stitchTotal": gaps.get("meta", {}).get("total", 0),
            "stitchReady": gaps.get("meta", {}).get("ready", 0),
            "withNarrative": narrative_count,
            "withPdf": pdf_count,
            "nfTotal": len(nf_lens),
            "nfReady": element_readiness.get("meta", {}).get("ready", 0),
            "nfNeedsPdf": nf_gaps.get("meta", {}).get("needsPdf", 0),
            "nfFullNarrative": nf_gaps.get("meta", {}).get("fullNarrative", 0),
            "nfNeedsFullNarrative": nf_gaps.get("meta", {}).get("needsFullNarrative", 0),
        },
    }


def build_story_ladder(story_id: str) -> dict | None:
    registry = _load_registry(story_id)
    if not registry:
        return None
    anchor = normalize_ts_number(registry.get("anchorSpec", "29.512"))
    if not load_narrative(anchor):
        return None
    return build_ladder_payload(
        registry.get("id", story_id),
        anchor,
        registry.get("title", ""),
        flow_id=registry.get("flowId"),
    )
