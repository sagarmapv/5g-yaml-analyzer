#!/usr/bin/env python3
"""Download 3GPP spec PDFs from ETSI deliver and install into Yaml-Files/5GC_APIs."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import YAML_DIR
from backend.services.pdf_clauses import _pdf_path_for_ts
from backend.services.spec_narrative import load_narrative
from backend.services.story_stitch import build_nf_gaps

# Match YAML corpus / externalDocs versions (Rel-18).
DEFAULT_VERSIONS: dict[str, str] = {
    "29.502": "18.6.0",
    "29.518": "18.5.0",
    "29.510": "18.6.0",
    "29.514": "18.5.0",
    "29.503": "18.5.0",
    "29.504": "18.5.0",
    "29.564": "18.4.0",
    "29.521": "18.4.0",
    "32.291": "18.5.0",
    "29.522": "18.5.0",
    "29.519": "18.5.0",
}

TS_VERSION_RE = re.compile(r"TS\s+(\d+\.\d+)\s+V([\d.]+)", re.I)
USER_AGENT = "5g-visualizer/1.0 (+https://www.etsi.org/deliver/)"


def version_from_yaml_corpus(ts_number: str) -> str | None:
    """Read Rel-18 version from OpenAPI description lines in the YAML corpus."""
    ts_number = normalize_ts(ts_number)
    compact = ts_number.replace(".", "")
    found: list[str] = []
    for path in YAML_DIR.glob(f"TS{compact}*.yaml"):
        text = path.read_text(encoding="utf-8", errors="ignore")[:4000]
        for match in TS_VERSION_RE.finditer(text):
            if match.group(1) == ts_number:
                found.append(match.group(2))
    return max(found) if found else None


def normalize_ts(ts: str) -> str:
    ts = ts.strip().replace("TS", "").strip()
    if re.fullmatch(r"\d{5}", ts):
        return f"{ts[:2]}.{ts[2:]}"
    return ts


def version_to_etsi_parts(version: str) -> tuple[str, str]:
    """V18.6.0 -> (folder 18.06.00_60, code 180600 for ts_129502v180600p.pdf)."""
    version = version.lstrip("Vv")
    major, minor, patch = (version.split(".") + ["0", "0"])[:3]
    folder = f"{major}.{minor.zfill(2)}.{patch.zfill(2)}_60"
    code = f"{major}{minor.zfill(2)}{patch.zfill(2)}"
    return folder, code


def etsi_pdf_url(ts_number: str, version: str) -> tuple[str, str]:
    ts_number = normalize_ts(ts_number)
    compact = "1" + ts_number.replace(".", "")
    low = (int(compact) // 100) * 100
    high = low + 99
    ver_folder, v_suffix = version_to_etsi_parts(version)
    filename = f"ts_{compact}v{v_suffix}p.pdf"
    url = f"https://www.etsi.org/deliver/etsi_ts/{low}_{high}/{compact}/{ver_folder}/{filename}"
    return url, filename


def download_file(url: str, dest: Path, dry_run: bool = False) -> bool:
    if dest.exists():
        print(f"  skip (exists): {dest.name}")
        return True
    if dry_run:
        print(f"  would download: {url}")
        print(f"  -> {dest}")
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=180) as resp:
            data = resp.read()
    except (HTTPError, URLError) as err:
        print(f"  FAILED: {url} ({err})", file=sys.stderr)
        return False
    dest.write_bytes(data)
    print(f"  saved {dest.name} ({len(data) // 1024} KB)")
    return True


def run_extract(ts_number: str) -> int:
    script = Path(__file__).resolve().parent / "extract_spec_pdf.py"
    proc = subprocess.run([sys.executable, str(script), ts_number], check=False)
    return proc.returncode


def missing_nf_specs() -> list[dict]:
    narrative = load_narrative("29.512")
    if not narrative:
        return []
    gaps = build_nf_gaps(narrative.get("elements", []), "29.512")
    return [i for i in gaps["items"] if i.get("needsPdf")]


def install_spec(ts_number: str, version: str | None, extract: bool, dry_run: bool) -> bool:
    ts_number = normalize_ts(ts_number)
    if _pdf_path_for_ts(ts_number) and not dry_run:
        existing = _pdf_path_for_ts(ts_number)
        print(f"TS {ts_number}: already have {existing.name}")
        if extract:
            run_extract(ts_number)
        return True

    ver = version or DEFAULT_VERSIONS.get(ts_number) or version_from_yaml_corpus(ts_number)
    if not ver:
        print(f"TS {ts_number}: no version — pass --version 18.x.y", file=sys.stderr)
        return False

    url, filename = etsi_pdf_url(ts_number, ver)
    dest = YAML_DIR / filename
    print(f"TS {ts_number} (V{ver.lstrip('Vv')})")
    print(f"  {url}")
    if not download_file(url, dest, dry_run=dry_run):
        return False
    if extract and not dry_run:
        return run_extract(ts_number) == 0
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download 3GPP TS PDFs from ETSI into Yaml-Files/5GC_APIs")
    parser.add_argument("ts_numbers", nargs="*", help="TS numbers to download (e.g. 29.502 29.518)")
    parser.add_argument("--nf-gaps", action="store_true", help="Download all NF primary specs missing PDF (29.512 story)")
    parser.add_argument("--list-missing", action="store_true", help="List NF specs missing PDF")
    parser.add_argument("--version", help="Override version for single TS (e.g. 18.6.0)")
    parser.add_argument("--extract", action="store_true", help="Run extract_spec_pdf.py after each download")
    parser.add_argument("--dry-run", action="store_true", help="Print URLs only")
    args = parser.parse_args()

    if args.list_missing:
        for item in missing_nf_specs():
            ver = DEFAULT_VERSIONS.get(item["primarySpec"], "?")
            url, _ = etsi_pdf_url(item["primarySpec"], ver) if ver != "?" else ("", "")
            print(f"{item['nf']:6} TS {item['primarySpec']:8} V{ver}")
            if url:
                print(f"         {url}")
        return 0

    targets: list[str] = []
    if args.nf_gaps:
        targets.extend(item["primarySpec"] for item in missing_nf_specs())
    targets.extend(normalize_ts(ts) for ts in args.ts_numbers)
    # dedupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for ts in targets:
        if ts not in seen:
            seen.add(ts)
            unique.append(ts)

    if not unique:
        parser.print_help()
        print("\nExamples:")
        print("  python scripts/download_spec_pdfs.py --list-missing")
        print("  python scripts/download_spec_pdfs.py 29.502 --extract")
        print("  python scripts/download_spec_pdfs.py --nf-gaps --extract")
        return 1

    ok = True
    for ts in unique:
        ver = args.version if len(unique) == 1 and args.version else None
        if not install_spec(ts, ver, extract=args.extract, dry_run=args.dry_run):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
