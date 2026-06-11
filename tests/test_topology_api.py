import pytest

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_topology_page(client):
    res = client.get("/topology")
    assert res.status_code == 200
    assert b"NF Topology" in res.data


def test_topology_api(client):
    res = client.get("/api/topology?coreOnly=true&minWeight=2")
    assert res.status_code == 200
    data = res.get_json()
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data
