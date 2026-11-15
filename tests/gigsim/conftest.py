"""GigSim test fixtures: a session-scoped embedded Postgres (pgserver) and a TestClient wrapper."""

from __future__ import annotations

import shutil
import tempfile

import pgserver
import pytest
from fastapi.testclient import TestClient
from gigsim_testkit import Api, make_settings

from gigsim.app import create_app


@pytest.fixture(scope="session")
def pg_uri():
    tmp = tempfile.mkdtemp(prefix="gigsim_pg_")
    srv = pgserver.get_server(tmp, cleanup_mode="stop")
    try:
        yield srv.get_uri()
    finally:
        try:
            srv.cleanup()
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="session")
def settings(pg_uri):
    return make_settings(pg_uri)


@pytest.fixture(scope="session")
def _client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


@pytest.fixture()
def api(_client):
    a = Api(_client)
    r = a.admin("/v1/admin/reset")
    assert r.status_code == 200, r.text
    return a
