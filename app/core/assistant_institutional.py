from __future__ import annotations

from typing import Any

import google.generativeai as genai  # type: ignore
from flask import current_app


def answer_with_gemini(user_text: str, context: dict[str, Any]) -> dict[str, Any]:
    if not user_text or not user_text.strip():
        raise ValueError("Texto do usuário não pode ser vazio.")

    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini API key não configurada.")

    model_name = current_app.config.get("GEMINI_INSTITUTIONAL_MODEL", "gemini-2.5-pro")
    persona = current_app.config.get("INSTITUTIONAL_PERSONA", "AntennaExpert")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)

    prompt = _build_prompt(user_text, persona, context)
    try:
        response = model.generate_content(prompt)
    except Exception as exc:  # pragma: no cover - network/SDK failure
        raise RuntimeError("Falha ao consultar Gemini institucional.") from exc

    reply_text = _extract_text(response)
    if not reply_text:
        raise RuntimeError("Resposta vazia retornada pelo modelo Gemini.")

    suggestions = _collect_suggestions(context)
    return {"reply_text": reply_text, "suggested_links": suggestions}


def _build_prompt(user_text: str, persona: str, context: dict[str, Any]) -> str:
    overview_text = (context.get("overview") or "").strip()
    faq_lines = _format_pairs(context.get("faq", []), prefix="Pergunta frequente")
    product_lines = _format_products(context.get("products", []))
    download_lines = _format_downloads(context.get("downloads", []))
    highlight_lines = _format_highlights(context.get("highlights", []))

    return (
        f"Você é {persona}, assistente técnico da EFTX. Respeite as regras fornecidas acima.\n\n"
        f"Resumo institucional:\n{overview_text or '- (sem resumo)'}\n\n"
        f"Diferenciais técnicos:\n{highlight_lines or '- (sem destaques)'}\n\n"
        f"FAQ institucional:\n{faq_lines or '- (sem registros)'}\n\n"
        f"Catálogo de produtos:\n{product_lines or '- (catalogo vazio)'}\n\n"
        f"Downloads disponíveis:\n{download_lines or '- (sem downloads)'}\n\n"
        f"Mensagem do usuário: {user_text.strip()}\n\n"
        "Produza uma resposta breve (até três parágrafos de até três frases) e adicione 'Próximos passos' quando for útil. Cite as fontes conforme solicitado."
    )


def _format_pairs(entries: list[dict[str, Any]], *, prefix: str) -> str:
    lines = []
    for entry in entries:
        question = entry.get("question") or entry.get("title")
        answer = entry.get("answer") or entry.get("text")
        if question and answer:
            lines.append(f"- {prefix}: {question} -> {answer}")
    return "\n".join(lines)


def _format_products(products: list[dict[str, Any]]) -> str:
    lines = []
    for product in products[:12]:
        name = product.get("name")
        if not name:
            continue
        category = product.get("category")
        description = product.get("description")
        link = product.get("link")
        datasheet = product.get("datasheet")
        fragments = [name]
        if category:
            fragments.append(f"categoria: {category}")
        if description:
            fragments.append(description)
        if datasheet:
            fragments.append(f"datasheet: {datasheet}")
        if link:
            fragments.append(f"detalhes: {link}")
        lines.append(" - ".join(fragments))
    return "\n".join(lines)


def _format_highlights(highlights: list[dict[str, Any]]) -> str:
    lines = []
    for item in highlights[:8]:
        title = item.get("title")
        description = item.get("description")
        if title and description:
            lines.append(f"- {title}: {description}")
    return "\n".join(lines)


def _format_downloads(downloads: list[dict[str, Any]]) -> str:
    lines = []
    for item in downloads[:12]:
        name = item.get("name")
        link = item.get("link")
        if not name:
            continue
        parts = [name]
        if link:
            parts.append(f"link: {link}")
        lines.append(" - ".join(parts))
    return "\n".join(lines)


def _extract_text(response) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) if content else None
        if not parts:
            continue
        buffer: list[str] = []
        for part in parts:
            value = getattr(part, "text", None)
            if value:
                buffer.append(value.strip())
        if buffer:
            joined = "\n".join([item for item in buffer if item])
            if joined:
                return joined
    return ""


def _collect_suggestions(context: dict[str, Any]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    for product in context.get("products", [])[:3]:
        name = product.get("name")
        link = product.get("link")
        if name and link:
            suggestions.append({"title": name, "url": link})
    for item in context.get("downloads", [])[:3]:
        name = item.get("name")
        link = item.get("link")
        if name and link:
            suggestions.append({"title": name, "url": link})
    return suggestions


__all__ = ["answer_with_gemini"]
