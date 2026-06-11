import json
from datetime import datetime, timezone
from pathlib import Path

from backend.config import (
    BUILD_STATUS_FILE,
    INDEX_JSON,
    PARSED_JSON_DIR,
    YAML_DIR,
)
from backend.services.bank_builder import build_bank_from_parsed_json
from backend.services.nf_topology import write_topology_cache
from backend.services.ts_catalog import write_ts_catalog_cache
from backend.services.nf_map import write_nf_map_cache
from backend.services.nf_map import build_nf_map
from backend.services.swagger_bundle import bundle_yaml_to_json as bundle_single_yaml
from backend.services.swagger_bundle import remove_path


def bundle_all_yamls(yaml_dir: Path | None = None, parsed_dir: Path | None = None) -> int:
    yaml_root = yaml_dir or YAML_DIR
    json_root = parsed_dir or PARSED_JSON_DIR
    json_root.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(yaml_root.glob("*.yaml"))
    if not yaml_files:
        return 0

    for old_json in json_root.glob("*.json"):
        remove_path(old_json)

    if INDEX_JSON.exists():
        INDEX_JSON.unlink()

    success_count = 0
    for yaml_path in yaml_files:
        json_path = json_root / f"{yaml_path.stem}.json"
        try:
            bundle_single_yaml(yaml_path, json_path)
            success_count += 1
        except RuntimeError as exc:
            if "not found" in str(exc).lower():
                raise
            print(f"swagger-cli failed for {yaml_path.name}: {exc}")

    return success_count


def write_build_status(yaml_count: int, parsed_count: int) -> dict:
    status = {
        "lastRebuild": datetime.now(timezone.utc).isoformat(),
        "yamlCount": yaml_count,
        "parsedCount": parsed_count,
    }
    with open(BUILD_STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)
    return status


def read_build_status() -> dict | None:
    if not BUILD_STATUS_FILE.exists():
        return None
    with open(BUILD_STATUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run_full_build(yaml_dir: Path | None = None, parsed_dir: Path | None = None) -> dict:
    yaml_root = yaml_dir or YAML_DIR
    yaml_count = len(list(yaml_root.glob("*.yaml")))
    parsed_count = bundle_all_yamls(yaml_root, parsed_dir or PARSED_JSON_DIR)
    index = build_bank_from_parsed_json(parsed_dir or PARSED_JSON_DIR)
    write_topology_cache()
    write_ts_catalog_cache()
    write_nf_map_cache(build_nf_map())
    status = write_build_status(yaml_count, parsed_count)
    return {
        "status": status,
        "indexNfCount": len(index),
        "serviceCount": sum(len(services) for services in index.values()),
    }
