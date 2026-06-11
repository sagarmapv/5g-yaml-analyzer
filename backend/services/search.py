import json
from pathlib import Path

from backend.config import BANK_DIR


def search_bank(query: str, bank_dir: Path | None = None) -> list[dict]:
    q = query.strip().lower()
    if not q:
        return []

    root = bank_dir or BANK_DIR
    if not root.exists():
        return []

    results = []
    for bank_file in sorted(root.glob("*_Bank.json")):
        with open(bank_file, "r", encoding="utf-8") as f:
            bank = json.load(f)

        nf = bank.get("nf", "")
        service = bank.get("service", "")
        source_file = bank.get("sourceFile", "")

        description = bank.get("serviceDescription", "")
        if (
            q in nf.lower()
            or q in service.lower()
            or q in source_file.lower()
            or q in description.lower()
        ):
            for msg in bank.get("messages", []):
                results.append(_result_from_message(bank, msg))
            continue

        for msg in bank.get("messages", []):
            haystack = " ".join(
                [
                    msg.get("operationId", ""),
                    msg.get("path", ""),
                    msg.get("method", ""),
                    msg.get("summary", ""),
                    msg.get("description", ""),
                ]
            ).lower()
            if q in haystack:
                results.append(_result_from_message(bank, msg))

    return results


def _result_from_message(bank: dict, msg: dict) -> dict:
    return {
        "nf": bank.get("nf", ""),
        "service": bank.get("service", ""),
        "sourceFile": bank.get("sourceFile", ""),
        "path": msg.get("path", ""),
        "method": msg.get("method", ""),
        "operationId": msg.get("operationId", ""),
        "summary": msg.get("summary", ""),
        "serviceDescription": bank.get("serviceDescription", ""),
    }


def load_bank(filename: str, bank_dir: Path | None = None) -> dict | None:
    root = bank_dir or BANK_DIR
    bank_name = filename.replace(".yaml", "_Bank.json")
    bank_path = root / bank_name
    if not bank_path.exists():
        return None
    with open(bank_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_operation(bank: dict, operation_id: str) -> dict | None:
    for msg in bank.get("messages", []):
        if msg.get("operationId") == operation_id:
            return msg
    return None
