import string
import logging
from dataclasses import dataclass
from functools import lru_cache
import spacy

logger = logging.getLogger ("factlens")

_SUBJECTIVITY_MODEL = "GroNLP/mdebertav3-subjectivity-english"
_SUBJ_LABEL = "LABEL_1"
SUBJECTIVITY_THRESHOLD = 0.5

_SUBJECTIVE_OPENERS = (
    "i think", "i believe", "i feel", "in my opinion", "i reckon",
    "personally,", "i'd say", "i would say",
)

_SUBJECTIVE_ADJECTIVES = {
    "good", "evil", "stupid", "ugly", "dumb", "awesome", "amazing",
    "beautiful", "gorgeous", "hideous", "disgusting", "terrible",
    "horrible", "wonderful", "awful", "pathetic", "incredible",
    "fantastic", "great", "worst", "best",
}

@dataclass
class ClassifiedSentence:
    text: str
    is_checkable: bool
    reason: str
    subjectivity_score: float | None = None

@lru_cache (maxsize = 1)
def _get_nlp ():
    return spacy.load ("en_core_web_sm")

@lru_cache (maxsize = 1)
def _get_model ():
    try:
        from transformers import pipeline
        return pipeline ("text-classification", model = _SUBJECTIVITY_MODEL, top_k = None)
    except Exception as exc:
        logger.warning ("could not load subjectivity model: %s", exc)
        return None

def extract_sentences (text):
    # split text into sentences using spacy
    nlp = _get_nlp ()
    doc = nlp (text)
    sentences = []
    for sent in doc.sents:
        cleaned = sent.text.strip ()
        if len (cleaned) > 0:
            sentences.append (cleaned)
    return sentences

def _rule_precheck (sentence):
    # quick check for first person opinion phrases
    lowered = sentence.lower ().strip ()
    for opener in _SUBJECTIVE_OPENERS:
        if lowered.startswith (opener):
            return ClassifiedSentence (
                text = sentence,
                is_checkable = False,
                reason = f"Opens with first-person subjective framing ('{opener}')",
            )
    return None

def _rule_fallback (sentence):
    # fallback check if model is not available
    clean_text = sentence.lower ()
    for symbol in string.punctuation:
        clean_text = clean_text.replace (symbol, " ")
    words = clean_text.split ()

    copula_words = ["is", "are", "was", "were"]
    articles = ["a", "an", "the"]

    found_opinion = False
    matched_word = ""

    total_words = len (words)
    index = 0
    while index < total_words:
        word = words [index]
        if word in copula_words:
            if index + 1 < total_words:
                next_word = words [index + 1]
                if next_word in _SUBJECTIVE_ADJECTIVES:
                    found_opinion = True
                    matched_word = f"{word} {next_word}"
                    break
                elif next_word in articles and index + 2 < total_words:
                    third_word = words [index + 2]
                    if third_word in _SUBJECTIVE_ADJECTIVES:
                        found_opinion = True
                        matched_word = f"{word} {next_word} {third_word}"
                        break
        index = index + 1

    if found_opinion:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = f"Matches opinion pattern: '{matched_word}' (offline rule fallback)",
        )
    return ClassifiedSentence (
        text = sentence,
        is_checkable = True,
        reason = "No opinion markers detected, treated as a checkable claim (offline rule fallback)",
    )

def _from_model_scores (sentence, scores):
    # check model probability for subjectivity
    subjectivity_score = 0.0
    for entry in scores:
        if entry ["label"] == _SUBJ_LABEL:
            subjectivity_score = entry ["score"]
            break

    if subjectivity_score >= SUBJECTIVITY_THRESHOLD:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = f"Subjectivity model classified this as an opinion ({subjectivity_score:.0%} subjective)",
            subjectivity_score = subjectivity_score,
        )
    else:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = True,
            reason = f"Subjectivity model classified this as objective ({1 - subjectivity_score:.0%} objective)",
            subjectivity_score = subjectivity_score,
        )

def classify_many (sentences):
    # run rule check first and model on the rest
    results = []
    pending_sentences = []
    pending_indices = []

    index = 0
    for sentence in sentences:
        precheck_result = _rule_precheck (sentence)
        if precheck_result is not None:
            results.append (precheck_result)
        else:
            results.append (None)
            pending_sentences.append (sentence)
            pending_indices.append (index)
        index = index + 1

    if len (pending_sentences) > 0:
        model = _get_model ()
        if model is None:
            for idx in pending_indices:
                results [idx] = _rule_fallback (sentences [idx])
        else:
            batch_scores = model (pending_sentences)
            pos = 0
            for scores in batch_scores:
                target_idx = pending_indices [pos]
                results [target_idx] = _from_model_scores (sentences [target_idx], scores)
                pos = pos + 1

    return results

def classify (sentence):
    return classify_many ([sentence]) [0]

def extract_claims (text):
    sentences = extract_sentences (text)
    return classify_many (sentences)

if __name__ == "__main__":
    samples = [
        "This woman is evil.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
        "I think the president did a great job this year.",
        "Water boils at 100 degrees Celsius at sea level.",
        "This is the best restaurant in the city.",
    ]
    for s in samples:
        for result in extract_claims (s):
            status = "CHECKABLE" if result.is_checkable else "OPINION"
            print (f"[{status}] {result.text}")
            print (f"   reason: {result.reason}")
        print ()
