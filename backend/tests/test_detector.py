from app.claims.detector import classify, extract_claims, extract_sentences, _rule_fallback

def test_extract_sentences_splits_correctly ():
    sentences = extract_sentences ("Ali is a good boy. He is fat.")
    assert sentences == ["Ali is a good boy.", "He is fat."]

def test_opinion_with_article_is_caught ():
    result = classify ("He is a good boy.")
    assert result.is_checkable is False

def test_opinion_without_article_is_caught ():
    result = classify ("This woman is evil.")
    assert result.is_checkable is False

def test_first_person_opener_is_caught ():
    result = classify ("I think the president did a great job this year.")
    assert result.is_checkable is False

def test_subjective_opinion_is_caught ():
    result = classify ("This restaurant is terrible.")
    assert result.is_checkable is False

def test_rule_fallback_catches_copula_opinion ():
    result = _rule_fallback ("This is the best restaurant in the city.")
    assert result.is_checkable is False

def test_neutral_factual_sentence_is_checkable ():
    result = classify ("The capital of France is Paris.")
    assert result.is_checkable is True

def test_harmful_but_factual_claim_stays_checkable ():
    result = classify ("The new vaccine causes infertility in most patients.")
    assert result.is_checkable is True

def test_extract_claims_end_to_end ():
    results = extract_claims ("Ali is a good boy. He is fat.")
    assert len (results) == 2
    assert results [0].is_checkable is False
    assert results [1].is_checkable is True