from flask import Blueprint, jsonify

from backend.services.build_pipeline import run_full_build

bp = Blueprint("rebuild", __name__)


@bp.route("/api/rebuild", methods=["POST"])
def api_rebuild():
    try:
        result = run_full_build()
        return jsonify({"ok": True, **result})
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
