"""Load and navigate canonical signaling flow graphs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.config import CONTENT_DIR

FLOWS_DIR = CONTENT_DIR / "flows"


@lru_cache(maxsize=32)
def load_flow(flow_id: str) -> dict | None:
    path = FLOWS_DIR / f"{flow_id}.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_layers(flow: dict, layers: list[str] | None = None) -> list[dict]:
    """Return ordered steps for the given layers (default: flow.defaultLayers)."""
    if not flow:
        return []
    layer_set = set(layers or flow.get("defaultLayers") or ["base"])
    steps = [s for s in flow.get("steps", []) if s.get("layer") in layer_set]
    async_steps = [s for s in flow.get("steps", []) if s.get("async") and s.get("layer") in layer_set]

    main_line = [s for s in steps if not s.get("async")]
    main_line.sort(key=lambda s: s.get("order", 0))
    return main_line + [s for s in async_steps if s not in main_line]


def step_by_id(flow: dict, step_id: str) -> dict | None:
    for step in flow.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


def next_step_ids(flow: dict, step_id: str) -> list[str]:
    step = step_by_id(flow, step_id)
    if not step:
        return []
    nxt = list(step.get("next") or [])
    on_success = step.get("onSuccess")
    if on_success and on_success not in nxt:
        nxt.append(on_success)
    return nxt


def list_flows() -> list[dict]:
    if not FLOWS_DIR.exists():
        return []
    items: list[dict] = []
    for path in sorted(FLOWS_DIR.glob("*.json")):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title", ""),
                "procedure": data.get("procedure", ""),
                "anchorSpec": data.get("anchorSpec", ""),
            }
        )
    return items
