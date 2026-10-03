"""
Unit tests for the NLI CrossEncoder verification module (backend/app/verification/verifier.py).
Tests true generalization across phrasing, polarity, and morphological negation.
"""

from app.retrieval.searcher import RetrievedPassage
from app.verification.verifier import verify_claim


def test_verify_supported_claim():
    claim = "The Eiffel Tower was completed in 1889."
    passage = RetrievedPassage(
        text="The Eiffel Tower was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        source="FEVER starter seed (ID: 10839)",
        bm25_score=15.8,
        embedding_score=0.85,
        combined_score=0.85,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60


def test_verify_refuted_claim():
    claim = "The COVID-19 vaccine causes infertility in patients."
    passage = RetrievedPassage(
        text="Clinical trials and observational studies of over 1.2 million individuals confirm that the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        source="SciFact starter seed (ID: 4128)",
        bm25_score=12.4,
        embedding_score=0.80,
        combined_score=0.75,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Refuted"
    assert result.confidence >= 60


def test_verify_pregnant_women_case_is_supported():
    """
    CRITICAL GENERALIZATION TEST (from code review):
    Claim: "The vaccine is safe for pregnant women." (no negation word)
    Evidence: "No evidence indicates risk to pregnant women from vaccination." (evidence contains negation)
    The NLI model must recognize this as ENTAILMENT -> Supported,
    not mistakenly fall through to Refuted.
    """
    claim = "The vaccine is safe for pregnant women."
    passage = RetrievedPassage(
        text="No evidence indicates risk to pregnant women from vaccination.",
        source="SciFact starter seed (ID: 5501)",
        bm25_score=14.0,
        embedding_score=0.88,
        combined_score=0.85,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60


def test_verify_morphological_negation_is_refuted():
    """
    CRITICAL GENERALIZATION TEST (from code review):
    Claim: "The new treatment is ineffective."
    Evidence: "Clinical trials confirm the treatment's effectiveness."
    Uses morphological negation ('ineffective') with zero literal 'not/no/never'.
    The NLI model must recognize this as CONTRADICTION -> Refuted.
    """
    claim = "The new treatment is ineffective."
    passage = RetrievedPassage(
        text="Clinical trials confirm the treatment's effectiveness.",
        source="SciFact starter seed (ID: 7712)",
        bm25_score=11.5,
        embedding_score=0.82,
        combined_score=0.80,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Refuted"
    assert result.confidence >= 60


def test_verify_negated_true_claim_is_supported():
    """
    A true claim containing negation words ('does not cause infertility')
    must be SUPPORTED when the evidence confirms the absence of a link.
    """
    claim = "The COVID-19 vaccine does not cause infertility."
    passage = RetrievedPassage(
        text="Clinical trials and observational studies of over 1.2 million individuals confirm that the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        source="SciFact starter seed (ID: 4128)",
        bm25_score=12.4,
        embedding_score=0.80,
        combined_score=0.75,
    )
    result = verify_claim(claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60


def test_verify_weak_evidence_returns_not_enough_evidence():
    claim = "A newly launched phone shipped with a graphene battery this year."
    passage = RetrievedPassage(
        text="Graphene is a single layer of carbon atoms arranged in a two-dimensional lattice.",
        source="SciFact starter seed (ID: 8820)",
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
