from flask import Flask


EFTX_BRAND = {
    "name": "EFTX",
    "tagline": "Antenna Pattern Composer",
    "primary_hex": "#0A4E8B",
    "accent_hex": "#FF6A3D",
}


def register_template_globals(app: Flask) -> None:
    app.jinja_env.globals["brand"] = EFTX_BRAND
