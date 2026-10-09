import os
import json
from app.retrieval.searcher import (
    _tokenize,
    retrieve,
    load_dataset_from_file,
    save_dataset_to_file,
    CorpusIndex,
    load_scifact_corpus,
    load_fever_claims,
    load_averitec_claims,
    load_feverous_claims,
    merge_all_datasets,
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

def test_load_scifact_corpus (tmp_path):
    # create a fake scifact corpus file with abstract as list
    corpus_file = str (tmp_path / "corpus.jsonl")
    with open (corpus_file, "w", encoding = "utf-8") as f:
        entry = {"doc_id": 101, "title": "Brain Study", "abstract": ["First sentence.", "Second sentence."], "structured": False}
        f.write (json.dumps (entry) + "\n")
        entry2 = {"doc_id": 102, "title": "Cancer Research", "abstract": ["Cancer is a disease."], "structured": True}
        f.write (json.dumps (entry2) + "\n")
    passages = load_scifact_corpus (corpus_file)
    assert len (passages) == 2
    assert passages [0] ["id"] == "scifact_101"
    assert passages [0] ["source"] == "SciFact"
    assert "First sentence. Second sentence." in passages [0] ["text"]
    assert passages [1] ["title"] == "Cancer Research"

def test_load_fever_claims (tmp_path):
    # create a fake fever file with claims and labels
    fever_file = str (tmp_path / "fever.jsonl")
    with open (fever_file, "w", encoding = "utf-8") as f:
        entry = {"id": 999, "verifiable": "VERIFIABLE", "label": "SUPPORTS", "claim": "The Earth is round.", "evidence": []}
        f.write (json.dumps (entry) + "\n")
        entry2 = {"id": 1000, "verifiable": "VERIFIABLE", "label": "REFUTES", "claim": "The Sun orbits Earth.", "evidence": []}
        f.write (json.dumps (entry2) + "\n")
    passages = load_fever_claims (fever_file, "FEVER 2018")
    assert len (passages) == 2
    assert passages [0] ["id"] == "fever_2018_999"
    assert passages [0] ["title"] == "SUPPORTS"
    assert passages [0] ["text"] == "The Earth is round."
    assert passages [1] ["source"] == "FEVER 2018"

def test_load_averitec_claims (tmp_path):
    # create a fake averitec json file with claims and justifications
    averitec_file = str (tmp_path / "averitec.json")
    data = [
        {"claim": "Vaccines cause autism.", "label": "Refuted", "justification": "No scientific evidence supports this."},
        {"claim": "Water is wet.", "label": "Supported", "justification": ""},
    ]
    with open (averitec_file, "w", encoding = "utf-8") as f:
        json.dump (data, f)
    passages = load_averitec_claims (averitec_file, "AVeriTeC 2024")
    assert len (passages) == 2
    assert "No scientific evidence supports this." in passages [0] ["text"]
    assert passages [1] ["text"] == "Water is wet."

def test_merge_removes_duplicates (tmp_path):
    # create a minimal folder with two datasets that have a duplicate claim
    fever_file = str (tmp_path / "train_fever.jsonl")
    with open (fever_file, "w", encoding = "utf-8") as f:
        f.write (json.dumps ({"id": 1, "label": "SUPPORTS", "claim": "Duplicate claim here."}) + "\n")
        f.write (json.dumps ({"id": 2, "label": "REFUTES", "claim": "Unique fever claim."}) + "\n")
    averitec_file = str (tmp_path / "train_averitec.json")
    with open (averitec_file, "w", encoding = "utf-8") as f:
        json.dump ([{"claim": "duplicate claim here.", "label": "Supported", "justification": ""}], f)
    merged = merge_all_datasets (str (tmp_path))
    texts = []
    for p in merged:
        texts.append (p ["text"].lower ())
    duplicate_count = texts.count ("duplicate claim here.")
    assert duplicate_count == 1
