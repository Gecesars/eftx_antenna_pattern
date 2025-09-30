from __future__ import annotations

from flask import Blueprint, render_template

from ...models import Antenna


public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def home():
    antennas = Antenna.query.order_by(Antenna.created_at.desc()).limit(6).all()
    return render_template("public/home.html", antennas=antennas)


@public_bp.route("/brand")
def brand():
    return render_template("public/brand.html")
