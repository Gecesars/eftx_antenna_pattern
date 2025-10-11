from __future__ import annotations

import math

from app.rs_core import lines, units


def test_electrical_length_phase():
    result = lines.electrical_length(units.to_hz(100, "mhz"), units.to_meters(2.5, "m"), velocity_factor=0.82)
    assert math.isclose(result.phase_deg, 6.1069, rel_tol=1e-4)
    assert math.isclose(result.guided_wavelength_m, 2.4583, rel_tol=1e-4)


def test_length_from_phase():
    result = lines.length_from_phase(units.to_hz(100, "mhz"), 90, velocity_factor=0.82)
    assert math.isclose(result.physical_length_m, 0.61457, rel_tol=1e-4)
