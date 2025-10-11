from __future__ import annotations

import math

from app.rs_core import diffraction_knife_edge, units


def test_knife_edge_loss():
    result = diffraction_knife_edge.compute_knife_edge(
        frequency_hz=units.to_hz(2.4, "ghz"),
        d1_m=units.to_meters(5000, "m"),
        d2_m=units.to_meters(6500, "m"),
        tx_height_m=35,
        rx_height_m=28,
        obstacle_height_m=55,
    )
    assert math.isclose(result.v, 1.7344, rel_tol=1e-4)
    assert math.isclose(result.loss_db, 17.906, rel_tol=1e-4)
    assert math.isclose(result.fresnel_radius_m, 18.7887, rel_tol=1e-4)
