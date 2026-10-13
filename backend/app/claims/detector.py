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
    category: str = "Fact"

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
    # normalize repeated punctuation like !!! or ??? to prevent fragmented splitting
    normalized = text
    while "!!" in normalized:
        normalized = normalized.replace ("!!", "!")
    while "??" in normalized:
        normalized = normalized.replace ("??", "?")
    while ".." in normalized:
        normalized = normalized.replace ("..", ".")

    # if all uppercase shouting text with internal punctuation, normalize internal marks
    tokens = normalized.split ()
    if len (tokens) >= 3 and normalized.isupper ():
        cleaned_tokens = []
        for i, t in enumerate (tokens):
            if i < len (tokens) - 1:
                cleaned_tokens.append (t.replace ("!", "").replace ("?", "").replace (".", ""))
            else:
                cleaned_tokens.append (t)
        normalized = " ".join (cleaned_tokens)

    # split text into sentences using spacy
    nlp = _get_nlp ()
    doc = nlp (normalized)
    sentences = []
    for sent in doc.sents:
        cleaned = sent.text.strip ()
        if len (cleaned) > 0:
            sentences.append (cleaned)
    return sentences

def _rule_precheck (sentence):
    # filter out questions
    trimmed = sentence.strip ()
    if trimmed.endswith ("?"):
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = "Questions are inquiries rather than verifiable factual claims",
            category = "Non-Checkable",
        )

    # filter out imperative commands and invitations
    lowered = trimmed.lower ()
    imperatives = ["visit ", "please ", "check ", "go to ", "look at ", "tell me ", "remember ", "download ", "eat ", "buy "]
    for imp in imperatives:
        if lowered.startswith (imp):
            return ClassifiedSentence (
                text = sentence,
                is_checkable = False,
                reason = "Imperatives and requests are not factual claims",
                category = "Non-Checkable",
            )

    doc_pre = _get_nlp () (sentence)
    if len (doc_pre) > 0:
        first_token = doc_pre [0]
        has_subject = False
        for token in doc_pre:
            if "subj" in token.dep_:
                has_subject = True
                break
        if not has_subject and (first_token.pos_ == "VERB" or first_token.tag_ in ("VB", "VBP")):
            return ClassifiedSentence (
                text = sentence,
                is_checkable = False,
                reason = "Imperatives and requests are not factual claims",
                category = "Non-Checkable",
            )

    # filter out exclamatory opinion phrases
    if lowered.startswith ("what a ") or lowered.startswith ("what an "):
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = "Exclamatory phrase expresses subjective opinion",
            category = "Opinion",
        )

    # filter out incomplete fragments with fewer than 3 words (e.g. 'It is.', 'Yes.', 'i')
    clean_words = sentence.translate (str.maketrans ("", "", string.punctuation)).split ()
    if len (clean_words) < 3:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = "Sentence fragment is too brief to form a complete checkable assertion",
            category = "Non-Checkable",
        )

    # quick check for first person opinion phrases
    for opener in _SUBJECTIVE_OPENERS:
        if lowered.startswith (opener):
            return ClassifiedSentence (
                text = sentence,
                is_checkable = False,
                reason = f"Opens with first-person subjective framing ('{opener}')",
                category = "Opinion",
            )

    # verify that sentence contains at least one verb or copula
    doc = _get_nlp () (sentence)
    has_predicate = False
    for token in doc:
        if token.pos_ in ("VERB", "AUX"):
            has_predicate = True
            break
    if not has_predicate and sentence.isupper ():
        for token in _get_nlp () (sentence.lower ()):
            if token.pos_ in ("VERB", "AUX"):
                has_predicate = True
                break
    if not has_predicate:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = "Sentence lacks a verb or predicate to form a checkable assertion",
            category = "Non-Checkable",
        )

    # verify that sentence contains meaningful content words
    has_content = False
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN", "VERB", "ADJ", "NUM"):
            has_content = True
            break
    if not has_content and sentence.isupper ():
        for token in _get_nlp () (sentence.lower ()):
            if token.pos_ in ("NOUN", "PROPN", "VERB", "ADJ", "NUM"):
                has_content = True
                break
    if not has_content:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = False,
            reason = "Sentence lacks content words (nouns, adjectives, or verbs) to form a meaningful assertion",
            category = "Non-Checkable",
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
            category = "Opinion",
        )
    return ClassifiedSentence (
        text = sentence,
        is_checkable = True,
        reason = "No opinion markers detected, treated as a checkable claim (offline rule fallback)",
        category = "Fact",
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
            category = "Opinion",
        )
    else:
        return ClassifiedSentence (
            text = sentence,
            is_checkable = True,
            reason = f"Subjectivity model classified this as objective ({1 - subjectivity_score:.0%} objective)",
            subjectivity_score = subjectivity_score,
            category = "Fact",
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
            prepared_sentences = []
            for s in pending_sentences:
                cleaned_item = s.strip ()
                if len (cleaned_item) > 0:
                    cleaned_item = cleaned_item [0].upper () + cleaned_item [1:]
                    if not cleaned_item.endswith (".") and not cleaned_item.endswith ("?") and not cleaned_item.endswith ("!"):
                        cleaned_item = cleaned_item + "."
                prepared_sentences.append (cleaned_item)

            unique_prepared = []
            for item in prepared_sentences:
                if item not in unique_prepared:
                    unique_prepared.append (item)

            unique_scores = model (unique_prepared)
            score_cache = {}
            u_index = 0
            for item in unique_prepared:
                score_cache [item] = unique_scores [u_index]
                u_index = u_index + 1

            pos = 0
            for prep in prepared_sentences:
                target_idx = pending_indices [pos]
                scores = score_cache [prep]
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
