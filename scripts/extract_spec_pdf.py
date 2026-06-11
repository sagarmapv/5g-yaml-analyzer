#!/usr/bin/env python3
"""Extract clause headings from a local 3GPP spec PDF into content/specs/."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.pdf_clauses import extract_clauses_from_pdf, clauses_cache_path, _pdf_path_for_ts


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PDF clause index for a 3GPP TS")
    parser.add_argument("ts_number", help="e.g. 29.512")
    parser.add_argument("--pdf", type=Path, help="Override PDF path")
    args = parser.parse_args()

    pdf_path = args.pdf or _pdf_path_for_ts(args.ts_number)
    if not pdf_path or not pdf_path.exists():
        print(f"No PDF found for TS {args.ts_number}", file=sys.stderr)
        return 1

    data = extract_clauses_from_pdf(pdf_path)
    data["tsNumber"] = args.ts_number
    out = clauses_cache_path(args.ts_number)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Wrote {data['clauseCount']} clauses to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
