import os
import pytest
from app.retrieval.urdu_preprocessor import (
    normalize_urdu_text,
    tokenize_urdu,
    URDU_STOPWORDS,
)
from app.retrieval.searcher import (
    CorpusIndex,
    retrieve,
    load_dataset_from_file,
    _URDU_SAMPLE_DATASET_FILE,
)

def test_urdu_normalizer_replaces_arabic_variants():
    # Arabic Yeh -> Urdu Yeh, Arabic Kaf -> Urdu Kaf, Arabic Heh -> Urdu Goal Heh
    arabic_text = "أمريكا كذلك مدينة"
    normalized = normalize_urdu_text(arabic_text)
    assert "\u064a" not in normalized  # Arabic yeh replaced
    assert "\u0643" not in normalized  # Arabic kaf replaced

def test_urdu_normalizer_strips_aerab_and_tatweel():
    # Text with Zabar, Zer, Pesh, Tashdeed, and Tatweel
    aerab_text = "مُحَمَّــد"
    normalized = normalize_urdu_text(aerab_text)
    assert "ـ" not in normalized
    assert normalized == "محمد"

def test_urdu_tokenizer_removes_stopwords():
    sample = "پاکستان ایک خوبصورت ملک ہے اور اسلام آباد اس کا دارالحکومت ہے۔"
    tokens = tokenize_urdu(sample, remove_stopwords=True)
    # Stopwords like ہے, اور, اس, کا, ایک should be filtered out
    assert "ہے" not in tokens
    assert "اور" not in tokens
    assert "کا" not in tokens
    assert "پاکستان" in tokens
    assert "اسلام" in tokens

def test_urdu_corpus_sample_exists_and_valid():
    assert os.path.exists(_URDU_SAMPLE_DATASET_FILE)
    passages = load_dataset_from_file(_URDU_SAMPLE_DATASET_FILE)
    assert len(passages) >= 100
    for p in passages[:10]:
        assert "id" in p
        assert "text" in p
        assert "source" in p
        assert len(p["text"]) > 10

def test_custom_urdu_corpus_retrieval():
    corpus = [
        {"id": "1", "source": "News", "title": "Weather", "text": "کل اسلام آباد اور راولپنڈی میں شدید بارش متوقع ہے۔"},
        {"id": "2", "source": "Sports", "title": "Cricket", "text": "بابر اعظم نے شاندار سنچری اسکور کی اور ٹیم کو فتح دلائی۔"},
        {"id": "3", "source": "Health", "title": "COVID", "text": "کورونا وائرس کی ویکسین محفوظ اور موثر ثابت ہوئی ہے۔"},
    ]
    index = CorpusIndex(corpus, is_urdu_corpus=True)
    results = index.search("بابر اعظم نے سنچری بنائی", top_k=1)
    assert len(results) == 1
    assert results[0].passage_id == "2"
    assert "بابر اعظم" in results[0].text

def test_bilingual_routing_in_retrieve():
    # Urdu query should match Urdu index
    results_ur = retrieve("صدر ٹرمپ نے اقدامات", top_k=1)
    assert len(results_ur) > 0
    # English query should match English index
    results_en = retrieve("COVID-19 vaccine clinical trials", top_k=1)
    assert len(results_en) > 0
    assert "vaccine" in results_en[0].text.lower()
