# -*- coding: utf-8 -*-
from flask import Flask

from .auth.views import auth_bp
from .admin.views import admin_bp
from .projects.views import projects_bp
from .api.views import api_bp
from .public.views import public_bp
from .integrations_whatsapp.views import integrations_whatsapp_bp
from .public_site.views import public_site_bp
from .aplicativos_rf import aplicativos_rf_bp


BLUEPRINTS = (
    auth_bp,
    admin_bp,
    projects_bp,
    api_bp,
    public_bp,
    integrations_whatsapp_bp,
    public_site_bp,
    aplicativos_rf_bp,
)


def register_blueprints(app: Flask) -> None:
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
