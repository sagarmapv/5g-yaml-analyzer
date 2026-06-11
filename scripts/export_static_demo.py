#!/usr/bin/env python3
"""Export baked JSON for GitHub Pages static demo."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.master_story import build_master_story, build_story_ladder
from backend.services.message_envelope import build_message_envelope
from backend.services.nf_topology import build_topology

_SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from patch_docs_html import patch_docs_html_files

DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = DOCS_DIR / "demo" / "data"
OPERATIONS_DIR = DATA_DIR / "operations"
SPECS_DIR = DATA_DIR / "specs"

JOURNEY_OPERATIONS = [
    "PostSmContexts",
    "GetSmData",
    "SearchNFInstances",
    "CreateSMPolicy",
    "UpdateSmContext",
    "SmPolicyUpdateNotification",
]

JOURNEY_STORY_ID = "pdu-session-sm-policy"


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def _ts_numbers_from_hub(hub: dict) -> set[str]:
    out: set[str] = set()
    anchor = hub.get("anchorSpec")
    if anchor:
        out.add(str(anchor))
    e2e = hub.get("enrichedE2eFlow") or {}
    for ref in e2e.get("refSpecs", []):
        ts = ref.get("ts")
        if ts:
            out.add(str(ts))
    for step in e2e.get("steps", []):
        for stitch in step.get("stitchRefs", []):
            ts = stitch.get("ts")
            if ts:
                out.add(str(ts))
    return out


def export_demo() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    SPECS_DIR.mkdir(parents=True, exist_ok=True)

    ladder = build_story_ladder(JOURNEY_STORY_ID)
    if ladder:
        _write_json(DATA_DIR / f"ladder-{JOURNEY_STORY_ID}.json", ladder)

    hub = build_master_story(JOURNEY_STORY_ID, view="hub")
    if hub:
        _write_json(DATA_DIR / f"stories-{JOURNEY_STORY_ID}-hub.json", hub)

    from backend.services.operation_detail import build_operation_detail
    from backend.services.message_envelope import attach_envelope_to_detail

    manifest_ops: list[dict] = []
    for op_id in JOURNEY_OPERATIONS:
        detail = build_operation_detail(op_id, view="request")
        if detail:
            detail = attach_envelope_to_detail(detail)
            _write_json(OPERATIONS_DIR / f"{op_id}.json", detail)
            manifest_ops.append(
                {
                    "id": op_id,
                    "method": detail.get("method", ""),
                    "path": detail.get("path", ""),
                    "summary": detail.get("summary", ""),
                }
            )
        else:
            env = build_message_envelope(op_id)
            if env:
                _write_json(OPERATIONS_DIR / f"{op_id}.json", {"operationId": op_id, "envelope": env})
                manifest_ops.append({"id": op_id, "summary": op_id})

    _write_json(
        DATA_DIR / "messages-manifest.json",
        {
            "journey": JOURNEY_STORY_ID,
            "anchorSpec": hub.get("anchorSpec") if hub else "29.512",
            "operations": manifest_ops,
        },
    )

    from backend.services.spec_story import build_spec_preview

    if hub:
        for ts in sorted(_ts_numbers_from_hub(hub)):
            preview = build_spec_preview(ts)
            if preview:
                _write_json(SPECS_DIR / f"{ts}-preview.json", preview)

    from backend.services.nf_catalog import catalog_summary

    _write_json(DATA_DIR / "nf-catalog-summary.json", catalog_summary())

    try:
        topo = build_topology(core_only=True)
        _write_json(DATA_DIR / "topology-core.json", topo)
    except Exception as exc:
        print(f"topology export skipped: {exc}")

    frontend = PROJECT_ROOT / "frontend"
    static_dest = DOCS_DIR / "static"
    if static_dest.exists():
        shutil.rmtree(static_dest)
    shutil.copytree(
        frontend,
        static_dest,
        ignore=shutil.ignore_patterns("*.html"),
    )

    demo_loader = PROJECT_ROOT / "frontend" / "demo-loader.js"
    if demo_loader.exists():
        shutil.copy2(demo_loader, DOCS_DIR / "static" / "demo-loader.js")

    for html in ("ladder.html", "master-story.html", "topology.html"):
        src = frontend / html
        if src.exists():
            shutil.copy2(src, DOCS_DIR / html)

    patched = patch_docs_html_files()
    print(f"Patched {patched} app HTML file(s) for Pages")

    print(f"Static demo exported to {DOCS_DIR}")


if __name__ == "__main__":
    export_demo()
