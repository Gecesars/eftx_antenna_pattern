from __future__ import annotations

from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, candidate: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, candidate)
    except VerifyMismatchError:
        return False


def _get_serializer() -> URLSafeTimedSerializer:
    secret_key = current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(secret_key)


def generate_email_token(email: str) -> str:
    serializer = _get_serializer()
    salt = current_app.config.get("SECURITY_EMAIL_SALT", "email-salt")
    return serializer.dumps(email, salt=salt)


def confirm_email_token(token: str, max_age: int = 86400) -> str | None:
    serializer = _get_serializer()
    salt = current_app.config.get("SECURITY_EMAIL_SALT", "email-salt")
    try:
        return serializer.loads(token, salt=salt, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
