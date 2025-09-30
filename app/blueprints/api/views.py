from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from ...extensions import limiter
from ...models import Project
from ...services.pattern_composer import compute_erp
from ...utils.calculations import total_feeder_loss


api_bp = Blueprint("api", __name__, url_prefix="/api")

api_limit = lambda: current_app.config.get("RATE_LIMIT_API", "30 per minute")


@api_bp.route("/projects/<uuid:project_id>/patterns", methods=["POST"])
@login_required
@limiter.limit(api_limit)
def project_patterns(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    payload = request.get_json(silent=True) or {}
    mutable_fields = (
        "frequency_mhz",
        "tx_power_w",
        "cable_length_m",
        "splitter_loss_db",
        "connector_loss_db",
        "v_count",
        "v_spacing_m",
        "v_beta_deg",
        "v_level_amp",
        "v_norm_mode",
        "h_count",
        "h_spacing_m",
        "h_beta_deg",
        "h_step_deg",
        "h_level_amp",
        "h_norm_mode",
        "feeder_loss_db",
    )
    originals = {field: getattr(project, field) for field in mutable_fields}
    for field in mutable_fields:
        if field in payload:
            setattr(project, field, payload[field])
    try:
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_type,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
        data = compute_erp(project)
    finally:
        for field, value in originals.items():
            setattr(project, field, value)
        project.feeder_loss_db = originals.get("feeder_loss_db", project.feeder_loss_db)
    return jsonify({k: v.tolist() if hasattr(v, "tolist") else v for k, v in data.items()})
