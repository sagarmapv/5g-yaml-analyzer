from flask import Blueprint, abort, jsonify, request, send_from_directory

from backend.config import FRONTEND_DIR
from backend.services.spec_narrative import load_narrative, normalize_ts_number
from backend.services.spec_platform import build_platform_index
from backend.services.spec_story import build_spec_detail, build_spec_preview
from backend.services.story_stitch import build_element_readiness
from backend.services.ts_catalog import get_ts_catalog, write_ts_catalog_cache
from backend.services.ts_catalog import build_ts_catalog as build_catalog
from backend.services.nf_map import get_nf_map, get_spec_map, write_nf_map_cache
from backend.services.nf_map import build_nf_map as build_map
from backend.services.nf_map import build_spec_map

bp = Blueprint("specs", __name__)


@bp.route("/specs")
def specs_page():
    return send_from_directory(FRONTEND_DIR, "specs.html")


@bp.route("/specs/<ts_number>")
def spec_story_page(ts_number: str):
    return send_from_directory(FRONTEND_DIR, "spec-story.html")


@bp.route("/api/specs/<ts_number>/element-readiness")
def api_element_readiness(ts_number: str):
    ts_number = normalize_ts_number(ts_number)
    narrative = load_narrative(ts_number)
    if not narrative or not narrative.get("elements"):
        abort(404, description=f"No elements for spec {ts_number}")
    return jsonify(build_element_readiness(narrative["elements"], ts_number))


@bp.route("/api/specs/<ts_number>/preview")
def api_spec_preview(ts_number: str):
    preview = build_spec_preview(ts_number)
    if preview is None:
        abort(404, description=f"Preview for spec {ts_number} not found")
    return jsonify(preview)


@bp.route("/api/specs/<ts_number>/detail")
def api_spec_detail(ts_number: str):
    refresh_pdf = request.args.get("refreshPdf", default="false").lower() in ("1", "true", "yes")
    detail = build_spec_detail(ts_number, refresh_pdf=refresh_pdf)
    if detail is None:
        abort(404, description=f"Spec {ts_number} not found")
    return jsonify(detail)


@bp.route("/api/specs")
def api_specs():
    refresh = request.args.get("refresh", default="false").lower() in ("1", "true", "yes")
    return jsonify(get_spec_map(refresh=refresh))


@bp.route("/api/specs/platform")
def api_specs_platform():
    refresh = request.args.get("refresh", default="false").lower() in ("1", "true", "yes")
    return jsonify(build_platform_index(refresh=refresh))


@bp.route("/api/map")
def api_nf_map():
    refresh = request.args.get("refresh", default="false").lower() in ("1", "true", "yes")
    return jsonify(get_nf_map(refresh=refresh))


@bp.route("/api/specs/catalog")
def api_specs_catalog():
    """Flat TS catalog with reference-only specs (legacy list view data)."""
    refresh = request.args.get("refresh", default="false").lower() in ("1", "true", "yes")
    return jsonify(get_ts_catalog(refresh=refresh))


@bp.route("/api/specs/rebuild", methods=["POST"])
def api_specs_rebuild():
    data = write_ts_catalog_cache(build_catalog())
    write_nf_map_cache(build_map())
    return jsonify({"ok": True, "meta": data.get("meta", {})})
