from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from flask import Blueprint, current_app, flash, redirect, render_template, url_for, abort, send_from_directory, request
from flask_login import current_user, login_required

from ...extensions import db
from ...forms.project import ProjectForm
from ...models import Antenna, Project, ProjectExport
from ...services.exporters import generate_project_export
from ...services.pattern_composer import compute_erp
from ...utils.calculations import total_feeder_loss, vertical_beta_deg


projects_bp = Blueprint("projects", __name__, url_prefix="/projects")




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

@projects_bp.route("/dashboard")
@login_required
def dashboard():
    projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.created_at.desc()).all()
    return render_template("projects/dashboard.html", projects=projects)


@projects_bp.route("/<uuid:project_id>")
@login_required
def detail(project_id):
    project = Project.query.filter_by(id=project_id, owner_id=current_user.id).first_or_404()
    data = compute_erp(project)
    data_payload = {k: v.tolist() if hasattr(v, "tolist") else v for k, v in data.items()}
    return render_template("projects/detail.html", project=project, data=data, data_payload=data_payload)


@projects_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = ProjectForm()
    form.antenna_id.choices = [(str(a.id), a.name) for a in Antenna.query.order_by(Antenna.name).all()]

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

        project = Project(
            owner=current_user,
            antenna=antenna,
            name=form.name.data,
            frequency_mhz=form.frequency_mhz.data,
            tx_power_w=form.tx_power_w.data,
            tower_height_m=form.tower_height_m.data,
            cable_type=form.cable_type.data or None,
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
        _apply_vertical_tilt(project)
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_type,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
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
    form.antenna_id.data = str(project.antenna_id)

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

        project.name = form.name.data
        project.antenna = antenna
        project.frequency_mhz = form.frequency_mhz.data
        project.tx_power_w = form.tx_power_w.data
        project.tower_height_m = form.tower_height_m.data
        project.cable_type = form.cable_type.data or None
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
        _apply_vertical_tilt(project)
        project.feeder_loss_db = total_feeder_loss(
            project.cable_length_m,
            project.frequency_mhz,
            project.cable_type,
            project.splitter_loss_db,
            project.connector_loss_db,
        )
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
    generate_project_export(project, export_root)
    flash("Arquivos gerados!", "success")
    return redirect(url_for("projects.detail", project_id=project.id))

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
