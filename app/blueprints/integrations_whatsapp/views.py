# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from flask import Blueprint, abort, current_app, jsonify, request, url_for

from ...core import answer_with_gemini, discover_site_root, load_products_from_site, list_pdfs_from_docs
from ...extensions import csrf, limiter


integrations_whatsapp_bp = Blueprint("integrations_whatsapp", __name__)


def _docs_root() -> Path:
    configured = current_app.config.get("DOCS_ROOT")
    if configured:
        path = Path(configured)
    else:
        path = Path(current_app.root_path).parent / "docs"
    return path.resolve()


def _faq_entries() -> list[dict[str, str]]:
    return [
        {
            "question": "Quais tecnologias de antena a EFTX oferece?",
            "answer": "Projetamos antenas FM, VHF/UHF para TV digital, enlaces micro-ondas, sistemas slot e arrays customizados.",
        },
        {
            "question": "Vocês prestam serviços de instalação e comissionamento?",
            "answer": "Sim. Cuidamos de medições, validação de cobertura e integração com infraestrutura existente.",
        },
        {
            "question": "É possível solicitar projeto sob medida?",
            "answer": "Nossa engenharia desenvolve soluções tailor-made com simulação EM, testes em câmara anecoica e suporte completo.",
        },
    ]


def _require_token() -> None:
    expected = current_app.config.get("N8N_WEBHOOK_TOKEN")
    provided = request.headers.get("X-Webhook-Token")
    if not expected or provided != expected:
        current_app.logger.warning("whatsapp.token.invalid", extra={"has_token": bool(provided)})
        abort(401)


def _build_context() -> dict[str, Any]:
    site_root = discover_site_root()
    products = load_products_from_site(site_root)
    docs_root = _docs_root()
    downloads = list_pdfs_from_docs(docs_root)
    base_url = request.url_root.rstrip("/")

    product_links = []
    for product in products:
        link = urljoin(base_url + "/", url_for("public_site.products") + f"#{product['slug']}")
        datasheet = product.get("datasheet_path")
        datasheet_url = url_for("public_site.site_asset", filename=datasheet, _external=True) if datasheet else None
        product_links.append(
            {
                "name": product.get("name"),
                "category": product.get("category"),
                "description": product.get("description"),
                "link": link,
                "datasheet": datasheet_url,
            }
        )

    download_links = [
        {
            "name": item["name"],
            "link": url_for("public_site.download_file", filename=item["path_rel"], _external=True),
            "size_bytes": item["size_bytes"],
            "modified_at": item["modified_at"].isoformat() if isinstance(item.get("modified_at"), datetime) else None,
        }
        for item in downloads
    ]

    return {
        "faq": _faq_entries(),
        "products": product_links,
        "downloads": download_links,
        "site_url": base_url,
    }


def _fallback_answer(user_text: str, context: dict[str, Any]) -> dict[str, Any]:
    products = context.get("products", [])[:3]
    downloads = context.get("downloads", [])[:2]
    lines = [
        "Olá! Sou o assistente institucional EFTX.",
        "Confira algumas informações que podem ajudar:",
    ]
    if products:
        lines.append("• Principais produtos: " + ", ".join(prod["name"] for prod in products if prod.get("name")))
    if downloads:
        lines.append("• Documentos sugeridos: " + ", ".join(doc["name"] for doc in downloads if doc.get("name")))
    lines.append("Se precisar de atendimento humano, fale com nossa engenharia: contato@eftx.com.br")

    suggestions = []
    for product in products:
        if product.get("link"):
            suggestions.append({"title": product["name"], "url": product["link"]})
    for doc in downloads:
        if doc.get("link"):
            suggestions.append({"title": doc["name"], "url": doc["link"]})

    return {
        "reply_text": "\n".join(lines),
        "suggested_links": suggestions,
    }


def _should_use_gemini() -> bool:
    use_gemini = current_app.config.get("USE_GEMINI", False)
    api_key = current_app.config.get("GEMINI_API_KEY")
    return bool(use_gemini and api_key)


@integrations_whatsapp_bp.route("/webhooks/whatsapp/inbound", methods=["POST"])
@csrf.exempt
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_WHATSAPP", "30 per minute"))
def whatsapp_inbound():
    _require_token()
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    sender = payload.get("from")
    trace_id = payload.get("trace_id") or str(uuid.uuid4())
    media = payload.get("media")

    if not message:
        return jsonify({"error": "invalid_message", "trace_id": trace_id}), 400

    context = _build_context()
    use_gemini = _should_use_gemini()
    current_app.logger.info(
        "whatsapp.inbound",
        extra={
            "trace_id": trace_id,
            "from": sender,
            "has_media": bool(media),
            "use_gemini": use_gemini,
        },
    )

    if use_gemini:
        try:
            response_payload = answer_with_gemini(message, context)
        except Exception as exc:  # pragma: no cover - external dependency
            current_app.logger.exception("whatsapp.gemini_failure", extra={"trace_id": trace_id})
            response_payload = _fallback_answer(message, context)
    else:
        response_payload = _fallback_answer(message, context)

    response_data = {
        "reply_text": response_payload.get("reply_text") or "Olá! Em instantes nossa equipe responderá.",
        "suggested_links": response_payload.get("suggested_links", []),
        "trace_id": trace_id,
    }
    return jsonify(response_data)


@integrations_whatsapp_bp.route("/webhooks/whatsapp/status", methods=["POST"])
@csrf.exempt
@limiter.limit(lambda: current_app.config.get("RATE_LIMIT_WHATSAPP_STATUS", "120 per minute"))
def whatsapp_status():
    _require_token()
    payload = request.get_json(silent=True) or {}
    trace_id = payload.get("trace_id")
    status = payload.get("status")
    current_app.logger.debug(
        "whatsapp.status",
        extra={
            "trace_id": trace_id,
            "status": status,
        },
    )
    return jsonify({"status": "ok", "trace_id": trace_id})
