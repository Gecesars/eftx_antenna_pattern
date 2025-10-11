from __future__ import annotations

from flask import url_for

from app.rs_core import units


def test_aplicativos_rf_requires_login(client):
    resp = client.get("/aplicativos-rf/", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_aplicativos_rf_page(authenticated_client, sample_cable):
    resp = authenticated_client.get("/aplicativos-rf/")
    assert resp.status_code == 200
    assert b"Aplicativos de RF" in resp.data

    post_data = {
        "sparams-form_id": "sparams",
        "sparams-magnitude_value": "0.5",
        "sparams-magnitude_unit": "linear",
        "sparams-phase_deg": "-45",
        "sparams-submit": "Calcular",
    }
    resp = authenticated_client.post("/aplicativos-rf/", data=post_data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"VSWR" in resp.data
    assert b"Return Loss" in resp.data
