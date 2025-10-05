from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from uuid import UUID

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from ...extensions import db
from ...forms.project import ProjectForm
from ...models import Antenna, Cable, Project, ProjectExport
from ...services.exporters import generate_project_export
from ...services.pattern_composer import get_composition
from ...services.visuals import generate_project_previews
from ...utils.calculations import total_feeder_loss, vertical_beta_deg


projects_bp = Blueprint("projects", __name__, url_prefix="/projects")


def _cable_label(cable: Cable) -> str:
    parts: list[str] = [cable.display_name]
    extras: list[str] = []
    if cable.size_inch:
        extras.append(cable.size_inch)
    if cable.model_code and cable.model_code not in {cable.display_name, *(extras or [])}:
        extras.append(cable.model_code)
    if cable.manufacturer:
        extras.append(cable.manufacturer)
    if extras:
        parts.append(f"({' / '.join(extras)})")
    return " ".join(parts)


def _cable_choices() -> list[tuple[str, str]]:
    choices: list[tuple[str, str]] = [("", "-- Selecionar cabo --")]
    for cable in Cable.query.order_by(Cable.display_name.asc()).all():
        choices.append((str(cable.id), _cable_label(cable)))
    return choices



def _apply_vertical_tilt(project: Project) -> None:
    project.v_tilt_deg = project.v_tilt_deg or 0.0
    spacing = project.v_spacing_m or 0.0
    project.v_beta_deg = vertical_beta_deg(project.frequency_mhz, spacing, project.v_tilt_deg)


def _populate_vertical_beta_from_form(form, fallback: Project | None = None) -> None:
    def _value(field, default=0.0):
        try:
            data = field.data
        except AttributeError:
            data = default
        if data in (None, ""):
            return default
        return data

    fallback_freq = getattr(fallback, "frequency_mhz", 0.0) if fallback else 0.0
    fallback_spacing = getattr(fallback, "v_spacing_m", 0.0) if fallback else 0.0
    fallback_tilt = getattr(fallback, "v_tilt_deg", 0.0) if fallback else 0.0
    freq = _value(form.frequency_mhz, fallback_freq)
    spacing = _value(form.v_spacing_m, fallback_spacing)
    tilt = _value(form.v_tilt_deg, fallback_tilt)
    form.v_beta_deg.data = vertical_beta_deg(freq or 0.0, spacing or 0.0, tilt or 0.0)


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return value or "export"


@projects_bp.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template("projects/dashboard.html", projects=projects)


@projects_bp.route("/<uuid:project_id>")
@login_required
def detail(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    composition_arrays, composition_payload = get_composition(project, refresh=True)
    erp_rows = [
        (
            int(angle % 360),
            float(erp_w),
            float(erp_dbw),
        )
        for angle, erp_w, erp_dbw in zip(
            composition_arrays.get("angles_deg", []),
            composition_arrays.get("erp_w", []),
            composition_arrays.get("erp_dbw", []),
        )
    ]
    previews = generate_project_previews(project, composition=composition_arrays)
    latest_export = None
    latest_files = {}
    calibrated_gain = None
    if project.revisions:
        latest_export = max(project.revisions, key=lambda exp: exp.created_at or datetime.min)
        latest_files = {
            "pdf": url_for("projects.download", project_id=project.id, export_id=latest_export.id, file_type="pdf"),
            "pat": url_for("projects.download", project_id=project.id, export_id=latest_export.id, file_type="pat"),
            "prn": url_for("projects.download", project_id=project.id, export_id=latest_export.id, file_type="prn"),
            "bundle": url_for("projects.download_bundle", project_id=project.id, export_id=latest_export.id),
            "comp_v": url_for("projects.view_asset", project_id=project.id, export_id=latest_export.id, name="composicao_vertical.png"),
            "comp_h": url_for("projects.view_asset", project_id=project.id, export_id=latest_export.id, name="composicao_horizontal.png"),
        }
        try:
            calibrated_gain = float((latest_export.erp_metadata or {}).get("metrics", {}).get("gain_dbi"))
        except Exception:
            calibrated_gain = None
    return render_template(
        "projects/detail.html",
        project=project,
        data=composition_arrays,
        data_payload=composition_payload,
        erp_rows=erp_rows,
        previews=previews,
        latest_export=latest_export,
        latest_files=latest_files,
        calibrated_gain=calibrated_gain,
    )


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ProjectForm()
    form.antenna_id.choices = [(str(a.id), a.name) for a in Antenna.query.order_by(Antenna.name).all()]
    form.cable_id.choices = _cable_choices()

    if form.validate_on_submit():
        try:
            antenna_uuid = UUID(form.antenna_id.data)
        except (ValueError, TypeError):
            form.antenna_id.errors.append("Antena invalida.")
            _populate_vertical_beta_from_form(form)
            return render_template("projects/form.html", form=form, login_url=url_for("auth.login"))

        antenna = db.session.get(Antenna, antenna_uuid)
        if not antenna:
            form.antenna_id.errors.append("Antena invalida.")
            _populate_vertical_beta_from_form(form)
            return render_template("projects/form.html", form=form, login_url=url_for("auth.login"))

        cable = None
        if form.cable_id.data:
            try:
                cable_uuid = UUID(form.cable_id.data)
            except (ValueError, TypeError):
                form.cable_id.errors.append("Cabo inválido.")
                _populate_vertical_beta_from_form(form)
                return render_template("projects/form.html", form=form, login_url=url_for("auth.login"))

            cable = db.session.get(Cable, cable_uuid)
            if not cable:
                form.cable_id.errors.append("Cabo inválido.")
                _populate_vertical_beta_from_form(form)
                return render_template("projects/form.html", form=form, login_url=url_for("auth.login"))

        project = Project(
            owner=current_user,
            name=form.name.data,
            frequency_mhz=form.frequency_mhz.data,
            tx_power_w=form.tx_power_w.data,
            tower_height_m=form.tower_height_m.data,
            cable_id=cable.id if cable else None,
            cable_type=cable.model_code if cable else None,
            cable_length_m=form.cable_length_m.data or 0.0,
            splitter_loss_db=form.splitter_loss_db.data or 0.0,
            connector_loss_db=form.connector_loss_db.data or 0.0,
            vswr_target=form.vswr_target.data or 1.5,
            v_count=form.v_count.data,
            v_spacing_m=form.v_spacing_m.data or 0.0,
            v_tilt_deg=form.v_tilt_deg.data or 0.0,
            v_beta_deg=form.v_beta_deg.data or 0.0,
            v_level_amp=form.v_level_amp.data or 1.0,
            v_norm_mode=form.v_norm_mode.data,
            h_count=form.h_count.data,
            h_spacing_m=form.h_spacing_m.data or 0.0,
            h_beta_deg=form.h_beta_deg.data or 0.0,
            h_step_deg=form.h_step_deg.data or 0.0,
            h_level_amp=form.h_level_amp.data or 1.0,
            h_norm_mode=form.h_norm_mode.data,
            notes=form.notes.data,
        )
        project.antenna = antenna
        project.cable = cable
        _apply_vertical_tilt(project)
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_reference,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
        get_composition(project, refresh=True)
        db.session.add(project)
        db.session.commit()
        flash("Projeto criado!", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    if request.method == "POST":
        _populate_vertical_beta_from_form(form)
    else:
        _populate_vertical_beta_from_form(form)
    return render_template("projects/form.html", form=form)


@projects_bp.route("/<uuid:project_id>/edit", methods=["GET", "POST"])
@login_required
def edit(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    form = ProjectForm(obj=project)
    form.antenna_id.choices = [(str(a.id), a.name) for a in Antenna.query.order_by(Antenna.name).all()]
    form.cable_id.choices = _cable_choices()
    primary_link = project.primary_antenna_link
    form.antenna_id.data = str(primary_link.antenna_id) if primary_link else (form.antenna_id.data or None)
    form.cable_id.data = str(project.cable_id) if project.cable_id else ""

    if form.validate_on_submit():
        try:
            antenna_uuid = UUID(form.antenna_id.data)
        except (ValueError, TypeError):
            form.antenna_id.errors.append("Antena invalida.")
            _populate_vertical_beta_from_form(form, project)
            return render_template("projects/form.html", form=form, project=project)

        antenna = db.session.get(Antenna, antenna_uuid)
        if not antenna:
            form.antenna_id.errors.append("Antena invalida.")
            _populate_vertical_beta_from_form(form, project)
            return render_template("projects/form.html", form=form, project=project)

        cable = None
        selected_cable_id = form.cable_id.data or ""
        if selected_cable_id:
            try:
                cable_uuid = UUID(selected_cable_id)
            except (ValueError, TypeError):
                form.cable_id.errors.append("Cabo inválido.")
                _populate_vertical_beta_from_form(form, project)
                return render_template("projects/form.html", form=form, project=project)

            cable = db.session.get(Cable, cable_uuid)
            if not cable:
                form.cable_id.errors.append("Cabo inválido.")
                _populate_vertical_beta_from_form(form, project)
                return render_template("projects/form.html", form=form, project=project)
        else:
            if project.cable_id:
                project.cable = None
                project.cable_type = None

        project.name = form.name.data
        project.antenna = antenna
        project.frequency_mhz = form.frequency_mhz.data
        project.tx_power_w = form.tx_power_w.data
        project.tower_height_m = form.tower_height_m.data
        if cable:
            project.cable = cable
            project.cable_type = cable.model_code
        project.cable_length_m = form.cable_length_m.data or 0.0
        project.splitter_loss_db = form.splitter_loss_db.data or 0.0
        project.connector_loss_db = form.connector_loss_db.data or 0.0
        project.vswr_target = form.vswr_target.data or 1.5
        project.v_count = form.v_count.data
        project.v_spacing_m = form.v_spacing_m.data or 0.0
        project.v_tilt_deg = form.v_tilt_deg.data or 0.0
        project.v_beta_deg = form.v_beta_deg.data or 0.0
        project.v_level_amp = form.v_level_amp.data or 1.0
        project.v_norm_mode = form.v_norm_mode.data
        project.h_count = form.h_count.data
        project.h_spacing_m = form.h_spacing_m.data or 0.0
        project.h_beta_deg = form.h_beta_deg.data or 0.0
        project.h_step_deg = form.h_step_deg.data or 0.0
        project.h_level_amp = form.h_level_amp.data or 1.0
        project.h_norm_mode = form.h_norm_mode.data
        project.notes = form.notes.data
        project.antenna = antenna
        _apply_vertical_tilt(project)
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_reference,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
        get_composition(project, refresh=True)
        db.session.commit()
        flash("Projeto atualizado.", "success")
        return redirect(url_for("projects.detail", project_id=project.id))

    if request.method == "POST":
        _populate_vertical_beta_from_form(form, project)
    else:
        form.v_tilt_deg.data = project.v_tilt_deg or 0.0
        form.v_beta_deg.data = project.v_beta_deg or 0.0
    return render_template("projects/form.html", form=form, project=project)


@projects_bp.route("/<uuid:project_id>/export")
@login_required
def export(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    export_root = Path(current_app.config.get("EXPORT_ROOT", "exports"))
    export, paths = generate_project_export(project, export_root)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(paths.pdf, arcname=paths.pdf.name)
        zf.write(paths.pat, arcname=paths.pat.name)
        zf.write(paths.prn, arcname=paths.prn.name)
    zip_buffer.seek(0)

    safe_name = _slugify(project.name)
    download_name = f"{safe_name}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=download_name)


@projects_bp.route("/<uuid:project_id>/download/<uuid:export_id>/<file_type>")
@login_required
def download(project_id, export_id, file_type):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    export = ProjectExport.query.filter_by(id=export_id, project_id=project.id).first_or_404()
    file_map = {
        "pat": export.pat_path,
        "prn": export.prn_path,
        "pdf": export.pdf_path,
    }
    if file_type not in file_map:
        abort(404)
    path = Path(file_map[file_type])
    export_root = Path(current_app.config.get("EXPORT_ROOT", "exports")).resolve()
    if not path.is_absolute():
        path = (export_root / path).resolve()
    else:
        path = path.resolve()
    if export_root not in path.parents and path != export_root:
        abort(403)
    if not path.exists():
        abort(404)
    return send_from_directory(path.parent, path.name, as_attachment=True)


@projects_bp.route("/<uuid:project_id>/download/<uuid:export_id>/bundle")
@login_required
def download_bundle(project_id, export_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    export = ProjectExport.query.filter_by(id=export_id, project_id=project.id).first_or_404()
    export_root = Path(current_app.config.get("EXPORT_ROOT", "exports")).resolve()

    def _resolve(relative: str) -> Path:
        p = Path(relative)
        return (export_root / p).resolve() if not p.is_absolute() else p.resolve()

    files = [
        _resolve(export.pdf_path),
        _resolve(export.pat_path),
        _resolve(export.prn_path),
    ]
    for file_path in files:
        if export_root not in file_path.parents and file_path != export_root:
            abort(403)
        if not file_path.exists():
            abort(404)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            zf.write(file_path, arcname=file_path.name)
    zip_buffer.seek(0)

    safe_name = _slugify(f"{project.name}-{export.created_at.strftime('%Y%m%d-%H%M%S') if export.created_at else 'export'}")
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=f"{safe_name}.zip")


@projects_bp.route("/<uuid:project_id>/asset/<uuid:export_id>/<path:name>")
@login_required
def view_asset(project_id, export_id, name):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    export = ProjectExport.query.filter_by(id=export_id, project_id=project.id).first_or_404()
    allowed = {"composicao_vertical.png", "composicao_horizontal.png"}
    if name not in allowed:
        abort(404)
    export_root = Path(current_app.config.get("EXPORT_ROOT", "exports")).resolve()
    base_dir = Path(export.pdf_path).parent if export.pdf_path else None
    if not base_dir:
        abort(404)
    path = (export_root / base_dir / name).resolve()
    if export_root not in path.parents:
        abort(403)
    if not path.exists():
        abort(404)
    from flask import request
    download = request.args.get("download") in {"1", "true", "yes"}
    return send_from_directory(path.parent, path.name, as_attachment=download)
