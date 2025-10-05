from __future__ import annotations

import json
import os
from typing import Any, Dict, Tuple

import google.generativeai as genai
from flask import current_app
from werkzeug.datastructures import FileStorage

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore


EXTRACT_KEYS = [
    "name",
    "model_number",
    "description",
    "nominal_gain_dbd",
    "polarization",
    "frequency_min_mhz",
    "frequency_max_mhz",
    "manufacturer",
]


def _save_upload(file: FileStorage) -> Tuple[str, str]:
    root = current_app.config.get("EXPORT_ROOT", "exports")
    target_dir = os.path.join(root, "uploads", "antennas")
    os.makedirs(target_dir, exist_ok=True)
    filename = file.filename or "datasheet.pdf"
    safe_name = filename.replace("/", "_").replace("\\", "_")
    path = os.path.join(target_dir, safe_name)
    file.stream.seek(0)
    file.save(path)
    return path, safe_name


def _extract_text_from_pdf(path: str) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n\n".join(t.strip() for t in texts if t and t.strip())
    except Exception:
        return ""


def _extract_first_image(path: str) -> str | None:
    """Best-effort: extract first embedded image from the first PDF pages.
    Returns saved path or None.
    """
    if PdfReader is None:
        return None
    try:
        reader = PdfReader(path)
        out_dir = os.path.join(current_app.config.get("EXPORT_ROOT", "exports"), "uploads", "antennas", "thumbs")
        os.makedirs(out_dir, exist_ok=True)
        for page_index, page in enumerate(reader.pages[:3]):
            images = getattr(page, "images", [])
            for img in images:
                img_name = getattr(img, "name", f"img_{page_index}")
                ext = ".png"
                if isinstance(img_name, str) and "." in img_name:
                    ext = os.path.splitext(img_name)[1] or ".png"
                out_path = os.path.join(out_dir, f"thumb_{os.path.basename(path)}_{page_index}{ext}")
                try:
                    with open(out_path, "wb") as fh:
                        fh.write(img.data)
                    return out_path
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _coerce(payload: Dict[str, Any]) -> Dict[str, Any]:
    def _to_float(x):
        try:
            if x is None:
                return None
            if isinstance(x, (int, float)):
                return float(x)
            s = str(x).strip().replace(",", ".")
            for suf in ["dBd", "dBi", "MHz"]:
                s = s.replace(suf, "").strip()
            return float(s)
        except Exception:
            return None

    payload["nominal_gain_dbd"] = _to_float(payload.get("nominal_gain_dbd"))
    payload["frequency_min_mhz"] = _to_float(payload.get("frequency_min_mhz"))
    payload["frequency_max_mhz"] = _to_float(payload.get("frequency_max_mhz"))
    return payload


def extract_antenna_from_datasheet(file: FileStorage) -> Dict[str, Any]:
    path, _ = _save_upload(file)
    text = _extract_text_from_pdf(path)
    if not text:
        file.stream.seek(0)
        raw = file.stream.read(4000)
        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    api_key = current_app.config.get("GEMINI_API_KEY")
    model_name = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        return {"error": "GEMINI_API_KEY ausente", "datasheet_path": path}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    prompt = (
        "Receba o texto do datasheet de uma antena. Extraia apenas metadados gerais (sem tabelas de diagrama), e responda APENAS com JSON válido. "
        "Campos: name, model_number, description, nominal_gain_dbd (dBd), polarization, frequency_min_mhz, frequency_max_mhz, manufacturer.\n\n"
        "Se algum valor não existir, use null.\n\nTexto:\n" + (text[:12000] if text else "")
    )
    try:
        response = model.generate_content([prompt])
        content = getattr(response, "text", None) or ""
        if not content:
            candidates = getattr(response, "candidates", None) or []
            for c in candidates:
                parts = getattr(getattr(c, "content", None), "parts", None)
                if parts:
                    for p in parts:
                        if getattr(p, "text", None):
                            content += p.text
        content = (content or "").strip()
        start = content.find("{")
        end = content.rfind("}")
        json_text = content[start : end + 1] if start >= 0 and end >= start else "{}"
        data = json.loads(json_text)
    except Exception as exc:
        return {"error": f"Falha ao consultar Gemini: {exc}", "datasheet_path": path}

    data = {k: data.get(k) for k in EXTRACT_KEYS if k in data}
    # Fabricante padrao fixo
    data["manufacturer"] = "EFTX Broadcast & Telecom"
    data["datasheet_path"] = path
    thumb = _extract_first_image(path)
    if thumb:
        data["thumbnail_path"] = thumb
    return _coerce(data)
