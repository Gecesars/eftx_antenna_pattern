# -*- coding: utf-8 -*-
from flask import Flask, current_app, request

from .cookies import CONSENT_COOKIE_NAME, get_consent, has_consent


EFTX_BRAND = {
    "name": "EFTX",
    "tagline": "Antenna Pattern Composer",
    "primary_hex": "#0A4E8B",
    "accent_hex": "#FF6A3D",
}


def register_template_globals(app: Flask) -> None:
    app.jinja_env.globals["brand"] = EFTX_BRAND

    @app.context_processor
    def _inject_globals():
        consent_present = CONSENT_COOKIE_NAME in request.cookies
        company = _company_info()
        return {
            "cookie_consent": get_consent(),
            "has_cookie_consent": has_consent,
            "cookie_banner_required": not consent_present,
            "company_info": company,
            "company_social_links": _company_social(company),
        }


def _company_info() -> dict:
    cfg = current_app.config
    data: dict[str, str] = {}
    try:
        from ..models import SiteContentBlock

        block = SiteContentBlock.query.filter_by(slug="contacts").first()
        if block and isinstance(block.data, dict):
            data = {key: value for key, value in block.data.items() if isinstance(key, str)}
    except Exception:  # pragma: no cover - defensive fallback
        data = {}

    return {
        "name": data.get("name") or cfg.get("COMPANY_NAME"),
        "phone": data.get("phone") or cfg.get("COMPANY_PHONE"),
        "email": data.get("email") or cfg.get("COMPANY_EMAIL"),
        "address": data.get("address") or cfg.get("COMPANY_ADDRESS"),
        "whatsapp": data.get("whatsapp") or cfg.get("COMPANY_WHATSAPP"),
        "instagram": data.get("instagram") or cfg.get("COMPANY_INSTAGRAM"),
        "facebook": data.get("facebook") or cfg.get("COMPANY_FACEBOOK"),
        "linkedin": data.get("linkedin") or cfg.get("COMPANY_LINKEDIN"),
        "map_embed": data.get("map_embed") or cfg.get("COMPANY_MAP_EMBED"),
    }


def _company_social(company: dict) -> list[dict[str, str]]:
    links = []
    for network in ("instagram", "facebook", "linkedin"):
        url = (company or {}).get(network)
        if url:
            links.append({"network": network, "url": url})
    return links
