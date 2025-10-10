from __future__ import annotations

import uuid

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from .config import config_by_name
from .extensions import csrf, db, limiter, login_manager, mail, migrate, jwt
from .utils.templating import register_template_globals
from .blueprints import register_blueprints
from .cli import register_cli


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=False)

    config_name = config_name or app.config.get("ENV", "development")
    config_cls = config_by_name.get(config_name, config_by_name["development"])
    app.config.from_object(config_cls)

    register_extensions(app)
    register_blueprints(app)
    register_template_globals(app)
    register_cli(app)
    register_security_headers(app)

    return app

def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    jwt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"
    login_manager.login_message_category = "warning"

    from .models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return None
        return db.session.get(User, user_uuid)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data.get("sub")
        try:
            user_uuid = uuid.UUID(identity) if identity else None
        except ValueError:
            return None
        if user_uuid is None:
            return None
        return db.session.get(User, user_uuid)


def register_security_headers(app: Flask) -> None:
    default_csp = (
        "default-src 'self'; "
        "img-src 'self' data: https:; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "connect-src 'self'; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "frame-src 'self' https://www.google.com https://maps.google.com https://maps.gstatic.com"
    )

    @app.after_request
    def _set_security_headers(response):
        response.headers.setdefault("Content-Security-Policy", app.config.get("CONTENT_SECURITY_POLICY", default_csp))
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response
