"""
Unit and integration tests for FastAPI backend pipeline.
"""

from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "FactLens" in data["service"]


def test_analyze_empty_string_returns_400():
    response = client.post("/api/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_opinion_returns_not_applicable():
    """
    Subjective opinion sentences should be extracted and marked as Opinion,
    yielding Not Applicable for fact checking.
    """
    response = client.post("/api/analyze", json={"text": "I think this restaurant is wonderful."})
    assert response.status_code == 200
    data = response.json()
    assert data["fact_check"]["all_opinion"] is True
    assert data["fact_check"]["overall_verdict"] == "Not Applicable"
    assert len(data["fact_check"]["sub_claims"]) == 1
    assert data["fact_check"]["sub_claims"][0]["status"] == "Opinion"


def test_analyze_factual_claim_retrieves_evidence():
    """
    A factual claim about Eiffel Tower should retrieve the corresponding FEVER passage.
    """
    query = "The Eiffel Tower was completed in 1889."
    response = client.post("/api/analyze", json={"text": query})
    assert response.status_code == 200
    data = response.json()

    fc = data["fact_check"]
    assert fc["all_opinion"] is False
    assert len(fc["sub_claims"]) >= 1

    claim_res = fc["sub_claims"][0]
    assert claim_res["status"] == "Fact"
    assert claim_res["verdict"] == "Supported"
    assert "1889" in claim_res["evidence"]
    assert "FEVER" in claim_res["source"]
