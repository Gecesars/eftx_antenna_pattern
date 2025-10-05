from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from ..models import Cable

C_LIGHT = 299_792_458.0


CABLE_DB_PER_100M = {
    "EFTX-RF240": 6.1,
    "EFTX-RF400": 3.8,
    "EFTX-RF600": 2.5,
    "COAX-1/2": 1.8,
    "COAX-7/8": 1.2,
}


def _resolve_base_loss(spec: Any) -> float:
    default_loss = 5.0
    if spec is None:
        return default_loss
    if isinstance(spec, str):
        key = spec.strip().upper()
        return float(CABLE_DB_PER_100M.get(key, default_loss))
    try:
        cable: "Cable" = spec
    except TypeError:  # pragma: no cover - defensive fallback
        return default_loss
    # Sem valor fixo: usar mapeamento por alias se disponível
    for attr in ("model_code", "display_name"):
        alias = getattr(cable, attr, None)
        if alias:
            lookup = CABLE_DB_PER_100M.get(str(alias).upper())
            if lookup is not None:
                return float(lookup)
    return default_loss


def _interp_curve(curve: dict[float, float] | dict, freq_mhz: float) -> float | None:
    try:
        items = sorted([(float(k), float(v)) for k, v in curve.items() if v is not None])
    except Exception:
        return None
    if not items:
        return None
    if len(items) == 1:
        return items[0][1]
    f = float(freq_mhz)
    # interval search
    for i in range(len(items) - 1):
        f0, a0 = items[i]
        f1, a1 = items[i + 1]
        if f0 <= f <= f1:
            # linear interp
            if f1 == f0:
                return a0
            t = (f - f0) / (f1 - f0)
            return a0 + t * (a1 - a0)
    # extrapolate
    if f < items[0][0]:
        f0, a0 = items[0]
        f1, a1 = items[1]
        if f1 == f0:
            return a0
        t = (f - f0) / (f1 - f0)
        return a0 + t * (a1 - a0)
    else:
        f0, a0 = items[-2]
        f1, a1 = items[-1]
        if f1 == f0:
            return a1
        t = (f - f0) / (f1 - f0)
        return a0 + t * (a1 - a0)


def cable_loss(length_m: float, freq_mhz: float, cable_spec: "Cable | str | None") -> float:
    if not length_m or not freq_mhz:
        return 0.0
    # Se o cabo tiver curva por frequência, use-a
    try:
        cable = cable_spec  # type: ignore
        curve = getattr(cable, "attenuation_db_per_100m_curve", None)
    except Exception:
        curve = None
    if curve:
        att = _interp_curve(curve, float(freq_mhz))
        if att is not None and att > 0:
            return (length_m / 100.0) * float(att)
    # fallback: aproximação sqrt(f)
    base_loss = _resolve_base_loss(cable_spec)
    scaling = math.sqrt(max(freq_mhz, 1) / 100)
    return (length_m / 100.0) * base_loss * scaling


def total_feeder_loss(
    length_m: float,
    freq_mhz: float,
    cable_spec: "Cable | str | None",
    splitter_loss_db: float | None,
    connector_loss_db: float | None,
) -> float:
    return (
        cable_loss(length_m, freq_mhz, cable_spec)
        + (splitter_loss_db or 0.0)
        + (connector_loss_db or 0.0)
    )



def vertical_beta_deg(frequency_mhz: float, spacing_m: float | None, tilt_deg: float | None) -> float:
    if not spacing_m or tilt_deg is None:
        return 0.0
    freq_hz = max(frequency_mhz, 0.0) * 1_000_000.0
    if freq_hz <= 0:
        return 0.0
    wavelength = C_LIGHT / freq_hz
    beta_rad = -2.0 * math.pi * spacing_m * math.sin(math.radians(tilt_deg)) / wavelength
    return math.degrees(beta_rad)
