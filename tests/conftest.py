from __future__ import annotations

import sys
import types
from uuid import uuid4

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db
from app.models import Cable, User
from app.utils.security import hash_password


if "matplotlib" not in sys.modules:
    matplotlib = types.ModuleType("matplotlib")
    figure_module = types.ModuleType("matplotlib.figure")

    class _DummyPatch:
        def set_facecolor(self, *_args, **_kwargs):
            return None

    class _DummyAxis:
        def plot(self, *_args, **_kwargs):
            return None

        def set_xlabel(self, *_args, **_kwargs):
            return None

        def set_ylabel(self, *_args, **_kwargs):
            return None

        def grid(self, *_args, **_kwargs):
            return None

        def set_facecolor(self, *_args, **_kwargs):
            return None

        def axvline(self, *_args, **_kwargs):
            return None

    class DummyFigure:
        def __init__(self, *_args, **_kwargs):
            self.patch = _DummyPatch()

        def add_subplot(self, *_args, **_kwargs):
            return _DummyAxis()

        def tight_layout(self):
            return None

        def savefig(self, buf, *_args, **_kwargs):
            buf.write(b"")

    figure_module.Figure = DummyFigure
    matplotlib.figure = figure_module
    sys.modules["matplotlib"] = matplotlib
    sys.modules["matplotlib.figure"] = figure_module


@pytest.fixture(scope="session")
def app():
    app = create_app('testing')
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_ENGINE_OPTIONS={
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        SERVER_NAME='test.local',
        TESTING=True,
    )
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='tester@eftx.com').first():
            user = User(
                email='tester@eftx.com',
                password_hash=hash_password('tester'),
                full_name='Test User',
                email_confirmed=True,
            )
            db.session.add(user)
            db.session.commit()
        else:
            user = User.query.filter_by(email='tester@eftx.com').first()
            if user and not user.email_confirmed:
                user.email_confirmed = True
                db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_context(app):
    with app.app_context():
        yield


@pytest.fixture()
def sample_cable(app_context):
    cable = Cable(
        display_name=f'FTX RF400 {uuid4()}'.strip(),
        model_code=f'RF400-{uuid4()}'.strip(),
        impedance_ohms=50.0,
        velocity_factor=0.82,
        attenuation_db_per_100m_curve={
            "points": [
                {"frequency_mhz": 100, "attenuation": 4.1},
                {"frequency_mhz": 300, "attenuation": 6.5},
                {"frequency_mhz": 600, "attenuation": 9.8},
            ]
        },
    )
    db.session.add(cable)
    db.session.commit()
    return cable


@pytest.fixture()
def authenticated_client(app, client):
    with app.app_context():
        user = User.query.first()
    response = client.post(
        '/auth/login',
        data={'email': user.email, 'password': 'tester'},
        follow_redirects=True,
    )
    assert response.status_code in (200, 302)
    return client
