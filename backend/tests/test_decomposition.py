"""
Tests for app/decomposition/decomposer.py

Run from backend/:
    pytest tests/test_decomposition.py -v

Groups:
  1. Should split          - the patterns the baseline is built for
  2. Must NOT split        - single-fact sentences and deliberate non-splits
  3. Invariants            - properties every output must satisfy
  4. Known limitations     - marked xfail; they document what the rule-based
                             baseline can't do yet (XPASS is a pleasant surprise)
"""

import pytest

from app.decomposition.decomposer import decompose


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def norm(s: str) -> str:
    return s.lower().strip().rstrip(".!?").strip()


def has_claim(claims: list[str], expected: str) -> bool:
    """Exact (case/period-insensitive) match against any claim."""
    return any(norm(c) == norm(expected) for c in claims)


def any_contains(claims: list[str], *parts: str) -> bool:
    """True if a single claim contains ALL the given substrings."""
    return any(all(p.lower() in c.lower() for p in parts) for c in claims)


# ---------------------------------------------------------------------------
# 1. Should split
# ---------------------------------------------------------------------------

class TestShouldSplit:
    def test_two_clauses_with_comma_and(self):
        out = decompose(
            "The new vaccine was approved last week, and it causes infertility in most patients."
        )
        assert len(out) == 2
        assert any_contains(out, "approved", "last week")
        assert any_contains(out, "causes infertility")

    def test_clause_split_leaves_no_dangling_conjunction(self):
        out = decompose(
            "The new vaccine was approved last week, and it causes infertility in most patients."
        )
        for c in out:
            assert not norm(c).startswith(("and ", "but "))
            assert not c.rstrip(".").endswith(",")

    def test_shared_subject_is_copied(self):
        out = decompose("Barack Obama was born in Hawaii and served as the 44th president.")
        assert len(out) == 2
        assert all(c.startswith("Barack Obama") for c in out)
        assert any_contains(out, "born in Hawaii")
        assert any_contains(out, "served as", "president")

    def test_shared_subject_passive(self):
        out = decompose("Python was created by Guido van Rossum and released in 1991.")
        assert len(out) == 2
        assert any_contains(out, "Python", "created", "Guido van Rossum")
        assert any_contains(out, "Python", "released", "1991")

    def test_contrastive_but(self):
        out = decompose("The vaccine is effective, but it is not perfect.")
        assert len(out) == 2
        assert any_contains(out, "vaccine", "effective")
        assert any_contains(out, "not perfect")

    def test_appositive(self):
        out = decompose("Paris, the capital of France, hosts the Eiffel Tower.")
        assert has_claim(out, "Paris is the capital of France.")
        assert has_claim(out, "Paris hosts the Eiffel Tower.")

    def test_appositive_not_left_in_main_claim(self):
        out = decompose("Paris, the capital of France, hosts the Eiffel Tower.")
        # no single claim should still contain both facts
        assert not any_contains(out, "capital", "hosts")

    def test_nonrestrictive_relative_clause(self):
        out = decompose("The Eiffel Tower, which was built in 1889, is in Paris.")
        assert has_claim(out, "The Eiffel Tower was built in 1889.")
        assert has_claim(out, "The Eiffel Tower is in Paris.")

    def test_relative_clause_with_who(self):
        out = decompose("Marie Curie, who discovered polonium, was born in Warsaw.")
        assert any_contains(out, "Marie Curie", "discovered polonium")
        assert any_contains(out, "Marie Curie", "born in Warsaw")
        assert not any_contains(out, "who")

    def test_three_facts_chained(self):
        out = decompose(
            "Apple announced the iPhone 15 in September 2023, and it uses USB-C, "
            "and it has a titanium design."
        )
        assert len(out) >= 2
        assert any_contains(out, "announced", "iPhone 15")
        assert any_contains(out, "USB-C")

    def test_relative_clause_plus_coordinated_verbs(self):
        out = decompose(
            "Barack Obama, who was born in Hawaii, served as president "
            "and signed the Affordable Care Act."
        )
        assert any_contains(out, "Obama", "born in Hawaii")
        assert any_contains(out, "Obama", "served as president")
        assert any_contains(out, "Obama", "signed", "Affordable Care Act")

    def test_multi_sentence_input(self):
        out = decompose(
            "Water boils at 100 degrees Celsius. The Eiffel Tower was built in 1889."
        )
        assert len(out) == 2
        assert any_contains(out, "Water boils")
        assert any_contains(out, "Eiffel Tower", "1889")

    def test_multi_sentence_with_splits_in_each(self):
        out = decompose(
            "Paris, the capital of France, hosts the Eiffel Tower. "
            "The vaccine was approved, and it causes infertility."
        )
        assert len(out) >= 4


# ---------------------------------------------------------------------------
# 2. Must NOT split
# ---------------------------------------------------------------------------

class TestMustNotSplit:
    @pytest.mark.parametrize(
        "sentence",
        [
            "Water boils at 100 degrees Celsius at sea level.",
            "The Eiffel Tower was built in 1889.",
            "Python was first released in 1991.",
        ],
    )
    def test_simple_single_fact(self, sentence):
        out = decompose(sentence)
        assert len(out) == 1
        assert norm(out[0]) == norm(sentence)

    def test_coordinated_nouns_not_split(self):
        out = decompose("Marie Curie won Nobel Prizes in physics and chemistry.")
        assert len(out) == 1

    def test_coordinated_subjects_not_split(self):
        out = decompose("Tom and Jerry are cartoon characters.")
        assert len(out) == 1

    def test_coordinated_adjectives_not_split(self):
        out = decompose("The vaccine is safe and effective.")
        assert len(out) == 1

    def test_disjunction_not_split(self):
        out = decompose("The patient will receive either the vaccine or a placebo.")
        assert len(out) == 1

    def test_or_between_verbs_not_split(self):
        out = decompose("The drug increases or decreases blood pressure in some patients.")
        assert len(out) == 1

    def test_restrictive_relative_clause_kept_intact(self):
        sentence = "The man who stole the car fled the scene."
        out = decompose(sentence)
        assert len(out) == 1
        assert "stole the car" in out[0]

    def test_reported_speech_not_split(self):
        out = decompose("The minister said that the vaccine is safe and the trial was large.")
        assert len(out) == 1

    def test_shared_object_fragment_guard(self):
        # splitting would leave "He bought." which is not a claim
        out = decompose("He bought and sold stocks.")
        assert len(out) == 1
        assert "bought" in out[0] and "sold" in out[0]

    def test_abbreviation_and_decimal_do_not_break_sentence(self):
        out = decompose("Dr. Smith measured 3.5 mg of the drug.")
        assert len(out) == 1
        assert "3.5" in out[0]


# ---------------------------------------------------------------------------
# 3. Invariants
# ---------------------------------------------------------------------------

INVARIANT_INPUTS = [
    "Water boils at 100 degrees Celsius at sea level.",
    "The new vaccine was approved last week, and it causes infertility in most patients.",
    "Paris, the capital of France, hosts the Eiffel Tower.",
    "The Eiffel Tower, which was built in 1889, is in Paris.",
    "Barack Obama was born in Hawaii and served as the 44th president.",
    "He bought and sold stocks.",
    "Tom and Jerry are cartoon characters.",
    "Paris is large. London is larger, and it has more people.",
]


class TestInvariants:
    @pytest.mark.parametrize("sentence", INVARIANT_INPUTS)
    def test_never_empty_for_real_input(self, sentence):
        assert len(decompose(sentence)) >= 1

    @pytest.mark.parametrize("sentence", INVARIANT_INPUTS)
    def test_claims_are_well_formed(self, sentence):
        for c in decompose(sentence):
            assert c == c.strip()
            assert c[0].isupper(), f"not capitalised: {c!r}"
            assert c[-1] in ".!?", f"no terminal punctuation: {c!r}"
            assert len(c.split()) >= 3, f"fragment: {c!r}"
            assert "  " not in c, f"double space: {c!r}"
            assert " ," not in c, f"space before comma: {c!r}"

    @pytest.mark.parametrize("sentence", INVARIANT_INPUTS)
    def test_no_duplicate_claims(self, sentence):
        out = [norm(c) for c in decompose(sentence)]
        assert len(out) == len(set(out))

    @pytest.mark.parametrize("sentence", INVARIANT_INPUTS)
    def test_deterministic(self, sentence):
        assert decompose(sentence) == decompose(sentence)

    @pytest.mark.parametrize("text", ["", "   ", "\n\t"])
    def test_empty_input_returns_empty_list(self, text):
        assert decompose(text) == []

    @pytest.mark.parametrize("text", ["asdf qwerty", "???", "12345", "Yes."])
    def test_garbage_or_fragment_input_does_not_crash_or_vanish(self, text):
        out = decompose(text)
        assert isinstance(out, list)
        assert len(out) >= 1

    def test_very_long_input_does_not_crash(self):
        text = " ".join(["The vaccine was approved, and it works."] * 50)
        out = decompose(text)
        assert len(out) >= 1


# ---------------------------------------------------------------------------
# 4. Known limitations (documented gaps of the rule-based baseline)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="semicolon-joined clauses (parataxis) not handled yet", strict=False)
def test_semicolon_clauses():
    out = decompose("The vaccine was approved last week; it causes infertility in most patients.")
    assert len(out) == 2


@pytest.mark.xfail(reason="subordinate 'although' clauses not handled yet", strict=False)
def test_although_clause():
    out = decompose("Although the vaccine was approved, it causes infertility in most patients.")
    assert len(out) == 2


@pytest.mark.xfail(reason="participial modifiers ('founded in 1998 by...') not handled yet", strict=False)
def test_participial_modifier():
    out = decompose(
        "The company, founded in 1998 by two students, reported record profits "
        "and announced it would hire 500 workers."
    )
    assert len(out) >= 3


@pytest.mark.xfail(reason="coordinated subjects are not split into separate claims", strict=False)
def test_coordinated_subjects_split():
    out = decompose("Obama and Biden won the 2012 election.")
    assert len(out) == 2


@pytest.mark.xfail(reason="clauses nested inside reported speech not split", strict=False)
def test_nested_clause_in_reported_speech():
    out = decompose("The minister said that the vaccine was approved and it is safe.")
    assert len(out) >= 2