"""
Tests for the retrieval module's tokenizer.

These specifically test the two real bugs found and fixed during
development, not hypothetical edge cases:

1. Punctuation wasn't being stripped, so "patients." never matched
   "patients" anywhere in the corpus.
2. Common stopwords weren't being removed, which let BM25's IDF
   weighting get thrown off on small corpora, "in" was once scored
   as more important than "vaccine" for exactly this reason.
"""

from app.retrieval.searcher import _tokenize, retrieve


def test_tokenizer_strips_punctuation():
    """
    'patients.' must tokenize the same as 'patients', otherwise a
    trailing period silently breaks every match against that word.
    """
    tokens = _tokenize("The vaccine causes infertility in most patients.")
    assert "patients" in tokens
    assert "patients." not in tokens


def test_tokenizer_lowercases():
    tokens = _tokenize("The Vaccine Causes Infertility")
    assert "vaccine" in tokens
    assert "Vaccine" not in tokens


def test_tokenizer_removes_stopwords():
    """
    Common words like 'the' and 'in' must not appear in the token
    list, they distort BM25's IDF weighting, especially on small
    corpora, and carry no real search meaning.
    """
    tokens = _tokenize("The vaccine was approved in the trial.")
    assert "the" not in tokens
    assert "in" not in tokens
    assert "was" not in tokens
    assert "vaccine" in tokens
    assert "approved" in tokens
    assert "trial" in tokens


def test_tokenizer_handles_multiple_punctuation_marks():
    tokens = _tokenize("Really?! The claim, allegedly, is false.")
    assert "really" in tokens
    assert "claim" in tokens
    assert "allegedly" in tokens
    assert "false" in tokens
    # nothing should retain punctuation
    assert all(t.isalnum() for t in tokens)


def test_retrieve_ranks_relevant_passage_above_irrelevant_one():
    """
    End-to-end check: given a vaccine-related query, a vaccine-related
    passage must outrank a completely unrelated one (Eiffel Tower).
    This is the exact scenario that surfaced both bugs above, kept as
    a regression test so neither bug can silently come back.
    """
    corpus = [
        ("The Eiffel Tower, located in Paris, France, was completed in 1889.", "wiki"),
        ("The vaccine received regulatory approval after completing clinical trials.", "fever"),
    ]
    results = retrieve("The vaccine causes infertility in most patients.", corpus, top_k=2)

    assert results[0].source == "fever", (
        "The vaccine-related passage should rank first, if the Eiffel Tower "
        "passage wins, the tokenizer or BM25 configuration has regressed."
    )


def test_retrieve_returns_empty_list_for_empty_corpus():
    assert retrieve("any query", [], top_k=3) == []
