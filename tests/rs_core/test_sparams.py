from __future__ import annotations

import math

from app.rs_core import sparams


def test_sparameter_conversions_linear_to_db():
    result = sparams.sparameter_from_linear_phase(0.5, -45)
    assert math.isclose(result.magnitude_db, -6.0206, rel_tol=1e-4)
    assert math.isclose(result.vswr, 3.0, rel_tol=1e-6)
    assert math.isclose(result.return_loss_db, 6.0206, rel_tol=1e-4)


def test_vswr_return_loss_roundtrip():
    gamma = sparams.gamma_from_vswr(1.2)
    rl = sparams.return_loss_from_vswr(1.2)
    assert math.isclose(gamma, 0.090909, rel_tol=1e-6)
    assert math.isclose(rl, 20.8278, rel_tol=1e-4)
    vswr = sparams.vswr_from_gamma(gamma)
    assert math.isclose(vswr, 1.2, rel_tol=1e-6)


def test_db_linear_amplitude():
    linear = sparams.magnitude_db_to_linear(-3.0)
    assert math.isclose(linear, 0.7079457, rel_tol=1e-6)
    db = sparams.magnitude_linear_to_db(linear)
    assert math.isclose(db, -3.0, rel_tol=1e-6)
