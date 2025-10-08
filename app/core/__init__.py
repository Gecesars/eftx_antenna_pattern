"""Core utilities for the EFTX antenna application."""

from .assistant_institutional import answer_with_gemini
from .site_content import (
    discover_site_root,
    list_local_images,
    load_products_from_site,
    list_pdfs_from_docs,
)

__all__ = [
    "answer_with_gemini",
    "discover_site_root",
    "list_local_images",
    "load_products_from_site",
    "list_pdfs_from_docs",
]
