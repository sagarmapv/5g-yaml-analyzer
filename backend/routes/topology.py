from flask import Blueprint, jsonify, request, send_from_directory

from backend.config import FRONTEND_DIR
from backend.services.nf_topology import get_topology, write_topology_cache
from backend.services.nf_topology import build_topology as build_topology_graph

bp = Blueprint("topology", __name__)


@bp.route("/topology")
def topology_page():
    return send_from_directory(FRONTEND_DIR, "topology.html")


@bp.route("/api/topology")
def api_topology():
    min_weight = request.args.get("minWeight", default=1, type=int)
    core_only = request.args.get("coreOnly", default="false").lower() in ("1", "true", "yes")
    refresh = request.args.get("refresh", default="false").lower() in ("1", "true", "yes")

    min_weight = max(1, min(min_weight, 50))
    return jsonify(get_topology(min_weight=min_weight, core_only=core_only, refresh=refresh))


@bp.route("/api/topology/rebuild", methods=["POST"])
def api_topology_rebuild():
    data = write_topology_cache(build_topology_graph())
    return jsonify({"ok": True, "meta": data.get("meta", {})})
