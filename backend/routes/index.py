import json
import os

from flask import Blueprint, jsonify, redirect, send_from_directory

from backend.config import FRONTEND_DIR, INDEX_JSON

bp = Blueprint("index", __name__)


@bp.route("/")
def serve_home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@bp.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@bp.route("/api/index")
def serve_index():
    if not INDEX_JSON.exists():
        return jsonify({})
    with open(INDEX_JSON, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@bp.route("/index")
def legacy_index():
    return redirect("/api/index", code=302)
