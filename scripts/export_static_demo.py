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

DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = DOCS_DIR / "demo" / "data"
OPERATIONS_DIR = DATA_DIR / "operations"

JOURNEY_OPERATIONS = [
    "PostSmContexts",
    "GetSmData",
    "SearchNFInstances",
    "CreateSMPolicy",
    "UpdateSmContext",
    "SmPolicyUpdateNotification",
]


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def export_demo() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OPERATIONS_DIR.mkdir(parents=True, exist_ok=True)

    ladder = build_story_ladder("pdu-session-sm-policy")
    if ladder:
        _write_json(DATA_DIR / "ladder-pdu-session-sm-policy.json", ladder)

    hub = build_master_story("pdu-session-sm-policy", view="hub")
    if hub:
        _write_json(DATA_DIR / "stories-pdu-session-sm-policy-hub.json", hub)

    for op_id in JOURNEY_OPERATIONS:
        from backend.services.operation_detail import build_operation_detail
        from backend.services.message_envelope import attach_envelope_to_detail

        detail = build_operation_detail(op_id, view="request")
        if detail:
            detail = attach_envelope_to_detail(detail)
            _write_json(OPERATIONS_DIR / f"{op_id}.json", detail)
        else:
            env = build_message_envelope(op_id)
            if env:
                _write_json(OPERATIONS_DIR / f"{op_id}.json", {"operationId": op_id, "envelope": env})

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

    for html in ("ladder.html", "master-story.html"):
        src = frontend / html
        if src.exists():
            shutil.copy2(src, DOCS_DIR / html)

    print(f"Static demo exported to {DOCS_DIR}")


if __name__ == "__main__":
    export_demo()
