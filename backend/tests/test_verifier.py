from app.retrieval.searcher import RetrievedPassage
from app.verification.verifier import verify_claim

def test_verify_supported_claim ():
    claim = "The Eiffel Tower was completed in 1889."
    passage = RetrievedPassage (
        text = "The Eiffel Tower was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        source = "Local corpus",
        bm25_score = 15.8,
        embedding_score = 0.85,
        combined_score = 0.85,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60

def test_verify_refuted_claim ():
    claim = "The COVID-19 vaccine causes infertility in patients."
    passage = RetrievedPassage (
        text = "Clinical trials and observational studies of over 1.2 million individuals confirm that the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        source = "Local corpus",
        bm25_score = 12.4,
        embedding_score = 0.80,
        combined_score = 0.75,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Refuted"
    assert result.confidence >= 60

def test_verify_pregnant_women_case_is_supported ():
    claim = "The vaccine is safe for pregnant women."
    passage = RetrievedPassage (
        text = "No evidence indicates risk to pregnant women from vaccination.",
        source = "Local corpus",
        bm25_score = 14.0,
        embedding_score = 0.88,
        combined_score = 0.85,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60

def test_verify_morphological_negation_is_refuted ():
    claim = "The new treatment is ineffective."
    passage = RetrievedPassage (
        text = "Clinical trials confirm the treatment's effectiveness.",
        source = "Local corpus",
        bm25_score = 11.5,
        embedding_score = 0.82,
        combined_score = 0.80,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Refuted"
    assert result.confidence >= 60

def test_verify_negated_true_claim_is_supported ():
    claim = "The COVID-19 vaccine does not cause infertility."
    passage = RetrievedPassage (
        text = "Clinical trials and observational studies of over 1.2 million individuals confirm that the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        source = "Local corpus",
        bm25_score = 12.4,
        embedding_score = 0.80,
        combined_score = 0.75,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Supported"
    assert result.confidence >= 60

def test_verify_weak_evidence_returns_not_enough_evidence ():
    claim = "A newly launched phone shipped with a graphene battery this year."
    passage = RetrievedPassage (
        text = "Graphene is a single layer of carbon atoms arranged in a two-dimensional lattice.",
        source = "Local corpus",
        bm25_score = 2.1,
        embedding_score = 0.30,
        combined_score = 0.22,
    )
    result = verify_claim (claim, passage)
    assert result.verdict == "Not Enough Evidence"
    assert result.confidence <= 65

def test_verify_none_passage_returns_not_enough_evidence ():
    result = verify_claim ("Any random claim", None)
    assert result.verdict == "Not Enough Evidence"
    assert result.confidence == 40
