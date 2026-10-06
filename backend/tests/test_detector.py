"""
Tests for fact/opinion detection and claim extraction.

Includes a regression test for a real bug found during development:
"He is a good boy" was wrongly classified as checkable, the opinion
pattern only handled "is the <adjective>", not "is a <adjective>".
"""

from app.claims.detector import classify, extract_claims, extract_sentences


def test_extract_sentences_splits_correctly():
    sentences = extract_sentences("Ali is a good boy. He is fat.")
    assert sentences == ["Ali is a good boy.", "He is fat."]


def test_opinion_with_article_is_caught():
    """
    Regression test: 'is a good' was not being matched before the fix,
    only 'is the good' style phrasing was. Keep this test so the bug
    cannot silently come back.
    """
    result = classify("He is a good boy.")
    assert result.is_checkable is False


def test_opinion_without_article_is_caught():
    result = classify("This woman is evil.")
    assert result.is_checkable is False


def test_first_person_opener_is_caught():
    result = classify("I think the president did a great job this year.")
    assert result.is_checkable is False


def test_subjective_opinion_is_caught():
    result = classify("This restaurant is terrible.")
    assert result.is_checkable is False


def test_rule_fallback_catches_copula_opinion():
    from app.claims.detector import _rule_fallback
    result = _rule_fallback("This is the best restaurant in the city.")
    assert result.is_checkable is False


def test_neutral_factual_sentence_is_checkable():
    """
    A sentence containing 'is' followed by a proper noun must not be
    falsely flagged as an opinion just because it uses a copula verb.
    """
    result = classify("The capital of France is Paris.")
    assert result.is_checkable is True


def test_harmful_but_factual_claim_stays_checkable():
    """
    A claim can be false or harmful and still be a checkable factual
    claim, not an opinion, that distinction matters, being wrong is
    not the same as being subjective.
    """
    result = classify("The new vaccine causes infertility in most patients.")
    assert result.is_checkable is True


def test_extract_claims_end_to_end():
    results = extract_claims("Ali is a good boy. He is fat.")
    assert len(results) == 2
    assert results[0].is_checkable is False  # "Ali is a good boy."
    assert results[1].is_checkable is True   # "He is fat."