from __future__ import annotations

import click
from flask import Flask

from .extensions import db
from .models import User
from .utils.security import hash_password


def register_cli(app: Flask) -> None:
    @app.cli.group()
    def users() -> None:
        """User management commands."""

    @users.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--name", prompt="Full name", default="EFTX Admin")
    def create_admin(email: str, password: str, name: str) -> None:
        if User.query.filter_by(email=email.lower()).first():
            click.echo("User already exists")
            return
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=name,
            email_confirmed=True,
            role="admin",
        )
        db.session.add(user)
        db.session.commit()
        click.echo("Admin user created")
