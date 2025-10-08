# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from datetime import timedelta

from flask import Request, current_app, request
from itsdangerous import BadSignature, URLSafeSerializer

CONSENT_COOKIE_NAME = "eftx_cookie_consent"
_COOKIE_MAX_AGE = timedelta(days=365)
_DEFAULT_CONSENT = {
    "essential": True,
    "analytics": False,
    "marketing": False,
    "functional": False,
}


def _serializer() -> URLSafeSerializer:
    secret_key = current_app.config.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("SECRET_KEY is required to sign consent cookies.")
    return URLSafeSerializer(secret_key, salt="eftx-cookie-consent")


def get_consent(req: Request | None = None) -> dict:
    req = req or request
    raw = req.cookies.get(CONSENT_COOKIE_NAME)
    if not raw:
        return dict(_DEFAULT_CONSENT)
    serializer = _serializer()
    try:
        data = serializer.loads(raw)
    except BadSignature:
        current_app.logger.warning("cookie.consent.invalid_signature")
        return dict(_DEFAULT_CONSENT)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            current_app.logger.warning("cookie.consent.invalid_json")
            return dict(_DEFAULT_CONSENT)
    if not isinstance(data, dict):
        return dict(_DEFAULT_CONSENT)
    payload = dict(_DEFAULT_CONSENT)
    payload.update({key: bool(value) for key, value in data.items()})
    return payload


def set_consent(response, consent: dict) -> None:
    payload = dict(_DEFAULT_CONSENT)
    payload.update({key: bool(value) for key, value in consent.items()})
    serializer = _serializer()
    token = serializer.dumps(payload)
    secure_flag = request.is_secure or current_app.config.get("PREFER_SECURE_COOKIES", False)
    response.set_cookie(
        CONSENT_COOKIE_NAME,
        token,
        max_age=int(_COOKIE_MAX_AGE.total_seconds()),
        secure=secure_flag,
        httponly=True,
        samesite="Lax",
        path="/",
    )


def has_consent(category: str) -> bool:
    if category == "essential":
        return True
    consent = get_consent()
    return bool(consent.get(category))


__all__ = ["get_consent", "set_consent", "has_consent", "CONSENT_COOKIE_NAME"]
