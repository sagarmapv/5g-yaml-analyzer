from flask import Blueprint, abort, jsonify, request

from backend.services.nf_catalog import catalog_summary, list_nfs, nf_by_id

bp = Blueprint("nfs", __name__)


@bp.route("/api/nfs")
def api_nfs_list():
    tier = request.args.get("tier")
    procedure = request.args.get("procedure")
    e2e_raw = request.args.get("e2eDefault")
    in_corpus = request.args.get("inCorpus", "").lower() in ("1", "true", "yes")
    summary = request.args.get("summary", "").lower() in ("1", "true", "yes")

    e2e_default: bool | None = None
    if e2e_raw is not None:
        e2e_default = e2e_raw.lower() in ("1", "true", "yes")

    if summary and not any([tier, procedure, e2e_raw, in_corpus]):
        return jsonify(catalog_summary())

    return jsonify(
        {
            "networkFunctions": list_nfs(
                tier=tier or None,
                procedure=procedure or None,
                e2e_default=e2e_default,
                in_corpus_only=in_corpus,
            )
        }
    )


@bp.route("/api/nfs/<nf_id>")
def api_nf_detail(nf_id: str):
    detail = nf_by_id(nf_id)
    if detail is None:
        abort(404, description=f"NF {nf_id} not found in catalog")
    return jsonify(detail)
