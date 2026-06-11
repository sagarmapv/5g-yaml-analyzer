from flask import Blueprint, abort, jsonify, request

from backend.services.message_envelope import attach_envelope_to_detail
from backend.services.operation_detail import build_operation_detail

bp = Blueprint("operations", __name__)


@bp.route("/api/operations/<operation_id>")
def api_operation_detail(operation_id: str):
    view = request.args.get("view", "full")
    if view not in ("full", "request"):
        view = "full"
    detail = build_operation_detail(operation_id, view=view)
    if detail is None:
        abort(404, description=f"Operation {operation_id} not found")
    if view == "request":
        detail = attach_envelope_to_detail(detail)
    return jsonify(detail)
