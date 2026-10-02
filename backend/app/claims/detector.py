"""
Fact/opinion detection and claim extraction module. Owner: Areesha.

Two jobs, done together because they operate on the same sentence-level
unit:

1. Claim extraction: split input text into individual sentences, the
   unit everything downstream (decomposition, retrieval, verification)
   operates on.
2. Fact/opinion classification: decide which of those sentences are
   actually checkable factual claims versus subjective opinions that
   shouldn't be sent to the fact-checking pipeline at all.

This is a RULE-BASED baseline, matching the Work Division table's
Iteration 1 plan ("Rule based decomposition module" / baseline). It is
not a trained classifier, the same category of tool as ClaimBuster
(cited in Slide 5), which also uses engineered signals rather than a
model to flag checkworthy sentences.

The specific failure case this exists to catch: "This woman is evil" is
an opinion, not a checkable claim, there is no evidence corpus that can
confirm or deny whether someone is "evil". Sending opinions into the
fact-checking pipeline produces nonsense verdicts, this module is the
filter that stops that before it happens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import spacy

# Sentences matching "<subject> <copula> <subjective word>" are opinions,
# not checkable claims. This list intentionally mirrors the pattern used
# in the FactLens prototype's mock logic, so the real pipeline and the
# demo prototype agree on what counts as an opinion.
_SUBJECTIVE_ADJECTIVES = {
    "good", "evil", "stupid", "ugly", "dumb", "awesome", "amazing",
    "beautiful", "gorgeous", "hideous", "disgusting", "terrible",
    "horrible", "wonderful", "awful", "pathetic", "incredible",
    "fantastic", "great", "worst", "best",
}

# Sentences that open with first-person subjective framing are opinions
# regardless of what follows, "I think the economy will improve" is a
# prediction/opinion, not a checkable fact, even though "the economy
# will improve" alone might look claim-shaped.
_SUBJECTIVE_OPENERS = (
    "i think", "i believe", "i feel", "in my opinion", "i reckon",
    "personally,", "i'd say", "i would say",
)

_COPULA_OPINION_PATTERN = re.compile(
    r"\b(is|are|was|were)\s+(a\s+|an\s+|the\s+)?(" + "|".join(_SUBJECTIVE_ADJECTIVES) + r")\b",
    re.IGNORECASE,
)


@dataclass
class ClassifiedSentence:
    text: str
    is_checkable: bool
    reason: str


@lru_cache(maxsize=1)
def _get_nlp():
    return spacy.load("en_core_web_sm")


def extract_sentences(text: str) -> list[str]:
    """
    Splits input text into individual sentences using spaCy's sentence
    boundary detection, rather than naively splitting on periods, which
    breaks on abbreviations, decimals, and initials.
    """
    nlp = _get_nlp()
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def classify(sentence: str) -> ClassifiedSentence:
    """
    Decides whether a single sentence is a checkable factual claim or
    a subjective opinion. Checkable sentences proceed to decomposition
    and retrieval, opinions are set aside with a reason explaining why.
    """
    lowered = sentence.lower().strip()

    for opener in _SUBJECTIVE_OPENERS:
        if lowered.startswith(opener):
            return ClassifiedSentence(
                text=sentence,
                is_checkable=False,
                reason=f"Opens with first-person subjective framing ('{opener}')",
            )

    match = _COPULA_OPINION_PATTERN.search(lowered)
    if match:
        return ClassifiedSentence(
            text=sentence,
            is_checkable=False,
            reason=f"Matches opinion pattern: '{match.group(0)}'",
        )

    return ClassifiedSentence(
        text=sentence,
        is_checkable=True,
        reason="No opinion markers detected, treated as a checkable claim",
    )


def extract_claims(text: str) -> list[ClassifiedSentence]:
    """
    The main entry point other modules should call: splits text into
    sentences and classifies each one. Only sentences where
    is_checkable is True should be passed on to decomposition.
    """
    return [classify(s) for s in extract_sentences(text)]


if __name__ == "__main__":
    samples = [
        "This woman is evil.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
        "I think the president did a great job this year.",
        "Water boils at 100 degrees Celsius at sea level.",
        "This is the best restaurant in the city.",
    ]
    for s in samples:
        for result in extract_claims(s):
            status = "CHECKABLE" if result.is_checkable else "OPINION"
            print(f"[{status}] {result.text}")
            print(f"   reason: {result.reason}")
        print()
