"""Extract clause headings from 3GPP spec PDFs (local, gitignored)."""

import json
import re
from pathlib import Path

from backend.config import CONTENT_DIR, YAML_DIR

CLAUSE_HEADING_RE = re.compile(
    r"^(\d+(?:\.\d+)*)\s+([A-Z][^\n]{3,120})$",
    re.MULTILINE,
)


def _pdf_path_for_ts(ts_number: str) -> Path | None:
    """Find a local PDF for TS number in YAML_DIR."""
    compact = ts_number.replace(".", "")
    patterns = [
        f"ts_1{compact}*.pdf",
        f"*{compact}*.pdf",
        f"*{ts_number.replace('.', '')}*.pdf",
    ]
    for pattern in patterns:
        matches = sorted(YAML_DIR.glob(pattern))
        if matches:
            return matches[0]
    return None


def extract_clauses_from_pdf(pdf_path: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as err:
        raise RuntimeError("pypdf is required for PDF extraction: pip install pypdf") from err

    reader = PdfReader(str(pdf_path))
    text_parts: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text_parts.append(extracted)

    full_text = "\n".join(text_parts)
    clauses: list[dict] = []
    seen: set[str] = set()

    for match in CLAUSE_HEADING_RE.finditer(full_text):
        number = match.group(1)
        title = match.group(2).strip()
        if number in seen:
            continue
        if len(number) > 12 or len(title) < 4:
            continue
        seen.add(number)
        clauses.append({"number": number, "title": title})

    version_match = re.search(
        r"3GPP\s+TS\s+(?P<num>\d+\.\d+)\s+version\s+(?P<ver>[\d.]+)\s+Release\s+(?P<rel>\d+)",
        full_text,
        re.I,
    )
    return {
        "sourceFile": pdf_path.name,
        "tsNumber": version_match.group("num") if version_match else "",
        "version": f"V{version_match.group('ver')}" if version_match else "",
        "release": f"Rel-{version_match.group('rel')}" if version_match else "",
        "clauseCount": len(clauses),
        "clauses": clauses,
    }


def clauses_cache_path(ts_number: str) -> Path:
    return CONTENT_DIR / "specs" / f"{ts_number}-clauses.json"


def load_pdf_clauses(ts_number: str, refresh: bool = False) -> dict | None:
    cache = clauses_cache_path(ts_number)
    if cache.exists() and not refresh:
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    pdf_path = _pdf_path_for_ts(ts_number)
    if not pdf_path or not pdf_path.exists():
        return None

    try:
        data = extract_clauses_from_pdf(pdf_path)
    except RuntimeError:
        return None

    data["tsNumber"] = ts_number
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def pdf_metadata(ts_number: str) -> dict | None:
    pdf_path = _pdf_path_for_ts(ts_number)
    if not pdf_path or not pdf_path.exists():
        return None
    clauses = load_pdf_clauses(ts_number, refresh=False)
    return {
        "path": str(pdf_path),
        "filename": pdf_path.name,
        "version": clauses.get("version", "") if clauses else "",
        "release": clauses.get("release", "") if clauses else "",
    }
