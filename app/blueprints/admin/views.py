from __future__ import annotations

import json
from datetime import datetime
from functools import wraps
from uuid import UUID

import numpy as np
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy.inspection import inspect

from ...extensions import db
from ...forms.admin import AntennaForm, PatternUploadForm
from ...models import Antenna, AntennaPattern, PatternType, Project, ProjectExport, User
from ...services.pattern_composer import resample_pattern, resample_vertical
from ...services.pattern_parser import parse_pattern_bytes
from ...services.visuals import generate_pattern_previews


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


MANAGED_MODELS: dict[str, type] = {
    "users": User,
    "antennas": Antenna,
    "patterns": AntennaPattern,
    "projects": Project,
    "exports": ProjectExport,
}


def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Acesso restrito ao administrador.", "danger")
            return redirect(url_for("public.home"))
        return func(*args, **kwargs)

    return wrapper


@admin_bp.route("/")
@admin_required
def dashboard():
    pending_cnpj = User.query.filter(User.cnpj.isnot(None), User.cnpj_verified.is_(False)).all()
    antennas = Antenna.query.order_by(Antenna.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", pending_cnpj=pending_cnpj, antennas=antennas)


@admin_bp.route("/antennas")
@admin_required
def antennas_list():
    antennas = Antenna.query.order_by(Antenna.name).all()
    return render_template("admin/antennas_list.html", antennas=antennas)


@admin_bp.route("/antennas/new", methods=["GET", "POST"])
@admin_required
def antennas_create():
    form = AntennaForm()
    if form.validate_on_submit():
        antenna = Antenna(
            name=form.name.data,
            model_number=form.model_number.data or None,
            description=form.description.data or None,
            nominal_gain_dbd=form.nominal_gain_dbd.data or 0.0,
            polarization=form.polarization.data or None,
            frequency_min_mhz=form.frequency_min_mhz.data or None,
            frequency_max_mhz=form.frequency_max_mhz.data or None,
        )
        db.session.add(antenna)
        db.session.commit()
        flash("Antena criada.", "success")
        return redirect(url_for("admin.antennas_list"))
    return render_template("admin/antenna_form.html", form=form)


@admin_bp.route("/antennas/<uuid:antenna_id>/edit", methods=["GET", "POST"])
@admin_required
def antennas_edit(antenna_id):
    antenna = Antenna.query.get_or_404(antenna_id)
    form = AntennaForm(obj=antenna)
    if form.validate_on_submit():
        antenna.name = form.name.data
        antenna.model_number = form.model_number.data or None
        antenna.description = form.description.data or None
        antenna.nominal_gain_dbd = form.nominal_gain_dbd.data or 0.0
        antenna.polarization = form.polarization.data or None
        antenna.frequency_min_mhz = form.frequency_min_mhz.data or None
        antenna.frequency_max_mhz = form.frequency_max_mhz.data or None
        db.session.commit()
        flash("Antena atualizada.", "success")
        return redirect(url_for("admin.antennas_list"))
    return render_template("admin/antenna_form.html", form=form, antenna=antenna)


@admin_bp.route("/antennas/<uuid:antenna_id>/patterns", methods=["GET", "POST"])
@admin_required
def antennas_patterns(antenna_id):
    antenna = Antenna.query.get_or_404(antenna_id)
    form = PatternUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        raw_bytes = file.read()
        try:
            base_angles, base_values = parse_pattern_bytes(raw_bytes, getattr(file, "filename", None))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("admin.antennas_patterns", antenna_id=antenna.id))

        base_angles = np.asarray(base_angles, dtype=float)
        base_values = np.asarray(base_values, dtype=float)
        base_values = np.clip(base_values, 0.0, None)

        pattern_type = PatternType(form.pattern_type.data)
        if pattern_type is PatternType.HRP:
            resampled_angles, resampled_values = resample_pattern(base_angles, base_values, -180, 180, 1)
        else:
            resampled_angles, resampled_values = resample_vertical(base_angles, base_values)

        pattern = AntennaPattern.query.filter_by(antenna_id=antenna.id, pattern_type=pattern_type).first()
        if not pattern:
            pattern = AntennaPattern(antenna=antenna, pattern_type=pattern_type)

        pattern.angles_deg = np.asarray(resampled_angles, dtype=float).tolist()
        pattern.amplitudes_linear = np.asarray(resampled_values, dtype=float).tolist()
        db.session.add(pattern)
        db.session.commit()
        flash("Padrao importado com sucesso.", "success")
        return redirect(url_for("admin.antennas_patterns", antenna_id=antenna.id))

    pattern_previews = generate_pattern_previews(antenna)
    return render_template("admin/patterns.html", antenna=antenna, form=form, pattern_previews=pattern_previews)


@admin_bp.route("/users/<uuid:user_id>/toggle-cnpj")
@admin_required
def toggle_cnpj(user_id):
    user = db.session.get(User, UUID(str(user_id)))
    if not user:
        flash("Usuario nao encontrado.", "danger")
    else:
        user.cnpj_verified = not user.cnpj_verified
        db.session.commit()
        flash("Status atualizado.", "success")
    return redirect(url_for("admin.dashboard"))


# --------------------- Data manager ---------------------


def _get_model(model_name: str) -> type:
    model = MANAGED_MODELS.get(model_name)
    if not model:
        abort(404)
    return model


def _primary_key(model: type):
    mapper = inspect(model)
    return mapper.primary_key[0]


def _coerce_value(raw: str, column) -> object:
    if raw == "":
        return None
    if column.type.__class__.__name__.lower().startswith("json"):
        return json.loads(raw)
    python_type = getattr(column.type, "python_type", str)
    try:
        if python_type is bool:
            return raw.lower() in {"1", "true", "on", "sim", "yes"}
        if python_type is int:
            return int(raw)
        if python_type is float:
            return float(raw)
        if python_type.__name__ == "datetime":
            return datetime.fromisoformat(raw)
    except Exception as exc:
        raise ValueError(f"{exc}") from exc
    return raw


def _serialise_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


@admin_bp.route("/data")
@admin_required
def data_index():
    return render_template("admin/data/index.html", models=MANAGED_MODELS)


@admin_bp.route("/data/<model_name>")
@admin_required
def data_list(model_name):
    model = _get_model(model_name)
    mapper = inspect(model)
    columns = [column.key for column in mapper.columns]
    pk_column = _primary_key(model)
    items = model.query.order_by(pk_column).limit(100).all()
    rows = []
    for item in items:
        values = {col: _serialise_value(getattr(item, col)) for col in columns}
        rows.append({"values": values, "pk": str(getattr(item, pk_column.key))})
    return render_template(
        "admin/data/list.html",
        model_name=model_name,
        columns=columns,
        rows=rows,
    )


@admin_bp.route("/data/<model_name>/<uuid:record_id>", methods=["GET", "POST"])
@admin_required
def data_edit(model_name, record_id):
    model = _get_model(model_name)
    mapper = inspect(model)
    pk_column = _primary_key(model)
    record = model.query.get_or_404(record_id)
    if request.method == "POST":
        errors: list[str] = []
        for column in mapper.columns:
            if column.primary_key:
                continue
            field = column.key
            raw_value = request.form.get(field, "")
            if raw_value == "" and column.nullable:
                setattr(record, field, None)
                continue
            try:
                value = _coerce_value(raw_value, column)
            except ValueError as exc:
                errors.append(f"Campo {field}: {exc}")
                continue
            setattr(record, field, value)
        if errors:
            for message in errors:
                flash(message, "danger")
        else:
            db.session.commit()
            flash("Registro atualizado com sucesso.", "success")
            return redirect(url_for("admin.data_edit", model_name=model_name, record_id=record_id))
    field_values = {
        column.key: _serialise_value(getattr(record, column.key))
        for column in mapper.columns
    }
    return render_template(
        "admin/data/edit.html",
        model_name=model_name,
        columns=mapper.columns,
        values=field_values,
        pk_name=pk_column.key,
        record=record,
        csrf_token=generate_csrf(),
    )