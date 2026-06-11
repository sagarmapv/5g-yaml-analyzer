from flask import Blueprint, jsonify

from backend.services.search import load_bank
from backend.utils import safe_filename

bp = Blueprint("bank", __name__)


@bp.route("/api/bank/<filename>")
def serve_bank(filename):
    safe = safe_filename(filename)
    if not safe or not safe.endswith(".yaml"):
        return jsonify({"error": "Invalid filename"}), 400
    bank = load_bank(safe)
    if bank is None:
        return jsonify({"error": "Bank not found. Run build first."}), 404
    return jsonify(bank)
