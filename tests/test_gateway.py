import pytest
from fastapi.testclient import TestClient
from src.cluster.engine_a_gateway import app, db

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_metrics_endpoint():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "financial_summary" in data
    assert "stored_opportunities" in data["financial_summary"]

def test_opportunities_unauthorized():
    response = client.get("/api/v1/opportunities")
    assert response.status_code == 401

def test_opportunities_authorized():
    # Use pre-registered master key
    response = client.get(
        "/api/v1/opportunities",
        headers={"X-API-Key": "cluster_secret_master_key_2026"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
