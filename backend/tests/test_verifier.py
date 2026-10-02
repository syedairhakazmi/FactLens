"""
Unit tests for the verification module (backend/app/verification/verifier.py).
"""

from app.retrieval.searcher import RetrievedPassage
from app.verification.verifier import verify_claim


def test_verify_supported_claim():
    claim = "The Eiffel Tower was completed in 1889."
    passage = RetrievedPassage(
        text="The Eiffel Tower was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        source="FEVER corpus (ID: 10839)",
        bm25_score=15.8,
        embedding_score=0.85,
        combined_score=0.85,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 75
    assert "1889" in result.evidence_text


def test_verify_refuted_claim():
    claim = "The COVID-19 vaccine causes infertility in patients."
    passage = RetrievedPassage(
        text="Clinical trials of over 1.2 million individuals found no statistically significant link between mRNA vaccines and fertility outcomes.",
        source="SciFact corpus (ID: 4128)",
        bm25_score=12.4,
        embedding_score=0.80,
        combined_score=0.75,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Refuted"
    assert result.confidence >= 75


def test_verify_negated_true_claim_is_supported():
    """
    CRITICAL EDGE CASE (flagged by code review):
    A true claim containing negation words ('does not cause infertility')
    must be SUPPORTED when the evidence confirms the absence of a link,
    rather than being mistakenly flipped to Refuted.
    """
    claim = "The COVID-19 vaccine does not cause infertility."
    passage = RetrievedPassage(
        text="Clinical trials of over 1.2 million individuals found no statistically significant link between mRNA vaccines and fertility outcomes.",
        source="SciFact corpus (ID: 4128)",
        bm25_score=12.4,
        embedding_score=0.80,
        combined_score=0.75,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 75


def test_verify_weak_evidence_returns_not_enough_evidence():
    claim = "A newly launched phone shipped with a graphene battery this year."
    passage = RetrievedPassage(
        text="Graphene is a single layer of carbon atoms arranged in a two-dimensional lattice.",
        source="SciFact corpus (ID: 8820)",
        bm25_score=2.1,
        embedding_score=0.30,
        combined_score=0.22,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Not Enough Evidence"
    assert result.confidence <= 65


def test_verify_none_passage_returns_not_enough_evidence():
    result = verify_claim("Any random claim", None)
    assert result.verdict == "Not Enough Evidence"
    assert result.confidence == 40
