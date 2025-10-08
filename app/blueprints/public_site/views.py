# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import re

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_from_directory, url_for

from ...core import discover_site_root, list_local_images, load_products_from_site, list_pdfs_from_docs
from ...extensions import csrf
from ...utils.cookies import set_consent
from ...services.knowledge_base import retrieve_contexts


public_site_bp = Blueprint("public_site", __name__)

QUICK_INTENTS: list[tuple[tuple[str, ...], str]] = [
    (
        ("diferenc",),
        "Nossos diferenciais principais: engenharia 360° (diagnóstico ao suporte), laboratório homologado para ensaios VSWR/intermodulação e stack numérica própria que exporta PAT/PRN com métricas HPBW, diretividade e SLL.",
    ),
    (
        ("referenc",),
        "Os projetos de referência mostram combinações típicas em FM, TV digital e backhaul 6 GHz com métricas reais (ERP, HPBW, disponibilidade) e links para solicitar estudos dedicados.",
    ),
    (
        ("produto",),
        "Acesse /produtos para ver o catálogo completo com cards por categoria e datasheets. Os PDFs estão também em /downloads.",
    ),
    (
        ("contato",),
        "Fale com nossa engenharia em contato@eftx.com.br, WhatsApp 5519998537007 ou pelos telefones (19) 98145-6085 / (19) 4117-0270.",
    ),
]


@public_site_bp.route("/")
def home() -> str:
    site_root = discover_site_root()
    all_products = load_products_from_site(site_root)
    docs_root = _docs_root()
    downloads = _enrich_downloads(list_pdfs_from_docs(docs_root))
    current_app.logger.debug(
        "Rendering public site home (products=%d, downloads=%d)",
        len(all_products),
        len(downloads),
    )

    assistant_greeting = (
        (current_app.config.get("ASSISTANT_GREETING") or "").strip()
        or "Olá! Sou o assistente técnico EFTX. Posso explicar nossas soluções, indicar downloads e orientar próximos passos."
    )

    hero_slides = _hero_slides(all_products)
    gallery_images = _institutional_gallery() or hero_slides

    hero_images = [slide.get("image") for slide in hero_slides if slide.get("image")]
    if not hero_images:
        hero_images = [item.get("image") for item in gallery_images if item.get("image")]

    try:
        hero_fallback = url_for("public_site.site_asset", filename="IMA/logo-site.png")
    except BuildError:
        hero_fallback = url_for("static", filename="img/logo.png")

    hero_promos = [
        {
            "title": "Cobertura perfeita para quem transmite confiança",
            "description": (
                "Da análise do cenário ao comissionamento, a EFTX entrega sistemas de antenas, enlaces e infraestrutura "
                "de telecom com eficiência comprovada em todo o Brasil e América Latina."
            ),
        },
        {
            "title": "Engenharia aplicada do laboratório ao topo da torre",
            "description": (
                "Simulamos, fabricamos e validamos cada sistema com ensaios de campo, memorial técnico completo e "
                "prontidão para homologações."
            ),
        },
        {
            "title": "Arrays multiantena calibrados para ERP ideal",
            "description": (
                "Nossa stack numérica controla tilt, perdas e ripple para entregar diagramas alinhados às normas de FM, "
                "TV digital e enlaces licenciados."
            ),
        },
        {
            "title": "Suporte contínuo com equipes em todo o país",
            "description": (
                "Squads regionais, telemetria e estoque dedicado garantem resposta rápida para expandir, manter e modernizar "
                "seu parque irradiador."
            ),
        },
    ]

    hero_sequences: list[dict[str, str]] = []
    for idx, promo in enumerate(hero_promos):
        image = hero_images[idx % len(hero_images)] if hero_images else hero_fallback
        hero_sequences.append({
            "title": promo["title"],
            "description": promo["description"],
            "image": image,
        })

    initial_hero = hero_sequences[0] if hero_sequences else {
        "title": hero_promos[0]["title"],
        "description": hero_promos[0]["description"],
        "image": hero_fallback,
    }

    context = {
        "title": "EFTX Broadcast & Telecom",
        "featured_products": all_products[:6],
        "featured_downloads": downloads[:4],
        "page_meta": _page_meta(
            title="EFTX Telecom — Soluções completas em antenas",
            description=(
                "Projetos, fabricação e suporte técnico especializado em antenas FM, TV, VHF/UHF e telecomunicações. "
                "Conheça a linha completa e fale com nossos especialistas."
            ),
            url=request.url_root.rstrip("/") or request.url_root,
        ),
        "organization_schema": _organization_schema(),
        "product_schema": _product_schema(all_products[:3]),
        "contact_info": _contact_info(),
        "social_links": _social_links(),
        "hero_slides": hero_slides,
        "gallery_images": gallery_images,
        "hero_sequences": hero_sequences,
        "initial_hero": initial_hero,
        "assistant_greeting": assistant_greeting,
    }
    return render_template("public_site/home.html", **context)


@public_site_bp.route("/produtos")
def products() -> str:
    site_root = discover_site_root()
    all_products = load_products_from_site(site_root)
    current_app.logger.debug("Rendering public site catalog (products=%d)", len(all_products))
    context = {
        "title": "Produtos | EFTX Broadcast & Telecom",
        "products": all_products,
        "page_meta": _page_meta(
            title="Produtos EFTX — Antenas profissionais e acessórios",
            description="Catálogo completo de antenas, arrays e acessórios para radiodifusão e telecom.",
            url=request.base_url,
        ),
        "product_schema": _product_schema(all_products),
    }
    return render_template("public_site/produtos.html", **context)


@public_site_bp.route("/downloads")
def downloads() -> str:
    docs_root = _docs_root()
    files = _enrich_downloads(list_pdfs_from_docs(docs_root))
    current_app.logger.debug("Rendering downloads page (files=%d)", len(files))
    context = {
        "title": "Downloads | EFTX Broadcast & Telecom",
        "downloads": files,
        "page_meta": _page_meta(
            title="Downloads técnicos EFTX",
            description="Datasheets, catálogos e normas técnicas disponíveis para consulta imediata.",
            url=request.base_url,
        ),
    }
    return render_template("public_site/downloads.html", **context)


@public_site_bp.route("/contato")
def contact() -> str:
    context = {
        "title": "Contato | EFTX Broadcast & Telecom",
        "page_meta": _page_meta(
            title="Fale com a EFTX",
            description="Converse com nossa equipe comercial e engenharia para tirar dúvidas e solicitar propostas.",
            url=request.base_url,
        ),
        "contact_info": _contact_info(),
        "social_links": _social_links(),
    }
    return render_template("public_site/contato.html", **context)


@public_site_bp.route("/assistente/ask", methods=["POST"])
@csrf.exempt
def ask_virtual_assistant():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"status": "error", "error": "Mensagem inválida."}), 400

    context = _assistant_context()
    kb_snippets = retrieve_contexts(message, top_k=3)
    context["kb_snippets"] = kb_snippets

    api_key = current_app.config.get("GEMINI_API_KEY")
    use_gemini = bool(api_key) and current_app.config.get("ENABLE_PUBLIC_GEMINI", False)

    if use_gemini:
        try:
            response = answer_with_gemini(message, context)
        except Exception as exc:  # pragma: no cover
            current_app.logger.exception("assistant.public.failure", extra={"error": str(exc)})
            response = _assistant_fallback(message, context, kb_snippets)
    else:
        response = _assistant_fallback(message, context, kb_snippets)

    return jsonify({
        "status": "ok",
        "reply": response.get("reply_text") or "Nossa equipe retornará em breve.",
        "links": response.get("suggested_links", []),
        "used_gemini": use_gemini,
    })


@public_site_bp.route("/politica-de-cookies")
def cookie_policy() -> str:
    context = {
        "page_meta": _page_meta(
            title="Política de Cookies EFTX",
            description="Entenda como coletamos preferências e respeitamos a privacidade no portal EFTX.",
            url=request.base_url,
        )
    }
    return render_template("public_site/politica_cookies.html", **context)


@public_site_bp.route("/privacidade")
def privacy() -> str:
    context = {
        "page_meta": _page_meta(
            title="Política de Privacidade EFTX",
            description="Detalhes sobre tratamento de dados pessoais segundo a LGPD.",
            url=request.base_url,
        )
    }
    return render_template("public_site/privacidade.html", **context)


@public_site_bp.route("/downloads/arquivo/<path:filename>")
def download_file(filename: str):
    docs_root = _docs_root()
    file_path = (docs_root / filename).resolve()
    try:
        file_path.relative_to(docs_root)
    except ValueError:
        abort(403)
    if not file_path.is_file():
        abort(404)
    return send_from_directory(str(docs_root), filename, as_attachment=True)


@public_site_bp.route("/site-assets/<path:filename>")
def site_asset(filename: str):
    site_root = discover_site_root()
    project_root = Path(current_app.root_path).parent
    local_root = project_root / "IMA"

    candidates: list[tuple[Path, Path]] = []

    if filename.startswith("IMA/"):
        relative = Path(filename[4:])
        candidates.append((local_root, relative))

    if site_root:
        candidates.append((site_root, Path(filename)))

    for base, rel in candidates:
        if not base or not base.exists():
            continue
        file_path = (base / rel).resolve()
        try:
            file_path.relative_to(base)
        except ValueError:
            continue
        if file_path.is_file():
            directory = file_path.parent
            return send_from_directory(str(directory), file_path.name)

    abort(404)


@public_site_bp.route("/cookies/consent", methods=["POST"])
@csrf.exempt
def update_cookie_consent():
    data = request.get_json(silent=True) or {}
    consent = data.get("consent", data)
    if not isinstance(consent, dict):
        consent = {}
    sanitized = {key: bool(value) for key, value in consent.items()}
    current_app.logger.debug("cookie.consent.update", extra={"consent": sanitized})
    response = jsonify({"status": "ok", "consent": sanitized})
    set_consent(response, sanitized)
    return response


@public_site_bp.route("/robots.txt")
def robots_txt():
    sitemap_url = url_for("public_site.sitemap", _external=True)
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        f"Sitemap: {sitemap_url}",
        "",
    ])
    return current_app.response_class(body, mimetype="text/plain")


@public_site_bp.route("/sitemap.xml")
def sitemap():
    pages = [
        url_for("public_site.home", _external=True),
        url_for("public_site.products", _external=True),
        url_for("public_site.downloads", _external=True),
        url_for("public_site.contact", _external=True),
        url_for("public_site.cookie_policy", _external=True),
        url_for("public_site.privacy", _external=True),
    ]
    lastmod = datetime.utcnow().date().isoformat()
    xml_items = "".join(
        f"<url><loc>{loc}</loc><lastmod>{lastmod}</lastmod><changefreq>weekly</changefreq></url>"
        for loc in pages
    )
    body = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
        f"{xml_items}"
        "</urlset>"
    )
    return current_app.response_class(body, mimetype="application/xml")


def _docs_root() -> Path:
    configured = current_app.config.get("DOCS_ROOT")
    if configured:
        path = Path(configured)
    else:
        path = Path(current_app.root_path).parent / "docs"
    return path.resolve()


def _organization_schema() -> dict:
    base_url = request.url_root.rstrip("/")
    try:
        logo_url = url_for("public_site.site_asset", filename="IMA/logo-site.png", _external=True)
    except BuildError:
        logo_url = url_for("static", filename="img/logo.png", _external=True)
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "EFTX Telecom",
        "url": base_url,
        "logo": logo_url,
        "contactPoint": [
            {
                "@type": "ContactPoint",
                "contactType": "commercial",
                "telephone": "+55 11 4002-8922",
                "email": "contato@eftx.com.br",
                "areaServed": "BR",
                "availableLanguage": ["Portuguese", "English"],
            }
        ],
        "sameAs": [
            "https://www.linkedin.com/company/eftx-telecom",
        ],
    }


def _product_schema(products: Iterable[dict]) -> list[dict]:
    base_url = request.url_root.rstrip("/")
    schema: list[dict] = []
    for product in products:
        if not product.get("name"):
            continue
        product_url = urljoin(base_url + "/", url_for("public_site.products") + f"#{product['slug']}")
        schema.append(
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": product["name"],
                "category": product.get("category"),
                "description": product.get("description"),
                "url": product_url,
                "image": _product_image_url(product),
                "offers": {
                    "@type": "AggregateOffer",
                    "priceCurrency": "BRL",
                    "availability": "https://schema.org/InStock",
                },
            }
        )
    return schema


def _product_image_url(product: dict) -> str | None:
    thumbnail = product.get("thumbnail_url")
    if not thumbnail:
        return None
    return thumbnail


def _page_meta(*, title: str, description: str, url: str) -> dict:
    try:
        og_image = url_for("public_site.site_asset", filename="IMA/logo-site.png", _external=True)
    except BuildError:
        og_image = url_for("static", filename="img/logo.png", _external=True)
    return {
        "title": title,
        "description": description,
        "url": url,
        "og": {
            "title": title,
            "description": description,
            "url": url,
            "image": og_image,
        },
        "twitter": {
            "card": "summary_large_image",
            "title": title,
            "description": description,
            "image": og_image,
        },
    }


def _enrich_downloads(items: list[dict]) -> list[dict]:
    enriched = []
    for item in items:
        size_label = _human_size(item.get("size_bytes", 0))
        modified = item.get("modified_at")
        if isinstance(modified, datetime):
            modified_label = modified.strftime("%d/%m/%Y")
        else:
            modified_label = "—"
        enriched.append(
            {
                **item,
                "size_label": size_label,
                "modified_label": modified_label,
                "download_url": url_for("public_site.download_file", filename=item["path_rel"]),
            }
        )
    return enriched


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:,.1f} {unit}".replace(",", ".")
        size /= 1024
    return "0 B"


def _contact_info() -> dict:
    cfg = current_app.config
    return {
        "name": cfg.get("COMPANY_NAME"),
        "phone": cfg.get("COMPANY_PHONE"),
        "email": cfg.get("COMPANY_EMAIL"),
        "address": cfg.get("COMPANY_ADDRESS"),
        "whatsapp": cfg.get("COMPANY_WHATSAPP"),
        "map_embed": cfg.get("COMPANY_MAP_EMBED"),
    }


def _social_links() -> list[dict[str, str]]:
    cfg = current_app.config
    links = [
        ("instagram", cfg.get("COMPANY_INSTAGRAM")),
        ("facebook", cfg.get("COMPANY_FACEBOOK")),
        ("linkedin", cfg.get("COMPANY_LINKEDIN")),
    ]
    return [
        {"network": network, "url": url}
        for network, url in links
        if url
    ]


def _assistant_context() -> dict:
    site_root = discover_site_root()
    products = load_products_from_site(site_root)[:6]
    downloads = _enrich_downloads(list_pdfs_from_docs(_docs_root()))[:6]
    return {
        "products": products,
        "downloads": downloads,
        "faq": _site_faq(),
        "overview": _site_overview_summary(),
        "highlights": _company_highlights(),
    }


def _simulation_scenarios() -> list[dict]:
    return [
        {
            "slug": "fm",
            "label": "Broadcast FM",
            "title": "Rede FM 20 kW / 4 painéis",
            "description": (
                "Stack vertical com quatro painéis e alimentação balanceada. Ideal para capitais com terreno acidentado, "
                "mantendo cobertura urbana sem exceder limites de campo."),
            "metrics": [
                {"name": "ERP composto", "value": "87 kW"},
                {"name": "HPBW", "value": "65°"},
                {"name": "SLL", "value": "-18 dB"},
            ],
            "notes": "Estudo considera perdas de linha de 1,2 dB e tilt elétrico de -1,5°.",
        },
        {
            "slug": "tv",
            "label": "TV Digital UHF",
            "title": "Array UHF 48 dBd / 8 bays",
            "description": (
                "Configuração axial com oito painéis; composição 361 pontos e normalização RMS para atender cadernos técnicos da Anatel."),
            "metrics": [
                {"name": "ERP setor frontal", "value": "512 kW"},
                {"name": "Tilt elétrico", "value": "-0,75°"},
                {"name": "F/B", "value": "28 dB"},
            ],
            "notes": "Inclui máscaras regionais e script de conformidade ISDB-Tb.",
        },
        {
            "slug": "telecom",
            "label": "Telecom Carrier",
            "title": "Backhaul 6 GHz / slot dual-pol",
            "description": (
                "Enlace ponto-a-ponto com antena parabólica 1,8 m, arranjo dual-pol e otimização automática de inclinação."),
            "metrics": [
                {"name": "Disponibilidade", "value": "99,995%"},
                {"name": "Ganho efetivo", "value": "39,5 dBi"},
                {"name": "Fade margin", "value": "32 dB"},
            ],
            "notes": "Integra cálculo ITU-R P.530 e ajuste dinâmico de potência via SNMP.",
        },
    ]


def _assistant_fallback(user_text: str, context: dict, kb_snippets: list[str] | None = None) -> dict:
    reply_text, suggestions = _quick_answer(user_text, context, kb_snippets)
    return {
        "reply_text": reply_text,
        "suggested_links": suggestions,
    }


def _site_overview_summary() -> str:
    contact = _contact_info()
    phone = contact.get("phone") or "(telefone corporativo disponível no site)"
    email = contact.get("email") or "contato@eftx.com.br"
    whatsapp = contact.get("whatsapp") or "https://wa.me/5519998537007"

    return (
        "O site institucional apresenta a EFTX como fornecedora 360º para broadcast, telecom, energia, defesa e IoT. "
        "A home destaca indicadores (700+ sistemas instalados, 26 anos de atuação, equipes em 12 estados), "
        "os pilares de serviços (planejamento e engenharia, fabricação e supply, integração em campo, gestão e suporte) "
        "o know-how documentado (laboratório próprio, stack numérica e homologações) e o fluxo de entrega Diagnóstico → Projeto executivo → Integração e testes → Operação assistida. "
        "Um bloco de projetos de referência reúne cenários pré-validados (Broadcast FM, TV Digital UHF e Telecom Carrier) com métricas de ERP, tilt, disponibilidade e margem de desvanecimento. "
        "Há catálogo completo com datasheets em /produtos, biblioteca técnica em /downloads e CTA para contato direto. "
        f"Canais oficiais: telefone {phone}, e-mail {email} e WhatsApp {whatsapp}."
    )


def _site_faq() -> list[dict[str, str]]:
    contact = _contact_info()
    phone = contact.get("phone") or "telefone corporativo informado no site"
    email = contact.get("email") or "contato@eftx.com.br"
    whatsapp = contact.get("whatsapp") or "https://wa.me/5519998537007"

    return [
        {
            "question": "Quais segmentos a EFTX atende?",
            "answer": "A home destaca projetos para broadcast, telecom, energia, defesa & segurança e IoT/Smart Cities, com atuação nacional.",
        },
        {
            "question": "Que serviços integrados o site descreve?",
            "answer": "Planejamento e engenharia, fabricação e supply próprios, integração em campo (VSWR, laudos) e gestão/suporte contínuo com SLAs definidos.",
        },
        {
            "question": "Como acessar produtos e documentação técnica?",
            "answer": "Os PDFs em /produtos trazem datasheets por categoria e a biblioteca /downloads lista guias técnicos com tamanho e data atualizados.",
        },
        {
            "question": "Como funcionam os projetos de referência?",
            "answer": "O bloco Projetos de Referência apresenta cenários EFTX para Broadcast FM, TV Digital e Telecom Carrier com métricas calculadas pela engenharia (ERP, HPBW, tilt, disponibilidade) e links para solicitar estudos dedicados.",
        },
        {
            "question": "Quais são os diferenciais técnicos da EFTX?",
            "answer": "Know-how 360° com engenharia, laboratório próprio, stack numérica proprietária, homologações Anatel/ITU e assistência contínua com times residentes em 12 estados.",
        },
        {
            "question": "Quais são os canais oficiais de contato?",
            "answer": f"Telefone {phone}, e-mail {email} e WhatsApp institucional {whatsapp}; o formulário de /contato envia mensagens diretamente à equipe.",
        },
    ]


def _company_highlights() -> list[dict[str, str]]:
    return [
        {
            "title": "Engenharia 360°",
            "description": "Planejamento, modelagem ERP, memorial, implantação e suporte pós-start-up em um mesmo fluxo."},
        {
            "title": "Laboratório homologado",
            "description": "Ensaios de VSWR, combinadores, filtros e validações ambientais garantem desempenho em campo."},
        {
            "title": "Stack numérica proprietária",
            "description": "Ferramentas internas para parsing, composição e exportação (.PAT/.PRN/.PDF) com métricas HPBW, diretividade, SLL."},
        {
            "title": "Atendimento nacional",
            "description": "26 anos de atuação, 700+ sistemas instalados e equipes residentes em 12 estados garantindo SLA."},
        {
            "title": "Integrações inteligentes",
            "description": "Assistente IA, automação de exportações e webhooks WhatsApp agilizam tomada de decisão e suporte."},
    ]


def _quick_answer(user_text: str, context: dict, kb_snippets: list[str] | None = None) -> tuple[str, list[dict[str, str]]]:
    message = (user_text or "").strip().lower()
    highlights = context.get("highlights", []) or []
    products = context.get("products", []) or []
    downloads = context.get("downloads", []) or []

    reply_parts: list[str] = []
    suggestions: list[dict[str, str]] = []
    suggestion_urls: set[str] = set()
    core_summary: str | None = None
    primary_info: str | None = None
    next_steps: list[str] = []

    highlight_match = next(
        (item for item in highlights if item.get("title") and item["title"].lower() in message),
        None,
    )
    product_match = next(
        (item for item in products if item.get("name") and item["name"].lower() in message),
        None,
    )

    matched_products: list[dict] = []
    if "vhf" in message:
        matched_products = [
            p for p in products
            if "vhf" in (p.get("category") or "").lower()
            or "vhf" in (p.get("name") or "").lower()
        ]
    elif "uhf" in message:
        matched_products = [
            p for p in products
            if "uhf" in (p.get("category") or "").lower()
            or "uhf" in (p.get("name") or "").lower()
        ]
    elif "fm" in message:
        matched_products = [
            p for p in products
            if "fm" in (p.get("category") or "").lower()
            or "fm" in (p.get("name") or "").lower()
        ]
    elif "parab" in message or "micro" in message:
        matched_products = [
            p for p in products
            if "micro" in (p.get("category") or "").lower()
            or "micro" in (p.get("name") or "").lower()
        ]

    if highlight_match:
        core_summary = f"{highlight_match['title']}: {highlight_match['description']}"
        reply_parts.append(core_summary)

    download_matches: list[dict] = []
    if "vhf" in message:
        download_matches = [doc for doc in downloads if "vhf" in (doc.get("name") or "").lower()]

    if matched_products:
        top_names = ", ".join(p["name"] for p in matched_products[:3] if p.get("name"))
        primary_info = (
            f"Temos opções dedicadas para { 'VHF' if 'vhf' in message else ('UHF' if 'uhf' in message else 'essa faixa') }: {top_names}."
        )
        reply_parts.append(primary_info)
        for prod in matched_products[:3]:
            url = prod.get("datasheet_url")
            if url and url not in suggestion_urls:
                suggestions.append({"title": prod.get("name", "Datasheet"), "url": url})
                suggestion_urls.add(url)
        next_steps.append("Explorar os detalhes no catálogo em /produtos")

    if product_match and not matched_products:
        primary_info = f"{product_match['name']} está disponível no nosso catálogo com datasheet pronto para download."
        reply_parts.append(primary_info)
        if product_match.get("datasheet_url"):
            url = product_match["datasheet_url"]
            if url not in suggestion_urls:
                suggestions.append({"title": product_match["name"], "url": url})
                suggestion_urls.add(url)
        next_steps.append("Abrir o datasheet para revisar especificações")

    elif download_matches:
        doc_names = ", ".join(doc["name"] for doc in download_matches[:3])
        primary_info = f"Confira nossos materiais VHF em /downloads: {doc_names}."
        reply_parts.append(primary_info)
        for doc in download_matches[:3]:
            url = doc.get("download_url")
            if url and url not in suggestion_urls:
                suggestions.append({"title": doc["name"], "url": url})
                suggestion_urls.add(url)
        next_steps.append("Baixar os memoriais disponíveis na biblioteca técnica")

    if (matched_products or download_matches) and not highlight_match:
        key_highlight = highlights[0] if highlights else None
        if key_highlight:
            core_summary = f"Somos a EFTX, engenharia 360° ({key_highlight['title']} e laboratório homologado)."
            reply_parts.insert(0, core_summary)

    if not reply_parts:
        key_highlight = highlight_match or (highlights[0] if highlights else None)
        core_summary = "Somos a EFTX, engenharia 360° com laboratório próprio e stack numérica para broadcast e telecom."
        reply_parts.append(core_summary)
        if key_highlight:
            extra = f"Diferencial: {key_highlight['title']} — {key_highlight['description']}"
            reply_parts.append(extra)
            if not primary_info:
                primary_info = extra
        else:
            reply_parts.append(
                "Consulte o catálogo em /produtos e a biblioteca técnica em /downloads para materiais completos."
            )
            if not primary_info:
                primary_info = reply_parts[-1]
    if "vhf" in message and not matched_products and not download_matches:
        custom = "Para VHF produzimos linhas sob encomenda. Envie os requisitos para contato@eftx.com.br e retornaremos com memoriais dedicados."
        reply_parts.append(custom)
        primary_info = custom
        next_steps.append("Compartilhar requisitos com a engenharia EFTX via contato@eftx.com.br")

    if not suggestions and products:
        first_product = products[0]
        url = first_product.get("datasheet_url")
        if url and url not in suggestion_urls:
            suggestions.append({"title": first_product["name"], "url": url})
            suggestion_urls.add(url)
    if downloads and len(suggestions) < 2:
        first_doc = downloads[0]
        url = first_doc.get("download_url")
        if url and url not in suggestion_urls:
            suggestions.append({"title": first_doc["name"], "url": url})
            suggestion_urls.add(url)

    faq_match = _match_public_faq(message)
    snippet_text = _normalize_snippet(faq_match) if faq_match else ""
    if not snippet_text and kb_snippets:
        snippet_text = _normalize_snippet(kb_snippets[0])

    summary_parts: list[str] = []
    if core_summary:
        summary_parts.append(core_summary)
    elif reply_parts:
        summary_parts.append(reply_parts[0])
    if primary_info and primary_info not in summary_parts:
        summary_parts.append(primary_info)
    elif snippet_text:
        summary_parts.append(snippet_text)
    elif len(reply_parts) > 1:
        summary_parts.append(reply_parts[1])

    reply_text = " ".join(summary_parts).strip()
    if next_steps:
        unique_steps = list(dict.fromkeys(step for step in next_steps if step))
        if unique_steps:
            reply_text = f"{reply_text}\n\nPróximos passos:\n- " + "\n- ".join(unique_steps)

    return reply_text, suggestions[:3]


def _match_public_faq(message: str) -> str | None:
    if not message:
        return None
    for keywords, answer in QUICK_INTENTS:
        if all(keyword in message for keyword in keywords):
            return answer
    for question, answer in _public_faq_entries():
        if question in message:
            return answer
    return None


@lru_cache(maxsize=1)
def _public_faq_entries() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    faq_path = _docs_root() / "public_faq.md"
    if not faq_path.exists():
        return entries
    for line in faq_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("- **") and "**" in line[4:]:
            try:
                question_part, answer_part = line[4:].split("**", 1)
            except ValueError:
                continue
            question = question_part.strip().lower()
            answer = answer_part.strip().lstrip(":- ")
            if question and answer:
                entries.append((question, answer))
    return entries


def _normalize_snippet(text: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"^(?:\d+[\).\-]\s*)+", "", cleaned)
    cleaned = re.sub(r"\b\d{1,2}(?:\.\d+)*\b", "", cleaned)
    cleaned = re.sub(r"^[\W_]+", "", cleaned)
    if len(cleaned) <= 240:
        return cleaned
    cut = cleaned[:240]
    dot = cut.rfind(".")
    if dot > 80:
        return cut[:dot + 1]
    return cut.rstrip() + "…"


def _pretty_title(name: str) -> str:
    tokens = [part for part in name.replace("_", " ").replace("-", " ").split() if part]
    return " ".join(token.capitalize() for token in tokens)


def _hero_slides(products: list[dict]) -> list[dict]:
    slides: list[dict] = []

    for product in products:
        image = product.get("thumbnail_url") or product.get("datasheet_url")
        if not image:
            continue
        slides.append(
            {
                "title": product.get("name"),
                "category": product.get("category"),
                "image": image,
            }
        )
        if len(slides) >= 6:
            break
    return slides


def _institutional_gallery(limit: int = 6) -> list[dict]:
    project_root = Path(current_app.root_path).parent
    ima_root = project_root / "IMA"
    if not ima_root.is_dir():
        return []

    keywords = ("fabr", "manuf", "infra", "campo", "linha", "planta", "montagem", "instal", "produc")
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    images: list[dict] = []

    for path in sorted(ima_root.iterdir(), key=lambda p: p.name.lower()):
        if path.suffix.lower() not in extensions:
            continue
        stem = path.stem.lower()
        if not any(key in stem for key in keywords):
            continue
        images.append(
            {
                "image": url_for("public_site.site_asset", filename=f"IMA/{path.name}"),
                "title": _pretty_title(path.stem),
            }
        )
        if len(images) >= limit:
            break

    if images:
        return images

    fallbacks = list_local_images(limit)
    return [
        {
            "image": image_url,
            "title": "Infraestrutura EFTX",
        }
        for image_url in fallbacks
    ]
