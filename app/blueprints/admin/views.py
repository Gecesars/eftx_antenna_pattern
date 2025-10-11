from __future__ import annotations

import json
from datetime import datetime
import numbers
from decimal import Decimal
from functools import wraps
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from flask_wtf.csrf import generate_csrf
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from ...core import discover_site_root, list_pdfs_from_docs, load_products_from_site
from ...extensions import db, csrf
from ...forms.admin import AntennaForm, CableForm, PatternUploadForm
from ...models import (
    Antenna,
    AntennaPattern,
    AntennaPatternPoint,
    Cable,
    PatternType,
    Project,
    ProjectAntenna,
    ProjectExport,
    SiteContentBlock,
    SiteDocument,
    User,
)
from ..public_site.views import DEFAULT_HERO_PROMOS, DEFAULT_HIGHLIGHTS, DEFAULT_FAQ
from ...services.pattern_composer import resample_pattern, resample_vertical
from ...services.pattern_parser import parse_pattern_bytes
from ...services.cable_extractor import extract_cable_from_datasheet
from ...services.antenna_extractor import extract_antenna_from_datasheet
from ...services.visuals import generate_pattern_previews


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


MANAGED_MODELS: dict[str, type] = {
    "users": User,
    "antennas": Antenna,
    "patterns": AntennaPattern,
    "projects": Project,
    "exports": ProjectExport,
    "cabos": Cable,
}

MEDIA_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
DOCUMENT_EXTENSIONS = {"pdf"}


def _project_root_path() -> Path:
    configured = current_app.config.get("PROJECT_ROOT")
    if configured:
        return Path(configured)
    return Path(current_app.root_path).parent


def _site_upload_root() -> Path:
    base = _project_root_path()
    folder = current_app.config.get("SITE_UPLOAD_ROOT", "site_uploads")
    root = base / folder
    root.mkdir(parents=True, exist_ok=True)
    return root


def _docs_root_path() -> Path:
    docs_root = _project_root_path() / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)
    return docs_root


def _resolve_media_path(path: str | None) -> str | None:
    if not path:
        return None
    if path.startswith(("http://", "https://", "/")):
        return path
    return url_for("public_site.site_asset", filename=path)


def _upsert_block(slug: str, data, *, label: str | None = None) -> SiteContentBlock:
    block = SiteContentBlock.query.filter_by(slug=slug).first()
    if block is None:
        block = SiteContentBlock(slug=slug, label=label)
        db.session.add(block)
    block.data = data
    if label is not None:
        block.label = label
    db.session.commit()
    return block


def _get_block(slug: str, default=None):
    try:
        block = SiteContentBlock.query.filter_by(slug=slug).first()
    except Exception:
        return default
    if block and block.data is not None:
        return block.data
    return default


def _store_image(file, *, section: str = "general") -> str:
    if file is None or not file.filename:
        raise ValueError("Nenhum arquivo enviado")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in MEDIA_EXTENSIONS:
        raise ValueError("Formato de imagem não suportado")
    filename = secure_filename(f"{uuid4().hex}.{ext}")
    target_dir = _site_upload_root() / "images" / section
    target_dir.mkdir(parents=True, exist_ok=True)
    file.save(target_dir / filename)
    return f"uploads/images/{section}/{filename}"


def _store_document(file) -> str:
    if file is None or not file.filename:
        raise ValueError("Nenhum arquivo enviado")
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in DOCUMENT_EXTENSIONS:
        raise ValueError("Somente arquivos PDF são permitidos")
    filename = secure_filename(file.filename)
    docs_root = _docs_root_path()
    destination = docs_root / filename
    counter = 1
    while destination.exists():
        name_without_ext = destination.stem
        destination = docs_root / f"{name_without_ext}_{counter}.{ext}"
        filename = destination.name
        counter += 1
    file.save(destination)
    return filename


def _documents_meta_map() -> dict[str, SiteDocument]:
    meta_map: dict[str, SiteDocument] = {}
    try:
        documents = SiteDocument.query.all()
    except Exception:
        return meta_map
    for doc in documents:
        meta_map[(doc.filename or "").lower()] = doc
    return meta_map


def _serialize_document_entry(item: dict, doc_meta: SiteDocument | None) -> dict:
    filename = (item.get("filename") or "").lower()
    display_name = item.get("name")
    description = item.get("description")
    category = item.get("category")
    metadata = {}
    doc_id = None
    is_featured = False
    thumbnail_path = None
    thumbnail_url = None
    if doc_meta:
        doc_id = str(doc_meta.id)
        if doc_meta.display_name:
            display_name = doc_meta.display_name
        if doc_meta.description:
            description = doc_meta.description
        if doc_meta.category:
            category = doc_meta.category
        if doc_meta.metadata_json:
            metadata = doc_meta.metadata_json
        if doc_meta.thumbnail_path:
            thumbnail_path = doc_meta.thumbnail_path
            thumbnail_url = _resolve_media_path(doc_meta.thumbnail_path)
        is_featured = bool(doc_meta.is_featured)

    return {
        **item,
        "id": doc_id,
        "filename": item.get("filename"),
        "display_name": display_name,
        "description": description,
        "category": category,
        "metadata": metadata,
        "thumbnail_path": thumbnail_path,
        "thumbnail_url": thumbnail_url,
        "is_featured": is_featured,
        "download_url": url_for("public_site.download_file", filename=item["path_rel"]),
    }


def _serialize_documents() -> list[dict]:
    docs_root = _docs_root_path()
    base_items = list_pdfs_from_docs(docs_root)
    meta_map = _documents_meta_map()
    return [
        _serialize_document_entry(item, meta_map.get((item.get("filename") or "").lower()))
        for item in base_items
    ]



def _json_payload() -> dict:
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}



def _apply_document_payload(doc: SiteDocument, payload: dict) -> None:
    if "display_name" in payload:
        value = payload.get("display_name")
        doc.display_name = value.strip() if isinstance(value, str) and value.strip() else None
    if "category" in payload:
        value = payload.get("category")
        doc.category = value.strip() if isinstance(value, str) and value.strip() else None
    if "description" in payload:
        value = payload.get("description")
        doc.description = value.strip() if isinstance(value, str) and value.strip() else None
    if "thumbnail_path" in payload:
        value = payload.get("thumbnail_path")
        doc.thumbnail_path = value.strip() if isinstance(value, str) and value.strip() else None
    if "is_featured" in payload:
        doc.is_featured = bool(payload.get("is_featured"))
    if "metadata" in payload and isinstance(payload.get("metadata"), dict):
        doc.metadata_json = payload.get("metadata")
def _build_site_state() -> dict:
    site_root = discover_site_root()

    contacts_block = _get_block("contacts", {}) or {}
    hero_promos_block = _get_block("hero_promos", []) or []
    hero_images_block = _get_block("hero_images", []) or []
    highlights_block = _get_block("highlights", []) or []
    gallery_block = _get_block("gallery", []) or []
    faq_block = _get_block("faq", []) or []

    return {
        "blocks": {
            "contacts": contacts_block,
            "hero_promos": hero_promos_block,
            "hero_images": hero_images_block,
            "highlights": highlights_block,
            "gallery": gallery_block,
            "faq": faq_block,
        },
        "defaults": {
            "hero_promos": DEFAULT_HERO_PROMOS,
            "highlights": DEFAULT_HIGHLIGHTS,
            "faq": DEFAULT_FAQ,
        },
        "documents": _serialize_documents(),
        "preview": {
            "home": url_for("public_site.home"),
            "products": url_for("public_site.products"),
            "downloads": url_for("public_site.downloads"),
        },
        "site_root": str(site_root) if site_root else None,
        "csrf_token": generate_csrf(),
    }

def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Acesso restrito ao administrador.", "danger")
            return redirect(url_for("public_site.home"))
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


@admin_bp.route("/cables")
@admin_required
def cables_list():
    cables = Cable.query.order_by(Cable.display_name).all()
    return render_template("admin/cables_list.html", cables=cables)


@admin_bp.route("/site-designer")
@admin_required
def site_designer():
    state = _build_site_state()
    return render_template("admin/site_designer.html", state=state)


@admin_bp.route("/site-designer/state")
@admin_required
def site_designer_state():
    return jsonify(_build_site_state())


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
            manufacturer=(form.manufacturer.data or "EFTX Broadcast & Telecom"),
            datasheet_path=form.datasheet_path.data or None,
            category=form.category.data or None,
            thumbnail_path=form.thumbnail_path.data or None,
        )
        gain_raw = (form.gain_table.data or "").strip()
        if gain_raw:
            try:
                antenna.gain_table = json.loads(gain_raw)
            except Exception:
                flash("JSON de tabela de ganho inválido. Valor ignorado.", "warning")
        db.session.add(antenna)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Já existe uma antena com este nome. Ajuste o identificador antes de salvar.", "danger")
        else:
            flash("Antena criada.", "success")
            return redirect(url_for("admin.antennas_list"))
    return render_template("admin/antenna_form.html", form=form)


@admin_bp.route("/cables/new", methods=["GET", "POST"])
@admin_required
def cables_create():
    form = CableForm()
    if form.validate_on_submit():
        cable = Cable(
            display_name=form.display_name.data.strip(),
            model_code=form.model_code.data.strip(),
            size_inch=(form.size_inch.data or None),
            impedance_ohms=form.impedance_ohms.data or None,
            manufacturer=(form.manufacturer.data or None),
            notes=form.notes.data or None,
            datasheet_path=(form.datasheet_path.data or None),
            frequency_min_mhz=form.frequency_min_mhz.data or None,
            frequency_max_mhz=form.frequency_max_mhz.data or None,
            velocity_factor=form.velocity_factor.data or None,
            max_power_w=form.max_power_w.data or None,
            min_bend_radius_mm=form.min_bend_radius_mm.data or None,
            outer_diameter_mm=form.outer_diameter_mm.data or None,
            weight_kg_per_km=form.weight_kg_per_km.data or None,
            vswr_max=form.vswr_max.data or None,
            shielding_db=form.shielding_db.data or None,
            temperature_min_c=form.temperature_min_c.data or None,
            temperature_max_c=form.temperature_max_c.data or None,
            conductor_material=(form.conductor_material.data or None),
            dielectric_material=(form.dielectric_material.data or None),
            jacket_material=(form.jacket_material.data or None),
            shielding_type=(form.shielding_type.data or None),
            conductor_diameter_mm=form.conductor_diameter_mm.data or None,
            dielectric_diameter_mm=form.dielectric_diameter_mm.data or None,
        )
        # curva de atenuacao (JSON opcional)
        curve_raw = (form.attenuation_db_per_100m_curve.data or "").strip()
        if curve_raw:
            try:
                cable.attenuation_db_per_100m_curve = json.loads(curve_raw)
            except Exception:
                flash("Curva de atenuacao em JSON invalida. Valor ignorado.", "warning")
        db.session.add(cable)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Nao foi possivel salvar o cabo. Verifique se o codigo ja esta em uso.", "danger")
            return render_template("admin/cable_form.html", form=form)
        flash("Cabo cadastrado.", "success")
        return redirect(url_for("admin.cables_list"))
    return render_template("admin/cable_form.html", form=form)


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
        antenna.manufacturer = (form.manufacturer.data or "EFTX Broadcast & Telecom")
        antenna.datasheet_path = form.datasheet_path.data or None
        antenna.category = form.category.data or None
        antenna.thumbnail_path = form.thumbnail_path.data or None
        gain_raw = (form.gain_table.data or "").strip()
        if gain_raw:
            try:
                antenna.gain_table = json.loads(gain_raw)
            except Exception:
                flash("JSON de tabela de ganho inválido. Valor mantido anterior.", "warning")
        db.session.commit()
        flash("Antena atualizada.", "success")
        return redirect(url_for("admin.antennas_list"))
    # Preencher textarea com JSON formatado
    if request.method == "GET" and antenna.gain_table:
        try:
            form.gain_table.data = json.dumps(antenna.gain_table, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return render_template("admin/antenna_form.html", form=form, antenna=antenna)


@admin_bp.route("/cables/<uuid:cable_id>/edit", methods=["GET", "POST"])
@admin_required
def cables_edit(cable_id):
    cable = Cable.query.get_or_404(cable_id)
    form = CableForm(obj=cable)
    if form.validate_on_submit():
        cable.display_name = form.display_name.data.strip()
        cable.model_code = form.model_code.data.strip()
        cable.size_inch = form.size_inch.data or None
        cable.impedance_ohms = form.impedance_ohms.data or None
        cable.manufacturer = form.manufacturer.data or None
        cable.notes = form.notes.data or None
        cable.datasheet_path = form.datasheet_path.data or None
        cable.frequency_min_mhz = form.frequency_min_mhz.data or None
        cable.frequency_max_mhz = form.frequency_max_mhz.data or None
        cable.velocity_factor = form.velocity_factor.data or None
        cable.max_power_w = form.max_power_w.data or None
        cable.min_bend_radius_mm = form.min_bend_radius_mm.data or None
        cable.outer_diameter_mm = form.outer_diameter_mm.data or None
        cable.weight_kg_per_km = form.weight_kg_per_km.data or None
        cable.vswr_max = form.vswr_max.data or None
        cable.shielding_db = form.shielding_db.data or None
        cable.temperature_min_c = form.temperature_min_c.data or None
        cable.temperature_max_c = form.temperature_max_c.data or None
        cable.conductor_material = form.conductor_material.data or None
        cable.dielectric_material = form.dielectric_material.data or None
        cable.jacket_material = form.jacket_material.data or None
        cable.shielding_type = form.shielding_type.data or None
        cable.conductor_diameter_mm = form.conductor_diameter_mm.data or None
        cable.dielectric_diameter_mm = form.dielectric_diameter_mm.data or None
        curve_raw = (form.attenuation_db_per_100m_curve.data or "").strip()
        if curve_raw:
            try:
                cable.attenuation_db_per_100m_curve = json.loads(curve_raw)
            except Exception:
                flash("Curva de atenuacao em JSON invalida. Valor mantido anterior.", "warning")
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Nao foi possivel atualizar o cabo. Revise os dados informados.", "danger")
            return render_template("admin/cable_form.html", form=form, cable=cable)
        flash("Cabo atualizado.", "success")
        return redirect(url_for("admin.cables_list"))
    return render_template("admin/cable_form.html", form=form, cable=cable)


@admin_bp.route("/cables/parse-datasheet", methods=["POST"])
@admin_required
def cables_parse_datasheet():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Arquivo nao enviado."}), 400
    data = extract_cable_from_datasheet(file)
    status = 200 if "error" not in data else 500
    # inclui token CSRF para formularios dinâmicos
    data["csrf_token"] = generate_csrf()
    return jsonify(data), status


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
            db.session.add(pattern)
            db.session.flush()

        if pattern.id:
            AntennaPatternPoint.query.filter_by(pattern_id=pattern.id).delete(synchronize_session=False)

        angles_list = np.asarray(resampled_angles, dtype=float).tolist()
        values_list = np.asarray(resampled_values, dtype=float).tolist()
        pattern.replace_points(angles_list, values_list)
        pattern.metadata_json = {
            "angles_deg": angles_list,
            "amplitudes_linear": values_list,
            "imported_at": datetime.utcnow().isoformat(),
            "source": getattr(file, "filename", None),
        }
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


def _titleize(identifier: str) -> str:
    parts = [part for part in identifier.replace("_", " ").split(" ") if part]
    return " ".join(part.capitalize() for part in parts) or identifier

def _truncate(text: str, limit: int = 60) -> str:
    if len(text) <= limit:
        return text
    safe_limit = max(limit - 3, 1)
    return text[:safe_limit] + "..."


def _format_cell_value(value) -> dict:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, Decimal):
        value = float(value)

    cell = {
        "text": "",
        "title": None,
        "badge": None,
        "is_code": False,
        "is_json": False,
        "muted": False,
        "summary": None,
        "is_multiline": False,
    }

    if value is None:
        cell["text"] = "--"
        cell["muted"] = True
        return cell

    if isinstance(value, bool):
        cell["text"] = "Sim" if value else "Nao"
        cell["badge"] = "positive" if value else "neutral"
        return cell

    if isinstance(value, datetime):
        cell["text"] = value.isoformat(timespec="seconds")
        cell["is_code"] = True
        return cell

    if isinstance(value, UUID):
        cell["text"] = str(value)
        cell["is_code"] = True
        return cell

    if isinstance(value, (dict, list)):
        summary = json.dumps(value, ensure_ascii=False)
        cell["summary"] = _truncate(summary, 70)
        cell["text"] = json.dumps(value, ensure_ascii=False, indent=2)
        cell["is_json"] = True
        cell["is_multiline"] = True
        return cell

    if isinstance(value, numbers.Integral):
        cell["text"] = f"{value}"
        cell["is_code"] = True
        return cell

    if isinstance(value, numbers.Real):
        cell["text"] = f"{value:.4f}".rstrip("0").rstrip(".")
        cell["is_code"] = True
        return cell

    text = str(value)
    normalised = text.replace("\r\n", "\n")
    cell["is_multiline"] = "\n" in normalised
    limit = 120 if cell["is_multiline"] else 90
    truncated = _truncate(normalised, limit)
    cell["text"] = truncated
    if truncated != normalised:
        cell["title"] = normalised
    return cell


@admin_bp.route("/data")
@admin_required
def data_index():
    model_cards: list[dict[str, object]] = []
    for key, model in MANAGED_MODELS.items():
        mapper = inspect(model)
        model_cards.append(
            {
                "name": key,
                "label": _titleize(key),
                "count": model.query.count(),
                "columns": len(mapper.columns),
            }
        )
    model_cards.sort(key=lambda item: str(item["label"]))
    return render_template("admin/data/index.html", models=model_cards)


@admin_bp.route("/data/<model_name>")
@admin_required
def data_list(model_name):
    model = _get_model(model_name)
    mapper = inspect(model)
    columns = [
        {
            "key": column.key,
            "label": _titleize(column.key),
            "type_hint": column.type.__class__.__name__,
            "is_primary": column.primary_key,
        }
        for column in mapper.columns
    ]
    pk_column = _primary_key(model)
    limit = 100
    items = model.query.order_by(pk_column).limit(limit).all()
    total_count = model.query.count()
    rows = []
    for item in items:
        values = {}
        for column in mapper.columns:
            raw_value = getattr(item, column.key)
            cell = _format_cell_value(raw_value)
            cell["raw"] = _serialise_value(raw_value)
            values[column.key] = cell
        rows.append({"cells": values, "pk": str(getattr(item, pk_column.key))})
    return render_template(
        "admin/data/list.html",
        model_name=model_name,
        model_label=_titleize(model_name),
        columns=columns,
        rows=rows,
        total_count=total_count,
        limit=limit,
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
    form_fields: list[dict[str, object]] = []
    for column in mapper.columns:
        value = field_values.get(column.key, "")
        value_str = value or ""
        type_name = column.type.__class__.__name__
        prefer_textarea = (
            len(value_str) > 120
            or "\n" in value_str
            or type_name.lower().startswith("json")
        )
        form_fields.append(
            {
                "key": column.key,
                "label": _titleize(column.key),
                "primary_key": column.primary_key,
                "nullable": column.nullable,
                "type_hint": type_name,
                "value": value_str,
                "widget": "textarea" if prefer_textarea else "input",
            }
        )
    return render_template(
        "admin/data/edit.html",
        model_name=model_name,
        model_label=_titleize(model_name),
        fields=form_fields,
        pk_name=pk_column.key,
        record=record,
        csrf_token=generate_csrf(),
    )
@admin_bp.route("/antennas/parse-datasheet", methods=["POST"])
@admin_required
def antennas_parse_datasheet():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Arquivo nao enviado."}), 400
    data = extract_antenna_from_datasheet(file)
    status = 200 if "error" not in data else 500
    data["csrf_token"] = generate_csrf()
    return jsonify(data), status


@admin_bp.route("/site-designer/contacts", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_contacts():
    payload = _json_payload()
    allowed = ["name", "phone", "email", "address", "whatsapp", "map_embed", "instagram", "facebook", "linkedin"]
    data = {}
    for key in allowed:
        if key in payload:
            value = payload.get(key)
            if isinstance(value, str):
                value = value.strip()
            if value in (None, ""):
                continue
            data[key] = value
    _upsert_block("contacts", data, label="Contatos")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/hero/promos", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_hero_promos():
    payload = _json_payload()
    items = payload.get("items")
    promos: list[dict[str, str | None]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            description = (item.get("description") or "").strip()
            image = item.get("image") or item.get("media") or item.get("cover")
            if not title:
                continue
            if isinstance(image, str):
                image = image.strip() or None
            promos.append({"title": title, "description": description, "image": image})
    _upsert_block("hero_promos", promos, label="Hero Promos")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/hero/images", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_hero_images():
    payload = _json_payload()
    items = payload.get("items")
    images: list[dict[str, str | None]] = []
    if isinstance(items, list):
        for item in items:
            title = None
            if isinstance(item, str):
                path = item.strip()
            elif isinstance(item, dict):
                path = (item.get("image") or item.get("path") or item.get("src") or "").strip()
                raw_title = item.get("title") or item.get("label") or ""
                title = raw_title.strip() or None
            else:
                continue
            if not path:
                continue
            images.append({"image": path, "title": title})
    _upsert_block("hero_images", images, label="Hero Images")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/highlights", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_highlights():
    payload = _json_payload()
    items = payload.get("items")
    highlights: list[dict[str, str]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            description = (item.get("description") or "").strip()
            if not title:
                continue
            highlights.append({"title": title, "description": description})
    _upsert_block("highlights", highlights, label="Highlights")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/gallery", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_gallery():
    payload = _json_payload()
    items = payload.get("items")
    gallery: list[dict[str, str | None]] = []
    if isinstance(items, list):
        for item in items:
            if isinstance(item, str):
                path = item.strip()
                title = None
            elif isinstance(item, dict):
                path = (item.get("image") or item.get("path") or item.get("src") or "").strip()
                raw_title = item.get("title") or item.get("label") or ""
                title = raw_title.strip() or None
            else:
                continue
            if not path:
                continue
            gallery.append({"image": path, "title": title})
    _upsert_block("gallery", gallery, label="Gallery")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/faq", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_update_faq():
    payload = _json_payload()
    items = payload.get("items")
    faq: list[dict[str, str]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            question = (item.get("question") or "").strip()
            answer = (item.get("answer") or "").strip()
            if not question or not answer:
                continue
            faq.append({"question": question, "answer": answer})
    _upsert_block("faq", faq, label="FAQ")
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/upload/image", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_upload_image():
    file = request.files.get("file")
    section = (request.form.get("section") or "general").strip() or "general"
    try:
        path = _store_image(file, section=section)
    except ValueError as exc:
        abort(400, str(exc))
    return jsonify({"status": "ok", "path": path, "url": _resolve_media_path(path)})


@admin_bp.route("/site-designer/upload/document", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_upload_document():
    file = request.files.get("file")
    if not file:
        abort(400, "Arquivo obrigatório")
    try:
        filename = _store_document(file)
    except ValueError as exc:
        abort(400, str(exc))
    doc = SiteDocument.query.filter_by(filename=filename).first()
    if doc is None:
        doc = SiteDocument(filename=filename)
        db.session.add(doc)
    payload = {
        "display_name": request.form.get("display_name"),
        "category": request.form.get("category"),
        "description": request.form.get("description"),
        "thumbnail_path": request.form.get("thumbnail_path"),
        "is_featured": request.form.get("is_featured") in {"1", "true", "True", "on"},
    }
    metadata_raw = request.form.get("metadata")
    if metadata_raw:
        try:
            payload["metadata"] = json.loads(metadata_raw)
        except json.JSONDecodeError:
            payload["metadata"] = None
    _apply_document_payload(doc, payload)
    db.session.commit()
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/documents", methods=["POST"])
@admin_required
@csrf.exempt
def site_designer_upsert_document():
    payload = _json_payload()
    filename = (payload.get("filename") or "").strip()
    if not filename:
        abort(400, "filename obrigatório")
    doc = SiteDocument.query.filter_by(filename=filename).first()
    if doc is None:
        doc = SiteDocument(filename=filename)
        db.session.add(doc)
    _apply_document_payload(doc, payload)
    db.session.commit()
    return jsonify({"status": "ok", "state": _build_site_state()})


@admin_bp.route("/site-designer/documents/<uuid:doc_id>", methods=["PATCH", "DELETE"])
@admin_required
@csrf.exempt
def site_designer_document_detail(doc_id):
    doc = SiteDocument.query.get_or_404(doc_id)
    if request.method == "DELETE":
        remove_file = request.args.get("remove_file") in {"1", "true", "True"}
        filename = doc.filename
        db.session.delete(doc)
        db.session.commit()
        if remove_file and filename:
            pdf_path = _docs_root_path() / filename
            if pdf_path.exists():
                pdf_path.unlink()
        return jsonify({"status": "ok", "state": _build_site_state()})

    payload = _json_payload()
    _apply_document_payload(doc, payload)
    db.session.commit()
    return jsonify({"status": "ok", "state": _build_site_state()})
