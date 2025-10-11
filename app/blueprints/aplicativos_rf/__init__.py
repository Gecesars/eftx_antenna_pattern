from flask import Blueprint

aplicativos_rf_bp = Blueprint(
    "aplicativos_rf",
    __name__,
    url_prefix="/aplicativos-rf",
    template_folder="templates",
    static_folder="static",
)

from . import routes  # noqa: E402,F401
