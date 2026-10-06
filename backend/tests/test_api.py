from fastapi.testclient import TestClient
from app.api.main import app

client = TestClient (app)

def test_health_check ():
    response = client.get ("/api/health")
    assert response.status_code == 200
    data = response.json ()
    assert data ["status"] == "ok"
    assert "FactLens" in data ["service"]

def test_analyze_empty_string_returns_400 ():
    response = client.post ("/api/analyze", json = {"text": "   "})
    assert response.status_code == 400
    assert "empty" in response.json () ["detail"].lower ()

def test_analyze_opinion_returns_not_applicable ():
    # subjective opinion sentences should be marked as opinion
    response = client.post ("/api/analyze", json = {"text": "I think this restaurant is wonderful."})
    assert response.status_code == 200
    data = response.json ()
    assert data ["fact_check"] ["all_opinion"] is True
    assert data ["fact_check"] ["overall_verdict"] == "Not Applicable"
    assert len (data ["fact_check"] ["sub_claims"]) == 1
    assert data ["fact_check"] ["sub_claims"] [0] ["status"] == "Opinion"

def test_analyze_factual_claim_retrieves_evidence ():
    # factual claim should retrieve matching evidence
    query = "The Eiffel Tower was completed in 1889."
    response = client.post ("/api/analyze", json = {"text": query})
    assert response.status_code == 200
    data = response.json ()

    fact_check = data ["fact_check"]
    assert fact_check ["all_opinion"] is False
    assert len (fact_check ["sub_claims"]) >= 1

    claim_result = fact_check ["sub_claims"] [0]
    assert claim_result ["status"] == "Fact"
    assert claim_result ["verdict"] == "Supported"
    assert "1889" in claim_result ["evidence"]
    assert "Local corpus" in claim_result ["source"]
