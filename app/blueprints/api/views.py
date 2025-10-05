from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import current_user as jwt_current_user, jwt_required, verify_jwt_in_request
from flask_login import current_user as login_current_user

from ...extensions import db, limiter, csrf
from ...models import Antenna, Cable, Project, ProjectExport
from ...services.assistant import (
    AssistantServiceError,
    ConversationSnapshot,
    send_assistant_message,
    snapshot_for,
)
from ...services.exporters import generate_project_export
from ...services.pattern_composer import get_composition
from ...utils.calculations import total_feeder_loss, vertical_beta_deg

api_bp = Blueprint("api", __name__, url_prefix="/api")

api_limit = lambda: current_app.config.get("RATE_LIMIT_API", "60 per minute")


def _require_admin() -> None:
    if not getattr(jwt_current_user, "is_admin", False):
        abort(403, description="Acesso restrito ao administrador.")


def _parse_float(value, field: str, *, required: bool = False, default: float | None = None) -> float | None:
    if value in (None, ""):
        if required:
            abort(400, description=f"Campo {field} e obrigatorio.")
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        abort(400, description=f"Valor invalido para {field}.")


def _parse_int(value, field: str, *, required: bool = False, default: int | None = None) -> int | None:
    if value in (None, ""):
        if required:
            abort(400, description=f"Campo {field} e obrigatorio.")
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        abort(400, description=f"Valor invalido para {field}.")


def _optional_str(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _normalise_mode(value, axis: str) -> str:
    allowed = {"max", "first", "sum"}
    if value in (None, ""):
        return "max"
    value = str(value).lower()
    if value not in allowed:
        abort(400, description=f"Normalizacao {axis} invalida. Use max, first ou sum.")
    return value


def _resolve_antenna(antenna_id) -> Antenna:
    if antenna_id in (None, ""):
        abort(400, description="Campo antenna_id e obrigatorio.")
    try:
        antenna_uuid = UUID(str(antenna_id))
    except (TypeError, ValueError):
        abort(400, description="Antena invalida.")
    antenna = db.session.get(Antenna, antenna_uuid)
    if not antenna:
        abort(404, description="Antena nao encontrada.")
    return antenna


def _resolve_cable(cable_id) -> Cable | None:
    if cable_id in (None, "", 0, "0"):
        return None
    try:
        cable_uuid = UUID(str(cable_id))
    except (TypeError, ValueError):
        abort(400, description="Cabo invalido.")
    cable = db.session.get(Cable, cable_uuid)
    if not cable:
        abort(404, description="Cabo nao encontrado.")
    return cable


def _antenna_to_dict(antenna: Antenna) -> dict:
    return {
        "id": str(antenna.id),
        "name": antenna.name,
        "model_number": antenna.model_number,
        "description": antenna.description,
        "nominal_gain_dbd": antenna.nominal_gain_dbd,
        "polarization": antenna.polarization,
        "frequency_min_mhz": antenna.frequency_min_mhz,
        "frequency_max_mhz": antenna.frequency_max_mhz,
        "patterns": [
            {
                "id": str(pattern.id),
                "type": pattern.pattern_type.value,
                "points": len(pattern.angles_deg or []),
            }
            for pattern in sorted(antenna.patterns, key=lambda p: p.pattern_type.value)
        ],
        "created_at": antenna.created_at.isoformat() if antenna.created_at else None,
        "updated_at": antenna.updated_at.isoformat() if antenna.updated_at else None,
    }


def _project_to_dict(project: Project, *, include_exports: bool = False) -> dict:
    data = {
        "id": str(project.id),
        "name": project.name,
        "owner_id": str(project.owner_id),
        "antenna_id": str(project.antenna_id),
        "antenna_name": project.antenna.name if project.antenna else None,
        "frequency_mhz": project.frequency_mhz,
        "tx_power_w": project.tx_power_w,
        "tower_height_m": project.tower_height_m,
        "cable_id": str(project.cable_id) if project.cable_id else None,
        "cable_type": project.cable_type,
        "cable_model_code": (project.cable.model_code if project.cable else project.cable_type),
        "cable_display_name": project.cable.display_name if project.cable else None,
        "cable_size_inch": project.cable.size_inch if project.cable else None,
        "cable_length_m": project.cable_length_m,
        "splitter_loss_db": project.splitter_loss_db,
        "connector_loss_db": project.connector_loss_db,
        "vswr_target": project.vswr_target,
        "v_count": project.v_count,
        "v_spacing_m": project.v_spacing_m,
        "v_tilt_deg": project.v_tilt_deg,
        "v_beta_deg": project.v_beta_deg,
        "v_level_amp": project.v_level_amp,
        "v_norm_mode": project.v_norm_mode,
        "h_count": project.h_count,
        "h_spacing_m": project.h_spacing_m,
        "h_beta_deg": project.h_beta_deg,
        "h_step_deg": project.h_step_deg,
        "h_level_amp": project.h_level_amp,
        "h_norm_mode": project.h_norm_mode,
        "feeder_loss_db": project.feeder_loss_db,
        "notes": project.notes,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
    }
    if include_exports:
        exports = sorted(project.revisions, key=lambda e: e.created_at or datetime.min, reverse=True)
        data["exports"] = [_export_to_dict(export) for export in exports]
    return data


def _export_to_dict(export: ProjectExport) -> dict:
    return {
        "id": str(export.id),
        "created_at": export.created_at.isoformat() if export.created_at else None,
        "pat_path": export.pat_path,
        "prn_path": export.prn_path,
        "pdf_path": export.pdf_path,
        "erp_metadata": export.erp_metadata,
    }


def _erp_payload(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if hasattr(value, "tolist"):
            result[key] = value.tolist()
        else:
            result[key] = value
    return result


def _snapshot_to_dict(snapshot: ConversationSnapshot) -> dict:
    return {
        "conversation_id": str(snapshot.conversation.id),
        "title": snapshot.conversation.title,
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "token_count": message.token_count,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in snapshot.messages
        ],
    }


def _get_project_for_user(project_id) -> Project:
    try:
        project_uuid = UUID(str(project_id))
    except (TypeError, ValueError):
        abort(404)
    project = Project.query.filter_by(id=project_uuid, owner_id=jwt_current_user.id).first()
    if not project:
        abort(404)
    return project


def _create_project_from_payload(payload: dict) -> Project:
    name = (payload.get("name") or "").strip()
    if not name:
        abort(400, description="Campo name e obrigatorio.")
    antenna = _resolve_antenna(payload.get("antenna_id"))
    frequency_mhz = _parse_float(payload.get("frequency_mhz"), "frequency_mhz", required=True)
    tx_power_w = _parse_float(payload.get("tx_power_w"), "tx_power_w", required=True)
    tower_height_m = _parse_float(payload.get("tower_height_m"), "tower_height_m", required=True)
    v_count = _parse_int(payload.get("v_count"), "v_count", required=True)
    h_count = _parse_int(payload.get("h_count"), "h_count", required=True)

    cable = _resolve_cable(payload.get("cable_id"))
    cable_type_value = _optional_str(payload.get("cable_type"))
    if cable:
        cable_type_value = cable.model_code

    project = Project(
        owner=jwt_current_user,
        antenna=antenna,
        name=name,
        frequency_mhz=frequency_mhz,
        tx_power_w=tx_power_w,
        tower_height_m=tower_height_m,
        cable_type=cable_type_value,
        cable_length_m=_parse_float(payload.get("cable_length_m"), "cable_length_m", default=0.0) or 0.0,
        splitter_loss_db=_parse_float(payload.get("splitter_loss_db"), "splitter_loss_db", default=0.0) or 0.0,
        connector_loss_db=_parse_float(payload.get("connector_loss_db"), "connector_loss_db", default=0.0) or 0.0,
        vswr_target=_parse_float(payload.get("vswr_target"), "vswr_target", default=1.5) or 1.5,
        v_count=v_count,
        v_spacing_m=_parse_float(payload.get("v_spacing_m"), "v_spacing_m", default=0.0) or 0.0,
        v_tilt_deg=_parse_float(payload.get("v_tilt_deg"), "v_tilt_deg", default=0.0) or 0.0,
        v_level_amp=_parse_float(payload.get("v_level_amp"), "v_level_amp", default=1.0) or 1.0,
        v_norm_mode=_normalise_mode(payload.get("v_norm_mode"), "vertical"),
        h_count=h_count,
        h_spacing_m=_parse_float(payload.get("h_spacing_m"), "h_spacing_m", default=0.0) or 0.0,
        h_beta_deg=_parse_float(payload.get("h_beta_deg"), "h_beta_deg", default=0.0) or 0.0,
        h_step_deg=_parse_float(payload.get("h_step_deg"), "h_step_deg", default=0.0) or 0.0,
        h_level_amp=_parse_float(payload.get("h_level_amp"), "h_level_amp", default=1.0) or 1.0,
        h_norm_mode=_normalise_mode(payload.get("h_norm_mode"), "horizontal"),
        notes=_optional_str(payload.get("notes")),
    )
    project.cable = cable
    project.v_beta_deg = vertical_beta_deg(project.frequency_mhz, project.v_spacing_m or 0.0, project.v_tilt_deg or 0.0)
    project.feeder_loss_db = total_feeder_loss(
        project.cable_length_m,
        project.frequency_mhz,
        project.cable_reference,
        project.splitter_loss_db,
        project.connector_loss_db,
    )
    return project


def _update_project_from_payload(project: Project, payload: dict) -> None:
    recompute_vertical = False
    recompute_feeder = False

    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            abort(400, description="Campo name e obrigatorio.")
        project.name = name
    if "antenna_id" in payload:
        project.antenna = _resolve_antenna(payload.get("antenna_id"))
        project.antenna_id = project.antenna.id
    if "frequency_mhz" in payload:
        project.frequency_mhz = _parse_float(payload.get("frequency_mhz"), "frequency_mhz", required=True)
        recompute_vertical = True
        recompute_feeder = True
    for field in ("tx_power_w", "tower_height_m"):
        if field in payload:
            setattr(project, field, _parse_float(payload.get(field), field, required=True))
    if "cable_id" in payload:
        cable = _resolve_cable(payload.get("cable_id"))
        project.cable = cable
        project.cable_type = cable.model_code if cable else None
        recompute_feeder = True
    if "cable_type" in payload and "cable_id" not in payload:
        project.cable_type = _optional_str(payload.get("cable_type"))
        if project.cable_id:
            project.cable = None
        recompute_feeder = True
    if "notes" in payload:
        project.notes = _optional_str(payload.get("notes"))
    for field in ("cable_length_m", "splitter_loss_db", "connector_loss_db"):
        if field in payload:
            setattr(project, field, _parse_float(payload.get(field), field, default=0.0) or 0.0)
            recompute_feeder = True
    if "vswr_target" in payload:
        project.vswr_target = _parse_float(payload.get("vswr_target"), "vswr_target", default=1.5) or 1.5
    if "v_count" in payload:
        project.v_count = _parse_int(payload.get("v_count"), "v_count", required=True)
    if "v_spacing_m" in payload:
        project.v_spacing_m = _parse_float(payload.get("v_spacing_m"), "v_spacing_m", default=0.0) or 0.0
        recompute_vertical = True
    if "v_tilt_deg" in payload:
        project.v_tilt_deg = _parse_float(payload.get("v_tilt_deg"), "v_tilt_deg", default=0.0) or 0.0
        recompute_vertical = True
    if "v_level_amp" in payload:
        project.v_level_amp = _parse_float(payload.get("v_level_amp"), "v_level_amp", default=1.0) or 1.0
    if "v_norm_mode" in payload:
        project.v_norm_mode = _normalise_mode(payload.get("v_norm_mode"), "vertical")
    if "h_count" in payload:
        project.h_count = _parse_int(payload.get("h_count"), "h_count", required=True)
    if "h_spacing_m" in payload:
        project.h_spacing_m = _parse_float(payload.get("h_spacing_m"), "h_spacing_m", default=0.0) or 0.0
    if "h_beta_deg" in payload:
        project.h_beta_deg = _parse_float(payload.get("h_beta_deg"), "h_beta_deg", default=0.0) or 0.0
    if "h_step_deg" in payload:
        project.h_step_deg = _parse_float(payload.get("h_step_deg"), "h_step_deg", default=0.0) or 0.0
    if "h_level_amp" in payload:
        value = _parse_float(payload.get("h_level_amp"), "h_level_amp", default=1.0)
        project.h_level_amp = value if value is not None else 1.0
    if "h_norm_mode" in payload:
        project.h_norm_mode = _normalise_mode(payload.get("h_norm_mode"), "horizontal")

    if recompute_vertical:
        project.v_beta_deg = vertical_beta_deg(project.frequency_mhz, project.v_spacing_m or 0.0, project.v_tilt_deg or 0.0)
    if recompute_feeder:
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_reference,
            project.splitter_loss_db,
            project.connector_loss_db,
        )


def _resolve_actor():
    if login_current_user.is_authenticated:
        return login_current_user
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        pass
    user = jwt_current_user
    if getattr(user, "id", None):
        return user
    abort(401, description="Autenticacao obrigatoria.")


@api_bp.route("/antennas", methods=["GET"])
@jwt_required()
@limiter.limit(api_limit)
def list_antennas():
    antennas = Antenna.query.order_by(Antenna.name).all()
    return jsonify([_antenna_to_dict(antenna) for antenna in antennas])


@api_bp.route("/antennas", methods=["POST"])
@jwt_required()
@limiter.limit(api_limit)
def create_antenna():
    _require_admin()
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        abort(400, description="Campo name e obrigatorio.")
    antenna = Antenna(
        name=name,
        model_number=_optional_str(payload.get("model_number")),
        description=_optional_str(payload.get("description")),
        nominal_gain_dbd=_parse_float(payload.get("nominal_gain_dbd"), "nominal_gain_dbd", default=0.0) or 0.0,
        polarization=_optional_str(payload.get("polarization")),
        frequency_min_mhz=_parse_float(payload.get("frequency_min_mhz"), "frequency_min_mhz"),
        frequency_max_mhz=_parse_float(payload.get("frequency_max_mhz"), "frequency_max_mhz"),
    )
    db.session.add(antenna)
    db.session.commit()
    return jsonify(_antenna_to_dict(antenna)), 201


@api_bp.route("/antennas/<uuid:antenna_id>", methods=["GET"])
@jwt_required()
@limiter.limit(api_limit)
def get_antenna(antenna_id):
    antenna = db.session.get(Antenna, antenna_id) or abort(404)
    return jsonify(_antenna_to_dict(antenna))


@api_bp.route("/antennas/<uuid:antenna_id>", methods=["PATCH", "PUT"])
@jwt_required()
@limiter.limit(api_limit)
def update_antenna(antenna_id):
    _require_admin()
    antenna = db.session.get(Antenna, antenna_id) or abort(404)
    payload = request.get_json(silent=True) or {}
    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            abort(400, description="Campo name e obrigatorio.")
        antenna.name = name
    if "model_number" in payload:
        antenna.model_number = _optional_str(payload.get("model_number"))
    if "description" in payload:
        antenna.description = _optional_str(payload.get("description"))
    if "nominal_gain_dbd" in payload:
        antenna.nominal_gain_dbd = _parse_float(payload.get("nominal_gain_dbd"), "nominal_gain_dbd", default=0.0) or 0.0
    if "polarization" in payload:
        antenna.polarization = _optional_str(payload.get("polarization"))
    if "frequency_min_mhz" in payload:
        antenna.frequency_min_mhz = _parse_float(payload.get("frequency_min_mhz"), "frequency_min_mhz")
    if "frequency_max_mhz" in payload:
        antenna.frequency_max_mhz = _parse_float(payload.get("frequency_max_mhz"), "frequency_max_mhz")
    db.session.commit()
    return jsonify(_antenna_to_dict(antenna))


@api_bp.route("/antennas/<uuid:antenna_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit(api_limit)
def delete_antenna(antenna_id):
    _require_admin()
    antenna = db.session.get(Antenna, antenna_id)
    if not antenna:
        abort(404)
    db.session.delete(antenna)
    db.session.commit()
    return jsonify({"status": "deleted"})


@api_bp.route("/projects", methods=["GET"])
@jwt_required()
@limiter.limit(api_limit)
def list_projects():
    projects = Project.query.filter_by(owner_id=jwt_current_user.id).order_by(Project.created_at.desc()).all()
    return jsonify([_project_to_dict(project, include_exports=False) for project in projects])


@api_bp.route("/projects", methods=["POST"])
@jwt_required()
@limiter.limit(api_limit)
def create_project():
    payload = request.get_json(silent=True) or {}
    project = _create_project_from_payload(payload)
    db.session.add(project)
    db.session.commit()
    return jsonify(_project_to_dict(project, include_exports=True)), 201


@api_bp.route("/projects/<uuid:project_id>", methods=["GET"])
@jwt_required()
@limiter.limit(api_limit)
def get_project(project_id):
    project = _get_project_for_user(project_id)
    include_query = (request.args.get("include") or "").split(",")
    include_exports = "exports" in include_query
    arrays, payload = get_composition(project, refresh="erp" in include_query)
    data = _project_to_dict(project, include_exports=include_exports)
    if "erp" in include_query:
        data["erp"] = _erp_payload(payload)
    return jsonify(data)


@api_bp.route("/projects/<uuid:project_id>", methods=["PATCH", "PUT"])
@jwt_required()
@limiter.limit(api_limit)
def update_project(project_id):
    project = _get_project_for_user(project_id)
    payload = request.get_json(silent=True) or {}
    if not payload:
        abort(400, description="Nenhuma alteracao informada.")
    _update_project_from_payload(project, payload)
    db.session.commit()
    return jsonify(_project_to_dict(project, include_exports=True))


@api_bp.route("/projects/<uuid:project_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit(api_limit)
def delete_project(project_id):
    project = _get_project_for_user(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"status": "deleted"})


@api_bp.route("/projects/<uuid:project_id>/export", methods=["POST"])
@jwt_required()
@limiter.limit(api_limit)
def export_project(project_id):
    project = _get_project_for_user(project_id)
    export_root = current_app.config.get("EXPORT_ROOT", "exports")
    export = generate_project_export(project, Path(export_root))
    return jsonify(_export_to_dict(export)), 201


@api_bp.route("/projects/<uuid:project_id>/exports", methods=["GET"])
@jwt_required()
@limiter.limit(api_limit)
def list_project_exports(project_id):
    project = _get_project_for_user(project_id)
    exports = sorted(project.revisions, key=lambda item: item.created_at or datetime.min, reverse=True)
    return jsonify([_export_to_dict(export) for export in exports])


@api_bp.route("/projects/<uuid:project_id>/patterns", methods=["POST"])
@jwt_required()
@limiter.limit(api_limit)
def project_patterns(project_id):
    project = _get_project_for_user(project_id)
    payload = request.get_json(silent=True) or {}
    mutable_fields = (
        "frequency_mhz",
        "tx_power_w",
        "cable_length_m",
        "splitter_loss_db",
        "connector_loss_db",
        "v_count",
        "v_spacing_m",
        "v_tilt_deg",
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
        project.v_tilt_deg = payload.get("v_tilt_deg", project.v_tilt_deg)
        project.v_beta_deg = vertical_beta_deg(project.frequency_mhz, project.v_spacing_m, project.v_tilt_deg)
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_reference,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
        arrays, payload = get_composition(project, refresh=True, store=False)
        data = payload
    finally:
        for field, value in originals.items():
            setattr(project, field, value)
        project.feeder_loss_db = originals.get("feeder_loss_db", project.feeder_loss_db)
    return jsonify(_erp_payload(data))


@api_bp.route("/assistant/conversation", methods=["GET"])
@jwt_required(optional=True)
@limiter.limit(api_limit)
def get_assistant_conversation():
    user = _resolve_actor()
    snapshot = snapshot_for(user)
    db.session.commit()
    return jsonify(_snapshot_to_dict(snapshot))


@api_bp.route("/assistant/message", methods=["POST"])
@jwt_required(optional=True)
@limiter.limit(api_limit)
@csrf.exempt
def post_assistant_message():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        current_app.logger.warning(
            "assistant.malformed_payload",
            extra={
                "payload": payload,
                "content_type": request.content_type,
            },
        )
        abort(400, description="Campo message e obrigatorio.")
    current_app.logger.debug(
        "assistant.request",
        extra={
            "payload": payload,
            "user_id": str(getattr(jwt_current_user, 'id', None) or getattr(login_current_user, 'id', None)),
        },
    )
    user = _resolve_actor()
    try:
        snapshot = send_assistant_message(user, message)
        db.session.commit()
    except AssistantServiceError as exc:
        db.session.rollback()
        abort(503, description=str(exc))
    except Exception:
        db.session.rollback()
        raise
    return jsonify(_snapshot_to_dict(snapshot)), 201
