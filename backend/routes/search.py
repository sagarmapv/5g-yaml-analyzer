from flask import Blueprint, jsonify, request

from backend.services.search import search_bank

bp = Blueprint("search", __name__)


@bp.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    return jsonify(search_bank(query))
