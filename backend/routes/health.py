from flask import Blueprint, jsonify

from backend.config import BANK_DIR, INDEX_JSON, PARSED_JSON_DIR, YAML_DIR
from backend.services.build_pipeline import read_build_status
from backend.services.curl_generator import generate_curl
from backend.services.parser import load_swagger_json
from backend.services.search import find_operation, load_bank
from backend.utils import safe_filename

bp = Blueprint("health", __name__)


@bp.route("/api/health")
def api_health():
    yaml_count = len(list(YAML_DIR.glob("*.yaml"))) if YAML_DIR.exists() else 0
    parsed_count = len(list(PARSED_JSON_DIR.glob("*.json"))) if PARSED_JSON_DIR.exists() else 0
    bank_count = len(list(BANK_DIR.glob("*_Bank.json"))) if BANK_DIR.exists() else 0
    build_status = read_build_status()

    return jsonify(
        {
            "status": "ok",
            "yamlCount": yaml_count,
            "parsedCount": parsed_count,
            "bankCount": bank_count,
            "indexExists": INDEX_JSON.exists(),
            "buildStatus": build_status,
        }
    )


@bp.route("/api/curl/<filename>/<operation_id>")
def api_curl(filename, operation_id):
    safe = safe_filename(filename)
    if not safe or not safe.endswith(".yaml"):
        return jsonify({"error": "Invalid filename"}), 400
    if not operation_id or ".." in operation_id or "/" in operation_id:
        return jsonify({"error": "Invalid operationId"}), 400

    bank = load_bank(safe)
    if bank is None:
        return jsonify({"error": "Bank not found. Run build first."}), 404

    operation = find_operation(bank, operation_id)
    if operation is None:
        return jsonify({"error": "Operation not found"}), 404

    try:
        swagger_json = load_swagger_json(safe)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    curl_cmd = generate_curl(swagger_json, operation)
    return jsonify({"operationId": operation_id, "curl": curl_cmd})
