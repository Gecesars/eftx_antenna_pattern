from flask import Flask

from .auth.views import auth_bp
from .admin.views import admin_bp
from .projects.views import projects_bp
from .api.views import api_bp
from .public.views import public_bp


BLUEPRINTS = (
    auth_bp,
    admin_bp,
    projects_bp,
    api_bp,
    public_bp,
)


def register_blueprints(app: Flask) -> None:
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
