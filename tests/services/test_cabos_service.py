from __future__ import annotations

import math

from app.services import cabos_service
from app.rs_core import units
from app.extensions import db
from app.models import Cable


def test_calcular_perda_total(sample_cable):
    freq_hz = units.to_hz(200, "mhz")
    detalhe = cabos_service.calcular_perda_total(sample_cable.id, freq_hz, 50.0, conectores_db=[0.2, 0.15])
    assert math.isclose(detalhe["perda_cabo_db"], 2.7417, rel_tol=1e-3)
    assert math.isclose(detalhe["perda_total_db"], 3.0917, rel_tol=1e-3)
    assert not detalhe["extrapolado"]


def test_interpolacao_extrapolada(sample_cable):
    freq_hz = units.to_hz(50, "mhz")
    detalhe = cabos_service.calcular_perda_total(sample_cable.id, freq_hz, 20.0)
    assert detalhe["extrapolado"]


def test_erro_sem_curva(app_context):
    cable = Cable(display_name="Sem Curva", model_code="SC-01", impedance_ohms=50.0)
    db.session.add(cable)
    db.session.commit()
    try:
        cabos_service.calcular_perda_total(cable.id, units.to_hz(100, "mhz"), 10.0)
        assert False, "Esperado ValueError"
    except ValueError:
        pass
