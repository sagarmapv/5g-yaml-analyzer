import pytest

from backend.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_api_map(client):
    res = client.get("/api/map")
    assert res.status_code == 200
    data = res.get_json()
    assert "nfs" in data
    assert "meta" in data
    if data["nfs"]:
        nf = data["nfs"][0]
        assert "nf" in nf
        assert "specs" in nf
        if nf["specs"]:
            spec = nf["specs"][0]
            assert "tsNumber" in spec
            assert "yamls" in spec
