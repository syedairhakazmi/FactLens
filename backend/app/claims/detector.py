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

Classification is a HYBRID of a cheap rule pre-check and a trained model:

  a. Rule pre-check: sentences opening with first-person subjective
     framing ("I think", "In my opinion", ...) are opinions, no model
     call needed.
  b. Model: everything else is scored by GroNLP/mdebertav3-subjectivity-
     english, an mDeBERTa-v3 model fine-tuned for the CLEF 2023
     CheckThat! Lab Task 2 (Subjectivity in News Articles), where it
     ranked 3rd (macro F1 0.77). It judges the whole sentence, so it
     isn't limited to a fixed list of opinion words the way the original
     rule-based baseline was.

The original rule-based baseline (subjective-adjective regex) is kept as
an offline fallback only, used when the model can't be loaded.

Note on "objective": a FALSE claim is still objective. "The vaccine
causes infertility" is checkable, it should pass through here so that
retrieval and verification can refute it. Subjectivity is about whether
a statement can be checked at all, not whether it's true.

The specific failure case this exists to catch: "This woman is evil" is
an opinion, not a checkable claim, there is no evidence corpus that can
confirm or deny whether someone is "evil". Sending opinions into the
fact-checking pipeline produces nonsense verdicts, this module is the
filter that stops that before it happens.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

import spacy

logger = logging.getLogger("factlens")

_SUBJECTIVITY_MODEL = "GroNLP/mdebertav3-subjectivity-english"

# The model's config has no label names, it outputs LABEL_0 / LABEL_1.
# Verified empirically on clear-cut examples: LABEL_1 = subjective (SUBJ),
# LABEL_0 = objective (OBJ).
_SUBJ_LABEL = "LABEL_1"

# A sentence is treated as an opinion when the model's SUBJ probability
# reaches this value. 0.5 = plain argmax. Tunable: raise it to let more
# borderline sentences through to fact-checking, lower it to filter more
# aggressively. Worth sweeping once labelled evaluation data is wired in.
SUBJECTIVITY_THRESHOLD = 0.5

# Sentences that open with first-person subjective framing are opinions
# regardless of what follows, "I think the economy will improve" is a
# prediction/opinion, not a checkable fact, even though "the economy
# will improve" alone might look claim-shaped.
_SUBJECTIVE_OPENERS = (
    "i think", "i believe", "i feel", "in my opinion", "i reckon",
    "personally,", "i'd say", "i would say",
)

# --- Offline fallback only (used when the model can't be loaded) ---
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

_COPULA_OPINION_PATTERN = re.compile(
    r"\b(is|are|was|were)\s+(a\s+|an\s+|the\s+)?(" + "|".join(_SUBJECTIVE_ADJECTIVES) + r")\b",
    re.IGNORECASE,
)


@dataclass
class ClassifiedSentence:
    text: str
    is_checkable: bool
    reason: str
    # Model's probability that the sentence is subjective, None when the
    # decision came from a rule rather than the model.
    subjectivity_score: float | None = None


@lru_cache(maxsize=1)
def _get_nlp():
    return spacy.load("en_core_web_sm")


@lru_cache(maxsize=1)
def _get_model():
    """
    Loads the subjectivity classifier once per process. Returns None if
    it can't be loaded (e.g. no internet on first run), so callers fall
    back to the rule-based baseline instead of crashing.
    """
    try:
        from transformers import pipeline
        return pipeline("text-classification", model=_SUBJECTIVITY_MODEL, top_k=None)
    except Exception as exc:
        logger.warning("Could not load subjectivity model, using rule fallback: %s", exc)
        return None


def extract_sentences(text: str) -> list[str]:
    """
    Splits input text into individual sentences using spaCy's sentence
    boundary detection, rather than naively splitting on periods, which
    breaks on abbreviations, decimals, and initials.
    """
    nlp = _get_nlp()
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def _rule_precheck(sentence: str) -> ClassifiedSentence | None:
    """Obvious first-person opinions, no model call needed."""
    lowered = sentence.lower().strip()
    for opener in _SUBJECTIVE_OPENERS:
        if lowered.startswith(opener):
            return ClassifiedSentence(
                text=sentence,
                is_checkable=False,
                reason=f"Opens with first-person subjective framing ('{opener}')",
            )
    return None


def _rule_fallback(sentence: str) -> ClassifiedSentence:
    """Original rule-based baseline, used only when the model is unavailable."""
    match = _COPULA_OPINION_PATTERN.search(sentence.lower())
    if match:
        return ClassifiedSentence(
            text=sentence,
            is_checkable=False,
            reason=f"Matches opinion pattern: '{match.group(0)}' (offline rule fallback)",
        )
    return ClassifiedSentence(
        text=sentence,
        is_checkable=True,
        reason="No opinion markers detected, treated as a checkable claim (offline rule fallback)",
    )


def _from_model_scores(sentence: str, scores: list[dict]) -> ClassifiedSentence:
    subj = next((d["score"] for d in scores if d["label"] == _SUBJ_LABEL), 0.0)
    if subj >= SUBJECTIVITY_THRESHOLD:
        return ClassifiedSentence(
            text=sentence,
            is_checkable=False,
            reason=f"Subjectivity model classified this as an opinion ({subj:.0%} subjective)",
            subjectivity_score=subj,
        )
    return ClassifiedSentence(
        text=sentence,
        is_checkable=True,
        reason=f"Subjectivity model classified this as objective ({1 - subj:.0%} objective)",
        subjectivity_score=subj,
    )


def classify_many(sentences: list[str]) -> list[ClassifiedSentence]:
    """
    Classifies a batch of sentences. Sentences caught by the rule
    pre-check skip the model, the rest are scored in a single batched
    model call, which is much faster than one call per sentence.
    """
    results: list[ClassifiedSentence | None] = [_rule_precheck(s) for s in sentences]
    pending = [i for i, r in enumerate(results) if r is None]

    if pending:
        model = _get_model()
        if model is None:
            for i in pending:
                results[i] = _rule_fallback(sentences[i])
        else:
            batch_scores = model([sentences[i] for i in pending])
            for i, scores in zip(pending, batch_scores):
                results[i] = _from_model_scores(sentences[i], scores)

    return results  # type: ignore[return-value]


def classify(sentence: str) -> ClassifiedSentence:
    """
    Decides whether a single sentence is a checkable factual claim or
    a subjective opinion. Checkable sentences proceed to decomposition
    and retrieval, opinions are set aside with a reason explaining why.
    """
    return classify_many([sentence])[0]


def extract_claims(text: str) -> list[ClassifiedSentence]:
    """
    The main entry point other modules should call: splits text into
    sentences and classifies each one. Only sentences where
    is_checkable is True should be passed on to decomposition.
    """
    return classify_many(extract_sentences(text))


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
