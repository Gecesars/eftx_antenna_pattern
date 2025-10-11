from __future__ import annotations

import math

from app.rs_core import microstrip, units


def test_microstrip_width_for_impedance():
    result = microstrip.width_for_impedance(50.0, 4.3, 1.6e-3, 35e-6)
    width_mm = units.from_meters(result.width_m, "mm")
    assert math.isclose(width_mm, 3.0464, rel_tol=1e-4)
    assert math.isclose(result.width_over_height, 1.9040, rel_tol=1e-4)
    assert math.isclose(result.effective_eps, 3.2683, rel_tol=1e-4)
