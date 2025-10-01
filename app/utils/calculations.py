from __future__ import annotations

import math

C_LIGHT = 299_792_458.0


CABLE_DB_PER_100M = {
    "EFTX-RF240": 6.1,
    "EFTX-RF400": 3.8,
    "EFTX-RF600": 2.5,
    "COAX-1/2": 1.8,
    "COAX-7/8": 1.2,
}


def cable_loss(length_m: float, freq_mhz: float, cable_type: str | None) -> float:
    if not length_m or not freq_mhz:
        return 0.0
    key = (cable_type or "").upper()
    base_loss = CABLE_DB_PER_100M.get(key, 5.0)
    scaling = math.sqrt(max(freq_mhz, 1) / 100)
    return (length_m / 100.0) * base_loss * scaling


def total_feeder_loss(
    length_m: float,
    freq_mhz: float,
    cable_type: str | None,
    splitter_loss_db: float | None,
    connector_loss_db: float | None,
) -> float:
    return (
        cable_loss(length_m, freq_mhz, cable_type)
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
