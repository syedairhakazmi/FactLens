import pytest
from fastapi.testclient import TestClient
from app.translation.translator import is_urdu, translate_ur_to_en, translate_en_to_ur, get_urdu_verdict, get_urdu_reason
from app.api.main import app
from app.coreference import resolver

@pytest.fixture (autouse = True)
def mock_coref_model (monkeypatch):
    monkeypatch.setattr (resolver, "_get_model", lambda: None)

client = TestClient (app)

def test_is_urdu_detects_urdu_script ():
    # verify that urdu text is identified
    assert is_urdu ("پیرس فرانس کا دارالحکومت ہے۔") is True
    assert is_urdu ("پانی 100 ڈگری سینٹی گریڈ پر ابلتا ہے۔") is True
    assert is_urdu ("یہ ایک دعویٰ ہے۔") is True

def test_is_urdu_returns_false_for_english ():
    # verify that english text is not labeled as urdu
    assert is_urdu ("Paris is the capital of France.") is False
    assert is_urdu ("Water boils at 100 degrees Celsius.") is False
    assert is_urdu ("") is False
    assert is_urdu (None) is False

def test_get_urdu_verdict_mapping ():
    # verify mapping of english verdicts to urdu
    assert get_urdu_verdict ("Supported") == "تصدیق شدہ"
    assert get_urdu_verdict ("Refuted") == "مسترد شدہ"
    assert get_urdu_verdict ("Not Enough Evidence") == "ناکافی شواہد"
    assert get_urdu_verdict ("Mixed") == "ملا جلا"
    assert get_urdu_verdict ("Opinion") == "رائے"
    assert get_urdu_verdict ("Non-Checkable") == "ناقابل تصدیق"

def test_analyze_urdu_input_end_to_end (monkeypatch):
    # test full api with urdu input
    monkeypatch.setattr ("app.api.main.translate_ur_to_en", lambda text: "Paris is the capital of France, and it hosts the Eiffel Tower.")
    monkeypatch.setattr ("app.api.main.translate_en_to_ur", lambda text: "پیرس فرانس کا دارالحکومت ہے۔" if "capital" in text else "پیرس ایفل ٹاور کی میزبانی کرتا ہے۔")

    payload = {"text": "پیرس فرانس کا دارالحکومت ہے اور ایفل ٹاور کی میزبانی کرتا ہے۔"}
    response = client.post ("/api/analyze", json = payload)
    assert response.status_code == 200
    data = response.json ()

    assert data ["language"] == "ur"
    assert data ["original_text"] == payload ["text"]
    assert "Paris" in data ["original_text_en"]

    fact_check = data ["fact_check"]
    assert fact_check ["language"] == "ur"
    assert fact_check ["overall_verdict"] == "Supported"
    assert fact_check ["overall_verdict_ur"] == "تصدیق شدہ"
    assert len (fact_check ["sub_claims"]) >= 2

    first_claim = fact_check ["sub_claims"] [0]
    assert first_claim ["status"] == "Fact"
    assert first_claim ["verdict"] == "Supported"
    assert first_claim ["verdict_ur"] == "تصدیق شدہ"
    assert first_claim ["text_ur"] is not None
