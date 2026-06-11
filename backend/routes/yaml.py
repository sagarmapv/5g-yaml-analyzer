import os

from flask import Blueprint, jsonify, send_from_directory

from backend.config import YAML_DIR
from backend.utils import safe_filename

bp = Blueprint("yaml", __name__)


@bp.route("/api/yaml/<filename>")
def serve_yaml(filename):
    safe = safe_filename(filename)
    if not safe or not safe.endswith(".yaml"):
        return jsonify({"error": "Invalid filename"}), 400
    if not (YAML_DIR / safe).exists():
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(YAML_DIR, safe)


@bp.route("/yaml/<filename>")
def legacy_yaml(filename):
    return serve_yaml(filename)


@bp.route("/api/list-yamls")
def list_yaml_files():
    if not YAML_DIR.exists():
        return jsonify([])
    files = sorted(f for f in os.listdir(YAML_DIR) if f.endswith(".yaml"))
    return jsonify(files)


@bp.route("/list-yamls")
def legacy_list_yamls():
    return list_yaml_files()
