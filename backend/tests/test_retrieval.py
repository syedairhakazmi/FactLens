from app.retrieval.searcher import _tokenize, retrieve

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
