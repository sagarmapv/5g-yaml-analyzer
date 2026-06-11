import pytest

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert "yamlCount" in data


def test_index_endpoint(client):
    res = client.get("/api/index")
    assert res.status_code == 200
    assert isinstance(res.get_json(), dict)


def test_legacy_index_redirect(client):
    res = client.get("/index")
    assert res.status_code == 302


def test_invalid_filename_rejected(client):
    res = client.get("/api/yaml/test..yaml")
    assert res.status_code == 400


def test_search_empty_query(client):
    res = client.get("/api/search")
    assert res.status_code == 200
    assert res.get_json() == []
