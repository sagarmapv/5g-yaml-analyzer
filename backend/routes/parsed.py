from flask import Blueprint, jsonify

from backend.services.parser import load_parsed_summary
from backend.utils import safe_filename

bp = Blueprint("parsed", __name__)


@bp.route("/api/parsed/<filename>")
def serve_parsed(filename):
    safe = safe_filename(filename)
    if not safe or not safe.endswith(".yaml"):
        return jsonify({"error": "Invalid filename"}), 400
    try:
        return jsonify(load_parsed_summary(safe))
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/parsed/<filename>")
def legacy_parsed(filename):
    return serve_parsed(filename)
