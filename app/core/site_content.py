from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from flask import current_app, url_for

from ..models import SiteDocument

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


@dataclass(slots=True)
class ProductCard:
    slug: str
    name: str
    category: str | None = None
    description: str | None = None
    thumbnail_url: str | None = None
    detail_url: str | None = None
    datasheet_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "detail_url": self.detail_url,
            "datasheet_url": self.datasheet_url,
        }


def _project_root() -> Path:
    try:
        app = current_app._get_current_object()
        configured = app.config.get("PROJECT_ROOT")
        if configured:
            return Path(configured)
        return Path(app.root_path).parent
    except RuntimeError:
        return Path(__file__).resolve().parents[2]


def _logger() -> logging.Logger:
    try:
        return current_app.logger
    except RuntimeError:
        return logging.getLogger(__name__)


def discover_site_root() -> Path | None:
    """Return the path where the institutional content lives, logging the choice."""

    app_logger = _logger()
    project_root = _project_root()

    try:
        configured = current_app.config.get("SITE_CONTENT_ROOT")  # type: ignore[attr-defined]
    except RuntimeError:
        configured = None

    if configured:
        candidate = Path(configured)
        if candidate.is_dir():
            app_logger.debug("Using SITE_CONTENT_ROOT configured at %s", candidate)
            return candidate

    for dirname in ("extx_site", "eftx_site"):
        candidate = project_root / dirname
        if candidate.is_dir():
            app_logger.info("Site content discovered at %s", candidate)
            try:
                current_app.config.setdefault("SITE_CONTENT_ROOT", str(candidate))  # type: ignore[attr-defined]
            except RuntimeError:
                pass
            return candidate

    app_logger.warning("No site content directory found (looked for extx_site/eftx_site under %s)", project_root)
    return None


def load_products_from_site(root: Path | None) -> list[dict]:
    """Load product cards using local docs as datasheets and /eftx_site images as thumbnails."""

    docs_repo = _project_root() / "docs"
    if not docs_repo.exists():
        return []

    image_root = _images_root(root)
    documents_map = _documents_index()

    def resolve_media(path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith(("http://", "https://", "/")):
            return path
        return url_for("public_site.site_asset", filename=path)

    products: list[ProductCard] = []
    local_fallbacks = _local_image_urls()
    fallback_iter = iter(local_fallbacks)
    static_fallback = url_for("static", filename="img/logo.png")

    for pdf_path in sorted(docs_repo.glob("*.pdf"), key=lambda p: p.name.lower()):
        card = _product_from_pdf(pdf_path, site_root=root, image_root=image_root)
        if not card:
            continue

        doc_meta = documents_map.get(pdf_path.name.lower())
        if doc_meta:
            card = ProductCard(**doc_meta.apply_to_card(card.to_dict(), resolver=resolve_media))
            extra = doc_meta.metadata_json or {}
            override_url = extra.get("datasheet_url")
            if override_url:
                card.datasheet_url = override_url
            if card.thumbnail_url:
                card.thumbnail_url = resolve_media(card.thumbnail_url)

        if not card.thumbnail_url:
            card.thumbnail_url = next(fallback_iter, local_fallbacks[0] if local_fallbacks else static_fallback)
        products.append(card)

    _logger().debug("Loaded %d product cards (docs=%s, images=%s)", len(products), docs_repo, image_root)
    return [product.to_dict() for product in products]


def _product_from_pdf(pdf_path: Path, *, site_root: Path | None, image_root: Path | None) -> ProductCard | None:
    if not pdf_path.is_file():
        return None

    slug = _slugify(pdf_path.stem)
    name = _pretty_name(pdf_path.stem)
    category = _infer_category(pdf_path.stem)
    description = _generate_description(pdf_path.stem)

    datasheet_url = url_for("public_site.download_file", filename=pdf_path.name)
    thumbnail_rel = _match_thumbnail(slug, site_root, image_root, pdf_path)
    thumbnail_url = url_for("public_site.site_asset", filename=thumbnail_rel) if thumbnail_rel else None

    return ProductCard(
        slug=slug,
        name=name,
        category=category,
        description=description,
        thumbnail_url=thumbnail_url,
        detail_url=None,
        datasheet_url=datasheet_url,
    )


def _images_root(root: Path | None) -> Path | None:
    if not root:
        return None
    candidates = [
        root / "content" / "images" / "eftx.com.br",
        root / "content" / "images",
        root / "images",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _match_thumbnail(slug: str, site_root: Path | None, image_root: Path | None, pdf_path: Path) -> str | None:
    local_ref = _match_local_thumbnail(slug, pdf_path)
    if local_ref:
        return local_ref

    if not site_root or not image_root or not image_root.exists():
        return None

    slug_lower = slug.lower()
    search_terms = {
        slug_lower,
        slug_lower.replace('-', '_'),
        pdf_path.stem.lower(),
        pdf_path.stem.lower().replace('_', '-'),
    }
    for extension in (".jpg", ".png", ".jpeg", ".webp"):
        candidates = []
        for term in search_terms:
            candidates.extend(image_root.rglob(f"*{term}*{extension}"))
        if candidates:
            first = sorted(set(candidates), key=lambda p: p.name.lower())[0]
            return str(first.relative_to(site_root))

    fallback = next((p for p in image_root.rglob("*.jpg")), None)
    if fallback:
        return str(fallback.relative_to(site_root))
    return None


def _match_local_thumbnail(slug: str, pdf_path: Path) -> str | None:
    local_root = _project_root() / "IMA"
    if not local_root.is_dir():
        return []

    candidates = []
    possible_names = {
        pdf_path.stem,
        pdf_path.stem.lower(),
        pdf_path.stem.replace('-', '_'),
        slug,
        slug.replace('-', '_'),
    }
    for name in possible_names:
        for extension in (".png", ".jpg", ".jpeg", ".webp"):
            path = local_root / f"{name}{extension}"
            if path.exists():
                candidates.append(path)

    if not candidates:
        for extension in (".png", ".jpg", ".jpeg", ".webp"):
            for path in local_root.glob(f"*{extension}"):
                if slug in path.stem.lower():
                    candidates.append(path)
        candidates = sorted(set(candidates), key=lambda p: p.name.lower())

    if candidates:
        return f"IMA/{candidates[0].name}"
    return None


def _local_image_urls(limit: int | None = None) -> list[str]:
    local_root = _project_root() / "IMA"
    if not local_root.is_dir():
        return []
    files = [
        path
        for path in sorted(local_root.iterdir(), key=lambda p: p.name.lower())
        if path.suffix.lower() in _IMAGE_EXTENSIONS and path.is_file()
    ]
    if limit is not None:
        files = files[:limit]
    return [url_for("public_site.site_asset", filename=f"IMA/{path.name}") for path in files]


def list_local_images(limit: int | None = None) -> list[str]:
    return _local_image_urls(limit)


def list_pdfs_from_docs(docs_root: Path | None) -> list[dict]:
    """Return metadata for PDF files stored under docs/."""

    if not docs_root or not docs_root.exists():
        return []

    records = []
    for path in sorted(docs_root.glob("*.pdf"), key=lambda p: p.name.lower()):
        stat = path.stat()
        records.append(
            {
                "name": _pretty_name(path.stem),
                "filename": path.name,
                "path_rel": path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime),
            }
        )
    return records


def _generate_description(stem: str) -> str | None:
    phrase = stem.replace("_", " ")
    return phrase.capitalize()


def _pretty_name(value: str) -> str:
    words = [part for part in value.replace("_", " ").split() if part]
    return " ".join(word.capitalize() for word in words)


def _infer_category(name: str) -> str | None:
    upper = name.upper()
    if "UHF" in upper:
        return "UHF"
    if "VHF" in upper:
        return "VHF"
    if "FM" in upper:
        return "FM"
    if "ACESS" in upper:
        return "Acessórios"
    return None


def _slugify(value: str) -> str:
    import re

    value = (value or "produto").lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "produto"


def _documents_index() -> dict[str, SiteDocument]:
    try:
        documents = SiteDocument.query.all()
    except Exception:
        return {}

    index: dict[str, SiteDocument] = {}
    for doc in documents:
        filename = (doc.filename or "").lower()
        if filename:
            index[filename] = doc
        slug = doc.slug.lower()
        index.setdefault(slug, doc)
    return index
