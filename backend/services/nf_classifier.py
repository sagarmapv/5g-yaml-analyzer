import re
from typing import Any

# 3GPP service name prefix (from filename or title) → display NF / domain
API_PREFIX_TO_NF: dict[str, str] = {
    # Core 5GC network functions
    "Namf": "AMF",
    "Nsmf": "SMF",
    "Nudm": "UDM",
    "Nausf": "AUSF",
    "Nnrf": "NRF",
    "Npcf": "PCF",
    "Nchf": "CHF",
    "Nnef": "NEF",
    "Nbsf": "BSF",
    "Nlmf": "LMF",
    "Nnssf": "NSSF",
    "Nudr": "UDR",
    "Nsmsf": "SMSF",
    "N5g-eir": "EIR",
    "Nsepp": "SEPP",
    "Nmnpf": "MNPF",
    "Nucmf": "UCMF",
    # Extended / adjacent 5GC functions
    "Nhss": "HSS",
    "Nnwdaf": "NWDAF",
    "Nupf": "UPF",
    "Ntsctsf": "TSCTSF",
    "Nmbsf": "MBSF",
    "Nmbsmf": "MBSMF",
    "Nmbstf": "MBSTF",
    "Ndcaf": "DCAF",
    "Nadrf": "ADRF",
    "Ndccf": "DCCF",
    "Nmfaf": "MFAF",
    "Neasdf": "EASDF",
    "Npanf": "PANF",
    "Nsoraf": "SORAF",
    "Npkmf": "PKMF",
    "Naf": "NAF",
    "Nimsas": "IMS-AS",
    "Nnssaaf": "NSSAAF",
    "Nnsacf": "NSACF",
    "Ngmlc": "GMLC",
    "Naanf": "ANF",
    "Nspaf": "SPAF",
    "N5g-ddnmf": "DDNMF",
    "Nipsmgw": "IP-SM-GW",
    "Nrouter": "ROUTER",
    "Niwmsc": "IW-MSC",
    "Nudsf": "UDSF",
    "Nslpkmf": "SLP-KMF",
    "Nbsp": "BSF",
    "Nmf": "MF",
    "N32": "SEPP",
    "SeppTelescopicFqdnMapping": "SEPP",
}

# Full filename stem (without TS prefix) → NF
FILENAME_STEM_TO_NF: dict[str, str] = {
    "JOSEProtectedMessageForwarding": "SEPP",
    "SeppTelescopicFqdnMapping": "SEPP",
    "GMDviaMBMSbyMB2": "MBS",
    "GMDviaMBMSbyxMB": "MBS",
    "AMInfluence": "NEF",
    "SliceParamProvision": "NSSF",
    "MdaReport": "OAM",
    "MdaNrm": "OAM",
    "IntentExpectations": "OAM",
    "HeartbeatNtf": "OAM",
}

# Filename token (after TS number) → domain when no N-prefix applies
FILENAME_TOKEN_TO_NF: dict[str, str] = {
    "Eecs": "EDGE",
    "Eees": "EDGE",
    "Ecas": "EDGE",
    "ADAE": "ADAE",
    "M1": "5GMS",
    "M5": "5GMS",
    "R2": "5GMS",
    "R4": "5GMS",
    "EventExposure": "5GMS",
    "CommonData": "COMMON",
    "MBSObjectManifest": "MBS",
    "MBSUserServiceAnnouncement": "MBS",
    "NSCE": "NSCE",
    "SS": "SEAL",
    "VAE": "V2X",
    "CAPIF": "CAPIF",
    "MSGG": "MSGIN",
    "MSGS": "MSGIN",
    "PIN": "PIN",
    "UAE": "UAV",
    "SDD": "SEALDD",
    "AEF": "CAPIF",
}

# Keyword patterns searched in title + description (order matters — first match wins)
TEXT_KEYWORD_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b5g\s*media\s*stream|\b5gms\b", re.I), "5GMS"),
    (re.compile(r"\bmbs\b|multicast|broadcast.*service", re.I), "MBS"),
    (re.compile(r"\bedge\s+enabler|\beecs\b|\beees\b|\beec\b|\beas\b", re.I), "EDGE"),
    (re.compile(r"\bnetwork\s+slice\s+capability|\bnsce\b", re.I), "NSCE"),
    (re.compile(r"\bseal\b|\bsealdd\b", re.I), "SEAL"),
    (re.compile(r"\bcapif\b", re.I), "CAPIF"),
    (re.compile(r"\bv2x\b|\bvae\b", re.I), "V2X"),
    (re.compile(r"\bims\b", re.I), "IMS"),
    (re.compile(r"\bnrf\b|network\s+repository\s+function", re.I), "NRF"),
    (re.compile(r"\bamf\b|access\s+and\s+mobility", re.I), "AMF"),
    (re.compile(r"\bsmf\b|session\s+management\s+function", re.I), "SMF"),
    (re.compile(r"\budm\b|unified\s+data\s+management", re.I), "UDM"),
    (re.compile(r"\budr\b|unified\s+data\s+repository", re.I), "UDR"),
    (re.compile(r"\bpcf\b|policy\s+control\s+function", re.I), "PCF"),
    (re.compile(r"\bausf\b|authentication\s+server\s+function", re.I), "AUSF"),
    (re.compile(r"\bnef\b|network\s+exposure", re.I), "NEF"),
    (re.compile(r"\bchf\b|charging\s+function", re.I), "CHF"),
    (re.compile(r"\bnssf\b|network\s+slice\s+selection", re.I), "NSSF"),
    (re.compile(r"\bsmsf\b|sms\s+function", re.I), "SMSF"),
    (re.compile(r"\blmf\b|location\s+management", re.I), "LMF"),
    (re.compile(r"\bgmlc\b|ngmlc\b", re.I), "GMLC"),
    (re.compile(r"\bnwdaf\b|network\s+data\s+analytics", re.I), "NWDAF"),
    (re.compile(r"\bupf\b|user\s+plane\s+function", re.I), "UPF"),
    (re.compile(r"\bhss\b|home\s+subscriber", re.I), "HSS"),
    (re.compile(r"\bsepp\b|security\s+edge\s+protection", re.I), "SEPP"),
    (re.compile(r"\b5g-?eir\b|equipment\s+identity", re.I), "EIR"),
    (re.compile(r"\btsctsf\b|time\s+sensitive\s+communication", re.I), "TSCTSF"),
    (re.compile(r"\bmda\b|management\s+data\s+analytics", re.I), "OAM"),
    (re.compile(r"\bintent\b", re.I), "OAM"),
    (re.compile(r"\bheartbeat\b", re.I), "OAM"),
    (re.compile(r"\bmbms\b|group\s+message\s+delivery", re.I), "MBS"),
    (re.compile(r"\b(provisioning|performance|fault|nrm|mns)\b", re.I), "OAM"),
    (re.compile(r"\b3gpp-", re.I), "SCEF"),
]

_N_PREFIX_RE = re.compile(r"\b(N[a-z][a-z0-9-]{2,})\b")
_FILENAME_N_PREFIX_RE = re.compile(r"_(N[a-z0-9-]+)_", re.I)
_FILENAME_TOKEN_RE = re.compile(r"^TS\d+_([^_]+)")


def _normalize_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    # Preserve N5g-eir style; normalize nmbsf → Nmbsf
    if prefix.lower().startswith("n") and prefix[1:2].islower():
        return "N" + prefix[1:]
    return prefix


def _nf_from_prefix(prefix: str) -> str | None:
    normalized = _normalize_prefix(prefix)
    if normalized in API_PREFIX_TO_NF:
        return API_PREFIX_TO_NF[normalized]
    # Case-insensitive fallback
    for key, nf in API_PREFIX_TO_NF.items():
        if key.lower() == normalized.lower():
            return nf
    return None


def _search_text_keywords(text: str) -> str | None:
    for pattern, nf in TEXT_KEYWORD_RULES:
        if pattern.search(text):
            return nf
    return None


def _extract_n_prefixes(text: str) -> list[str]:
    return [_normalize_prefix(m) for m in _N_PREFIX_RE.findall(text)]


def classify_nf(source_file: str, info: dict[str, Any] | None = None) -> str:
    """
    Resolve NF/domain for a spec using filename, info.title, and info.description.

    Resolution order:
    1. N-service prefix in filename (e.g. TS29519_Npcf_...)
    2. Title underscore prefix (e.g. Namf_Communication)
    3. N-service prefix anywhere in title
    4. Filename domain token (Eees, M1, NSCE, ...)
    5. Keyword match in title + description
    6. N-service prefix in description
    """
    info = info or {}
    title = (info.get("title") or "").strip()
    description = (info.get("description") or "").strip()
    combined = f"{title}\n{description}"

    stem = source_file.replace(".yaml", "").replace(".json", "")

    # 1. Filename N-prefix
    for match in _FILENAME_N_PREFIX_RE.finditer(stem):
        nf = _nf_from_prefix(match.group(1))
        if nf:
            return nf

    # 2. Title underscore prefix
    if "_" in title:
        nf = _nf_from_prefix(title.split("_")[0])
        if nf:
            return nf

    # 3. N-prefix in title
    for prefix in _extract_n_prefixes(title):
        nf = _nf_from_prefix(prefix)
        if nf:
            return nf

    # 4. Full filename stem (after TS number)
    stem_suffix = _FILENAME_TOKEN_RE.match(stem)
    if stem_suffix:
        full_stem = stem_suffix.group(1)
        if full_stem in FILENAME_STEM_TO_NF:
            return FILENAME_STEM_TO_NF[full_stem]

    # 5. Filename domain token
    token_match = stem_suffix
    if token_match:
        token = token_match.group(1)
        if token in FILENAME_TOKEN_TO_NF:
            return FILENAME_TOKEN_TO_NF[token]
        # Title starts with token (Eees_ACREvents)
        if title.startswith(token + "_") or title == token:
            mapped = FILENAME_TOKEN_TO_NF.get(token.split("_")[0])
            if mapped:
                return mapped

    # 6. Keyword rules on title + description
    keyword_nf = _search_text_keywords(combined)
    if keyword_nf:
        return keyword_nf

    # 7. N-prefix in description
    for prefix in _extract_n_prefixes(description):
        nf = _nf_from_prefix(prefix)
        if nf:
            return nf

    # 8. Human-readable title hints (no underscore)
    if title:
        keyword_nf = _search_text_keywords(title)
        if keyword_nf:
            return keyword_nf

    return "OTHER"
