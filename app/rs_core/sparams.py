"""Conversões e utilidades para parâmetros S."""
from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

from . import units


class SParameterError(ValueError):
    """Erro de domínio para cálculos de S-parâmetros."""


@dataclass(slots=True)
class SParameterResult:
    magnitude_linear: float
    magnitude_db: float
    phase_deg: float
    gamma_complex: complex
    gamma_mag: float
    reflection_loss_db: float
    return_loss_db: float
    vswr: float
    rho: float


def magnitude_db_to_linear(db_value: float) -> float:
    return pow(10.0, db_value / 20.0)


def magnitude_linear_to_db(magnitude: float) -> float:
    magnitude = units.sanitize_positive(magnitude, field="|S|")
    return 20.0 * math.log10(magnitude)


def power_db_to_linear(db_value: float) -> float:
    return pow(10.0, db_value / 10.0)


def power_linear_to_db(linear: float) -> float:
    linear = units.sanitize_positive(linear, field="potência")
    return 10.0 * math.log10(linear)


def gamma_from_vswr(vswr: float) -> float:
    vswr = units.sanitize_positive(vswr, field="VSWR")
    if vswr < 1.0:
        raise SParameterError("VSWR deve ser >= 1.0")
    return (vswr - 1.0) / (vswr + 1.0)


def vswr_from_gamma(gamma_mag: float) -> float:
    if not 0 <= gamma_mag < 1:
        raise SParameterError("|Γ| deve estar no intervalo [0, 1).")
    return (1.0 + gamma_mag) / (1.0 - gamma_mag)


def return_loss_from_gamma(gamma_mag: float) -> float:
    if not 0 < gamma_mag < 1:
        raise SParameterError("|Γ| deve estar no intervalo (0, 1).")
    return -20.0 * math.log10(gamma_mag)


def gamma_from_return_loss(return_loss_db: float) -> float:
    if return_loss_db <= 0:
        raise SParameterError("RL deve ser positivo (dB).")
    return pow(10.0, -return_loss_db / 20.0)



def vswr_from_return_loss(return_loss_db: float) -> float:
    gamma = gamma_from_return_loss(return_loss_db)
    return vswr_from_gamma(gamma)


def return_loss_from_vswr(vswr: float) -> float:
    gamma = gamma_from_vswr(vswr)
    return return_loss_from_gamma(gamma)

def mismatch_loss_db(gamma_mag: float) -> float:
    if not 0 <= gamma_mag < 1:
        raise SParameterError("|Γ| deve estar no intervalo [0, 1).")
    power_ratio = 1.0 - gamma_mag**2
    if power_ratio <= 0:
        raise SParameterError("Perda por desadaptação indefinida para |Γ| → 1.")
    return -10.0 * math.log10(power_ratio)


def sparameter_from_linear_phase(magnitude_linear: float, phase_deg: float) -> SParameterResult:
    magnitude_linear = units.sanitize_positive(magnitude_linear, field="|S|")
    phase_rad = math.radians(phase_deg)
    gamma_complex = cmath.rect(magnitude_linear, phase_rad)
    gamma_mag = abs(gamma_complex)
    if gamma_mag >= 1:
        # ainda podemos retornar VSWR infinito
        vswr = math.inf
        rl = 0.0
    else:
        vswr = vswr_from_gamma(gamma_mag)
        rl = return_loss_from_gamma(gamma_mag)
    mismatch = mismatch_loss_db(min(gamma_mag, 0.999999)) if gamma_mag < 1 else math.inf
    return SParameterResult(
        magnitude_linear=magnitude_linear,
        magnitude_db=magnitude_linear_to_db(magnitude_linear),
        phase_deg=phase_deg,
        gamma_complex=gamma_complex,
        gamma_mag=gamma_mag,
        reflection_loss_db=mismatch,
        return_loss_db=rl,
        vswr=vswr,
        rho=gamma_mag,
    )


def sparameter_from_db_phase(magnitude_db: float, phase_deg: float) -> SParameterResult:
    magnitude_linear = magnitude_db_to_linear(magnitude_db)
    return sparameter_from_linear_phase(magnitude_linear, phase_deg)


def sparameter_from_vswr(vswr: float, phase_deg: float = 0.0) -> SParameterResult:
    gamma_mag = gamma_from_vswr(vswr)
    result = sparameter_from_linear_phase(gamma_mag, phase_deg)
    return result


def normalized_phase(angle_deg: float) -> float:
    """Normaliza fase para [-180, 180)."""
    angle = math.fmod(angle_deg, 360.0)
    if angle >= 180.0:
        angle -= 360.0
    if angle < -180.0:
        angle += 360.0
    return angle
