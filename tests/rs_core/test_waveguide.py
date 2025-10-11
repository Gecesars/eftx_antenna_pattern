from __future__ import annotations

import math

from app.rs_core import units, waveguide


def test_waveguide_cutoff_te10_wr90():
    summary = waveguide.cutoff_summary(
        "TE",
        1,
        0,
        units.to_meters(22.86, "mm"),
        units.to_meters(10.16, "mm"),
    )
    assert math.isclose(summary.cutoff_ghz, 6.5571, rel_tol=1e-4)


def test_waveguide_propagation_above_cutoff():
    summary = waveguide.cutoff_summary(
        "TE",
        1,
        0,
        units.to_meters(22.86, "mm"),
        units.to_meters(10.16, "mm"),
        units.to_hz(10, "ghz"),
    )
    propagation = waveguide.propagation_parameters(units.to_hz(10, "ghz"), summary.cutoff_hz)
    assert propagation.guide_wavelength_m is not None
    assert math.isclose(propagation.guide_wavelength_m, 0.039707, rel_tol=1e-4)
