import pytest

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_specs_tree(client):
    res = client.get("/api/specs")
    assert res.status_code == 200
    data = res.get_json()
    assert "specs" in data
    assert "meta" in data
    if data["specs"]:
        spec = data["specs"][0]
        assert "tsNumber" in spec
        assert "nfs" in spec
        if spec["nfs"]:
            nf = spec["nfs"][0]
            assert "nf" in nf
            assert "yamls" in nf


def test_api_specs_platform(client):
    res = client.get("/api/specs/platform")
    assert res.status_code == 200
    data = res.get_json()
    assert "specs" in data
    assert "map" in data
    assert "meta" in data
    if data["specs"]:
        item = data["specs"][0]
        assert "tsNumber" in item
        assert "platformUrl" in item
        assert "storyUrl" in item
        assert "hasYaml" in item
