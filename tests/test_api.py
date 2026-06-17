from fastapi.testclient import TestClient

from chiron.api.main import app

client = TestClient(app)


def test_health_endpoint_structure():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"chiron_http" in response.content or b"python" in response.content
