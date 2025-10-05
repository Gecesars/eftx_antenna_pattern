from __future__ import annotations

from flask import Blueprint, render_template
from flask import current_app, send_from_directory, abort
from pathlib import Path

from ...models import Antenna


public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    antennas = Antenna.query.order_by(Antenna.name.asc()).all()
    categories = ["TV", "FM", "Microondas", "Telecom", None]
    grouped: dict[str, list[Antenna]] = {cat: [] for cat in categories}
    for ant in antennas:
        key = ant.category if ant.category in grouped else None
        grouped[key].append(ant)
    return render_template("public/home.html", grouped=grouped)


@public_bp.route("/antenna-thumb")
def antenna_thumb():
    from flask import request
    rel_path = request.args.get("path")
    if not rel_path:
        abort(404)
    export_root = Path(current_app.config.get("EXPORT_ROOT", "exports")).resolve()
    path = (export_root / rel_path).resolve() if not Path(rel_path).is_absolute() else Path(rel_path).resolve()
    if export_root not in path.parents and path != export_root:
        abort(403)
    if not path.exists():
        abort(404)
    return send_from_directory(path.parent, path.name, as_attachment=False)


@public_bp.route("/brand")
def brand():
    return render_template("public/brand.html")
