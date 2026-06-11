#!/usr/bin/env python3
"""Build Parsed-JSON, Bank, and index.json from YAML sources."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.services.build_pipeline import run_full_build  # noqa: E402


def main() -> int:
    try:
        result = run_full_build()
        status = result["status"]
        print(f"Build complete: {status['parsedCount']}/{status['yamlCount']} YAMLs parsed")
        print(f"Index: {result['indexNfCount']} NFs, {result['serviceCount']} services")
        return 0 if status["yamlCount"] == 0 or status["parsedCount"] > 0 else 1
    except RuntimeError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
