from __future__ import annotations

import uuid

from flask import Flask

from .config import config_by_name
from .extensions import csrf, db, limiter, login_manager, mail, migrate
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

    return app


def register_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

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



