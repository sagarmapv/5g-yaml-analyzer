import json
import re
from collections import defaultdict
from pathlib import Path

from backend.config import BANK_DIR, PROJECT_ROOT, YAML_DIR
from backend.services.nf_classifier import classify_nf

TOPOLOGY_CACHE = PROJECT_ROOT / ".topology.json"

REF_RE = re.compile(r"([A-Za-z0-9_-]+\.yaml)#/")
SERVER_NF_RE = re.compile(r"/(n[a-z0-9-]+)/v\d", re.I)
API_ROOT_RE = re.compile(r"\{(nrf|amf|smf|udm|pcf|nef|ausf|chf|nssf|nrf)ApiRoot\}", re.I)

SERVER_SEGMENT_TO_NF: dict[str, str] = {
    "namf-comm": "AMF",
    "namf-evts": "AMF",
    "namf-mt": "AMF",
    "namf-loc": "AMF",
    "namf-mbs": "AMF",
    "nsmf-pdusession": "SMF",
    "nsmf-eventexposure": "SMF",
    "nnrf-nfm": "NRF",
    "nnrf-disc": "NRF",
    "nudm-sdm": "UDM",
    "nudm-uecm": "UDM",
    "nudm-ee": "UDM",
    "nudr-dr": "UDR",
    "npcf-am-policy-control": "PCF",
    "npcf-smpolicycontrol": "PCF",
    "npcf-policyauthorization": "PCF",
    "nausf-auth": "AUSF",
    "nausf-sorprotection": "AUSF",
    "nausf-upuprotection": "AUSF",
    "nbsf-management": "BSF",
    "nnef-pfdmanagement": "NEF",
    "nnef-smcontext": "NEF",
    "nchf-spendinglimitcontrol": "CHF",
    "nchf-convergedcharging": "CHF",
    "nnssf-nsselection": "NSSF",
    "nnssf-nssaiavailability": "NSSF",
    "nsmsf-sms": "SMSF",
    "nlmf-loc": "LMF",
    "nsepp-telescopic": "SEPP",
    "n32c-handshake": "SEPP",
    "n32-fwd": "SEPP",
    "nnwdaf-eventssubscription": "NWDAF",
    "nnwdaf-analyticsinfo": "NWDAF",
}

API_ROOT_TO_NF = {
    "nrf": "NRF",
    "amf": "AMF",
    "smf": "SMF",
    "udm": "UDM",
    "pcf": "PCF",
    "nef": "NEF",
    "ausf": "AUSF",
    "chf": "CHF",
    "nssf": "NSSF",
}

SKIP_TARGET_NFS = frozenset({"COMMON", "OAM", "OTHER"})
SKIP_REF_SUBSTRINGS = ("CommonData", "ComDefs", "GenericNrm")

# Proxy NFs: rarely appear as cross-NF $ref targets; detect via SBI routing patterns.
SEPP_REF_PREFIX = "TS29573_"
SCP_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"scp-domain", re.I), "scp-domain-routing-info"),
    (re.compile(r"\bScpInfo\b"), "ScpInfo schema"),
    (re.compile(r"\btargetScp\b"), "targetScp redirect"),
    (re.compile(r"servedScpInfoList", re.I), "servedScpInfoList"),
    (re.compile(r"originated by an SCP\b", re.I), "SCP error response"),
    (re.compile(r"redirected.*\bSCP\b", re.I), "SCP redirect"),
    (re.compile(r"nnrf-disc:scp", re.I), "NRF SCP discovery scope"),
]
SEPP_TEXT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bSEPP\b"), "SEPP reference"),
    (re.compile(r"n32c-handshake", re.I), "N32-c handshake"),
    (re.compile(r"n32-fwd", re.I), "N32-fwd forwarding"),
    (re.compile(r"Telescopic\s*FQDN", re.I), "telescopic FQDN mapping"),
    (re.compile(r"JOSE\s+Protected\s+Message", re.I), "JOSE forwarding"),
    (re.compile(r"\bN32Purpose\b"), "N32Purpose"),
    (re.compile(r"originated by an SCP or SEPP", re.I), "SCP/SEPP error response"),
    (re.compile(r"inter-PLMN", re.I), "inter-PLMN"),
]

CORE_NFS = frozenset(
    {
        "AMF",
        "SMF",
        "UDM",
        "UDR",
        "PCF",
        "NRF",
        "NEF",
        "AUSF",
        "BSF",
        "CHF",
        "NSSF",
        "SMSF",
        "LMF",
        "SEPP",
        "SCP",
        "NWDAF",
        "UPF",
        "HSS",
        "GMLC",
        "EIR",
    }
)


def _should_skip_ref(ref_yaml: str) -> bool:
    return any(part in ref_yaml for part in SKIP_REF_SUBSTRINGS)


def _target_nf_from_ref_yaml(ref_yaml: str) -> str | None:
    if ref_yaml.startswith(SEPP_REF_PREFIX):
        return "SEPP"
    if _should_skip_ref(ref_yaml):
        return None
    nf = classify_nf(ref_yaml, {})
    if nf in SKIP_TARGET_NFS:
        return None
    return nf


def _detect_proxy_edges(
    edge_map: dict[tuple[str, str], dict],
    source_nf: str,
    text: str,
) -> None:
    """Detect SCP/SEPP — routing proxies, not typical OpenAPI $ref peers."""
    if source_nf in ("SCP", "SEPP"):
        return

    for pattern, label in SCP_TEXT_PATTERNS:
        if pattern.search(text):
            _add_edge(edge_map, source_nf, "SCP", "scp-proxy", label)

    for pattern, label in SEPP_TEXT_PATTERNS:
        if pattern.search(text):
            _add_edge(edge_map, source_nf, "SEPP", "sepp-proxy", label)


def _nf_from_server_paths(text: str) -> set[str]:
    targets: set[str] = set()
    for segment in SERVER_NF_RE.findall(text):
        key = segment.lower()
        for prefix, nf in SERVER_SEGMENT_TO_NF.items():
            if key.startswith(prefix) or key == prefix:
                targets.add(nf)
                break
    for root in API_ROOT_RE.findall(text):
        nf = API_ROOT_TO_NF.get(root.lower())
        if nf:
            targets.add(nf)
    return targets


def _add_edge(
    edge_map: dict[tuple[str, str], dict],
    source_nf: str,
    target_nf: str,
    signal: str,
    example: str,
) -> None:
    if not target_nf or target_nf == source_nf or source_nf in SKIP_TARGET_NFS:
        return
    key = (source_nf, target_nf)
    edge_map[key]["count"] += 1
    edge_map[key]["signals"].add(signal)
    if example and len(edge_map[key]["examples"]) < 8:
        edge_map[key]["examples"].add(example)


def _extract_edges_from_yaml_text(source_file: str, text: str) -> dict[tuple[str, str], dict]:
    source_nf = classify_nf(source_file, {})
    edge_map: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "signals": set(), "examples": set()}
    )

    if source_nf in SKIP_TARGET_NFS:
        return edge_map

    for ref_yaml in REF_RE.findall(text):
        if ref_yaml == source_file:
            continue
        target_nf = _target_nf_from_ref_yaml(ref_yaml)
        if target_nf:
            _add_edge(edge_map, source_nf, target_nf, "schema-ref", ref_yaml)

    for target_nf in _nf_from_server_paths(text):
        _add_edge(edge_map, source_nf, target_nf, "sbi-path", target_nf)

    _detect_proxy_edges(edge_map, source_nf, text)

    return edge_map


def build_topology(
    yaml_dir: Path | None = None,
    min_weight: int = 1,
    core_only: bool = False,
) -> dict:
    yaml_root = yaml_dir or YAML_DIR
    if not yaml_root.exists():
        return {"nodes": [], "edges": [], "meta": {"edgeCount": 0, "nodeCount": 0}}

    merged: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "signals": set(), "examples": set()}
    )

    for yaml_path in sorted(yaml_root.glob("*.yaml")):
        try:
            text = yaml_path.read_text(encoding="utf-8", errors="ignore")
            edges = _extract_edges_from_yaml_text(yaml_path.name, text)
            for key, data in edges.items():
                merged[key]["count"] += data["count"]
                merged[key]["signals"].update(data["signals"])
                merged[key]["examples"].update(data["examples"])
        except Exception as exc:
            print(f"Topology: skipped {yaml_path.name}: {exc}")

    service_counts: dict[str, int] = defaultdict(int)
    if BANK_DIR.exists():
        for bank_file in BANK_DIR.glob("*_Bank.json"):
            with open(bank_file, "r", encoding="utf-8") as f:
                bank = json.load(f)
            service_counts[bank.get("nf", "")] += 1
    # Proxy NFs: count dedicated specs when present
    if YAML_DIR.exists():
        for yaml_path in YAML_DIR.glob("*.yaml"):
            nf = classify_nf(yaml_path.name, {})
            if nf in ("SCP", "SEPP"):
                service_counts[nf] += 1

    edge_list = []
    node_ids: set[str] = set()
    for (source, target), data in merged.items():
        if data["count"] < min_weight:
            continue
        if core_only and (source not in CORE_NFS or target not in CORE_NFS):
            continue
        node_ids.add(source)
        node_ids.add(target)
        edge_list.append(
            {
                "from": source,
                "to": target,
                "weight": data["count"],
                "signals": sorted(data["signals"]),
                "examples": sorted(data["examples"])[:5],
            }
        )

    edge_list.sort(key=lambda e: (-e["weight"], e["from"], e["to"]))

    nodes = [
        {
            "id": nf,
            "label": nf,
            "serviceCount": service_counts.get(nf, 0),
            "isCore": nf in CORE_NFS,
        }
        for nf in sorted(node_ids)
    ]

    return {
        "nodes": nodes,
        "edges": edge_list,
        "meta": {
            "nodeCount": len(nodes),
            "edgeCount": len(edge_list),
            "coreOnly": core_only,
            "minWeight": min_weight,
        },
    }


def write_topology_cache(topology: dict | None = None) -> dict:
    data = topology or build_topology()
    with open(TOPOLOGY_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def read_topology_cache() -> dict | None:
    if not TOPOLOGY_CACHE.exists():
        return None
    with open(TOPOLOGY_CACHE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_topology(
    min_weight: int = 1,
    core_only: bool = False,
    refresh: bool = False,
) -> dict:
    if refresh:
        return write_topology_cache(build_topology(min_weight=min_weight, core_only=core_only))

    cached = read_topology_cache()
    if cached is None:
        return write_topology_cache(build_topology(min_weight=min_weight, core_only=core_only))

    meta = cached.get("meta", {})
    if meta.get("minWeight") == min_weight and meta.get("coreOnly") == core_only:
        return cached

    return build_topology(min_weight=min_weight, core_only=core_only)
