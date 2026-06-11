"""Narrative JSON loading and TS number normalization."""

import json
import re
from pathlib import Path

from backend.config import CONTENT_DIR


def normalize_ts_number(ts: str) -> str:
    ts = ts.strip().replace("TS", "").replace("ts", "").strip()
    if re.fullmatch(r"\d{5}", ts):
        return f"{ts[:2]}.{ts[2:]}"
    return ts


def _narrative_path(ts_number: str) -> Path:
    return CONTENT_DIR / "specs" / f"{ts_number}.json"


def load_narrative(ts_number: str) -> dict | None:
    path = _narrative_path(ts_number)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
