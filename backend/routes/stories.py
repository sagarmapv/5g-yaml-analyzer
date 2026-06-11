from flask import Blueprint, abort, jsonify, request, send_from_directory

from backend.config import FRONTEND_DIR
from backend.services.master_story import build_master_story, build_story_ladder, list_stories

bp = Blueprint("stories", __name__)


@bp.route("/stories")
def stories_page():
    return send_from_directory(FRONTEND_DIR, "master-story.html")


@bp.route("/ladder")
def ladder_page():
    return send_from_directory(FRONTEND_DIR, "ladder.html")


@bp.route("/api/stories")
def api_stories_list():
    return jsonify(list_stories())


@bp.route("/api/stories/<story_id>/ladder")
def api_story_ladder(story_id: str):
    payload = build_story_ladder(story_id)
    if payload is None:
        abort(404, description=f"Ladder for story {story_id} not found")
    return jsonify(payload)


@bp.route("/api/stories/<story_id>")
def api_story_detail(story_id: str):
    view = request.args.get("view", "full")
    if view not in ("full", "hub"):
        view = "full"
    detail = build_master_story(story_id, view=view)
    if detail is None:
        abort(404, description=f"Story {story_id} not found")
    return jsonify(detail)
