from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

import numpy as np

from ..models import Antenna, PatternType, Project
from ..utils.calculations import vertical_beta_deg

C_LIGHT = 299_792_458.0
EPSILON = 1e-12


def resample_pattern(angles: Iterable[float], amplitudes: Iterable[float], start: int, stop: int, step: int) -> tuple[np.ndarray, np.ndarray]:
    src_angles = np.asarray(list(angles), dtype=float)
    src_amp = np.asarray(list(amplitudes), dtype=float)
    dest_angles = np.arange(start, stop + step, step, dtype=float)
    sort_idx = np.argsort(src_angles)
    src_angles = np.mod(src_angles[sort_idx], 360)
    src_amp = src_amp[sort_idx]
    # extend for circular interpolation
    src_angles_ext = np.concatenate((src_angles - 360, src_angles, src_angles + 360))
    src_amp_ext = np.concatenate((src_amp, src_amp, src_amp))
    dest_amp = np.interp(dest_angles, src_angles_ext, src_amp_ext)
    return dest_angles, dest_amp


def resample_vertical(angles: Iterable[float], amplitudes: Iterable[float]) -> tuple[np.ndarray, np.ndarray]:
    src_angles = np.asarray(list(angles), dtype=float)
    src_amp = np.asarray(list(amplitudes), dtype=float)
    dest_angles = np.arange(-90, 91, 1, dtype=float)
    sort_idx = np.argsort(src_angles)
    src_angles = src_angles[sort_idx]
    src_amp = src_amp[sort_idx]
    dest_amp = np.interp(dest_angles, src_angles, src_amp, left=src_amp[0], right=src_amp[-1])
    return dest_angles, dest_amp


def wavelength_m(frequency_mhz: float) -> float:
    return C_LIGHT / (frequency_mhz * 1_000_000)


def array_factor(
    count: int,
    spacing_m: float,
    beta_deg: float,
    level_amp: float,
    wave_number: float,
    angles_rad: np.ndarray,
    projection: str,
) -> np.ndarray:
    if count <= 1:
        return np.ones_like(angles_rad)
    beta = math.radians(beta_deg)
    indices = np.arange(count, dtype=float).reshape((-1, 1))
    weights = (level_amp ** indices) if level_amp not in (None, 0) else np.ones_like(indices)
    if projection == "horizontal":
        phase = wave_number * spacing_m * np.sin(angles_rad)
    else:
        phase = wave_number * spacing_m * np.cos(angles_rad)
    af = np.sum(weights * np.exp(1j * (indices * beta + phase)), axis=0)
    return np.abs(af)


def normalise(array: np.ndarray, mode: str) -> np.ndarray:
    if mode == "sum":
        total = np.sum(array)
        return array / total if total > EPSILON else array
    if mode == "first":
        base = array[0]
        return array / base if abs(base) > EPSILON else array
    peak = np.max(array)
    return array / peak if peak > EPSILON else array


def compose_horizontal_pattern(project: Project) -> tuple[np.ndarray, np.ndarray]:
    antenna: Antenna = project.antenna
    hrp = antenna.pattern_for(PatternType.HRP)
    if not hrp:
        angles = np.arange(-180, 181)
        return angles, np.ones_like(angles, dtype=float)
    base_angles, base_amp = np.array(hrp.angles_deg, dtype=float), np.array(hrp.amplitudes_linear, dtype=float)
    angles, amp = resample_pattern(base_angles, base_amp, -180, 180, 1)

    wave_num = 2 * math.pi / wavelength_m(project.frequency_mhz)
    af = array_factor(
        count=project.h_count,
        spacing_m=project.h_spacing_m,
        beta_deg=project.h_beta_deg,
        level_amp=project.h_level_amp if project.h_level_amp else 1.0,
        wave_number=wave_num,
        angles_rad=np.radians(angles + project.h_step_deg),
        projection="horizontal",
    )
    af = normalise(af, project.h_norm_mode)
    composed = amp * af
    return angles, composed


def compose_vertical_pattern(project: Project) -> tuple[np.ndarray, np.ndarray]:
    antenna: Antenna = project.antenna
    vrp = antenna.pattern_for(PatternType.VRP)
    if not vrp:
        angles = np.arange(-90, 91)
        return angles, np.ones_like(angles, dtype=float)
    base_angles, base_amp = np.array(vrp.angles_deg, dtype=float), np.array(vrp.amplitudes_linear, dtype=float)
    angles, amp = resample_vertical(base_angles, base_amp)
    wave_num = 2 * math.pi / wavelength_m(project.frequency_mhz)
    beta_deg = vertical_beta_deg(project.frequency_mhz, project.v_spacing_m or 0.0, project.v_tilt_deg or 0.0)
    project.v_beta_deg = beta_deg
    af = array_factor(
        count=project.v_count,
        spacing_m=project.v_spacing_m or 0.0,
        beta_deg=beta_deg,
        level_amp=project.v_level_amp if project.v_level_amp else 1.0,
        wave_number=wave_num,
        angles_rad=np.radians(angles),
        projection="vertical",
    )
    af = normalise(af, project.v_norm_mode)
    composed = amp * af
    return angles, composed


def compute_erp(project: Project) -> dict[str, np.ndarray]:
    angles_deg, hrp = compose_horizontal_pattern(project)
    v_angles_deg, vrp = compose_vertical_pattern(project)

    # Use the VRP value near 0° elevation to scale ERP radials (horizon)
    horizon_idx = int(np.argmin(np.abs(v_angles_deg)))
    vertical_scalar = max(vrp[horizon_idx], EPSILON)

    nominal_gain_dbd = project.antenna.nominal_gain_dbd or 0.0
    power_w = max(project.tx_power_w, EPSILON)
    feeder_loss_db = project.feeder_loss_db if project.feeder_loss_db is not None else 0.0

    hrp_composed = hrp * vertical_scalar
    hrp_linear = np.clip(hrp_composed, EPSILON, None)
    attenuation_db = 20 * np.log10(np.maximum(hrp_linear, EPSILON))
    gain_dbd = nominal_gain_dbd - attenuation_db
    erp_dbw = 10 * np.log10(power_w) - feeder_loss_db + gain_dbd
    erp_w = 10 ** (erp_dbw / 10)
    return {
        "angles_deg": angles_deg,
        "hrp_linear": hrp,
        "vrp_angles_deg": v_angles_deg,
        "vrp_linear": vrp,
        "attenuation_db": attenuation_db,
        "gain_dbd": gain_dbd,
        "erp_dbw": erp_dbw,
        "erp_w": erp_w,
        "vertical_scalar": vertical_scalar,
    }


def export_pat(file_path: Path, data: dict[str, np.ndarray]) -> None:
    angles = data["angles_deg"].astype(int)
    erp_dbw = data["erp_dbw"]
    with file_path.open("w", encoding="ascii") as fh:
        fh.write("# EFTX PAT export\n")
        for angle, value in zip(angles, erp_dbw):
            fh.write(f"{int(angle % 360):03d}\t{value:.3f}\n")


def export_prn(file_path: Path, data: dict[str, np.ndarray]) -> None:
    angles = data["angles_deg"].astype(int)
    erp_w = data["erp_w"]
    with file_path.open("w", encoding="ascii") as fh:
        fh.write("Angle,ERP_W\n")
        for angle, value in zip(angles, erp_w):
            fh.write(f"{int(angle % 360)},{value:.6f}\n")
