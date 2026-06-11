import json
from collections import defaultdict
from pathlib import Path

from backend.config import BANK_DIR, PROJECT_ROOT, YAML_DIR
from backend.services.nf_classifier import classify_nf
from backend.services.ts_catalog import resolve_primary_spec

NF_MAP_CACHE = PROJECT_ROOT / ".nf-map.json"


def _load_bank_metadata() -> dict[str, dict]:
    """sourceFile -> {service, serviceDescription, nf}"""
    meta: dict[str, dict] = {}
    if not BANK_DIR.exists():
        return meta
    for bank_file in BANK_DIR.glob("*_Bank.json"):
        with open(bank_file, "r", encoding="utf-8") as f:
            bank = json.load(f)
        source = bank.get("sourceFile", "")
        if source:
            meta[source] = {
                "service": bank.get("service", ""),
                "serviceDescription": bank.get("serviceDescription", ""),
                "nf": bank.get("nf", ""),
            }
    return meta


def build_nf_map(yaml_dir: Path | None = None) -> dict:
    yaml_root = yaml_dir or YAML_DIR
    if not yaml_root.exists():
        return {"nfs": [], "meta": {"nfCount": 0, "specCount": 0, "yamlCount": 0}}

    bank_meta = _load_bank_metadata()

    # nf -> tsNumber -> spec bucket
    tree: dict[str, dict[str, dict]] = defaultdict(
        lambda: defaultdict(
            lambda: {
                "tsNumber": "",
                "title": "",
                "url": "",
                "versions": [],
                "yamls": [],
            }
        )
    )

    yaml_count = 0
    for yaml_path in sorted(yaml_root.glob("*.yaml")):
        filename = yaml_path.name
        text = yaml_path.read_text(encoding="utf-8", errors="ignore")
        spec = resolve_primary_spec(filename, text)
        ts_num = spec["tsNumber"]

        bank = bank_meta.get(filename, {})
        nf = bank.get("nf") or classify_nf(filename, {})

        spec_bucket = tree[nf][ts_num]
        spec_bucket["tsNumber"] = ts_num
        if spec.get("title") and len(spec["title"]) > len(spec_bucket.get("title", "")):
            spec_bucket["title"] = spec["title"]
        if spec.get("url"):
            spec_bucket["url"] = spec["url"]
        for ver in spec.get("versions", []):
            if ver not in spec_bucket["versions"]:
                spec_bucket["versions"].append(ver)

        spec_bucket["yamls"].append(
            {
                "sourceFile": filename,
                "service": bank.get("service") or filename.replace(".yaml", ""),
                "serviceDescription": bank.get("serviceDescription", ""),
            }
        )
        yaml_count += 1

    nfs = []
    spec_total = 0
    for nf_name in sorted(tree.keys()):
        specs = []
        for ts_num in sorted(tree[nf_name].keys(), key=lambda t: (t == "unknown", t)):
            bucket = tree[nf_name][ts_num]
            yamls = sorted(bucket["yamls"], key=lambda y: y["sourceFile"])
            specs.append(
                {
                    "tsNumber": bucket["tsNumber"],
                    "title": bucket["title"],
                    "url": bucket.get("url", ""),
                    "versions": sorted(bucket.get("versions", [])),
                    "yamlCount": len(yamls),
                    "yamls": yamls,
                }
            )
        spec_total += len(specs)
        yaml_in_nf = sum(s["yamlCount"] for s in specs)
        nfs.append(
            {
                "nf": nf_name,
                "specCount": len(specs),
                "yamlCount": yaml_in_nf,
                "specs": specs,
            }
        )

    return {
        "nfs": nfs,
        "meta": {
            "nfCount": len(nfs),
            "specCount": spec_total,
            "yamlCount": yaml_count,
        },
    }


def build_spec_map(yaml_dir: Path | None = None) -> dict:
    """Invert NF → Spec → YAML into Spec → NF → YAML."""
    nf_map = build_nf_map(yaml_dir)
    specs_dict: dict[str, dict] = {}

    for nf_block in nf_map.get("nfs", []):
        for spec in nf_block.get("specs", []):
            ts_num = spec["tsNumber"]
            if ts_num not in specs_dict:
                specs_dict[ts_num] = {
                    "tsNumber": ts_num,
                    "title": spec.get("title", ""),
                    "url": spec.get("url", ""),
                    "versions": list(spec.get("versions", [])),
                    "nfs": [],
                    "yamlCount": 0,
                }
            entry = specs_dict[ts_num]
            if spec.get("title") and len(spec["title"]) > len(entry["title"]):
                entry["title"] = spec["title"]
            if spec.get("url"):
                entry["url"] = spec["url"]
            for ver in spec.get("versions", []):
                if ver not in entry["versions"]:
                    entry["versions"].append(ver)

            yamls = spec.get("yamls", [])
            entry["nfs"].append(
                {
                    "nf": nf_block["nf"],
                    "yamlCount": len(yamls),
                    "yamls": yamls,
                }
            )
            entry["yamlCount"] += len(yamls)

    spec_list = []
    for ts_num in sorted(specs_dict.keys(), key=lambda t: (t == "unknown", t)):
        entry = specs_dict[ts_num]
        entry["nfs"] = sorted(entry["nfs"], key=lambda n: n["nf"])
        entry["nfCount"] = len(entry["nfs"])
        entry["versions"] = sorted(entry["versions"])
        spec_list.append(entry)

    return {
        "specs": spec_list,
        "meta": {
            "specCount": len(spec_list),
            "nfCount": nf_map["meta"]["nfCount"],
            "yamlCount": nf_map["meta"]["yamlCount"],
        },
    }


def get_spec_map(refresh: bool = False) -> dict:
    if refresh:
        write_nf_map_cache()
    return build_spec_map()


def write_nf_map_cache(nf_map: dict | None = None) -> dict:
    data = nf_map or build_nf_map()
    with open(NF_MAP_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def get_nf_map(refresh: bool = False) -> dict:
    if refresh or not NF_MAP_CACHE.exists():
        return write_nf_map_cache()
    with open(NF_MAP_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)
