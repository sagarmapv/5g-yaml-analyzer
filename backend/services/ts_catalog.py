import json
import re
from collections import defaultdict
from pathlib import Path

from backend.config import PROJECT_ROOT, YAML_DIR
from backend.services.nf_classifier import classify_nf

TS_CATALOG_CACHE = PROJECT_ROOT / ".ts-catalog.json"

# 3GPP TS 29.518 V18.5.0; title...  or  TS 29.598 UDSF Services, V18.4.0.
TS_DESC_RE = re.compile(
    r"3GPP\s+TS\s+(?P<num>\d+\.\d+)\s*,?\s*(?:(?P<ver>V[\d.]+)[;:\s]+)?(?P<title>[^\n]+)",
    re.IGNORECASE,
)
TS_URL_RE = re.compile(
    r"archive/(?P<series>\d+)_series/(?P<num>\d+\.\d+)",
    re.IGNORECASE,
)
FILENAME_TS_RE = re.compile(r"^TS(\d{2})(\d{3})_", re.IGNORECASE)


def _ts_from_filename(filename: str) -> str | None:
    match = FILENAME_TS_RE.match(filename)
    if not match:
        return None
    return f"{match.group(1)}.{match.group(2)}"


def _extract_external_docs_block(text: str) -> str | None:
    match = re.search(r"^externalDocs:\s*\n(.*?)(?=^[a-zA-Z])", text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else None


def _parse_external_docs(block: str) -> dict | None:
    result: dict = {"versions": set(), "titles": set(), "urls": set()}

    for desc_match in TS_DESC_RE.finditer(block):
        result["tsNumber"] = desc_match.group("num")
        if desc_match.group("ver"):
            result["versions"].add(desc_match.group("ver"))
        title = (desc_match.group("title") or "").strip().rstrip(".")
        if title:
            result["titles"].add(title)

    for url_match in TS_URL_RE.finditer(block):
        result["urls"].add(url_match.group(0))
        if "tsNumber" not in result:
            result["tsNumber"] = url_match.group("num")

    if "tsNumber" not in result:
        return None

    return result


def _all_ts_mentions(text: str) -> list[str]:
    """Every TS number mentioned anywhere in the file (e.g. 29.501 in apiRoot clauses)."""
    return list({m.group("num") for m in TS_DESC_RE.finditer(text)})


def resolve_primary_spec(filename: str, text: str | None = None) -> dict:
    """Primary 3GPP TS for a YAML file (externalDocs, else filename)."""
    if text is None:
        path = YAML_DIR / filename
        if not path.exists():
            ts_num = _ts_from_filename(filename)
            return {
                "tsNumber": ts_num or "unknown",
                "title": "",
                "versions": [],
                "url": f"https://www.3gpp.org/ftp/Specs/archive/29_series/{ts_num}/" if ts_num else "",
            }
        text = path.read_text(encoding="utf-8", errors="ignore")

    block = _extract_external_docs_block(text)
    parsed = _parse_external_docs(block) if block else None
    if parsed:
        ts_num = parsed["tsNumber"]
        title = next(iter(parsed.get("titles", [])), "")
        versions = sorted(parsed.get("versions", set()))
        urls = parsed.get("urls", set())
        url = f"https://www.3gpp.org/ftp/Specs/{next(iter(urls))}/" if urls else ""
        return {"tsNumber": ts_num, "title": title, "versions": versions, "url": url}

    ts_num = _ts_from_filename(filename)
    return {
        "tsNumber": ts_num or "unknown",
        "title": "",
        "versions": [],
        "url": f"https://www.3gpp.org/ftp/Specs/archive/29_series/{ts_num}/" if ts_num else "",
        "inferredFromFilename": True,
    }


def build_ts_catalog(yaml_dir: Path | None = None) -> dict:
    yaml_root = yaml_dir or YAML_DIR
    if not yaml_root.exists():
        return {"specs": [], "meta": {"totalSpecs": 0, "totalYamlFiles": 0}}

    # Primary specs (externalDocs) keyed by TS number
    specs: dict[str, dict] = {}
    file_primary: dict[str, str] = {}

    for yaml_path in sorted(yaml_root.glob("*.yaml")):
        text = yaml_path.read_text(encoding="utf-8", errors="ignore")
        filename = yaml_path.name
        nf = classify_nf(filename, {})

        block = _extract_external_docs_block(text)
        parsed = _parse_external_docs(block) if block else None

        if parsed:
            ts_num = parsed["tsNumber"]
            file_primary[filename] = ts_num
            if ts_num not in specs:
                specs[ts_num] = {
                    "tsNumber": ts_num,
                    "title": "",
                    "versions": [],
                    "urls": [],
                    "yamlFiles": [],
                    "nfServices": [],
                    "referenceOnlyIn": [],
                }
            entry = specs[ts_num]
            entry["yamlFiles"].append(filename)
            if nf and nf not in entry["nfServices"]:
                entry["nfServices"].append(nf)
            for ver in parsed.get("versions", set()):
                if ver not in entry["versions"]:
                    entry["versions"].append(ver)
            for title in parsed.get("titles", set()):
                if not entry["title"] or len(title) > len(entry["title"]):
                    entry["title"] = title
            for url in parsed.get("urls", set()):
                full_url = f"https://www.3gpp.org/ftp/Specs/{url}/"
                if full_url not in entry["urls"]:
                    entry["urls"].append(full_url)
        else:
            # Fallback: filename TS number
            ts_num = _ts_from_filename(filename)
            if ts_num:
                file_primary[filename] = ts_num
                if ts_num not in specs:
                    specs[ts_num] = {
                        "tsNumber": ts_num,
                        "title": "",
                        "versions": [],
                        "urls": [
                            f"https://www.3gpp.org/ftp/Specs/archive/29_series/{ts_num}/"
                        ],
                        "yamlFiles": [],
                        "nfServices": [],
                        "referenceOnlyIn": [],
                        "inferredFromFilename": True,
                    }
                entry = specs[ts_num]
                entry["yamlFiles"].append(filename)
                if nf and nf not in entry["nfServices"]:
                    entry["nfServices"].append(nf)

    # Secondary references (e.g. TS 29.501 cited in many files)
    ref_counts: dict[str, set[str]] = defaultdict(set)
    for yaml_path in sorted(yaml_root.glob("*.yaml")):
        text = yaml_path.read_text(encoding="utf-8", errors="ignore")
        primary = file_primary.get(yaml_path.name)
        for ts_num in _all_ts_mentions(text):
            if ts_num != primary:
                ref_counts[ts_num].add(yaml_path.name)

    for ts_num, files in ref_counts.items():
        if ts_num in specs:
            specs[ts_num]["referenceOnlyIn"] = sorted(files)
        else:
            specs[ts_num] = {
                "tsNumber": ts_num,
                "title": "(referenced only — no externalDocs in corpus)",
                "versions": [],
                "urls": [f"https://www.3gpp.org/ftp/Specs/archive/29_series/{ts_num}/"],
                "yamlFiles": [],
                "nfServices": [],
                "referenceOnlyIn": sorted(files),
                "referenceOnly": True,
            }

    spec_list = sorted(specs.values(), key=lambda s: s["tsNumber"])
    for entry in spec_list:
        entry["yamlFiles"] = sorted(entry["yamlFiles"])
        entry["nfServices"] = sorted(entry.get("nfServices", []))
        entry["yamlCount"] = len(entry["yamlFiles"])
        entry["referenceCount"] = len(entry.get("referenceOnlyIn", []))

    return {
        "specs": spec_list,
        "meta": {
            "totalSpecs": len(spec_list),
            "totalYamlFiles": len(list(yaml_root.glob("*.yaml"))),
            "primarySpecs": sum(1 for s in spec_list if s.get("yamlFiles")),
            "referenceOnlySpecs": sum(1 for s in spec_list if s.get("referenceOnly")),
        },
    }


def write_ts_catalog_cache(catalog: dict | None = None) -> dict:
    data = catalog or build_ts_catalog()
    with open(TS_CATALOG_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def get_ts_catalog(refresh: bool = False) -> dict:
    if refresh or not TS_CATALOG_CACHE.exists():
        return write_ts_catalog_cache()
    with open(TS_CATALOG_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)
