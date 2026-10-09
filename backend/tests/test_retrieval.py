import os
from app.retrieval.searcher import (
    _tokenize,
    retrieve,
    load_dataset_from_file,
    save_dataset_to_file,
    CorpusIndex,
)

def test_tokenizer_strips_punctuation ():
    tokens = _tokenize ("The vaccine causes infertility in most patients.")
    assert "patients" in tokens
    assert "patients." not in tokens

def test_tokenizer_lowercases ():
    tokens = _tokenize ("The Vaccine Causes Infertility")
    assert "vaccine" in tokens
    assert "Vaccine" not in tokens

def test_tokenizer_removes_stopwords ():
    tokens = _tokenize ("The vaccine was approved in the trial.")
    assert "the" not in tokens
    assert "in" not in tokens
    assert "was" not in tokens
    assert "vaccine" in tokens
    assert "approved" in tokens
    assert "trial" in tokens

def test_tokenizer_handles_multiple_punctuation_marks ():
    tokens = _tokenize ("Really?! The claim, allegedly, is false.")
    assert "really" in tokens
    assert "claim" in tokens
    assert "allegedly" in tokens
    assert "false" in tokens
    assert all (t.isalnum () for t in tokens)

def test_retrieve_ranks_relevant_passage_above_irrelevant_one ():
    corpus = [
        ("The Eiffel Tower, located in Paris, France, was completed in 1889.", "wiki"),
        ("The vaccine received regulatory approval after completing clinical trials.", "local"),
    ]
    results = retrieve ("The vaccine causes infertility in most patients.", corpus, top_k = 2)
    assert results [0].source == "local"

def test_retrieve_returns_empty_list_for_empty_corpus ():
    assert retrieve ("any query", [], top_k = 3) == []

def test_load_and_save_dataset_file (tmp_path):
    temp_file = str (tmp_path / "test_corpus.jsonl")
    data = [
        {"id": "doc_1", "title": "Test 1", "source": "FEVER", "text": "This is test passage one."},
        {"id": "doc_2", "title": "Test 2", "source": "SciFact", "text": "This is test passage two."},
    ]
    save_dataset_to_file (data, temp_file)
    loaded = load_dataset_from_file (temp_file)
    assert len (loaded) == 2
    assert loaded [0] ["id"] == "doc_1"
    assert loaded [1] ["source"] == "SciFact"

def test_corpus_index_with_dataset_records (tmp_path):
    passages = [
        {"id": "f_1", "title": "Eiffel", "source": "FEVER", "text": "The Eiffel Tower is located in Paris France."},
        {"id": "s_1", "title": "Vaccine", "source": "SciFact", "text": "Vaccines undergo randomized clinical trials."},
    ]
    cache_path = str (tmp_path / "cache.npy")
    index = CorpusIndex (passages, cache_file_path = cache_path)
    results = index.search ("Where is the Eiffel Tower located?", top_k = 1)
    assert len (results) == 1
    assert results [0].passage_id == "f_1"
    assert results [0].source == "FEVER"
    assert os.path.exists (cache_path)

def test_global_dataset_retrieve ():
    results = retrieve ("The COVID-19 vaccine and pregnancy", top_k = 1)
    assert len (results) >= 1
    assert results [0].source in ["SciFact", "FEVER", "Local corpus"]
