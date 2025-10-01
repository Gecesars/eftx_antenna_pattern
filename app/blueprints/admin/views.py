from __future__ import annotations

import csv
from functools import wraps
from io import StringIO
from uuid import UUID

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...extensions import db
from ...forms.admin import AntennaForm, PatternUploadForm
from ...models import Antenna, AntennaPattern, PatternType, User
from ...services.pattern_composer import resample_pattern, resample_vertical


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


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
        raw = file.read().decode("utf-8")
        sample = raw[:1024]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.get_dialect("excel")
        reader = csv.reader(StringIO(raw), dialect)
        angles, amplitudes = [], []
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            try:
                angle = float(row[0])
                amp = float(row[1])
            except (ValueError, IndexError):
                continue
            angles.append(angle)
            amplitudes.append(max(amp, 0.0))
        if not angles:
            flash("Nenhum dado reconhecido.", "danger")
            return redirect(url_for("admin.antennas_patterns", antenna_id=antenna.id))
        pattern_type = PatternType(form.pattern_type.data)
        if pattern_type is PatternType.HRP:
            resampled_angles, resampled_amp = resample_pattern(angles, amplitudes, -180, 180, 1)
        else:
            resampled_angles, resampled_amp = resample_vertical(angles, amplitudes)
        pattern = AntennaPattern.query.filter_by(antenna_id=antenna.id, pattern_type=pattern_type).first()
        if not pattern:
            pattern = AntennaPattern(antenna=antenna, pattern_type=pattern_type)
        pattern.angles_deg = resampled_angles.tolist()
        pattern.amplitudes_linear = resampled_amp.tolist()
        db.session.add(pattern)
        db.session.commit()
        flash("Padrão importado com sucesso.", "success")
        return redirect(url_for("admin.antennas_patterns", antenna_id=antenna.id))
    pattern_previews = [
        {"id": str(p.id), "type": p.pattern_type.value, "angles": p.angles_deg, "values": p.amplitudes_linear}
        for p in sorted(antenna.patterns, key=lambda item: item.pattern_type.value)
    ]

    return render_template("admin/patterns.html", antenna=antenna, form=form, pattern_previews=pattern_previews)


@admin_bp.route("/users/<uuid:user_id>/toggle-cnpj")
@admin_required
def toggle_cnpj(user_id):
    user = db.session.get(User, UUID(str(user_id)))
    if not user:
        flash("Usuário não encontrado.", "danger")
    else:
        user.cnpj_verified = not user.cnpj_verified
        db.session.commit()
        flash("Status atualizado.", "success")
    return redirect(url_for("admin.dashboard"))



